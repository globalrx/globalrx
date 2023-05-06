import json
import logging
import os
import shutil
import urllib.request as request
from contextlib import closing
from distutils.util import strtobool
from zipfile import ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand

import requests

from data.models import DrugLabel


logger = logging.getLogger(__name__)

FDA_JSON_URL = "https://api.fda.gov/download.json"


# python manage.py remove_non_nda_dls_fda --cleanup True
class Command(BaseCommand):
    help = """Removes non-NDA drug labels from OpenFDA data. Should be a one-time run to clean up data,
    as future runs will already filter to only include NDA (innovator) labels.
    """

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        self.root_dir = settings.MEDIA_ROOT / "fda"
        os.makedirs(self.root_dir, exist_ok=True)
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument("--cleanup", type=strtobool, help="Set to cleanup files", default=False)

    def handle(self, *args, **options):
        self.cleanup = options["cleanup"]

        # Download and extract JSON data if it doesn't exist
        dl_json = json.loads(requests.get(FDA_JSON_URL).text)
        labels_json = dl_json["results"]["drug"]["label"]
        urls = [x["file"] for x in labels_json["partitions"]]
        json_zips = self.download_json(urls)
        self.extract_json_zips(json_zips)
        file_dir = self.root_dir / "record_zips"

        # Iterate the json files in the directory one by one
        # Build a list of records to delete
        for file in os.listdir(file_dir):
            json_file = file_dir / file
            raw_json_result = None
            with open(json_file, encoding="utf-8-sig") as f:
                raw_json_result = json.load(f)
                logger.info(f"start loading json {json_file}")
            raw_json_result = raw_json_result["results"]
            logger.info(f"Finished loading {json_file}")

            # Filter out non-NDA labels
            logger.info("Filtering non-NDA labels")
            records_to_delete = self.filter_data(raw_json_result)
            logger.info(f"Records to delete: {len(records_to_delete)}")
            logger.info("Sample --------")
            logger.info(records_to_delete[0:100])
            # Delete the records
            break
            # self.delete_data(records_to_delete)
            # logger.info(f"Finished deleting {json_file}")

    def filter_data(self, raw_json_result):
        # create a list of records to delete
        # only records that start with NDA should be kept
        app_nums_to_delete = []
        for record in raw_json_result:
            try:
                application_num = record["openfda"]["application_number"]
                if not application_num.startswith("NDA"):
                    app_nums_to_delete.append(application_num)
            except KeyError:
                logger.info(f"KeyError - no application_number: {record['openfda']}")
        return app_nums_to_delete

    def delete_data(self, records):
        # delete the records
        for record in records:
            application_num = record["metadata"]["application_number"]
            DrugLabel.objects.filter(source_product_number=application_num).delete()

    def download_json(self, urls):
        # Taken from load_fda_data
        logger.info("Downloading bulk archives.")
        file_dir = self.root_dir / "json_zip"
        os.makedirs(file_dir, exist_ok=True)
        records = []
        for url in urls:
            records.append(self.download_single_json(url, file_dir))
        return records

    def download_single_json(self, url, dest):
        # taken from load_fda_data
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
        # taken from load_fda_data
        logger.info("Extracting json zips")
        file_dir = self.root_dir / "record_zips"
        os.makedirs(file_dir, exist_ok=True)
        try:
            for zip_file in zips:
                with ZipFile(zip_file, "r") as zf:
                    for zobj in zf.infolist():
                        if os.path.exists(file_dir / zobj.filename):
                            logger.info(f"Already extracted file {zobj.filename}")
                        else:
                            zf.extract(zobj, file_dir)
                            logger.info(f"Extracted file {zobj.filename}")
        except Exception as e:
            logger.error("Failed while extracting json zips")
            logger.error(str(e))
            raise
