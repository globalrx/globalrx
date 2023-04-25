import asyncio
import json
import logging
from datetime import datetime
from distutils.util import strtobool

from django.core.management.base import BaseCommand, CommandError

from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

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
            help="'TGA', 'FDA', 'EMA', 'HC'",
        )
        parser.add_argument(
            "--vectorize_in_docker",
            type=strtobool,
            help="Forces vectorization within Docker, which runs very slow on M1 at least",
            default=False,
        )
        parser.add_argument(
            "--vector_file",
            type=str,
            help="If a file is passed, insert the existing vectors, then ingest",
        )

    @background
    def compute_section_vector_wrapper(self, section):
        vec = compute_section_embedding(text=section.section_text, model=self.model, normalize=True)
        section.bert_vector = json.dumps(vec)
        section.save()

    def handle(self, *args, **options):
        agency = options["agency"]
        vectorize_in_docker = options["vectorize_in_docker"]
        vector_filename = options["vector_file"]

        if agency not in ["EMA", "FMA", "TGA", "HC"]:
            raise CommandError("'agency' parameter must be an agency")

        logger.info(self.style.SUCCESS("start vectorizing"))
        logger.info(f"Agency: {agency}")

        # TODO finish and test
        if vector_filename:
            """Load the vectors from file to PSQL via Django ORM"""
            logger.info(f"Opening {vector_filename}")
            with open(vector_filename, "r") as f:
                vectors = json.load(f)
            logger.info("Vectors JSON loaded. Ingesting vectors into Django.")
            for source_product_id in tqdm(vectors.keys()):
                versions = vectors[source_product_id]
                for version in versions.keys():
                    # logger.info(f"{source_product_id} - {version}")
                    for section_name in vectors[source_product_id][version]:
                        # logger.info(f"{source_product_id} - {version} - {section_name}")
                        vector = json.loads(vectors[source_product_id][version][section_name])
                        try:
                            section = ProductSection.objects.get(
                                section_name=section_name,
                                label_product__drug_label__source_product_number=source_product_id,
                                label_product__drug_label__version_date=datetime.strptime(
                                    version, "%Y/%m/%d"
                                ),
                            )
                            section.bert_vector = vector
                            section.save()
                        except ProductSection.DoesNotExist:
                            logger.error(
                                f"Could not find ProductSection based on: section_name={section_name}, label_product__drug_label__source_product_number={source_product_id}, and label_product__drug_label__version_date={datetime.strptime(version, '%Y/%m/%d')} "
                            )
                        except ProductSection.MultipleObjectsReturned:
                            logger.error(
                                f"Found multiple ProductSections based on: section_name={section_name}, label_product__drug_label__source_product_number={source_product_id}, and label_product__drug_label__version_date={datetime.strptime(version, '%Y/%m/%d')} "
                            )

        if vectorize_in_docker:
            sections = ProductSection.objects.filter(label_product__drug_label__source=agency).all()
            self.total_sections = sections.count()

            start = datetime.now()
            loop = asyncio.get_event_loop()
            looper = tqdm_asyncio.gather(*[self.compute_section_vector_wrapper(s) for s in sections])  # type: ignore
            results = loop.run_until_complete(looper)
            end = datetime.now()
            elapsed = end - start

            logger.info(
                f"finished computing vectors ------------- { int(elapsed.total_seconds()) } seconds"
            )
            logger.info(results)
