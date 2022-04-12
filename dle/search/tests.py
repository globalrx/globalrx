from django.test import TestCase
import logging

logger = logging.getLogger(__name__)

# Create your tests here.
# runs with `python manage.py test search`
class SearchTests(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)
        # root_logger.setLevel(logging.DEBUG)
        logger.info(f"logger includes INFO")
        logger.debug(f"logger includes DEBUG")

    def test_true(self):
        self.assertTrue(True)
