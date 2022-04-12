from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import setup_test_environment
from django.core.files.storage import default_storage
from django.conf import settings
import time
import datetime as dt
import logging

logger = logging.getLogger(__name__)

TEST_QUERIES = [
    # select_section=&search_text=&select_agency=&manufacturer_input=&generic_name_input=&brand_name_input=
    {
        "select_section": "",
        "search_text": "kidney",
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "indications",
        "search_text": "heart disease",
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
]

# e.g. `python manage.py performance_tests --verbosity 2 --num_runs 4`
# runs with `python manage.py performance_tests`
# add `--num_runs 3` to run the tests 3 times
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    help = "Runs performance tests, outputs results to media/perf_test.csv"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = Client()
        setup_test_environment()

    def add_arguments(self, parser):
        parser.add_argument(
            "--num_runs", type=int, help="number of test runs", default=2
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
        num_runs = options["num_runs"]

        self.set_log_verbosity(int(options["verbosity"]))

        logger.info(self.style.SUCCESS("start process"))

        # we want to run a number of performance tests
        # output response times to a file
        # create a set of test queries
        # calculate how long each takes to run
        # run them again
        # print a file to output the times in csv
        # query_0, query1, query2

        output_file = settings.MEDIA_ROOT / "perf_test.csv"
        f = default_storage.open(output_file, "a")
        logger.info(f"saving data to: {output_file}")

        for i in range(num_runs):
            logger.info(f"run number: {i+1}")

            query_times = []
            # date_str is first column of output
            date_str = dt.datetime.now().strftime("%Y%m%d_%H%I%S")
            query_times.append(date_str)

            for query_obj in TEST_QUERIES:
                start_time = time.perf_counter()
                response = self.client.get("/search/results", query_obj)
                end_time = time.perf_counter()
                query_time = end_time - start_time
                query_times.append(str(round(query_time, 3)))
                logger.debug(f"response.content: {response.content}")
                logger.debug(f"response.context: {response.context}")

                try:
                    logger.info(
                        f"num search results: {len(response.context['search_results'])}"
                    )
                except (KeyError, TypeError):
                    logger.info(f"NO search results found")

            query_time_csv_str = ",".join(query_times) + "\n"
            f.write(query_time_csv_str)
