import asyncio
import json
import logging
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from api.apps import ApiConfig
from data.models import ProductSection
from data.util import compute_section_embedding


logger = logging.getLogger(__name__)


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


class Command(BaseCommand):
    help = "Vectorizes existing data"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.model = ApiConfig.pubmedbert_model
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)

    def add_arguments(self, parser):
        parser.add_argument(
            "--agency",
            type=str,
            help="'TGA', 'FDA', 'EMA', 'HC', or 'all'",
        )

    @background
    def compute_section_vector_wrapper(self, section):
        vec = compute_section_embedding(text=section.section_text, model=self.model, normalize=True)
        section.bert_vector = json.dumps(vec)
        section.save()

    def handle(self, *args, **options):
        agency = options["agency"]

        if agency not in ["EMA", "FMA", "TGA", "HC", "all"]:
            raise CommandError("'agency' parameter must be an agency")

        logger.info(self.style.SUCCESS("start vectorizing"))
        logger.info(f"Agency: {agency}")

        if agency == "all":
            sections = ProductSection.objects.filter(bert_vector__isnull=True)
        else:
            sections = ProductSection.objects.filter(
                label_product__drug_label__source=agency
            ).filter(bert_vector__isnull=True)
        self.total_sections = sections.count()

        start = datetime.now()
        loop = asyncio.get_event_loop()
        looper = asyncio.gather(*[self.compute_section_vector_wrapper(s) for s in sections])  # type: ignore
        results = loop.run_until_complete(looper)  # noqa F841
        end = datetime.now()
        elapsed = end - start

        logger.info(
            f"finished computing vectors ------------- { int(elapsed.total_seconds()) } seconds"
        )
        # logger.info(results)
