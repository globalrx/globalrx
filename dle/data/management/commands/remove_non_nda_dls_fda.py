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
from tqdm import tqdm

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

        logger.info(f"Total records in JSONs: {total_records}")
        logger.info(f"Total FDA DLs in Django: {DrugLabel.objects.filter(source='FDA').count()}")
        logger.info(f"JSON records with multiple NDCs: {self.multiple_ndcs}")
        logger.info(f"NDA in JSON count: {len(all_ndas)}")
        logger.info(
            f"NDA matches in Django: {DrugLabel.objects.filter(source_product_number__in=all_ndas).count()}"
        )
        logger.info(f"Non-NDA in JSON count: {len(all_records_to_delete)}")
        logger.info(
            f"Non-NDA matches in Django, to delete: {DrugLabel.objects.filter(source_product_number__in=all_records_to_delete).count()}"
        )

        # Try this, might error on RAM if QuerySet is too large
        # Also getting: django.db.utils.OperationalError: sending query and params failed: number of parameters must be between 0 and 65535
        # List of ndc ids is too long

        # delete_results = DrugLabel.objects.filter(source_product_number__in=all_records_to_delete).delete()
        # logger.info(f"Delete results: {delete_results}")

        # progressbar = tqdm(total=to_del.count())
        # for dl in to_del.iterator(chunk_size=1000):
        #     dl.delete()
        #     progressbar.update(1)

        # Slow but works
        to_del = DrugLabel.objects.filter(source="FDA").filter(
            source_product_number__in=all_records_to_delete
        )
        progressbar = tqdm(total=to_del.count())
        logger.info(f"Deleting {to_del.count()} records ...")
        while (
            DrugLabel.objects.filter(source="FDA")
            .filter(source_product_number__in=all_records_to_delete)
            .count()
        ):
            ids = (
                DrugLabel.objects.filter(source="FDA")
                .filter(source_product_number__in=all_records_to_delete)
                .values_list("pk", flat=True)[0:1000]
            )
            DrugLabel.objects.filter(pk__in=ids).delete()
            progressbar.update(1000)

        logger.info(f"Completed deleting {to_del.count()}")

    def filter_data(self, raw_json_result):
        # create a list of records to delete
        # only records that start with NDA should be kept
        # also filter and only include DLs with "is_original_packager" and "human_prescription_drug"
        # return two lists, the NDAs and not NDAs
        product_ndcs_to_delete = []
        product_ndcs_to_keep = []
        for record in raw_json_result:
            try:
                if len(record["openfda"]["product_ndc"]) > 1:
                    # logger.info(f"Multiple NDCs")
                    self.multiple_ndcs += 1
                application_num_list = record["openfda"]["application_number"]
                if len(application_num_list) > 1:
                    logger.info(f"More than one application number: {application_num_list}")
                    raise TypeError
                application_num = application_num_list[0]
                ndc = record["openfda"]["product_ndc"][0]
                if not application_num.startswith("NDA"):
                    product_ndcs_to_delete.append(ndc)
                elif "is_original_packager" not in record["openfda"].keys():
                    product_ndcs_to_delete.append(ndc)
                elif not self.check_type(record) == "human_prescription_drug":
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

    def check_type(self, res):
        # Taken from load_fda_data
        if "product_type" not in res["openfda"].keys():
            return "uncategorized_drug"
        pt = res["openfda"]["product_type"]
        if type(pt) == float:
            return "uncategorized_drug"
        if type(pt) == list:
            assert len(pt) == 1
            return pt[0].lower().replace(" ", "_")
        else:
            logger.info(f"Problem determining type: {pt}")

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
