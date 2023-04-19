import logging
import os
import re
import shutil
import json
import requests
import urllib.request as request
from contextlib import closing
from datetime import datetime, timedelta
from distutils.util import strtobool
from zipfile import ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError, OperationalError

from bs4 import BeautifulSoup

from data.constants import FDA_SECTION_NAME_MAP
from data.models import DrugLabel, LabelProduct, ProductSection
from users.models import MyLabel


logger = logging.getLogger(__name__)


# python manage.py load_fda_data --type test --cleanup False --insert False --count_titles True
# python manage.py load_fda_data --type my_label --my_label_id 9 --cleanup False --insert False
# runs with `python manage.py load_fda_data --type {type}`
class Command(BaseCommand):
    help = "Loads data from FDA"
    re_combine_whitespace = re.compile(r"\s+")
    re_remove_nonalpha_characters = re.compile("[^a-zA-Z ]")
    dl_json_url = 'https://api.fda.gov/download.json'
    dl_json = json.loads(requests.get(dl_json_url).text)
    drugs_json = dl_json['results']['drug']
    labels_json = dl_json['results']['drug']['label']
    urls = [x['file'] for x in labels_json['partitions']]

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)

        self.root_dir = settings.MEDIA_ROOT / "fda"
        os.makedirs(self.root_dir, exist_ok=True)
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument(
            "--type", type=str, help="full, monthly, test or my_label", default="monthly"
        )
        parser.add_argument("--insert", type=strtobool, help="Set to connect to DB", default=True)
        parser.add_argument("--cleanup", type=strtobool, help="Set to cleanup files", default=False)
        parser.add_argument(
            "--my_label_id", type=int, help="set my_label_id for --type my_label", default=None
        )
        parser.add_argument(
            "--count_titles",
            type=strtobool,
            help="output counts of the section_names",
            default=False,
        )

    """
    Entry point into class from command line
    """

    def handle(self, *args, **options):
        insert = options["insert"]
        dl_json_url = 'https://api.fda.gov/download.json'
        dl_json = json.loads(requests.get(dl_json_url).text)
        #drugs_json = dl_json['results']['drug']
        labels_json = dl_json['results']['drug']['label']
        urls = [x['file'] for x in labels_json['partitions']]
        json_zips = self.download_json(urls)
        self.extract_json_zips(json_zips)
        file_dirs = self.root_dir / "record_zips"
        #file_dirs = os.listdir(file_dir)
        logger.info(f'file_dirs: {file_dirs}')
        record_zips = self.combine_jsons(file_dirs)
        filtered_records = self.filter_data(record_zips)
        self.import_records(filtered_records, insert)

        cleanup = options["cleanup"]
        logger.debug(f"options: {options}")


        if cleanup:
            self.cleanup(record_zips)
            self.cleanup(filtered_records)

        logger.info("DONE")

    def download_json(self, urls):
        logger.info("Downloading bulk archives.")
        file_dir = self.root_dir / "json_zip"
        os.makedirs(file_dir, exist_ok=True)
        records = []
        for url in urls:
            records.append(self.download_single_json(url, file_dir))
        return records
    
    def download_single_json(self, url, dest):
        url_filename = url.split("/")[-1]
        file_path = dest / url_filename
        if os.path.exists(file_path):
            logger.info(f"File already exists: {file_path}. Skipping.")
            return file_path       
         # Download the drug labels archive file
        with closing(request.urlopen(url)) as r:
            with open(file_path, "wb") as f:
                logger.info(f"Downloading {url} to {file_path}")
                shutil.copyfileobj(r, f)
        return file_path
    
    def extract_json_zips(self, zips):
        logger.info("Extracting json zips")
        file_dir = self.root_dir / "record_zips"
        os.makedirs(file_dir, exist_ok=True)
        for zip_file in zips:
            with ZipFile(zip_file, "r") as zf:
                for zobj in zf.infolist():
                    if os.path.exists(file_dir / zobj.filename):
                        logger.info(f'Already extracted file {zobj.filename}')
                    else:
                        zf.extract(zobj, file_dir)
                        logger.info(f'Extracted file {zobj.filename}')
        #return file_dir

    def combine_jsons(self, file_dir):
        record_zips = []
        for file in os.listdir(file_dir):
            logger.info(f'File: {file}')
            with open(file_dir / file, encoding='utf-8') as f:
                j = json.load(f)
                logger.info("start:::")
                record_zips += j['results']
                logger.info("finished one")
                break
        return record_zips
    
    def filter_data(self, record_zips):
        results_by_type = {}
        for res in record_zips:
            product_type = self.check_type(res)
            if product_type not in results_by_type.keys():
                results_by_type[product_type] = [res]
            else:
                results_by_type[product_type].append(res)
        #%% we only care about the prescription drugs, save to disk
        drugs_ref= results_by_type['human_prescription_drug']
        drugs = []
        for dg in drugs_ref:
            if 'is_original_packager' in dg['openfda'].keys():
                drugs.append(dg)

        errors = []
        records = {}
        # restructure to match ema format and save to disk
        for drug in drugs:
            try:
                info = {}
                info['metadata'] = drug['openfda']
                info['metadata']['effective_time'] = drug['effective_time']

                label_text = {}
                for key,val in drug.items():
                    # for my purposes I didn't need tables (mostly html formatting)
                    if (type(val)==list) and ('table' not in key):
                        label_text[key] = list(set(val)) # de-duplicate contents
                info['Label Text'] = label_text
                records[drug['id']] = info
            except:
                errors += [drug]
        return records

    def check_type(self, res):
        if 'product_type' not in res['openfda'].keys():
            return 'uncategorized_drug'
        pt = res['openfda']['product_type']
        if type(pt)==float:
            return 'uncategorized_drug'
        if type(pt)==list:
            assert(len(pt)==1)
            return(pt[0].lower().replace(' ','_'))
        else:
            logger.info(f'Problem determining type: {pt}')

    
    def import_records(self, jsons, insert):
        logger.info("Building Drug Label DB records from XMLs")
        for key in jsons.keys():
            json_file = jsons[key]
            try:
                dl = DrugLabel()
                self.process_json_file(json_file, dl, insert)
            except Exception as e:
                logger.error(f"Could not parse {json_file}")
                logger.error(str(e))
                continue
            
    def process_json_file(self, json_file, dl, insert):
        dl.source = "FDA"
        dl.product_name = json_file['metadata']['brand_name']
        dl.generic_name = json_file['metadata']['generic_name']
        dl.version_date = datetime.strptime(json_file['metadata']['effective_time'], "%Y%m%d")
        dl.marketer = json_file['metadata']['manufacturer_name']
        dl.source_product_number = json_file['metadata']['product_ndc']
        application_num = json_file['metadata']['application_number'][0][4:]
        dl.link = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&varApplNo={application_num}"

        dl.raw_rext = ""
        lp = LabelProduct(drug_label=dl)
        try:
            if insert:
                dl.save()
                logger.info(f"Saving new drug label: {dl}")
        except IntegrityError as e:
            logger.error(str(e))
            return
        try:
            if insert:
                lp.save()
                logger.info("Saving new label product")
        except IntegrityError as e:
            logger.error(str(e))
            return
        # Now that the sections have been parsed, save them
        for key, value in enumerate(json_file['Label Text']):
            ps = ProductSection(
                label_product=lp,
                section_name=key,
                section_text=value,
            )
            try:
                if insert:
                    ps.save()
                    logger.debug(f"Saving new product section {ps}")
            except IntegrityError as e:
                logger.error(str(e))
            except OperationalError as e:
                logger.error(str(e))

    def cleanup(self, files):
        for file in files:
            logger.debug(f"remove: {file}")
            os.remove(file)
