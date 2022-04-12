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
        logger.info(f"setting logger level to INFO")

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

        date_str = dt.datetime.now().strftime("%Y%m%d_%H%I%S")
        output_file = settings.MEDIA_ROOT / f"perf_test_{date_str}.csv"
        logger.info(f"saving data to: {output_file}")
        f = default_storage.open(output_file, "w")

        for i in range(NUM_RUNS):
            logger.info(f"run number: {i+1}")

            query_times = []
            for query_obj in SearchPerformanceTests.TEST_QUERIES:
                start_time = time.perf_counter()
                response = self.client.get("/search/", query_obj)
                end_time = time.perf_counter()
                query_time = end_time - start_time
                query_times.append(str(query_time))
                self.assertEqual(response.status_code, 200)

            query_time_csv_str = ",".join(query_times) + "\n"
            f.write(query_time_csv_str)


