from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from requests.exceptions import ChunkedEncodingError
from data.models import (
    DrugLabel,
    LabelProduct,
    ProductSection,
)
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import re
import datetime
import pandas as pd
import time
import logging
import random

logger = logging.getLogger(__name__)

EMA_EPAR_EXCEL_URL = "https://www.ema.europa.eu/sites/default/files/Medicines_output_european_public_assessment_reports.xlsx"


class EmaSectionRe:
    """Use regular expressions to parse the Sections from the text"""

    def __init__(self, pattern, name):
        """
        Args:
            pattern: re pattern to use to match a section
            name: section_name for inserting into the db
        """
        self.prog = re.compile(pattern, re.DOTALL)
        self.name = name
        self.end_idx = -1

    def find_match(self, text, start_idx):
        """
        Args:
            text: the string to search
            start_idx: the start index for where to start the search

        Returns: The section_text matched or None
        """
        match = self.prog.search(text, start_idx)
        if match:
            self.end_idx = match.end(2)
            return match[2]
        else:
            return None

    def get_end_idx(self):
        """
        Returns: The end index for the match. Or -1 if there was no match.
        """
        return self.end_idx


# these should be in order of how they appear in the pdf
EMA_PDF_PRODUCT_SECTIONS = [
    # notes for the re pattern:
    # escape the period we want to match e.g. "1.0" => r"1\.0"
    # look for one or more whitespace characters r"\s+"
    # find any characters (one or more times) r"(.+)" with re.DOTALL flag
    # stop when we find the closing string
    EmaSectionRe(
        r"(4\.1\s+Therapeutic indications)(.+)(4\.2\s+Posology and method of administration)",
        "Indications",
    ),
    EmaSectionRe(
        r"(4\.2\s+Posology and method of administration)(.+)(4\.3\s+Contraindications)",
        "Posology",
    ),
    EmaSectionRe(
        r"(4\.3\s+Contraindications)(.+)(4\.4\s+Special warnings and precautions for use)",
        "Contraindications",
    ),
    EmaSectionRe(
        r"(4\.4\s+Special warnings and precautions for use)(.+)(4\.5\s+Interaction with other medicinal products and other forms of interaction)",
        "Warnings",
    ),
    EmaSectionRe(
        r"(4\.5\s+Interaction with other medicinal products and other forms of interaction)(.+)(4\.6\s+Fertility, pregnancy and lactation)",
        "Interactions",
    ),
    EmaSectionRe(
        r"(4\.6\s+Fertility, pregnancy and lactation)(.+)(4\.7\s+Effects on ability to drive and use machines)",
        "Pregnancy",
    ),
    EmaSectionRe(
        r"(4\.7\s+Effects on ability to drive and use machines)(.+)(4\.8\s+Undesirable effects)",
        "Effects on driving",
    ),
    EmaSectionRe(
        r"(4\.8\s+Undesirable effects)(.+)(4\.9\s+Overdose)",
        "Side effects",
    ),
    EmaSectionRe(
        r"(4\.9\s+Overdose)(.+)(5\.\s+PHARMACOLOGICAL PROPERTIES)",
        "Overdose",
    ),
]

# runs with `python manage.py load_ema_data`
# add `--type full` to import the full dataset
# add `--type rand_test` to import 3 random records
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    help = "Loads data from EMA"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.num_drug_labels_parsed = 0
        "keep track of the number of labels processed"
        self.error_urls = {}
        "dictionary to keep track of the urls that have parsing errors; form: {url: True}"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type", type=str, help="'full', 'test' or 'rand_test'", default="test"
        )

    def handle(self, *args, **options):
        # import_type is 'full', 'test' or 'rand_test'
        import_type = options["type"]
        if import_type not in ["full", "test", "rand_test"]:
            raise CommandError("'type' parameter must be 'full', 'test' or 'rand_test'")

        # basic logging config is in settings.py
        # verbosity is 1 by default, gives critical, error and warning output
        # `--verbosity 2` gives info output
        # `--verbosity 3` gives debug output
        verbosity = int(options["verbosity"])
        root_logger = logging.getLogger("")
        if verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)

        logger.info(self.style.SUCCESS("start process"))
        logger.info(f"import_type: {import_type}")

        if import_type == "test":
            urls = [
                "https://www.ema.europa.eu/en/medicines/human/EPAR/skilarence",
                "https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica",
                "https://www.ema.europa.eu/en/medicines/human/EPAR/ontilyv",
            ]
        else:
            urls = self.get_ema_epar_urls()

        if import_type == "rand_test":
            # pick a random 3 urls for the test
            urls = random.sample(list(urls), 3)
            logger.debug(f"first rand url: {urls[0]}")

        logger.info(f"total urls to process: {len(urls)}")

        for url in urls:
            try:
                logger.info(f"processing url: {url}")
                dl = self.get_drug_label_from_url(url)
                logger.debug(repr(dl))
                # dl.link is url of pdf
                # for now, assume only one LabelProduct per DrugLabel
                lp = LabelProduct(drug_label=dl)
                lp.save()
                dl.raw_text = self.parse_pdf(dl.link, lp)
                dl.save()
                self.num_drug_labels_parsed += 1
            except IntegrityError as e:
                logger.warning(self.style.WARNING("Label already in db"))
                logger.debug(e, exc_info=True)
            logger.info(f"sleep 1s")
            time.sleep(1)

        for url in self.error_urls.keys():
            logger.warning(self.style.WARNING(f"error parsing url: {url}"))

        logger.info(f"num_drug_labels_parsed: {self.num_drug_labels_parsed}")
        logger.info(self.style.SUCCESS("process complete"))
        return

    def get_drug_label_from_url(self, url):
        dl = DrugLabel()  # empty object to populate as we go
        dl.source = "EMA"

        # grab the webpage
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        # logger.debug(soup.prettify())
        # logger.debug(repr(soup))

        # ref: https://www.crummy.com/software/BeautifulSoup/bs4/doc/

        # for now, we want to grab 6 things from the web page:
        # product_name
        # generic_name
        # version_date
        # source_product_number
        # marketer
        # url for product-information pdf

        # look in the "Authorisation details" section
        # "Name" => product_name
        # "Active substance" => generic_name
        # "Agency product number" => source_product_number
        # "Marketing-authorisation holder" => marketer

        # "Product information" section
        # product-information pdf
        # "Last updated: DD/MM/YYYY" # note EU has different date format from USA

        # look for the section
        tag = soup.find(id="authorisation-details-section")

        # product_name
        # find the 'td' cell that contains the 'Name' text
        cell = tag.find_next("td", string=re.compile(r"\sName\s"))
        # grab the text from the 'next sibling'
        str = cell.find_next_sibling().get_text(strip=True)
        # logger.debug(repr(str))
        # set it in our object
        dl.product_name = str

        # generic_name
        cell = tag.find_next("td", string=re.compile(r"\sActive substance\s"))
        str = cell.find_next_sibling().get_text(strip=True)
        str = str[0:255]  # limiting to 255 chars
        dl.generic_name = str

        # source_product_number
        cell = tag.find_next("td", string=re.compile(r"\sAgency product number\s"))
        str = cell.find_next_sibling().get_text(strip=True)
        dl.source_product_number = str

        # marketer -- can be missing / null
        try:
            cell = tag.find_next(
                "td", string=re.compile(r"\sMarketing-authorisation holder\s")
            )
            str = cell.find_next_sibling().get_text(strip=True)
            dl.marketer = str
        except AttributeError:
            dl.marketer = "_"

        tag = soup.find(id="product-information-section")

        # version_date
        date_str_key = "Last updated:"
        entry = tag.find_next(string=re.compile(date_str_key))
        if entry is None:
            # if there is no "Last updated:" date, use "First published:" date
            date_str_key = "First published:"
            entry = tag.find_next(string=re.compile(date_str_key))

        entry = entry.strip()
        sub_str = entry[len(date_str_key) :].strip()
        # parse sub_str into date, from DD/MM/YYYY to: YYYY-MM-DD
        dt_obj = datetime.datetime.strptime(sub_str, "%d/%m/%Y")
        str = dt_obj.strftime("%Y-%m-%d")
        dl.version_date = str

        # url for product-information pdf
        entry = tag.find_next("a", href=True)
        dl.link = entry["href"]

        dl.save()
        return dl

    def get_backoff_time(self, tries=5):
        """Get an amount of time to backoff. Starts with no backoff.
        Returns: number of seconds to wait
        """
        # starts with no backoff
        yield 0
        # then we have an exponential backoff with jitter
        for i in range(tries - 1):
            yield 2**i + random.uniform(0, 1)

    def parse_pdf(self, pdf_url, lp):
        # have a backoff time for pulling the pdf from the website
        for t in self.get_backoff_time(5):
            try:
                logger.info(f"time to sleep: {t}")
                time.sleep(t)
                response = requests.get(pdf_url)
                break  # no Exception means we were successful
            except (ValueError, ChunkedEncodingError) as e:
                logger.error(self.style.ERROR(f"caught error: {e.__class__.__name__}"))
                logger.warning(self.style.WARNING("Unable to read url, may continue"))
                response = None

        if not response:
            logger.error(self.style.ERROR("unable to grab url contents"))
            self.error_urls[pdf_url] = True
            return "unable to download pdf"

        # save pdf to default_storage / MEDIA_ROOT
        filename = default_storage.save(
            settings.MEDIA_ROOT / "ema.pdf", ContentFile(response.content)
        )
        logger.info(f"saved file to: {filename}")

        # PyMuPDF references
        # ty: https://stackoverflow.com/a/63486976/1807627
        # https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/PDF2Text.py
        # https://github.com/pymupdf/PyMuPDF/blob/master/fitz/fitz.i

        # populate raw_text with the contents of the pdf
        raw_text = ""
        with fitz.open(settings.MEDIA_ROOT / "ema.pdf") as pdf_doc:
            for page in pdf_doc:
                raw_text += page.get_text()

        # the sections are in order
        # so keep track of where to start the search in each iteration
        start_idx = 0
        for section in EMA_PDF_PRODUCT_SECTIONS:
            logger.info(f"section.name: {section.name}")

            section_text = section.find_match(raw_text, start_idx)
            end_idx = section.get_end_idx()

            if not section_text:
                logger.error(self.style.ERROR("Unable to find section_text"))
                self.error_urls[pdf_url] = True
                continue

            logger.debug(f"found section_text: {section_text}")
            logger.debug(f"end_idx: {end_idx}")

            ps = ProductSection(
                label_product=lp, section_name=section.name, section_text=section_text
            )
            ps.save()

            # start search for next section after the end_idx of this section
            start_idx = end_idx

        # logger.debug(f"raw_text: {repr(raw_text)}")

        # delete the file when done
        default_storage.delete(filename)

        logger.info("Success")
        return raw_text

    def get_ema_epar_urls(self):
        """Download the EMA provided Excel file and grab the urls from there"""
        # return a list of the epar urls, e.g. ["https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica"]
        # load excel file into pandas, directly from url
        # there are some header rows to skip
        # only load the columns we are interested in
        df = pd.read_excel(
            EMA_EPAR_EXCEL_URL,
            skiprows=8,
            usecols=["Category", "Authorisation status", "URL"],
            engine="openpyxl",
        )
        # filter results by:
        # "Category" == "Human"
        # "Authorisation status" == "Authorised"
        df = df[df["Category"] == "Human"]
        # TODO verify we only want "Authorised" medicines
        df = df[df["Authorisation status"] == "Authorised"]
        return df["URL"]
