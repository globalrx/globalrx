from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import setup_test_environment
import time
import logging
import random
import threading
from .performance_tests import (
    SECTIONS,
    SEARCH_TEXTS_ONE_WORD,
    SEARCH_TEXTS_TWO_WORDS,
    AGENCIES,
    MARKETERS,
    GENERIC_NAMES,
    PRODUCT_NAMES,
)

logger = logging.getLogger(__name__)


# runs with `python manage.py load_tests`
# e.g. `python manage.py load_tests --verbosity 2 --num_threads 3`
# `--num_threads X` sets the number of runs
# `--verbosity 2` gives info output
# `--verbosity 3` gives debug output
class Command(BaseCommand):
    help = "Runs load tests"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = Client()
        setup_test_environment()
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)

    def add_arguments(self, parser):
        parser.add_argument(
            "--num_threads", type=int, help="number of test threads", default=7
        )

    def set_log_verbosity(self, verbosity):
        """
        basic logging config is in settings.py
        verbosity is 1 by default, gives critical, error and warning output
        `--verbosity 2` gives info output
        `--verbosity 3` gives debug output
        """
        root_logger = logging.getLogger("")
        if verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)

    def handle(self, *args, **options):
        num_threads = options["num_threads"]
        self.set_log_verbosity(int(options["verbosity"]))
        logger.info(self.style.SUCCESS("start process"))

        for i in range(num_threads):
            query_obj = self.get_query_obj()
            new_thread = threading.Thread(target=self.run_query, args=[query_obj])
            # self.run_query(query_obj)
            new_thread.start()

        logger.info(self.style.SUCCESS("process complete"))

    def run_query(self, query_obj):
        start_time = time.perf_counter()
        response = self.client.get("/search/results", query_obj)
        end_time = time.perf_counter()
        query_time = end_time - start_time

        try:
            logger.info(
                f"num search results: {len(response.context['search_results'])}"
            )
        except (KeyError, TypeError):
            logger.info(f"NO search results found")

        logger.info(f"query_time: {str(round(query_time, 3))}")

    def get_query_obj(self):
        return {
            "select_section": random.choice(SECTIONS),
            "search_text": '"'
            + random.choice(SEARCH_TEXTS_TWO_WORDS)
            + " "
            + random.choice(SEARCH_TEXTS_ONE_WORD)
            + '"',
            "select_agency": random.choice(AGENCIES),
            "manufacturer_input": random.choice(MARKETERS),
            "generic_name_input": random.choice(GENERIC_NAMES),
            "brand_name_input": random.choice(PRODUCT_NAMES),
        }
