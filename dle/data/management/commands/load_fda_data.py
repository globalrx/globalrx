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
from django.db.utils import IntegrityError, OperationalError

from data.models import DrugLabel, LabelProduct, ProductSection
from data.constants import FDA_SECTION_NAMES

logger = logging.getLogger(__name__)


# runs with `python manage.py load_fda_data --type {type}`
class Command(BaseCommand):
    help = "Loads data from FDA"
    re_combine_whitespace = re.compile(r"\s+")
    re_remove_nonalpha_characters = re.compile('[^a-zA-Z ]')

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
        xml_files = self.extract_xmls(record_zips)
        # self.count_titles(xml_files)
        self.import_records(xml_files, insert=insert)
        # self.cleanup(record_zips)
        # self.cleanup(xml_files)
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

    def extract_prescription_zips(self, zips):
        logger.info("Extracting prescription Archives")
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
                            logger.info(f"Record Zip already exists: {outfile}. Skipping.")
                        else:
                            logger.info(f"Creating Record Zip {outfile}")
                            zip_file_object.extract(file_info, file_dir)
                        record_zips.append(outfile)
        return record_zips

    def extract_xmls(self, zips):
        logger.info("Extracting XMLs")
        file_dir = self.root_dir / "xmls"
        os.makedirs(file_dir, exist_ok=True)
        xml_files = []

        for zip_file in zips:
            with ZipFile(zip_file, 'r') as zip_file_object:
                for file in zip_file_object.namelist():
                    if file.endswith(".xml"):
                        outfile = file_dir / file
                        if (os.path.exists(outfile)):
                            logger.info(f"XML already exists: {outfile}. Skipping.")
                        else:
                            logger.info(f"Creating XML {outfile}")
                            zip_file_object.extract(file, file_dir)
                        xml_files.append(outfile)
        return xml_files

    def count_titles(self, xml_records):
        titles = []
        m = 4000
        for xml_file in xml_records:
            try:
                with open(xml_file) as f:
                    content = BeautifulSoup(f.read(), 'lxml')
                    codes = content.find_all("code", attrs={"codesystem": "2.16.840.1.113883.6.1"})
                    for code in codes:
                        my_str = str(code.get("displayname")).upper()
                        my_str = self.re_combine_whitespace.sub(" ", my_str).strip()
                        my_str = self.re_remove_nonalpha_characters.sub("", my_str)
                        my_str = self.re_combine_whitespace.sub(" ", my_str).strip()
                        titles.append(my_str)
            except Exception as e:
                logger.error("Error")
                raise e
            m = m - 1
            if m % 250 == 0:
                logger.info(m)
            if m < 0:
                break
        import collections
        counter = collections.Counter(titles)
        logger.info(counter.most_common(10))
        import csv
        with open("top_displaynames.csv", "w") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(["displayname", "count"])
            csvwriter.writerows(counter.most_common(1000))

    def import_records(self, xml_records, user_id=None, insert=False):
        logger.info("Building Drug Label DB records from XMLs")

        for xml_file in xml_records:
            try:
                with open(xml_file) as f:
                    content = BeautifulSoup(f.read(), "lxml")
                    dl = DrugLabel()
                    dl.source = "FDA"
                    dl.product_name = content.find("subject").find("name").text.upper()
                    try:
                        generic_name = content.find("genericmedicine").find("name").text
                    except AttributeError:
                        # don't insert record if we cannot find this
                        logger.error("unable to find generic_name")
                        continue
                    dl.generic_name = generic_name[:255]

                    try:
                        dl.version_date = datetime.strptime(content.find("effectivetime").get("value"), "%Y%m%d")
                    except ValueError:
                        dl.version_date = datetime.now()

                    try:
                        dl.marketer = content.find("author").find("name").text.upper()
                    except AttributeError:
                        dl.marketer = ""
                    dl.source_product_number = content.find("code", attrs={"codesystem": "2.16.840.1.113883.6.69"}).get(
                        "code")

                    texts = [p.text for p in content.find_all("paragraph")]
                    dl.raw_text = "\n".join(texts)

                    lp = LabelProduct(drug_label=dl)

                    root = content.find("setid").get("root")
                    dl.link = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={root}"

                    try:
                        if insert:
                            dl.save()
                            logger.info(f"Saving new drug label: {dl}")
                    except IntegrityError as e:
                        logger.error(str(e))
                        continue

                    try:
                        if insert:
                            lp.save()
                            logger.info(f"Saving new label product")
                    except IntegrityError as e:
                        logger.error(str(e))
                        continue

                    # In the following section we will build the different sections. We do this by matching XML components
                    # to predetermined FDA_SECTION_NAMES, and for components that do not match, we add them to an "OTHER"
                    # category
                    section_map = {}
                    for section in content.find_all("component"):
                        code = section.find("code", attrs={"codesystem": "2.16.840.1.113883.6.1"})
                        if code is None:
                            continue
                        title = str(code.get("displayname")).upper()
                        title = self.re_combine_whitespace.sub(" ", title).strip()
                        title = self.re_remove_nonalpha_characters.sub("", title)
                        title = self.re_combine_whitespace.sub(" ", title).strip()

                        if title not in FDA_SECTION_NAMES:
                            section_name = "OTHER"
                        else:
                            section_name = title

                        # Now that we have determined what section, grab all the text in the component and add it as the
                        # value to a corresponding hashmap. If a value already exists, add it to the end
                        raw_section_texts = [str(p) for p in section.find_all("text")]
                        section_texts = "<br>".join(raw_section_texts)

                        # Save other titles in section text
                        if section_name == "OTHER":
                            section_texts = title + "<br>" + section_texts

                        # Save to keyed section of map, concatenating repeat sections
                        if section_map.get(section_name) is None:
                            section_map[section_name] = section_texts
                        else:
                            if section_name is not "OTHER":
                                logger.debug(f"Found another section: {section_name}\twith title\t{title}")
                            section_map[section_name] = section_map[section_name] + f"<br>{title}<br>" + section_texts

                    # Now that the sections have been parsed, save them
                    for section_name, section_text in section_map.items():
                        ps = ProductSection(label_product=lp, section_name=section_name.upper(),
                                            section_text=section_text)
                        try:
                            if insert:
                                ps.save()
                                logger.debug(f"Saving new product section {ps}")
                        except IntegrityError as e:
                            logger.error(str(e))
                        except OperationalError as e:
                            logger.error(str(e))

            except Exception as e:
                logger.error(f"Could not parse {xml_file}")
                logger.error(str(e));
                continue;

        def cleanup(self, files):
            for file in files:
                logger.debug(f"remove: {file}")
                os.remove(file)
