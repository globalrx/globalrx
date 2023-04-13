import datetime
import logging
import random
import re
import string
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

import requests
from bs4 import BeautifulSoup
from Levenshtein import distance as levdistance
from requests.exceptions import ChunkedEncodingError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

from data.models import DrugLabel, LabelProduct, ProductSection

from .pdf_parsing_helper import get_pdf_sections, read_pdf


# from users.models import MyLabel


logger = logging.getLogger(__name__)

TGA_BASE_URL = "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/"

OTHER_FORMATTED_SECTIONS = [
    r"^NAME OF THE MEDICINE",
    r"^DESCRIPTION",
    r"^PHARMACOLOGY",
    r"^CLINICAL TRIALS",
    r"^INDICATIONS",
    r"^CONTRAINDICATIONS",
    r"^PRECAUTIONS",
    r"^(?:INTERACTIONS WITH OTHER MEDICINES|Interactions with other medicines)",
    r"^ADVERSE (?:REACTIONS|EFFECTS)",
    r"^DOSAGE AND ADMINISTRATION",
    r"^OVERDOSAGE",
    r"^PRESENTATION AND STORAGE CONDITIONS",
    r"^NAME AND ADDRESS OF THE SPONSOR",
    r"^POISON SCHEDULE OF THE MEDICINE",
    r"^.*INCLUSION IN THE AUSTRALIAN.*",
    r"^DATE OF MOST RECENT AMENDMENT",
]


# runs with `python manage.py load_tga_data`
# add `--type full` to import the full dataset
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    help = "Loads data from TGA"

    records = {}

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.num_drug_labels_parsed = 0
        "keep track of the number of labels processed"
        self.error_urls = {}
        "dictionary to keep track of the urls that have parsing errors; form: {url: True}"
        self.options = Options()
        self.options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=self.options)
        self.total_to_process = 0
        self.processed_with_current_cookies = 0
        self.cookies = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            help="'full', 'test'",
            default="test",
        )

    def get_tga_cookies(self) -> dict:
        """Get cookies from TGA website
        Accept the access terms
        Store the cookies and include with BeautifulSoup requests
        """
        self.driver.delete_all_cookies()
        self.driver.get(TGA_BASE_URL + "/pdf?OpenAgent")
        time.sleep(1)
        # This is the xpath to the accept button
        button = self.driver.find_element(
            by=By.XPATH, value="/html/body/form/div[2]/div[3]/div[1]/a[1]"
        )
        self.driver.execute_script("arguments[0].click();", button)
        # Wait a bit for it to load
        time.sleep(5)
        driver_cookies = self.driver.get_cookies()
        cookies = {c["name"]: c["value"] for c in driver_cookies}
        logger.info("Got or renewed cookies")
        return cookies

    def handle(self, *args, **options):
        import_type = options["type"]
        if import_type not in ["full", "test"]:
            raise CommandError("'type' parameter must be 'full' or 'test'")

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
                "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k=0&r=/",
                "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k=5&r=/",
                "https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k=Y&r=/",
            ]
        else:
            # Get full list of addresses to query
            urls = self.get_tga_pi_urls()

        self.total_to_process = len(urls)
        logger.info(f"total urls to process: {len(urls)}")

        self.cookies = self.get_tga_cookies()

        # Iterate all the query URLs
        for url in urls:
            logger.info(f"processing url: {url}")
            # Grab the webpage
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            table_body = table.find("tbody")
            rows = table_body.find_all("tr")
            # Iterate all the products in the table
            for row in rows:
                # If we have processed a bunch of labels, get a new cookie so we don't time out
                if self.processed_with_current_cookies >= 200:
                    new_cookies = self.get_tga_cookies()
                    self.cookies = new_cookies
                    self.processed_with_current_cookies = 0
                try:
                    dl, label_text = self.get_drug_label_from_row(soup, row, self.cookies)
                    logger.debug(repr(dl))
                    # dl.link is url of pdf
                    # for now, assume only one LabelProduct per DrugLabel
                    lp = LabelProduct(drug_label=dl)
                    lp.save()
                    self.save_product_sections(lp, label_text)
                    self.num_drug_labels_parsed += 1
                except IntegrityError as e:
                    logger.warning(self.style.WARNING("Label already in db"))
                    logger.debug(e, exc_info=True)
                except AttributeError as e:
                    logger.warning(self.style.ERROR(repr(e)))
                except ValueError as e:
                    logger.warning(self.style.WARNING(repr(e)))
                # increment this regardless of success, still takes time
                self.processed_with_current_cookies += 1

            for url in self.error_urls.keys():
                logger.warning(self.style.WARNING(f"error parsing url: {url}"))

        logger.info(f"num_drug_labels_parsed: {self.num_drug_labels_parsed}")
        logger.info(self.style.SUCCESS("process complete"))
        return

    def convert_date_string(self, date_string):
        for date_format in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y"):
            try:
                dt_obj = datetime.datetime.strptime(date_string, date_format)
                converted_string = dt_obj.strftime("%Y-%m-%d")
                return converted_string
            except ValueError:
                pass
        return ""

    def get_drug_label_from_row(self, soup, row, cookies):
        dl = DrugLabel()  # empty object to populate as we go
        dl.source = "TGA"

        columns = row.find_all("td")
        # product name is located at the fitst column
        dl.product_name = columns[0].text.strip()
        # pdf link is located at the second column
        dl.link = TGA_BASE_URL + columns[1].find("a")["href"]
        dl.source_product_number = columns[1].find("a")["target"]
        # active ingredient(s) at the third column
        dl.generic_name = columns[2].text.strip()

        # get version date from the pdf
        dl.raw_text, label_text = self.get_and_parse_pdf(dl.link, dl.source_product_number, cookies)
        dl.version_date = ""
        date_string = ""
        # First to look for date of revision, if it exists and contains a valid date, then store that date
        # Otherwise look for date of first approval, and store that date if it's available
        if "Date Of Revision" in label_text.keys():
            date_string = label_text["Date Of Revision"][0].split("\n")[0]
            dl.version_date = self.convert_date_string(date_string)

        if dl.version_date == "" and "Date Of First Approval" in label_text.keys():
            date_string = label_text["Date Of First Approval"][0].split("\n")[0]
            dl.version_date = self.convert_date_string(date_string)

        if dl.version_date == "" and "Date Of Most Recent Amendment" in label_text.keys():
            date_string = label_text["Date Of Most Recent Amendment"][0].split("\n")[0]
            dl.version_date = self.convert_date_string(date_string)

        # Raise an error if the version date is still empty
        if dl.version_date == "":
            raise AttributeError(f"Failed to parse for version date ({date_string}) from {dl.link}")

        dl.save()
        return dl, label_text

    def save_product_sections(self, lp, label_text):
        for index, key in enumerate(label_text):
            text_block = ""
            # label_text[key] is an array of text. Convert it to a block of text
            for s in label_text[key]:
                text_block += s
            ps = ProductSection(label_product=lp, section_name=key, section_text=text_block)
            ps.save()

    def get_backoff_time(self, tries=5):
        """Get an amount of time to backoff. Starts with no backoff.
        Returns: number of seconds to wait
        """
        # starts with no backoff
        yield 0
        # then we have an exponential backoff with jitter
        for i in range(tries - 1):
            yield 2**i + random.uniform(0, 1)

    def get_and_parse_pdf(self, pdf_url, source_product_number, cookies):
        # have a backoff time for pulling the pdf from the website
        for t in self.get_backoff_time(5):
            try:
                logger.info(f"time to sleep: {t}")
                time.sleep(t)
                response = requests.get(pdf_url, cookies=cookies)
                break  # no Exception means we were successful
            except (ValueError, ChunkedEncodingError) as e:
                logger.error(self.style.ERROR(f"caught error: {e.__class__.__name__}"))
                logger.warning(self.style.WARNING("Unable to read url, may continue"))
                response = None
        if not response:
            logger.error(self.style.ERROR("unable to grab url contents"))
            self.error_urls[pdf_url] = True
            return "unable to download pdf"

        filename = default_storage.save(
            settings.MEDIA_ROOT / "tga.pdf", ContentFile(response.content)
        )
        logger.info(f"saved {pdf_url} file to: {filename}")
        tga_file = settings.MEDIA_ROOT / filename
        raw_text, label_text = self.process_tga_pdf_file(tga_file, source_product_number, pdf_url)
        # delete the file when done
        default_storage.delete(filename)

        logger.info(f"Parsed {pdf_url}")

        return raw_text, label_text

    def get_pdf_sections_with_format(self, text, section_format):
        idx, headers, sections = [], [], []
        start_idx = 0
        for section in section_format:
            for i, line in enumerate(text[start_idx:], start=start_idx):
                if re.match(section, line):
                    start_idx = i + 1  # +1 to start at next line
                    idx += [i]
                    headers += [line.strip()]

        for n, h in enumerate(headers):
            if (n + 1) < len(headers):
                contents = text[idx[n] + 1 : idx[n + 1]]
            else:
                contents = text[idx[n] + 1 :]
            sections += ["\n".join(contents)]

        return headers, sections

    centers = [
        "Clinical Particulars",
        "Contraindications",
        "Date Of First Approval",
        "Date Of Revision",
        "Effects On Ability To Drive And Use Machines",
        "Fertility, Pregnancy And Lactation",
        "Incompatibilities",
        "Interaction With Other Medicinal Products And Other Forms Of Interaction",
        "List Of Excipients",
        "Marketing Authorisation Holder",
        "Marketing Authorisation Number",
        "Name Of The Medicinal Product",
        "Nature And Contents Of Container",
        "Overdose",
        "Pharmaceutical Form",
        "Pharmaceutical Particulars",
        "Pharmacodynamic Properties",
        "Pharmacokinetic Properties",
        "Pharmacological Properties",
        "Posology And Method Of Administration",
        "Preclinical Safety Data",
        "Pregnancy And Lactation",
        "Qualitative And Quantitative Composition",
        "Shelf Life",
        "Special Precautions For Disposal",
        "Special Precautions For Disposal And Other Handling",
        "Special Precautions For Storage",
        "Special Warnings And Precautions For Use",
        "Therapeutic Indications",
        "Undesirable Effects",
        "Description",
        "Pharmacology",
        "Indications",
        "Precautions",
        "Interaction With Other Medicines",
        "Name and address of the sponsor",
        "Correction to the Medicine Schedule",
        "Dosage and Administration",
        "Date Of Most Recent Amendment",
    ]
    # note: maybe we should manually merge these pairs:
    #   FERTILITY, PREGNANCY AND LACTATION
    #   PREGNANCY AND LACTATION
    #   SPECIAL PRECAUTIONS FOR DISPOSAL AND OTHER HANDLING
    #   SPECIAL PRECAUTIONS FOR DISPOSAL
    # but not doing so lets the similarity computation do its thing

    # improved initial text parsing step so this clustering problem wasn't so messy
    def get_fixed_header(self, text):
        # return center with the lowest edit distance,
        #   or placeholder (last entry) if no there's good match
        dists = [levdistance(text.lower(), c.lower()) for c in self.centers]
        # ix = np.argmin(dists)
        ix = dists.index(min(dists))
        if dists[ix] > 0.6 * len(text):
            return None
        else:
            return self.centers[ix]

    def process_tga_pdf_file(self, tga_file, source_product_number, pdf_url=""):
        raw_text = []
        label_text = {}  # next level = product page w/ metadata

        try:
            raw_text = read_pdf(tga_file, no_annex=False)
            info = {}
            product_code = source_product_number
            # row = self.df[self.df["Product number"] == product_code]
            # info["metadata"] = row.iloc[0].apply(str).to_dict()

            headers, sections = [], []

            headers, sections = get_pdf_sections(raw_text, pattern=r"^[0-9]+\.?[0-9]*\s+[A-Z].*")

            # With the above method, it should at least find 20 sections, if less than that,
            #  then parse it with other method
            if len(headers) < 20:
                logger.info("Failed to parse. Using another method...")
                headers, sections = self.get_pdf_sections_with_format(
                    raw_text, OTHER_FORMATTED_SECTIONS
                )
                if len(headers) == 0:
                    raise Exception("Failed to parse pdf with both methods")
            for h, s in zip(headers, sections):
                header = self.get_fixed_header(h)
                if (header is not None) and (len(s) > 0):
                    logger.info(f"Found original header ({h}) fixed to {header}")
                    if header not in label_text.keys():
                        label_text[header] = [s]
                    else:
                        label_text[header].append(s)

            info["Label Text"] = label_text
            self.records[product_code] = info
        except Exception as e:
            logger.error(self.style.ERROR(repr(e)))
            logger.error(self.style.ERROR(f"Failed to process {tga_file}, url = {pdf_url}"))
            self.error_urls[pdf_url] = True

        return raw_text, label_text

    def get_tga_pi_urls(self):
        """
        The TGA query address is https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k=0&r=/
        Iterate the query parameter k with 0-9 and A-Z
        """
        URLs = []
        for i in range(0, 10):  # queries 0-9
            base_url = f"https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k={i}&r=/"
            URLs.append(base_url)
        for c in string.ascii_uppercase:  # queries A-Z
            base_url = f"https://www.ebs.tga.gov.au/ebs/picmi/picmirepository.nsf/PICMI?OpenForm&t=PI&k={c}&r=/"
            URLs.append(base_url)
        return URLs
