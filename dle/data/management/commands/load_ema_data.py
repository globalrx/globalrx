from django.core.management.base import BaseCommand, CommandError
from data.models import DrugLabel, LabelProduct, ProductSection
import datetime
import requests
import PyPDF2
from io import BytesIO

EMA_DATA_URL = "https://www.ema.europa.eu/en/medicines/field_ema_web_categories%253Aname_field/Human/ema_group_types/ema_medicine"

# 3 sample data urls/pdfs for testing
SAMPLE_1 = "https://www.ema.europa.eu/en/medicines/human/EPAR/skilarence"
PDF_1 = "https://www.ema.europa.eu/en/documents/product-information/skilarence-epar-product-information_en.pdf"

SAMPLE_2 = "https://www.ema.europa.eu/en/medicines/human/EPAR/lyrica"
PDF_2 = "https://www.ema.europa.eu/documents/product-information/lyrica-epar-product-information_en.pdf"

SAMPLE_3 = "https://www.ema.europa.eu/en/medicines/human/EPAR/ontilyv"
PDF_3 = "https://www.ema.europa.eu/documents/product-information/ontilyv-epar-product-information_en.pdf"

PDFS = [PDF_1, PDF_2, PDF_3]

# runs with `python manage.py load_ema_data`
class Command(BaseCommand):
    help = "Loads data from EMA"

    def handle(self, *args, **options):
        # WIP
        response = requests.get(PDF_1)
        pdf_data = response.content

        text = ""
        num_pages = 0
        # ref: https://stackoverflow.com/a/64997181/1807627
        # ref: https://stackoverflow.com/q/9751197/1807627
        # ref: https://www.geeksforgeeks.org/how-to-scrape-all-pdf-files-in-a-website/
        with BytesIO(pdf_data) as data:
            pdf_reader = PyPDF2.PdfFileReader(data)
            # just curious
            pdf_info = pdf_reader.getDocumentInfo()
            self.stdout.write(f"pdf_info: {pdf_info}")
            for page in range(pdf_reader.getNumPages()):
                num_pages += 1
                page_text = pdf_reader.getPage(page).extractText()
                text += page_text
                text_sample = page_text[0:100]
                self.stdout.write(f"page: {num_pages}")
                self.stdout.write(f"page_sample: {text_sample}")

        self.stdout.write(f"total pages: {num_pages}")

        today = datetime.date.today()
        self.stdout.write(f"today: {today}")

        self.load_fake_drug_label()

        self.stdout.write(self.style.SUCCESS("Success"))

    def load_fake_drug_label(self):
        # For now, just loading one dummy-label
        dl = DrugLabel(
            source='EMA',
            product_name='Diffusia',
            generic_name='lorem ipsem',
            version_date='2022-03-15',
            source_product_number='ABC-123-DO-RE-ME',
            raw_text='Fake raw label text',
            marketer='Landau Pharma',
        )
        dl.save()
        lp = LabelProduct(drug_label=dl)
        lp.save()
        ps = ProductSection(
            label_product=lp,
            section_name='INDICATIONS',
            section_text='Cures cognitive deficit disorder'
        )
        ps.save()
        ps = ProductSection(
            label_product=lp,
            section_name='WARN',
            section_text='May cause x, y, z'
        )
        ps.save()
        ps = ProductSection(
            label_product=lp,
            section_name='PREG',
            section_text='Good to go'
        )
        ps.save()
