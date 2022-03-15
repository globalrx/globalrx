from django.core.management.base import BaseCommand, CommandError
from data.models import DrugLabel, LabelProduct, ProductSection
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import datetime
import requests
import fitz # PyMuPDF
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

# only doing a few to start
# dictionary of {pdf_text -> product_section}
EMA_PDF_PRODUCT_SECTIONS = {
    "4.1 Therapeutic indications": "INDICATIONS",
    "4.3 Contraindications": "CONTRA",
    "4.4 Special warnings and precautions for use": "WARN",
    "4.6 Fertility, pregnancy and lactation": "PREG",
}

# runs with `python manage.py load_ema_data`
class Command(BaseCommand):
    help = "Loads data from EMA"

    def handle(self, *args, **options):
        # WIP

        # save pdf to default_storage / MEDIA_ROOT
        response = requests.get(PDF_1)
        filename = default_storage.save(settings.MEDIA_ROOT / "ema.pdf", ContentFile(response.content))
        self.stdout.write(f"saved file to: {filename}")

        raw_text = ""
        with fitz.open(settings.MEDIA_ROOT / "ema.pdf") as pdf_doc:
            for page in pdf_doc:
                raw_text += page.getText().strip()

        self.stdout.write(f"raw_text: {raw_text}")
        self.process_ema_text(raw_text)

        # delete the file when done
        default_storage.delete(filename)

        self.stdout.write(self.style.SUCCESS("Success"))
        return

        # ref: https://stackoverflow.com/a/64997181/1807627
        # ref: https://stackoverflow.com/q/9751197/1807627
        # ref: https://www.geeksforgeeks.org/how-to-scrape-all-pdf-files-in-a-website/

        # try to save to MEDIA dir, then open
        # ty: https://stackoverflow.com/a/63486976/1807627
        # https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/text-extraction/PDF2Text.py
        # https://github.com/pymupdf/PyMuPDF/blob/master/fitz/fitz.i


    def process_ema_text(self, raw_text):
        pass

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
