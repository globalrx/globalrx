import datetime
import logging
import random
import re
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

import fitz  # PyMuPDF
import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ChunkedEncodingError

from data.models import DrugLabel, LabelProduct, ProductSection
from users.models import MyLabel

import pdfplumber
from Levenshtein import distance as levdistance
import json

logger = logging.getLogger(__name__)

EMA_EPAR_EXCEL_URL = "https://www.ema.europa.eu/sites/default/files/Medicines_output_european_public_assessment_reports.xlsx"

# runs with `python manage.py load_ema_data`
# add `--type full` to import the full dataset
# add `--type rand_test` to import 3 random records
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
# support for my_labels with: --type my_label --my_label_id ml.id
class Command(BaseCommand):
    help = "Loads data from EMA"
    
    records = {}
    df = []

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
            help="'full', 'test', 'rand_test' or 'my_label'",
            default="test",
        )
        parser.add_argument(
            "--my_label_id",
            type=int,
            help="set my_label_id for --type my_label",
            default=None,
        )
        parser.add_argument(
            "--dump_json",
            type=bool,
            help="Dump all parsed outputs to a json file",
            default=False,
        )
    def handle(self, *args, **options):
        import_type = options["type"]
        if import_type not in ["full", "test", "rand_test", "my_label"]:
            raise CommandError("'type' parameter must be 'full', 'test', 'rand_test' or 'my_label'")

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

        # Read ema excel into df
        self.read_ema_excel()

        if import_type == "test":
            urls = [
                "https://www.ema.europa.eu/en/medicines/human/EPAR/skilarence",
                "https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica",
                "https://www.ema.europa.eu/en/medicines/human/EPAR/ontilyv",
            ]
        elif import_type == "my_label":
            my_label_id = options["my_label_id"]
            ml = MyLabel.objects.filter(pk=my_label_id).get()

            ema_file = ml.file.path
            dl = ml.drug_label

            lp = LabelProduct(drug_label=dl)
            lp.save()

            dl.raw_text = self.process_ema_file(ema_file, lp)
            dl.save()

            # TODO would be nice to know if the file was successfully parsed
            ml.is_successfully_parsed = True
            ml.save()
            logger.info(self.style.SUCCESS("process complete"))
            return
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
            except IntegrityError as e:  # noqa: F841
                logger.warning(self.style.WARNING("Label already in db"))
                # logger.debug(e, exc_info=True)
            except AttributeError as e:
                logger.warning(self.style.ERROR(repr(e)))
            # logger.info(f"sleep 1s")
            # time.sleep(1)

        for url in self.error_urls.keys():
            logger.warning(self.style.WARNING(f"error parsing url: {url}"))

        logger.info(f"num_drug_labels_parsed: {self.num_drug_labels_parsed}")
        logger.info(self.style.SUCCESS("process complete"))

        if(options["dump_json"] == True):
            logger.info(self.style.SUCCESS("Outputing parsed data to human-rx-drug-ema.json"))
            with open('human-rx-drug-ema.json', 'w') as f:
                json.dump(self.records, f, indent=4)

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
            cell = tag.find_next("td", string=re.compile(r"\sMarketing-authorisation holder\s"))
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

        ema_file = settings.MEDIA_ROOT / "ema.pdf"
        raw_text = self.process_ema_file(ema_file, lp, pdf_url)
        # delete the file when done
        default_storage.delete(filename)
        return raw_text

    centers = [
        'Clinical Particulars',
        'Contraindications',
        'Date Of First Authorisation/Renewal Of The Authorisation',
        'Date Of Revision Of The Text',
        'Effects On Ability To Drive And Use Machines',
        'Fertility, Pregnancy And Lactation',
        'Incompatibilities',
        'Interaction With Other Medicinal Products And Other Forms Of Interaction',
        'List Of Excipients',
        'Marketing Authorisation Holder',
        'Marketing Authorisation Number',
        'Name Of The Medicinal Product',
        'Nature And Contents Of Container',
        'Overdose',
        'Pharmaceutical Form',
        'Pharmaceutical Particulars',
        'Pharmacodynamic Properties',
        'Pharmacokinetic Properties',
        'Pharmacological Properties',
        'Posology And Method Of Administration',
        'Preclinical Safety Data',
        'Pregnancy And Lactation',
        'Qualitative And Quantitative Composition',
        'Shelf Life',
        'Special Precautions For Disposal',
        'Special Precautions For Disposal And Other Handling',
        'Special Precautions For Storage',
        'Special Warnings And Precautions For Use',
        'Therapeutic Indications',
        'Undesirable Effects'
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
        dists = [levdistance(text.lower(),c.lower()) for c in self.centers]
        #ix = np.argmin(dists)
        ix = dists.index(min(dists))
        if dists[ix] > 0.6*len(text):
            return None
        else:
            return self.centers[ix]

    # function: input text, output list of section headers and content
    def get_smpc_sections(self, text):
        idx, headers, sections = [], [], []
        for i,line in enumerate(text):
            if re.match('^[0-9]+\.[0-9]*\s+.*[A-Z].*', line):
                idx += [i]
                headers += [line.strip()]
        
        # in headers, must increment or restart, and not end in punctuation
        idx_valid, headers_valid = [idx[0]], [headers[0]]
        for n in range(1,len(headers)):
            prev = float(headers[n-1].split()[0])
            curr = float(headers[n].split()[0])
            lastchar = headers[n].strip()[-1].lower()
            valid = (prev < curr <= prev+1) or (curr==1)
            valid = valid and (lastchar in 'qwertyuiopasdfghjklzxcvbnm()')
            if valid:
                idx_valid.append(idx[n])
                headers_valid.append(headers[n])
        idx, headers = idx_valid, headers_valid
        
        for n,h in enumerate(headers):
            if (n+1)<len(headers):
                contents = text[idx[n]+1:idx[n+1]]
            else:
                contents = text[idx[n]+1:]
            sections += ['\n'.join(contents)]
        
        return headers, sections

    # helper function for pdfplumber
    def remove_tables(self, page):
        ts = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
        bboxes = [table.bbox for table in page.find_tables(table_settings=ts)]
        
        def not_within_bboxes(obj):
            #Check if the object is in any of the table's bbox.
            def obj_in_bbox(_bbox):
                #See https://github.com/jsvine/pdfplumber/blob/stable/pdfplumber/table.py#L404
                v_mid = (obj["top"] + obj["bottom"]) / 2
                h_mid = (obj["x0"] + obj["x1"]) / 2
                x0, top, x1, bottom = _bbox
                return (h_mid >= x0) and (h_mid < x1) and (v_mid >= top) and (v_mid < bottom)
            return not any(obj_in_bbox(__bbox) for __bbox in bboxes)
        
        return page.filter(not_within_bboxes)

    # helper function for pdfplumber    
    def remove_margins(self, page, dpi=72, size=0.7):
        # strip 0.7 inches from top and bottom (page numbers, header text if any), A4 is 8.25 x 11.75
        # syntax is page.crop((x0, top, x1, bottom))
        w = float(page.width)/dpi
        h = float(page.height)/dpi
        return page.crop((0, (size)*dpi, w*dpi, (h-size)*dpi))


    # function: input file, output text of annex 1
    def read_smpc(self, filename, no_blanks=False, no_tables=False):
        text = []
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                page = self.remove_margins(page)
                
                if no_tables:
                    page = self.remove_tables(page)
                    
                page_text = page.extract_text().split('\n')
                text += page_text

        annex_lines = [re.match('.*ANNEX\s+I.*', line) is not None for line in text]
        annex_index = [i for i,v in enumerate(annex_lines) if v]
        
        text = text[annex_index[0]:annex_index[1]]
        if no_blanks:
            text = [line for line in text if not line.isspace()]
        
        return text

    def process_ema_file(self, ema_file, lp, pdf_url=""):
        text = self.read_smpc(ema_file)
        
        try:
            info = {}
            product_code = lp.drug_label.source_product_number
            row = self.df[self.df["Product number"] == product_code]
            info['metadata'] = row.iloc[0].apply(str).to_dict()
            
            label_text = {} # next level = product page w/ metadata
            headers, sections = self.get_smpc_sections(text)

            for h,s in zip(headers,sections):
                header = self.get_fixed_header(h)
                if (header is not None) and (len(s)>0):
                    if header not in label_text.keys():
                        label_text[header] = [s]
                        ps = ProductSection(
                            label_product=lp, section_name=header, section_text=s
                        )
                        ps.save()
                    else:
                        label_text[header].append(s)
            info['Label Text'] = label_text
            self.records[row['Product number'].iloc[0]] = info
        except:
            logger.error(self.style.ERROR(f"Failed to process {ema_file}, url = {pdf_url}"))
            self.error_urls[pdf_url] = True

        logger.info("Success")
        return text

    def read_ema_excel(self):
        """Download the EMA provided Excel file and grab the urls from there"""
        # return a list of the epar urls, e.g. ["https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica"]
        # load excel file into pandas, directly from url
        # there are some header rows to skip
        # only load the columns we are interested in
        self.df = pd.read_excel(
            EMA_EPAR_EXCEL_URL,
            skiprows=8,
            usecols=["Category", "Authorisation status", "Product number", "URL"],
            engine="openpyxl",
        )
        # filter results by:
        # "Category" == "Human"
        # "Authorisation status" == "Authorised"
        self.df = self.df[self.df["Category"] == "Human"]
        # TODO verify we only want "Authorised" medicines
        self.df = self.df[self.df["Authorisation status"] == "Authorised"]
        
    def get_ema_epar_urls(self):
        return self.df["URL"]
