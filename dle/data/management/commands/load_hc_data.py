import datetime
import json
import logging
import random
import re
import time
from distutils.util import strtobool

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

import requests
from bs4 import BeautifulSoup
from Levenshtein import distance as levdistance
from psycopg import DataError
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

from data.models import DrugLabel, LabelProduct, ParsingError, ProductSection
from data.util import PDFParseException, check_recently_updated, strfdelta

from .pdf_parsing_helper import filter_headers, get_pdf_sections, read_pdf


logger = logging.getLogger(__name__)

HC_BASE_URL = "https://health-products.canada.ca"
HC_SEARCH_URL = "https://health-products.canada.ca/dpd-bdpp/search/"
HC_RESULT_URL = "https://health-products.canada.ca/dpd-bdpp/dispatch-repartition"

# The following sections are assumed to be in this order in the pdf when they are parsed
OTHER_FORMATTED_SECTIONS = [
    r"^(?:SUMMARY PRODUCT INFORMATION|ACTIONS?(?: AND CLINICAL PHARMACOLOGY)?)$",
    r"^DESCRIPTION$",
    r"^INDICATIONS(?: AND (?:CLINICAL USES?|USAGE))?$",
    r"^CONTRAINDICATIONS$",
    r"^WARNINGS AND PRECAUTIONS$",
    r"^WARNINGS$",
    r"^PRECAUTIONS$",
    r"^ADVERSE REACTIONS$",
    r"^DRUG INTERACTIONS$",
    r"^DOSAGE AND ADMINISTRATION$",
    r"^OVERDOSAGE$",
    r"^ACTIONS? AND CLINICAL PHARMACOLOGY$",
    r"^STORAGE AND STABILITY$",
    r"^DOSAGE FORMS, COMPOSITION AND PACKAGING$",
    r"^PHARMACEUTICAL INFORMATION$",
    r"^CLINICAL TRIALS$",
    r"^TOXICOLOGY$",
]


# runs with `python manage.py load_hc_data`
# add `--type full` to import the full dataset
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    help = "Loads data from HC"
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            help="'full', 'test'",
            default="test",
        )
        parser.add_argument(
            "--skip_more_recent_than_n_hours",
            type=int,
            help="Skip re-scraping labels more recently imported than this number of hours old. Default is 168 (7 days)",
            default=168,  # 7 days; set to 0 to re-scrape everything
        )
        parser.add_argument(
            "--skip_known_errors",
            type=strtobool,
            help="Skip labels that have previously had parsing errors. Default is True",
            default=True,
        )

    def handle(self, *args, **options):
        self.skip_labels_updated_within_span = datetime.timedelta(
            hours=int(options["skip_more_recent_than_n_hours"])
        )
        self.skip_errors = options["skip_known_errors"]
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

        # Before being able to access the drugs,
        #  we have to do a search with "approved" status and "human" class.
        # Then store the cookies and pass it to the requests
        for t in self.get_backoff_time(5):
            try:
                time.sleep(t)
                self.driver.get(HC_SEARCH_URL)
                time.sleep(1)
                # Click the approve field
                approved_status_field = self.driver.find_element(
                    by=By.XPATH,
                    value="/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[1]/div/select/option[2]",
                )
                approved_status_field.click()
                # Unclick the select all field
                select_all_status_field = self.driver.find_element(
                    by=By.XPATH,
                    value="/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[1]/div/select/option[1]",
                )
                ActionChains(self.driver).key_down(Keys.CONTROL).click(
                    select_all_status_field
                ).key_up(Keys.CONTROL).perform()

                # Click the human field
                human_class_field = self.driver.find_element(
                    by=By.XPATH,
                    value="/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[7]/div/select/option[3]",
                )
                human_class_field.click()
                # Unclick the select all field
                select_all_class_field = self.driver.find_element(
                    by=By.XPATH,
                    value="/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[7]/div/select/option[1]",
                )
                ActionChains(self.driver).key_down(Keys.CONTROL).click(
                    select_all_class_field
                ).key_up(Keys.CONTROL).perform()

                # Click the search button
                search_button = self.driver.find_element(
                    by=By.XPATH,
                    value="/html/body/main/div[1]/div[1]/div[3]/form/div[1]/div/input[1]",
                )
                search_button.click()

                # Wait a bit for it to load
                time.sleep(10)

                # Grab the result webpage
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                table = soup.find("table")
                table_attrs = json.loads(table.get("data-wb-tables"))
                # num_displayed_results = table_attrs["iDisplayLength"]
                num_total_results = table_attrs["iDeferLoading"]
                # No error means success, break out of the loop
                break
            except Exception as e:
                logger.error(self.style.ERROR(repr(e)))
                logger.error("Failed to get HC result. Retrying")

        drug_label_parsed = 0
        # Iterate all the drugs in the table
        while drug_label_parsed < num_total_results:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table")
            table_body = table.find("tbody")
            rows = table_body.find_all("tr")
            # Iterate all the products in the table
            for row in rows:
                source_product_number = row.find_all("td")[1].text.strip()
                # first see if it's a label with a known error; if so, skip it
                if self.skip_errors:
                    existing_errors = ParsingError.objects.filter(
                        source="HC", source_product_number=source_product_number
                    )
                    if existing_errors.count() >= 1:
                        logger.warning(
                            self.style.WARNING(
                                f"Label skipped. Known error: {existing_errors[0].error_type}"
                            )
                        )
                        continue
                # then see if it's a label we've already parsed recently; if so, skip it
                existing_labels = DrugLabel.objects.filter(
                    source="HC", source_product_number=source_product_number
                ).order_by("-updated_at")
                if existing_labels.count() >= 1:
                    existing_label = existing_labels[0]
                    if check_recently_updated(
                        dl=existing_label, skip_timeframe=self.skip_labels_updated_within_span
                    ):
                        last_updated_ago = (
                            datetime.datetime.now(datetime.timezone.utc) - existing_label.updated_at
                        )
                        logger.warning(
                            self.style.WARNING(
                                f"Label skipped. Updated {strfdelta(last_updated_ago)} ago, less than {self.skip_labels_updated_within_span}"
                            )
                        )
                        continue

                try:
                    dl = self.get_drug_label_from_row(row)
                    logger.debug(repr(dl))
                    # dl.link is url of pdf
                    # for now, assume only one LabelProduct per DrugLabel
                    lp = LabelProduct(drug_label=dl)
                    lp.save()
                    if dl.link == "":
                        raise ValueError(f"{dl.product_name} doesn't have a PDF label")
                    dl.raw_text = self.get_and_parse_pdf(dl.link, dl.source_product_number, lp)
                    dl.save()
                    self.num_drug_labels_parsed += 1
                except IntegrityError as e:
                    logger.warning(self.style.WARNING("Label already in db"))
                    logger.debug(e, exc_info=True)
                except AttributeError as e:
                    logger.warning(self.style.ERROR(repr(e)))
                    # TODO add to error table - need the PDF url?
                    msg = str(repr(e))
                    parsing_error, created = ParsingError.objects.get_or_create(
                        source="HC",
                        message=msg,
                        source_product_number=source_product_number,
                        error_type="attribute_error",
                    )
                    if created:
                        logger.warning(f"Created ParsingError {parsing_error}")
                    else:
                        logger.warning(
                            f"Failed to create ParsingError {parsing_error} - likely already exists"
                        )
                except ValueError as e:
                    # Typically ValueError("AG-TOPIRAMATE TABLETS 200 MG doesn't have a PDF label")
                    logger.warning(self.style.WARNING(repr(e)))
                    msg = str(repr(e))
                    parsing_error, created = ParsingError.objects.get_or_create(
                        source_product_number=source_product_number,
                        message=msg,
                        source="HC",
                        error_type="no_pdf",
                    )
                    if created:
                        logger.warning(f"Created ParsingError {parsing_error}")
                    else:
                        logger.warning(
                            f"Failed to create ParsingError {parsing_error} - likely already exists"
                        )
                except DataError as e:
                    # Got one Data Error:
                    # 2023-04-18 06:12:49,645 ERROR DataError('PostgreSQL text fields cannot contain NUL (0x00) bytes')
                    # 2023-04-18 06:12:49,645 ERROR Failed to process /app/media/hc_dV1W8Qo.pdf, url = https://pdf.hres.ca/dpd_pm/00058978.PDF
                    # Could try to clean it? https://stackoverflow.com/questions/57371164/django-postgres-a-string-literal-cannot-contain-nul-0x00-characters
                    logger.error(self.style.ERROR(e))
                    msg = str(repr(e))
                    parsing_error, created = ParsingError.objects.get_or_create(
                        source="HC",
                        source_product_number=source_product_number,
                        message=msg,
                        error_type="data_error",
                    )
                    if created:
                        logger.warning(f"Created ParsingError {parsing_error}")
                    else:
                        logger.warning(
                            f"Failed to create ParsingError {parsing_error} - likely already exists"
                        )
                time.sleep(0.5)
                drug_label_parsed += 1
                # For test, if it succesfully parses 3 labels, then break
                if import_type == "test" and drug_label_parsed == 3:
                    break
            if import_type == "test":
                break
            else:
                # Click the next button
                next_button = self.driver.find_element(by=By.ID, value="results_next")
                if next_button is not None and drug_label_parsed < num_total_results:
                    next_button.click()
                    # Wait for a bit, take awhile for it to load
                    time.sleep(10)
                else:
                    break

        for url in self.error_urls.keys():
            logger.warning(self.style.WARNING(f"error parsing url: {url}"))
        logger.info(f"num_drug_labels_parsed: {self.num_drug_labels_parsed}")
        logger.info(self.style.SUCCESS("process complete"))
        return

    def get_drug_label_from_row(self, row):
        dl = DrugLabel()  # empty object to populate as we go
        dl.source = "HC"

        columns = row.find_all("td")
        # DIN is located at the second column
        # TODO: Is DIN same as source product number?
        dl.source_product_number = columns[1].text.strip()

        # Company is located at the third column
        # TODO: Is Company same as marketer?
        dl.marketer = columns[2].text.strip()

        # product name is located at the fourth column
        # strength is located at the 10th column
        dl.product_name = columns[3].text.strip() + " " + columns[9].text.strip()

        # The column under DIN is a clickable link to the drug details
        link_to_drug_details = HC_BASE_URL + columns[1].find("a")["href"]
        logger.info(f"Scraping URL {link_to_drug_details}")
        response = self.requests_with_retries(link_to_drug_details)
        if not response:
            raise ValueError(f"unable to grab url contents {link_to_drug_details}")

        soup = BeautifulSoup(response.text, "html.parser")
        divs = soup.findAll("div", attrs={"class": "row"})
        # Get the version date and the pdf link
        dl.version_date = ""
        dl.link = ""
        for div in divs:
            ps = div.findAll("p", attrs={"class": "col-sm-8"})
            for p in ps:
                if p.find("strong"):
                    if "Date" in p.find("strong").text:
                        spans = p.findAll("span")
                        dl.version_date = spans[0].text
                        dl.link = spans[1].find("a")["href"]
        if dl.link == "":
            logger.info(f"{dl.product_name} does not have a PDF label: {link_to_drug_details}")

        # If version date is not available, then get the status date instead
        if dl.version_date == "":
            for div in divs:
                p1 = div.find("p", attrs={"class": "col-sm-4"})
                if p1 and p1.find("strong") and p1.find("strong").text == "Current status date:":
                    p = div.find("p", attrs={"class": "col-sm-8"})
                    dl.version_date = p.text

        # Get all the active ingredient(s)
        div = soup.find("div", attrs={"class": "table-responsive mrgn-tp-lg"})
        table = div.find("table")
        rows = table.findAll("tr")
        active_ingredients = ""
        for row in rows:
            if row.find("td"):
                # Semi-colon separated
                if active_ingredients == "":
                    active_ingredients = row.find("td").text.strip()
                else:
                    active_ingredients = active_ingredients + "; " + row.find("td").text.strip()
        dl.generic_name = active_ingredients

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

    def requests_with_retries(self, url):
        # have a backoff time for pulling the pdf from the website
        for t in self.get_backoff_time(5):
            try:
                logger.info(f"time to sleep: {t}")
                time.sleep(t)
                response = requests.get(url)
                break  # no Exception means we were successful
            except:
                logger.error(f"Failed. Retry to request {url}")
                response = None
        return response

    def get_and_parse_pdf(self, pdf_url, source_product_number, lp):
        response = self.requests_with_retries(pdf_url)
        if not response:
            logger.error(self.style.ERROR("unable to grab url contents"))
            self.error_urls[pdf_url] = True
            return "unable to download pdf"

        filename = default_storage.save(
            settings.MEDIA_ROOT / "hc.pdf", ContentFile(response.content)
        )
        logger.info(f"saved {pdf_url} file to: {filename}")
        hc_file = settings.MEDIA_ROOT / filename
        raw_text = self.process_hc_pdf_file(hc_file, source_product_number, lp, pdf_url)
        # delete the file when done
        default_storage.delete(filename)
        return raw_text

    def get_pdf_sections_with_format(self, text, section_format):
        idx, headers, sections = [], [], []
        start_idx = 0
        for section in section_format:
            for i, line in enumerate(text[start_idx:], start=start_idx):
                if re.match(section, line.upper()):
                    start_idx = i + 1  # +1 to start at next line
                    idx += [i]
                    headers += [line.strip()]
                    break

        if len(headers) != 0:
            idx, headers = filter_headers(idx, headers)

        for n, h in enumerate(headers):
            if (n + 1) < len(headers):
                contents = text[idx[n] + 1 : idx[n + 1]]
            else:
                contents = text[idx[n] + 1 :]
            sections += ["\n".join(contents)]

        return headers, sections

    centers = [
        "Indications",
        "Indications and Clinical Use",
        "Contraindications",
        "Serious Warnings and Precautions Box",
        "Dosage And Administration",
        "Overdosage",
        "Dosage Forms, Strenths, Composition, and Packaging",
        "Warnings and Precautions",
        "Warnings",
        "Precautions",
        "Adverse Reactions",
        "Drug Interactions",
        "Clinical Pharmacology",
        "Storage, Stability and Disposal",
        "Special Handling Instructions",
        "Pharmaceutical Information",
        "Clinical Trials",
        "Microbiology",
        "Non-clinical Toxicology",
        "Supporting Product Monographs",
        "Summary Product Information",
        "Toxicology",
        "Description",
    ]

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

    def fix_headers(self, headers, sections):
        label_text = {}
        for h, s in zip(headers, sections):
            header = self.get_fixed_header(h)
            if (header is not None) and (len(s) > 0):
                logger.info(f"Found original header ({h}) fixed to {header}")
                if header not in label_text.keys():
                    label_text[header] = [s]
                else:
                    label_text[header].append(s)
        return label_text

    def process_hc_pdf_file(self, hc_file, source_product_number, lp, pdf_url=""):
        raw_text = []
        label_text = {}  # next level = product page w/ metadata

        try:
            raw_text = read_pdf(hc_file, no_margins=False, no_annex=False)

            info = {}
            product_code = source_product_number

            headers, sections = [], []
            # Match headers that start with section numbers (e,g, 4.1)
            headers, sections = get_pdf_sections(raw_text, pattern=r"^[1-9][0-9]?\.?\s+[A-Z].*")
            label_text = self.fix_headers(headers, sections)

            # With the above method, it should at least find 10 sections, if less than that,
            #  then parse it with other method
            if len(label_text) < 10:
                logger.info("Failed to parse. Using another method...")
                # Method that parses for headers with more rigid regular expressions
                headers, sections = self.get_pdf_sections_with_format(
                    raw_text, OTHER_FORMATTED_SECTIONS
                )
                label_text = self.fix_headers(headers, sections)
                if len(label_text) == 0:
                    raise PDFParseException("Failed to parse pdf with both methods")

            for index, key in enumerate(label_text):
                text_block = ""
                # label_text[key] is an array of text. Convert it to a block of text
                for s in label_text[key]:
                    text_block += s
                ps = ProductSection(label_product=lp, section_name=key, section_text=text_block)
                ps.save()

            info["Label Text"] = label_text
            self.records[product_code] = info
            logger.info(f"{hc_file} parsed Successfully")
        except PDFParseException as e:
            logger.error(self.style.ERROR(repr(e)))
            logger.error(self.style.ERROR(f"Failed to process {hc_file}, url = {pdf_url}"))
            self.error_urls[pdf_url] = True
            parsing_error, created = ParsingError.objects.get_or_create(
                url=pdf_url,
                message=repr(e),
                source_product_number=source_product_number,
                error_type="pdf_error",
            )
            if created:
                logger.warning(f"Created ParsingError {parsing_error}")
            else:
                logger.warning(
                    f"Failed to create ParsingError {parsing_error} - likely already exists"
                )
        except Exception as e:
            logger.error(self.style.ERROR(repr(e)))
            logger.error(self.style.ERROR(f"Failed to process {hc_file}, url = {pdf_url}"))
            self.error_urls[pdf_url] = True
        return raw_text
