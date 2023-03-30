import datetime as dt
import logging
import random
import time

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import setup_test_environment


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
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD),
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
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": "",
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": random.choice(SECTIONS),
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": "",
        "manufacturer_input": "",
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": "",
    },
    {
        "select_section": "",
        "search_text": '"'
        + random.choice(SEARCH_TEXTS_TWO_WORDS)
        + " "
        + random.choice(SEARCH_TEXTS_ONE_WORD)
        + '"',
        "select_agency": random.choice(AGENCIES),
        "manufacturer_input": random.choice(MARKETERS),
        "generic_name_input": random.choice(GENERIC_NAMES),
        "brand_name_input": random.choice(PRODUCT_NAMES),
    },
    {
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
        parser.add_argument("--num_runs", type=int, help="number of test runs", default=2)
        parser.add_argument("--make_plot", type=bool, help="set to True to make plot", default=True)
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
                    logger.info(f"num search results: {len(response.context['search_results'])}")
                except (KeyError, TypeError):
                    logger.info("NO search results found")

            query_time_csv_str = ",".join(query_times) + "\n"
            f.write(query_time_csv_str)

    def make_plot(self):
        logger.info("running make_plot")
        file = settings.MEDIA_ROOT / PERF_TEST_CSV
        import matplotlib.pyplot as plt
        import pandas as pd

        df = pd.read_csv(file, header=None)
        num_rows = df.shape[0]
        num_cols = df.shape[1]

        column_label_map = {
            1: "all sections",
            2: "single section",
            3: "all sections + manufacturer",
            4: "single section + manufacturer",
            5: "all sections + generic",
            6: "single section + generic",
            7: "all sections + 4 inputs",
            8: "single section + 4 inputs",
            9: "all sections",
            10: "single section",
            11: "all sections + manufacturer",
            12: "single section + manufacturer",
            13: "all sections + generic",
            14: "single section + generic",
            15: "all sections + 4 inputs",
            16: "single section + 4 inputs",
            17: "all sections",
            18: "single section",
            19: "all sections + manufacturer",
            20: "single section + manufacturer",
            21: "all sections + generic",
            22: "single section + generic",
            23: "all sections + 4 inputs",
            24: "single section + 4 inputs",
            25: "all sections",
            26: "single section",
            27: "all sections + manufacturer",
            28: "single section + manufacturer",
            29: "all sections + generic",
            30: "single section + generic",
            31: "all sections + 4 inputs",
            32: "single section + 4 inputs",
            33: "all sections",
            34: "single section",
            35: "all sections + manufacturer",
            36: "single section + manufacturer",
            37: "all sections + generic",
            38: "single section + generic",
            39: "all sections + 4 inputs",
            40: "single section + 4 inputs",
        }
        # x and y values for each of the labels
        label_vals = {
            "all sections": [[], []],
            "single section": [[], []],
            "all sections + manufacturer": [[], []],
            "single section + manufacturer": [[], []],
            "all sections + generic": [[], []],
            "single section + generic": [[], []],
            "all sections + 4 inputs": [[], []],
            "single section + 4 inputs": [[], []],
        }

        # x = []
        # y = []
        x_avg = []
        y_avg = []
        # skip the first column
        for col in range(1, num_cols):
            logger.info(f"average query time; col: {col}; value: {df[col].mean()}")
            x_avg.append(col)
            y_avg.append(df[col].mean())

            for row in range(num_rows):
                logger.debug(f"row: {row}; col: {col}; value: {df[col][row]}")
                label = column_label_map[col]
                vals = label_vals[label]
                vals[0].append(col)
                vals[1].append(df[col][row])
                label_vals[label] = vals
                # x.append(col)
                # y.append(df[col][row])

        total_avg = sum(y_avg) / len(y_avg)
        logger.info(f"total average query time: {total_avg}")

        plt.figure(figsize=(16, 6))
        # plt.scatter(x, y, label="query time")

        for label, vals in label_vals.items():
            plt.scatter(vals[0], vals[1], label=label)

        # plt.scatter([x[1], x[9], x[17], x[25], x[33]],
        #             [y[1], y[9], y[17], y[25], y[33]], label="single section")
        # plt.scatter([x[2], x[10], x[18], x[26], x[34]],
        #             [y[2], y[10], y[18], y[26], y[34]], label="all sections + manufacturer")
        # plt.scatter([x[3], x[11], x[19], x[27], x[35]],
        #             [y[3], y[11], y[19], y[27], y[35]], label="single section + manufacturer")
        # plt.scatter([x[4], x[12], x[20], x[28], x[36]],
        #             [y[4], y[12], y[20], y[28], y[36]], label="all sections + generic")
        # plt.scatter([x[5], x[13], x[21], x[29], x[37]],
        #             [y[5], y[13], y[21], y[29], y[37]], label="single section + generic")
        # plt.scatter([x[6], x[14], x[22], x[30], x[38]],
        #             [y[6], y[14], y[22], y[30], y[38]], label="all sections + 4 inputs")
        # plt.scatter([x[7], x[15], x[23], x[31], x[39]],
        #             [y[7], y[15], y[23], y[31], y[39]], label="single section + 4 inputs")

        # plt.scatter(x_avg, y_avg, label="avg query time per query")
        plt.axhline(total_avg, label="avg query time")
        plt.title("Performance testing")
        plt.xlabel("Queries")
        plt.ylabel("time to complete query (seconds)")
        plt.legend(loc="best")

        fig_file = settings.MEDIA_ROOT / PERF_TEST_PNG
        plt.savefig(fig_file)
