from bs4 import BeautifulSoup
from contextlib import closing
from datetime import datetime, timedelta
import logging
import re
import shutil
import urllib.request as request
import os
from zipfile import ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.utils import IntegrityError

from data.models import DrugLabel, LabelProduct, ProductSection, FDA_SECTION_NAMES


# runs with `python manage.py load_fda_data --type {type}`
class Command(BaseCommand):
    help = "Loads data from FDA"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S')
        self.root_dir = settings.MEDIA_ROOT / "fda"
        os.makedirs(self.root_dir, exist_ok=True)
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, help="full, monthly, or test", default="monthly")
        parser.add_argument('--insert', type=bool, help="Set to connect to DB", default=False)

    """
    Entry point into class from command line
    """

    def handle(self, *args, **options):
        import_type = options['type']
        insert = options['insert']
        root_zips = self.download_records(import_type)
        record_zips = self.extract_prescription_zips(root_zips)
        if(import_type == "test"):
            record_zips.extend([
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20120118_4c222831-90af-4336-8bf6-5628ddf24326.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20120118_4c222831-90af-4336-8bf6-5628ddf24326.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20210302_8bc4bed6-9a97-4aa1-b34d-6053bdb143a4.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20210417_36338030-20e2-4ddb-bc06-6c43be4f50a0.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20210611_3dd61fa5-1620-4ebf-bbdb-ede29b92fce2.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20210731_bc2b7a3d-72cf-497c-95b0-ba2b71f63c64.zip",
                "/Users/kennethbr/cs599/dle/dle/media/fda/record_zips/20211029_8df0ca6a-58cf-41fc-b890-5c7fa5a3792c.zip"
            ])
        xml_files = self.extract_xmls(record_zips)
        self.import_records(xml_files, insert=insert)
        logging.info("DONE")

    def download_records(self, import_type):
        logging.info("Downloading bulk archives.")
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
            logging.info(f"File already exists: {file_path}. Skipping.")
            return file_path

        # Download the drug labels archive file
        with closing(request.urlopen(ftp)) as r:
            with open(file_path, "wb") as f:
                logging.info(f"Downloading {ftp} to {file_path}")
                shutil.copyfileobj(r, f)
        return file_path

    """
    Daily Med will package it's bulk and monthly into groups of zips. This step is neccesary to
    extract individual drug label zips from the bulk archive.
    """

    def extract_prescription_zips(self, zips):
        logging.info("Extracting prescription Archives")
        file_dir = self.root_dir / "record_zips"
        os.makedirs(file_dir, exist_ok=True)
        record_zips = []

        for zip_file in zips:
            with ZipFile(zip_file, 'r') as zip_file_object:
                for file_info in zip_file_object.infolist():
                    if file_info.filename.startswith("prescription") and file_info.filename.endswith(".zip"):
                        outfile = file_dir / os.path.basename(file_info.filename)
                        file_info.filename = os.path.basename(file_info.filename)
                        if (os.path.exists(outfile)):
                            logging.info(f"Record Zip already exists: {outfile}. Skipping.")
                        else:
                            logging.info(f"Creating Record Zip {outfile}")
                            zip_file_object.extract(file_info, file_dir)
                        record_zips.append(outfile)
        return record_zips

    def extract_xmls(self, zips):
        logging.info("Extracting XMLs")
        file_dir = self.root_dir / "xmls"
        os.makedirs(file_dir, exist_ok=True)
        xml_files = []

        for zip_file in zips:
            with ZipFile(zip_file, 'r') as zip_file_object:
                for file in zip_file_object.namelist():
                    if file.endswith(".xml"):
                        outfile = file_dir / file
                        if (os.path.exists(outfile)):
                            logging.info(f"XML already exists: {outfile}. Skipping.")
                        else:
                            logging.info(f"Creating XML {outfile}")
                            zip_file_object.extract(file, file_dir)
                        xml_files.append(outfile)
        return xml_files

    def import_records(self, xml_records, user_id=None, insert=False):
        logging.info("Building Drug Label DB records from XMLs")
        for xml_file in xml_records:
            with open(xml_file) as f:
                content = BeautifulSoup(f.read(), "lxml")
                dl = DrugLabel()
                dl.source = "FDA"

                dl.product_name = content.find("subject").find("name").text

                dl.generic_name = content.find("genericmedicine").find("name").text

                dl.version_date = datetime.strptime(content.find("effectivetime").get("value"), "%Y%m%d")

                dl.source_product_number = content.find("code", attrs={"codesystem": "2.16.840.1.113883.6.69"}).get(
                    "code")

                texts = [p.text for p in content.find_all("paragraph")]
                dl.raw_text = "\n".join(texts)

                lp = LabelProduct(drug_label=dl)

                dl.marketer = content.find("author").find("name").text

                root = content.find("setid").get("root")
                dl.link = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={root}"

                try:
                    if insert:
                        dl.save()
                        logging.info(f"Saving new drug label: {dl}")
                except IntegrityError as e:
                    logging.error(str(e))
                    continue

                try:
                    if insert:
                        lp.save()
                        logging.info(f"Saving new label product")
                except IntegrityError as e:
                    logging.error(str(e))
                    continue

                # In the following section we will build the different sections. We do this by matching XML components
                # to predetermined FDA_SECTION_NAMES, and for components that do not match, we add them to an "OTHER"
                # category
                section_map = {}
                for section in content.find_all("component"):
                    if section.find("title") is None:
                        continue

                    # From the title of the component, find the corresponding section name
                    title = section.find("title").text.strip().upper()
                    match = None
                    section_name = None
                    for fda_section_name in FDA_SECTION_NAMES:
                        match = re.search(fda_section_name, title)
                        if match:
                            section_name = fda_section_name
                            break;
                    if match is None:
                        section_name = "OTHER"

                    # Now that we have determined what section, grab all the text in the component and add it as the
                    # value to a corresponding hashmap. If a value already exists, add it to the end
                    raw_section_texts = [p.text for p in section.find_all("paragraph")]
                    section_texts = "\n".join(raw_section_texts)
                    if section_map.get(section_name) is None:
                        section_map[section_name] = section_texts
                    else:
                        if section_name is not "OTHER":
                            logging.debug(f"Found another section: {section_name}\twith title\t{title}")
                        section_map[section_name] = section_map[section_name] + f"\n{title}\n" + section_texts

                # Now that the sections have been parsed, save them
                for section_name, section_text in section_map.items():
                    ps = ProductSection(label_product=lp, section_name=section_name.upper(), section_text=section_text)
                    try:
                        if insert:
                            ps.save()
                            logging.info(f"Saving new product section {ps}")
                    except IntegrityError as e:
                        logging.error(str(e))
