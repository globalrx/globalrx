import logging
from distutils.util import strtobool

from django.core.management.base import BaseCommand

from elasticsearch import logger as es_logger

from search.utils.provision_es import create_index, populate_index


es_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sets up ElasticSearch indices and provisions them with data"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)

    def add_arguments(self, parser):
        parser.add_argument(
            "--agency", type=str, help="'TGA', 'FDA', 'EMA', or 'all'", default="all"
        )
        parser.add_argument(
            "--delete_and_recreate_index",
            type=strtobool,
            help="Whether to delete and recreate the productsection index",
            default=False,
        )
        parser.add_argument(
            "--mapping_file",
            type=str,
            help="Path to the mapping file",
            default="/app/search/mappings/provision.json",
        )

    def handle(self, *args, **options):
        agency = options["agency"]
        delete_and_recreate_index = options["delete_and_recreate_index"]
        mapping_file = options["mapping_file"]

        logger.info(
            f"Provisioning index 'productsection' - agency: {agency} - delete_and_recreate_index: {delete_and_recreate_index}"
        )
        # Index must exist to index documents
        res = create_index(
            "productsection", mapping_file=mapping_file, recreate=delete_and_recreate_index
        )
        if not res:
            logger.warning("Did not create or delete/recreate index 'productsection'")
        else:
            logger.info("Index creation response:")
            logger.info(res)
            logger.info(res.body)

        logger.info(f"Populating index with agency: {agency}")
        populate_index(index_name="productsection", agency=agency)
