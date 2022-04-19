from django.core.management.base import BaseCommand
import logging
from data.constants import LASTEST_DRUG_LABELS_TABLE
from django.db import connection

logger = logging.getLogger(__name__)


# runs with `python manage.py update_latest_drug_labels`
# add `--verbosity 2` for info output
# add `--verbosity 3` for debug output
class Command(BaseCommand):
    """Run after loading the data to maintain a latest_drug_labels table"""
    help = "Loads data from EMA"

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
        # basic logging config is in settings.py
        # verbosity is 1 by default, gives critical, error and warning output
        # `--verbosity 2` gives info output
        # `--verbosity 3` gives debug output
        self.set_log_verbosity(int(options["verbosity"]))
        logger.info(self.style.SUCCESS("start process"))

        sql_1 = f"DROP TABLE IF EXISTS {LASTEST_DRUG_LABELS_TABLE}"

        sql_2 = f"""
        CREATE TEMPORARY TABLE latest_dl_versions_temp AS
        SELECT source, source_product_number, max(version_date) AS version_date
        FROM data_druglabel
        GROUP BY source, source_product_number
        """

        sql_3 = f"""
        CREATE TABLE {LASTEST_DRUG_LABELS_TABLE} AS
        SELECT id FROM data_druglabel AS dl
        JOIN latest_dl_versions_temp AS t ON
            dl.source = t.source
            AND dl.source_product_number = t.source_product_number
            AND dl.version_date = t.version_date
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_1)
            result = cursor.fetchone()
            logger.debug(f"result: {result}")
            cursor.execute(sql_2)
            result = cursor.fetchone()
            logger.debug(f"result: {result}")
            cursor.execute(sql_3)
            result = cursor.fetchone()
            logger.debug(f"result: {result}")
            # result = cursor.fetchall()

        logger.info(self.style.SUCCESS("process complete"))
        return
