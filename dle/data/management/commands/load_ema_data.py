from django.core.management.base import BaseCommand, CommandError
from data.models import DrugLabel, LabelProduct, ProductSection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
import re
import datetime

# pip install bs4
# pip install pymupdf


EMA_DATA_URL = "https://www.ema.europa.eu/en/medicines/field_ema_web_categories%253Aname_field/Human/ema_group_types/ema_medicine"


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
class Command(BaseCommand):
    help = "Loads data from EMA"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.drug_label_idx = 0

    def handle(self, *args, **options):
        # get the next url to parse the data from EMA website
        # while loop terminates when get_next_drug_label_url returns None or False
        while url := self.get_next_drug_label_url():
            self.stdout.write(f"processing url: {url}")
            dl = self.get_drug_label_from_url(url)
            self.stdout.write(self.style.SUCCESS(repr(dl)))
            # dl.link is url of pdf
            # for now, assume only one LabelProduct per DrugLabel
            lp = LabelProduct(drug_label=dl)
            lp.save()
            self.parse_pdf(dl.link, lp)
            # TODO need to consider how to handle errors, log unexpected results
        return

    def get_drug_label_from_url(self, url):
        dl = DrugLabel() # empty object to populate as we go
        dl.source = 'EMA'

        # grab the webpage
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # self.stdout.write(soup.prettify())
        # self.stdout.write(repr(soup))

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
        # self.stdout.write(repr(str))
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
        cell = tag.find_next("td", string=re.compile(r"\sMarketing-authorisation holder\s"))
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
        sub_str = entry[len(date_str_key):].strip()
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
        response = requests.get(pdf_url)
        filename = default_storage.save(
            settings.MEDIA_ROOT / "ema.pdf", ContentFile(response.content)
        )
        self.stdout.write(f"saved file to: {filename}")

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
            self.stdout.write(f"section.name: {section.name}")
            self.stdout.write(f"looking for section.start_text: {section.start_text}")
            idx = raw_text.find(section.start_text, start_idx)
            if idx == -1:
                self.stderr.write(self.style.ERROR("Unable to find section_start_text"))
                continue
            else:
                self.stdout.write(self.style.SUCCESS(f"Found section.start_text, idx: {idx}"))

            # look for section_end_text
            self.stdout.write(f"looking for section.end_text: {section.end_text}")
            end_idx = raw_text.find(section.end_text, idx)
            if end_idx == -1:
                self.stderr.write(self.style.ERROR("Unable to find section.end_text"))
                continue
            else:
                self.stdout.write(self.style.SUCCESS(f"Found section.end_text, end_idx: {end_idx}"))

            # the section_text is between idx and end_idx
            section_text = raw_text[idx: end_idx]
            self.stdout.write(f"found section_text: {section_text}")
            ps = ProductSection(
                label_product=lp,
                section_name=section.name,
                section_text=section_text
            )
            ps.save()

            # start search for next section after the end_idx of this section
            start_idx = end_idx

        # self.stdout.write(f"raw_text: {repr(raw_text)}")

        # delete the file when done
        default_storage.delete(filename)

        self.stdout.write(self.style.SUCCESS("Success"))
        return

    def load_fake_drug_label(self):
        # For now, just loading one dummy-label
        dl = DrugLabel(
            source="EMA",
            product_name="Diffusia",
            generic_name="lorem ipsem",
            version_date="2022-03-15",
            source_product_number="ABC-123-DO-RE-ME",
            raw_text="Fake raw label text",
            marketer="Landau Pharma",
        )
        dl.save()
        lp = LabelProduct(drug_label=dl)
        lp.save()
        ps = ProductSection(
            label_product=lp,
            section_name="INDICATIONS",
            section_text="Cures cognitive deficit disorder",
        )
        ps.save()
        ps = ProductSection(
            label_product=lp, section_name="WARN", section_text="May cause x, y, z"
        )
        ps.save()
        ps = ProductSection(
            label_product=lp, section_name="PREG", section_text="Good to go"
        )
        ps.save()

    def get_next_drug_label_url(self):
        """For now, only supporting 3 hard-coded EMA drug labels"""

        # 3 sample data urls for testing
        if self.drug_label_idx == 0:
            url = "https://www.ema.europa.eu/en/medicines/human/EPAR/skilarence"
        elif self.drug_label_idx == 1:
            url = "https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica"
        elif self.drug_label_idx == 2:
            url = "https://www.ema.europa.eu/en/medicines/human/EPAR/ontilyv"
        else:
            url = None

        self.drug_label_idx += 1
        return url
