from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import setup_test_environment
from django.core.files.storage import default_storage
from django.conf import settings
import time
import datetime as dt
import logging
import random

logger = logging.getLogger(__name__)

PERF_TEST_CSV = "perf_test.csv"
PERF_TEST_PNG = "perf_test.png"

SECTIONS = [
    "OTHER",
    "INDICATIONS",
    "DOSAGE",
    "WARN",
    "DESCRIPTION",
    "CLINICAL PHARMACOLOGY",
    "PHARMACOKINETICS",
    "PRECAUTIONS",
    "CONTRA",
    "POSE",
]
SEARCH_TEXTS_ONE_WORD = [
    "kidney",
    "bone",
    "heart",
    "lung",
    "death",
    "birth",
    "pregnancy",
    "warning",
    "health",
    "doctor",
]
SEARCH_TEXTS_TWO_WORDS = [
    "kidney disease",
    "bone cancer",
    "atrial fibrillation",
    "lung cancer",
    "death certificate",
    "heart disease",
    "birth affects",
    "serious warning",
    "health affects",
    "doctor visit",
]
AGENCIES = ["FDA", "EMA"]

# select marketer, count(*) from data_druglabel group by 1 order by 2 desc limit 10;
MARKETERS = [
    "bryant ranch prepack",
    "A-S Medication Solutions",
    "REMEDYREPACK INC.",
    "NuCare Pharmaceuticals,Inc.",
    "Proficient Rx LP",
    "Physicians Total Care, Inc.",
    "Aphena Pharma Solutions - Tennessee, LLC",
    "PD-Rx Pharmaceuticals, Inc.",
    "Denton Pharma, Inc. DBA Northwind Pharmaceuticals",
    "Direct Rx",
]

# select generic_name, count(*) from data_druglabel group by 1 order by 2 desc limit 10;
GENERIC_NAMES = [
    "OXYGEN",
    "Gabapentin",
    "Metformin Hydrochloride",
    "bupropion hydrochloride",
    "Ibuprofen",
    "Prednisone",
    "Lisinopril",
    "Diclofenac Sodium",
    "acyclovir",
    "Hydrochlorothiazide",
]

# select product_name, count(*) from data_druglabel group by 1 order by 2 desc limit 10;
PRODUCT_NAMES = [
    "Gabapentin",
    "Oxygen",
    "Metformin Hydrochloride",
    "Prednisone",
    "Lisinopril",
    "ATORVASTATIN CALCIUM ",
    "Ciprofloxacin",
    "Ibuprofen",
    "cyclobenzaprine hydrochloride",
    "HYDROCHLOROTHIAZIDE",
]

TEST_QUERIES = [
    # select_section=&search_text=&select_agency=&manufacturer_input=&generic_name_input=&brand_name_input=

    # one word NLP search
    # - all sections
    # - single section
    # - all sections + manufacturer
    # - single section + manufacturer
    # - all sections + generic
    # - single section + generic
    # - all sections + 4 inputs
    # - single section + 4 inputs
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },

    # two word NLP search
    # - all sections
    # - single section
    # - all sections + manufacturer
    # - single section + manufacturer
    # - all sections + generic
    # - single section + generic
    # - all sections + 4 inputs
    # - single section + 4 inputs
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },

    # three word NLP search
    # - all sections
    # - single section
    # - all sections + manufacturer
    # - single section + manufacturer
    # - all sections + generic
    # - single section + generic
    # - all sections + 4 inputs
    # - single section + 4 inputs
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },

    # two word exact match search
    # - all sections
    # - single section
    # - all sections + manufacturer
    # - single section + manufacturer
    # - all sections + generic
    # - single section + generic
    # - all sections + 4 inputs
    # - single section + 4 inputs
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + '"',
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },

    # three word exact match search
    # - all sections
    # - single section
    # - all sections + manufacturer
    # - single section + manufacturer
    # - all sections + generic
    # - single section + generic
    # - all sections + 4 inputs
    # - single section + 4 inputs
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"' + random.choice(SEARCH_TEXTS_TWO_WORDS) + " " + random.choice(SEARCH_TEXTS_ONE_WORD) + '"',
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
]

# runs with `python manage.py performance_tests`
# e.g. `python manage.py performance_tests --verbosity 2 --num_runs 3`
# `--num_runs X` sets the number of runs
# `--verbosity 2` gives info output
# `--verbosity 3` gives debug output
# `--skip_tests True` skips the tests, so we can just do the plot
# `--make_plot False` skips making the plot
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
        parser.add_argument(
            "--make_plot", type=bool, help="set to True to make plot", default=True
        )
        parser.add_argument(
            "--skip_tests",
            type=bool,
            help="set to True to skip the testing",
            default=False,
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
        make_plot = options["make_plot"]
        skip_tests = options["skip_tests"]
        self.set_log_verbosity(int(options["verbosity"]))
        logger.info(self.style.SUCCESS("start process"))

        if not skip_tests:
            self.run_tests(num_runs)

        # make_plot is not going to run the tests
        # will use perf_test.csv from previous run(s)
        if make_plot:
            self.make_plot()

        logger.info(self.style.SUCCESS("process complete"))

    def run_tests(self, num_runs):
        # we want to run a number of performance tests
        # output response times to a file
        # create a set of test queries
        # calculate how long each takes to run
        # run them again
        # print a file to output the times in csv
        # query_0, query1, query2

        output_file = settings.MEDIA_ROOT / PERF_TEST_CSV
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

    def make_plot(self):
        logger.info("running make_plot")
        file = settings.MEDIA_ROOT / PERF_TEST_CSV
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.read_csv(file, header=None)
        num_rows = df.shape[0]
        num_cols = df.shape[1]

        x = []
        y = []
        x_avg = []
        y_avg = []
        # skip the first column
        for col in range(1, num_cols):
            logger.info(f"average query time; col: {col}; value: {df[col].mean()}")
            x_avg.append(col)
            y_avg.append(df[col].mean())

            for row in range(num_rows):
                logger.debug(f"row: {row}; col: {col}; value: {df[col][row]}")
                x.append(col)
                y.append(df[col][row])

        total_avg = sum(y_avg) / len(y_avg)
        logger.info(f"total average query time: {total_avg}")

        plt.figure(figsize=(16, 6))
        plt.scatter(x, y, label="query time")
        plt.scatter(x_avg, y_avg, label="avg query time per query")
        plt.axhline(total_avg, label="avg query time")
        plt.title("Performance testing")
        plt.xlabel("Queries")
        plt.ylabel("time to complete query (seconds)")
        plt.legend(loc="best")

        fig_file = settings.MEDIA_ROOT / PERF_TEST_PNG
        plt.savefig(fig_file)
