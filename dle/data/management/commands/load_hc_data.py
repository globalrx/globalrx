from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from requests.exceptions import ChunkedEncodingError
from data.models import (
    DrugLabel,
    LabelProduct,
    ProductSection,
)
from users.models import MyLabel
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
import string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import json

logger = logging.getLogger(__name__)

HC_BASE_URL = "https://health-products.canada.ca"
HC_SEARCH_URL = "https://health-products.canada.ca/dpd-bdpp/search/"
HC_RESULT_URL = "https://health-products.canada.ca/dpd-bdpp/dispatch-repartition"

EU_FORMATTED_SECTIONS = [
    # notes for the re pattern:
    # escape the period we want to match e.g. "1.0" => r"1\.0"
    # look for one or more whitespace characters r"\s+"
    # find any characters (one or more times) r"(.+)" with re.DOTALL flag
    # stop when we find the closing string
    (r"(4\.1\.?\s+(?:THERAPEUTIC\sINDICATIONS|Therapeutic\s[i|I]ndications)\s)(.+)(\n4\.2\.?\s+(DOSE\sAND\sMETHOD\sOF\sADMINISTRATION|Dose\s[a|A]nd\s[m|M]ethod\s[o|O]f\s[a|A]dministration)\s)", "Indications"),
    (r"(4\.2\.?\s+(?:DOSE\sAND\sMETHOD\sOF\sADMINISTRATION|Dose\s[a|A]nd\s[m|M]ethod\s[o|O]f\s[a|A]dministration)\s)(.+)(\n4\.3\.?\s+(CONTRAINDICATIONS|Contraindications)\s)", "Posology"),
    (r"(4\.3\.?\s+(?:CONTRAINDICATIONS|Contraindications)\s)(.+)(\n4\.4\.?\s+(SPECIAL\sWARNINGS\sAND\sPRECAUTIONS\sFOR\sUSE|[s|S]pecial\s[w|W]arnings\s[a|A]nd\s[p|P]recautions\s[f|F]or\s[u|U]se)\s)", "Contraindications"),
    (r"(4\.4\.?\s+(?:SPECIAL\sWARNINGS\sAND\sPRECAUTIONS\sFOR\sUSE|[s|S]pecial\s[w|W]arnings\s[a|A]nd\s[p|P]recautions\s[f|F]or\s[u|U]se)\s)(.+)(\n4\.5\.?\s+(INTERACTIONS\s+WITH\s+OTHER\s+MEDICINES(?:\s+AND\s+OTHER\s+FORMS\s+OF\s+INTERACTIONS)?|Interations\s+[w|W]ith\s+[o|O]ther\s+[m|M]edicines(?:\s+[a|A]nd\s+[o|O]ther\s+[f|F]orms\s+[o|O]f\s+[i|I]nterations)?)\s)", "Warnings"),
    (r"(4\.5\.?\s+(?:INTERACTIONS\s+WITH\s+OTHER\s+MEDICINES(?:\s+AND\s+OTHER\s+FORMS\s+OF\s+INTERACTIONS)?|Interations\s+[w|W]ith\s+[o|O]ther\s+[m|M]edicines(?:\s+[a|A]nd\s+[o|O]ther\s+[f|F]orms\s+[o|O]f\s+[i|I]nterations)?)\s)(.+)(\n4\.6\.?\s+(FERTILITY,\s?PREGNANCY,?\s?AND\sLACTATION|[f|F]ertility,\s?[p|P]regnancy\sand\s[l|L]actation)\s)", "Interactions"),
    (r"(4\.6\.?\s+(?:FERTILITY, PREGNANCY AND LACTATION|[f|F]ertility, [p|P]regnancy and [l|L]actation)\s)(.+)(\n4\.7\.?\s+(EFFECTS\sON\sABILITY\sTO\sDRIVE\sAND\sUSE\sMACHINES|[e|E]ffects [o|O]n [a|A]bility [t|T]o [d|D]rive [a|A]nd [u|U]se [m|M]achines)\s)", "Pregnancy"),
    (r"(4\.7\.?\s+(?:EFFECTS\sON\sABILITY\sTO\sDRIVE\sAND\sUSE\sMACHINES|[e|E]ffects [o|O]n [a|A]bility [t|T]o [d|D]rive [a|A]nd [u|U]se [m|M]achines)\s)(.+)(\n4\.8\.?\s+(ADVERSE EFFECTS \(UNDESIRABLE EFFECTS\)|[a|A]dverse [e|E]ffects)\s)", "Effects on driving"),
    (r"(4\.8\.?\s+(?:ADVERSE EFFECTS \(UNDESIRABLE EFFECTS\)|[a|A]dverse [e|E]ffects)\s)(.+)(\n4\.9\.?\s+(OVERDOSE|Overdose)\s)", "Side effects"),
    (r"(4\.9\.?\s+(?:OVERDOSE|Overdose)\s)(.+)(\n5\.?\s+PHARMACOLOGICAL)", "Overdose")
]

OTHER_FORMATTED_SECTIONS = [
    (r"(INDICATIONS)(.+)(CONTRAINDICATIONS)", "Indications"),
    (r"(CONTRAINDICATIONS)(.+)(PRECAUTIONS)", "Contraindications"),
    # Pregnancy, Interactions and Effects on driving are all under the PRECAUTIONS section
    (r"(Use in [p|P]regnancy)(.+)(Use in [l|L]actation)", "Pregnancy"),
    (r"(Interactions with other medicines)(.+)(Effects on laboratory tests)", "Interactions"),
    (r"(Effects on ability to drive and use machines)(.+)(ADVERSE (REACTIONS|EFFECTS))", "Effects on driving"),
    (r"(PRECAUTIONS)(.+)(ADVERSE (REACTIONS|EFFECTS))", "Warnings"),
    (r"(ADVERSE (?:REACTIONS|EFFECTS))(.+)(DOSAGE AND ADMINISTRATION)", "Side effects"),
    (r"(DOSAGE AND ADMINISTRATION)(.+)(OVERDOSAGE)", "Posology"),
    (r"(OVERDOSAGE)(.+)(PRESENTATION)", "Overdose")
]

# runs with `python manage.py load_tga_data`
# add `--type full` to import the full dataset
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    help = "Loads data from TGA"
    pdf_counter = 0
    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.num_drug_labels_parsed = 0
        "keep track of the number of labels processed"
        self.error_urls = {}
        "dictionary to keep track of the urls that have parsing errors; form: {url: True}"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            help="'full'",
            default="full",
        )

    def handle(self, *args, **options):
        import_type = options["type"]
        if import_type not in ["full"]:
            raise CommandError(
                "'type' parameter must be 'full'"
            )

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
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(HC_SEARCH_URL)
        time.sleep(1)
        # Click the approve field
        approved_status_field = driver.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[1]/div/select/option[2]')
        approved_status_field.click()
        # Unclick the select all field
        select_all_status_field = driver.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[1]/div/select/option[1]')
        ActionChains(driver).key_down(Keys.CONTROL).click(select_all_status_field).key_up(Keys.CONTROL).perform()

        # Click the human field
        human_class_field = driver.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[7]/div/select/option[3]')
        human_class_field.click()
        # Unclick the select all field
        select_all_class_field = driver.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[3]/form/fieldset[3]/div[7]/div/select/option[1]')
        ActionChains(driver).key_down(Keys.CONTROL).click(select_all_class_field).key_up(Keys.CONTROL).perform()

        # Click the search button
        search_button = driver.find_element_by_xpath('/html/body/main/div[1]/div[1]/div[3]/form/div[1]/div/input[1]')
        search_button.click()

        # Wait a bit for it to load
        time.sleep(5)

        # Grab the result webpage
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        table_attrs = json.loads(table.get("data-wb-tables"))
        num_displayed_results = table_attrs["iDisplayLength"]
        num_total_results = table_attrs["iDeferLoading"]
    
        drug_label_parsed = 0
        # Iterate all the drugs in the table
        while(drug_label_parsed != num_total_results):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table")
            table_body = table.find("tbody")
            rows = table_body.find_all("tr")
            # Iterate all the products in the table
            for row in rows:
                try:
                    dl = self.get_drug_label_from_row(row)
                    logger.debug(repr(dl))
                    # dl.link is url of pdf
                    # for now, assume only one LabelProduct per DrugLabel
                    lp = LabelProduct(drug_label=dl)
                    lp.save()
                    if(dl.link == ""):
                        raise ValueError(f"{dl.product_name} doesn't have a PDF label")
                    dl.raw_text = self.get_and_parse_pdf(dl.link, lp)
                    dl.save()
                    self.num_drug_labels_parsed += 1
                except IntegrityError as e:
                    logger.warning(self.style.WARNING("Label already in db"))
                    logger.debug(e, exc_info=True)
                except AttributeError as e:
                    logger.warning(self.style.ERROR(repr(e)))
                except ValueError as e:
                    logger.warning(self.style.WARNING(repr(e)))
                #logger.info(f"sleep 1s")
                #time.sleep(1)
                drug_label_parsed += 1
            # Click the next button
            next_button = driver.find_element_by_id('results_next')
            if next_button and drug_label_parsed != num_total_results:
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
        print(dl.product_name)
        # The column under DIN is a clickable link to the drug details
        link_to_drug_details = HC_BASE_URL + columns[1].find('a')['href']
        response = requests.get(link_to_drug_details)
        soup = BeautifulSoup(response.text, "html.parser")
        divs = soup.findAll('div', attrs={"class":"row"})
        # Get the version date and the pdf link
        dl.version_date = ""
        dl.link = ""
        for div in divs:
            ps = div.findAll('p', attrs={"class":"col-sm-8"})
            for p in ps:
                if(p.find("strong")):
                    if("Date" in p.find("strong").text):
                        spans = p.findAll('span')
                        dl.version_date = spans[0].text
                        dl.link = spans[1].find('a')['href']
        # If version date is not available, then get the status date instead 
        if(dl.version_date == ""):
            for div in divs:
                p1 = div.find('p', attrs={"class":"col-sm-4"})
                if(p1 and p1.find("strong") and p1.find("strong").text == "Current status date:"):
                    p = div.find('p', attrs={"class":"col-sm-8"})
                    dl.version_date = p.text

        # Get all the active ingredient(s)
        div = soup.find('div', attrs={"class":"table-responsive mrgn-tp-lg"})
        table = div.find('table')
        rows = table.findAll("tr")
        active_ingredients = ""
        for row in rows:
            if(row.find("td")):
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

    def get_and_parse_pdf(self, pdf_url, lp):
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

        filename = default_storage.save(
            settings.MEDIA_ROOT / f"hc_{self.pdf_counter}.pdf", ContentFile(response.content)
        )
        logger.info(f"saved file to: {filename}")
        hc_file = settings.MEDIA_ROOT / filename
        raw_text = self.process_hc_pdf_file(hc_file, lp, pdf_url)
        self.pdf_counter += 1
        # delete the file when done
        #default_storage.delete(filename)
        return raw_text

    def process_hc_pdf_file(self, tga_file, lp, pdf_url=""):
        raw_text = ""
        logger.info("process_hc_pdf_file Stubbed out")

        return raw_text