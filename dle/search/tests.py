from django.test import TestCase, Client
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import time
import datetime as dt
import logging

logger = logging.getLogger(__name__)

# Create your tests here.
# runs with `python manage.py test search`
class SearchPerformanceTests(TestCase):

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = Client()
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)
        # root_logger.setLevel(logging.DEBUG)
        logger.info(f"logger includes INFO")
        logger.debug(f"logger includes DEBUG")

    def test_true(self):
        self.assertTrue(True)

    def test_run_perf_test(self):
        # we want to run a number of performance tests
        # output response times to a file

        # create a set of test queries
        # calculate how long each takes to run
        # run them again
        # print a file to output the times in csv
        # query_0, query1, query2

        NUM_RUNS = 2

        output_file = settings.MEDIA_ROOT / "perf_test.csv"
        f = default_storage.open(output_file, "a")
        logger.info(f"saving data to: {output_file}")

        for i in range(NUM_RUNS):
            logger.info(f"run number: {i+1}")

            query_times = []
            date_str = dt.datetime.now().strftime("%Y%m%d_%H%I%S")
            query_times.append(date_str)

            for query_obj in SearchPerformanceTests.TEST_QUERIES:
                start_time = time.perf_counter()
                response = self.client.get("/search/results", query_obj)
                end_time = time.perf_counter()
                query_time = end_time - start_time
                query_times.append(str(round(query_time, 3)))
                logger.debug(f"response content: {response.content}")
                logger.debug(f"response context: {response.context}")

                try:
                    logger.info(
                        f"num search results: {len(response.context['search_results'])}"
                    )
                except KeyError:
                    logger.info(f"NO search results found")

                self.assertEqual(response.status_code, 200)

            query_time_csv_str = ",".join(query_times) + "\n"
            f.write(query_time_csv_str)
