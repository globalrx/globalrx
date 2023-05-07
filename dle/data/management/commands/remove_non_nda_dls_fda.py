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
        total_records = 0
        all_records_to_delete = []
        all_ndas = []
        self.multiple_ndcs = 0

        for file in os.listdir(file_dir):
            json_file = file_dir / file
            raw_json_result = None
            with open(json_file, encoding="utf-8-sig") as f:
                raw_json_result = json.load(f)
                logger.info(f"start loading json {json_file}")
            raw_json_result = raw_json_result["results"]
            logger.info(f"Finished loading {json_file}")

            total_records += len(raw_json_result)

            # Filter out non-NDA labels
            logger.info("Filtering non-NDA labels")
            records_to_delete, ndas = self.filter_data(raw_json_result)
            all_records_to_delete.extend(records_to_delete)
            all_ndas.extend(ndas)

            # logger.info(f"Total records in JSON: {len(raw_json_result)}")

            # logger.info(f"NDA count: {len(ndas)}")
            # records_keep = DrugLabel.objects.filter(source_product_number__in=ndas)
            # logger.info(f"NDA matches: {records_keep.count()}")

            # logger.info(f"Records to delete: {len(records_to_delete)}")
            # Delete the records
            # Still testing ...
            # self.delete_data(records_to_delete)
            # logger.info(f"Finished deleting {json_file}")
        logger.info(f"Total records in JSONs: {total_records}")
        logger.info(f"Total FDA DLs in Django: {DrugLabel.objects.all().count()}")
        logger.info(f"NDA count: {len(all_ndas)}")
        logger.info(
            f"NDA matches in Django: {DrugLabel.objects.filter(source_product_number__in=all_ndas).count()}"
        )
        logger.info(f"Non-NDA count: {len(all_records_to_delete)}")
        logger.info(
            f"Non-NDA matches in Django, to delete: {DrugLabel.objects.filter(source_product_number__in=all_records_to_delete).count()}"
        )
        logger.info(f"Records with multiple NDCs: {self.multiple_ndcs}")

    def filter_data(self, raw_json_result):
        # create a list of records to delete
        # only records that start with NDA should be kept
        # return two lists, the NDAs and not NDAs
        product_ndcs_to_delete = []
        product_ndcs_to_keep = []
        for record in raw_json_result:
            try:
                application_num_list = record["openfda"]["application_number"]
                if len(application_num_list) > 1:
                    logger.info(f"More than one application number: {application_num_list}")
                    raise TypeError
                application_num = application_num_list[0]
                if len(record["openfda"]["product_ndc"]) > 1:
                    # logger.info(f"Multiple NDCs")
                    self.multiple_ndcs += 1
                ndc = record["openfda"]["product_ndc"][0]
                if not application_num.startswith("NDA"):
                    product_ndcs_to_delete.append(ndc)
                else:
                    product_ndcs_to_keep.append(ndc)
            except KeyError:
                # logger.info(f"KeyError - no application_number: {record['openfda']}")
                pass
            except TypeError:
                # logger.info(f"TypeError - multiple application_numbers: {record['openfda']}")
                pass
        return product_ndcs_to_delete, product_ndcs_to_keep

    def delete_data(self, product_ndcs_to_delete):
        # delete the records
        logger.info(f"Test - {len(product_ndcs_to_delete)} DLs to try to delete")
        records = DrugLabel.objects.filter(source_product_number__in=product_ndcs_to_delete)
        logger.info(f"Test - {records.count()} DLs matched")
        # records.delete()

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
