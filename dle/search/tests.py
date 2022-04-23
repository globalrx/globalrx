from django.test import TestCase
import logging
from .services import process_search
from .models import SearchRequest
from django.core import management

logger = logging.getLogger(__name__)

# Create your tests here.
# runs with `python manage.py test search`
class SearchTests(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)
        root_logger.setLevel(logging.DEBUG)
        logger.info(f"logger includes INFO")
        logger.debug(f"logger includes DEBUG")

    def test_true(self):
        self.assertTrue(True)

    def test_dl_query_0(self):
        management.call_command("update_latest_drug_labels")

        request = SearchRequest(
            search_text="kidney",
            select_section="Indications",
            manufacturer_input="Pfizer"
        )

        results = process_search(request)
        logger.debug(f"search results: {results}")
        self.assertTrue(True)
        pass
