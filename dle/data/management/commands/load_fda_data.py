from bs4 import BeautifulSoup
from contextlib import closing
from datetime import datetime, timedelta
import logging
import shutil
import urllib.request as request
import os
from zipfile import ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.utils import IntegrityError, OperationalError

from data.models import (
    DrugLabel,
    DrugLabelDoc,
    DrugLabelRawText,
    LabelProduct,
    ProductSection,
)

logger = logging.getLogger(__name__)

# runs with `python manage.py load_fda_data --type {type}`
class Command(BaseCommand):
    help = "Loads data from FDA"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)
        root_logger.setLevel(logging.DEBUG)
        self.root_dir = settings.MEDIA_ROOT / "fda"
        os.makedirs(self.root_dir, exist_ok=True)
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument(
            "--type", type=str, help="full, monthly, or test", default="monthly"
        )

    """
    Entry point into class from command line
    """

    def handle(self, *args, **options):
        import_type = options["type"]
        root_zips = self.download_records(import_type)

        for root_zip in root_zips:
            record_zips = self.extract_prescription_zips(root_zip)
            for record_zip in record_zips:
                xml_files = self.extract_xmls(record_zip)
                self.import_records(xml_files)

                # cleanup
                logger.debug(f"remove: {record_zip}")
                os.remove(record_zip)
                for file in xml_files:
                    logger.debug(f"remove: {file}")
                    os.remove(file)

        logger.info("DONE")

    def download_records(self, import_type):
        logger.info("Downloading bulk archives.")
        file_dir = self.root_dir / import_type
        os.makedirs(file_dir, exist_ok=True)
        records = []

        if import_type == "full":
            for i in range(1, 5):
                archive_url = f"ftp://public.nlm.nih.gov/nlmdata/.dailymed/dm_spl_release_human_rx_part{i}.zip"
                records.append(self.download_single_zip(archive_url, file_dir))
        elif import_type == "monthly":
            now = datetime.now()
            prev_month_lastday = now.replace(day=1) - timedelta(days=1)
            month, year = (
                prev_month_lastday.strftime("%b").lower(),
                prev_month_lastday.year,
            )
            archive_url = f"ftp://public.nlm.nih.gov/nlmdata/.dailymed/dm_spl_monthly_update_{month}{year}.zip"
            records.append(self.download_single_zip(archive_url, file_dir))
        elif import_type == "test":
            archive_url = f"ftp://public.nlm.nih.gov/nlmdata/.dailymed/dm_spl_daily_update_10262021.zip"
            records.append(self.download_single_zip(archive_url, file_dir))
            archive_url = f"ftp://public.nlm.nih.gov/nlmdata/.dailymed/dm_spl_daily_update_10182021.zip"
            records.append(self.download_single_zip(archive_url, file_dir))
        else:
            raise CommandError("Type must be one of 'full', 'monthly', or 'test'")

        return records

    def download_single_zip(self, ftp, dest):
        url_filename = ftp.split("/")[-1]
        file_path = dest / url_filename

        if os.path.exists(file_path):
            logger.info(f"File already exists: {file_path}. Skipping.")
            return file_path

        # Download the drug labels archive file
        with closing(request.urlopen(ftp)) as r:
            with open(file_path, "wb") as f:
                logger.info(f"Downloading {ftp} to {file_path}")
                shutil.copyfileobj(r, f)
        return file_path

    """
    Daily Med will package it's bulk and monthly into groups of zips. This step is neccesary to
    extract individual drug label zips from the bulk archive.
    """

    def extract_prescription_zips(self, zip_file):
        logger.info("Extracting prescription Archives")
        file_dir = self.root_dir / "record_zips"
        os.makedirs(file_dir, exist_ok=True)
        record_zips = []

        with ZipFile(zip_file, "r") as zip_file_object:
            for file_info in zip_file_object.infolist():
                if file_info.filename.startswith(
                    "prescription"
                ) and file_info.filename.endswith(".zip"):
                    outfile = file_dir / os.path.basename(file_info.filename)
                    file_info.filename = os.path.basename(file_info.filename)
                    if os.path.exists(outfile):
                        logger.info(f"Record Zip already exists: {outfile}. Skipping.")
                    else:
                        logger.info(f"Creating Record Zip {outfile}")
                        zip_file_object.extract(file_info, file_dir)
                    record_zips.append(outfile)
        return record_zips

    def extract_xmls(self, zip_file):
        logger.info("Extracting XMLs")
        file_dir = self.root_dir / "xmls"
        os.makedirs(file_dir, exist_ok=True)
        xml_files = []

        with ZipFile(zip_file, "r") as zip_file_object:
            for file in zip_file_object.namelist():
                if file.endswith(".xml"):
                    outfile = file_dir / file
                    if os.path.exists(outfile):
                        logger.info(f"XML already exists: {outfile}. Skipping.")
                    else:
                        logger.info(f"Creating XML {outfile}")
                        zip_file_object.extract(file, file_dir)
                    xml_files.append(outfile)
        return xml_files

    def import_records(self, xml_records, user_id=None):
        logger.info("Building Drug Label DB records from XMLs")
        for xml_file in xml_records:
            with open(xml_file) as f:
                content = BeautifulSoup(f.read(), "lxml")
                dld = DrugLabelDoc()
                dld.source = "FDA"

                dld.product_name = content.find("subject").find("name").text

                # TODO should be a many to 1 instead of text
                try:
                    generic_name = content.find("genericmedicine").find("name").text
                except AttributeError:
                    # don't insert record if we cannot find this
                    logger.error("unable to find generic_name")
                    continue

                dld.generic_name = generic_name[:255]

                try:
                    dld.version_date = datetime.strptime(
                        content.find("effectivetime").get("value"), "%Y%m%d"
                    )
                except ValueError:
                    dld.version_date = datetime.now()

                dld.source_product_number = content.find(
                    "code", attrs={"codesystem": "2.16.840.1.113883.6.69"}
                ).get("code")

                try:
                    dld.marketer = content.find("author").find("name").text
                except AttributeError:
                    dld.marketer = "_"

                root = content.find("setid").get("root")
                dld.link = (
                    f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={root}"
                )

                try:
                    dld.save()
                    lp = LabelProduct(drug_label=dld)
                    lp.save()
                    texts = [p.text for p in content.find_all("paragraph")]
                    raw_text = "\n".join(texts)
                    rt = DrugLabelRawText(drug_label=dld, raw_text=raw_text)
                    rt.save()
                    dl = DrugLabel.from_child(dld)
                    dl.save()
                    logger.debug(f"Saving new drug label: {dl}")
                except (IntegrityError, OperationalError) as e:
                    logger.error(str(e))
                    continue

                for section in content.find_all("component"):
                    if section.find("title") is None:
                        continue
                    raw_section_texts = [p.text for p in section.find_all("paragraph")]
                    section_texts = "\n".join(raw_section_texts)
                    section_name = section.find("title").text
                    section_name = section_name[:42]
                    ps = ProductSection(
                        label_product=lp,
                        section_name=section_name,
                        section_text=section_texts,
                    )

                    try:
                        ps.save()
                    except OperationalError as e:
                        logger.error(str(e))
