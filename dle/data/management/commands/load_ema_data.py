from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from urllib3.exceptions import InvalidChunkLength

from data.models import DrugLabel, LabelProduct, ProductSection
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

class EmaSectionDef:
    """struct to hold info that helps us parse the Sections"""

    def __init__(self, start_text, end_text, name):
        self.start_text = start_text
        self.end_text = end_text
        self.name = name


# only doing a few to start
# these should be in order of how they appear in the pdf
EMA_PDF_PRODUCT_SECTIONS = [
    EmaSectionDef(
        "4.1 \nTherapeutic indications",
        "4.2 \nPosology and method of administration",
        "INDICATIONS",
    ),
    EmaSectionDef(
        "4.3 \nContraindications",
        "4.4 \nSpecial warnings and precautions for use",
        "CONTRA",
    ),
    EmaSectionDef(
        "4.4 \nSpecial warnings and precautions for use",
        "4.5 \nInteraction with other medicinal products and other forms of interaction",
        "WARN",
    ),
    EmaSectionDef(
        "4.6 \nFertility, pregnancy and lactation",
        "4.7 \nEffects on ability to drive and use machines",
        "PREG",
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

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, help="'full', 'test' or 'rand_test'", default="test")

    def handle(self, *args, **options):
        # import_type is 'full', 'test' or 'rand_test'
        import_type = options['type']
        if import_type not in ['full', 'test', 'rand_test']:
            raise CommandError("'type' parameter must be 'full', 'test' or 'rand_test'")

        # basic logging config is in settings.py
        # verbosity is 1 by default, gives critical, error and warning output
        # `--verbosity 2` gives info output
        # `--verbosity 3` gives debug output
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)

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
                raw_text = self.parse_pdf(dl.link, lp)
                dl.raw_text = raw_text
                dl.save()
                self.num_drug_labels_parsed += 1
            except IntegrityError as e:
                logger.warning(self.style.WARNING("Label already in db"))
            time.sleep(1)
        logger.info(f"num_drug_labels_parsed: {self.num_drug_labels_parsed}")
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
        dl.generic_name = str

        # source_product_number
        cell = tag.find_next("td", string=re.compile(r"\sAgency product number\s"))
        str = cell.find_next_sibling().get_text(strip=True)
        dl.source_product_number = str

        # marketer
        cell = tag.find_next(
            "td", string=re.compile(r"\sMarketing-authorisation holder\s")
        )
        str = cell.find_next_sibling().get_text(strip=True)
        dl.marketer = str

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

    def parse_pdf(self, pdf_url, lp):
        # save pdf to default_storage / MEDIA_ROOT
        try:
            response = requests.get(pdf_url)
        except InvalidChunkLength as e:
            logger.critical(self.style.ERROR("Unable to read url"))
            # TODO maybe put in a back-off
            return

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
            logger.debug(f"looking for section.start_text: {section.start_text}")
            idx = raw_text.find(section.start_text, start_idx)
            if idx == -1:
                logger.error(self.style.ERROR("Unable to find section_start_text"))
                continue
            else:
                logger.debug(f"Found section.start_text, idx: {idx}")

            # look for section_end_text
            logger.debug(f"looking for section.end_text: {section.end_text}")
            end_idx = raw_text.find(section.end_text, idx)
            if end_idx == -1:
                logger.error(self.style.ERROR("Unable to find section.end_text"))
                continue
            else:
                logger.debug(f"Found section.end_text, end_idx: {end_idx}")

            # the section_text is between idx and end_idx
            section_text = raw_text[idx:end_idx]
            logger.debug(f"found section_text: {section_text}")
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
        df = pd.read_excel(EMA_EPAR_EXCEL_URL, skiprows=8, usecols=["Category", "Authorisation status", "URL"], engine='openpyxl')
        # filter results by:
        # "Category" == "Human"
        # "Authorisation status" == "Authorised"
        df = df[df["Category"] == "Human"]
        # TODO verify we only want "Authorised" medicines
        df = df[df["Authorisation status"] == "Authorised"]
        return df["URL"]
