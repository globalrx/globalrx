import json
import logging
from datetime import datetime
from distutils.util import strtobool

from django.core.management.base import BaseCommand, CommandError

from elasticsearch import logger as es_logger
from elasticsearch_django.settings import get_client
from tqdm import tqdm

from api.apps import ApiConfig
from data.models import ProductSection
from data.util import compute_section_embedding


es_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


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
            help="'TGA', 'FDA', 'EMA'",
        )
        parser.add_argument(
            "--elasticingest",
            type=strtobool,
            help="Whether to ingest texts into Elastic",
            default=True,
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

    def handle(self, *args, **options):
        agency = options["agency"]
        elasticingest = options["elasticingest"]
        vectorize_in_docker = options["vectorize_in_docker"]
        vector_filename = options["vector_file"]

        if agency not in ["EMA", "FMA", "TGA"]:
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
                version = vectors[source_product_id]
                for sec in vectors[source_product_id][version]:
                    vector = json.loads(sec)
                    section = ProductSection.get(
                        source_product_id=source_product_id,
                        version_date=datetime.strptime(version, "%Y/%m/%d"),
                    )
                    section.bert_vector = vector
                    section.save()

        # Get QuerySet of ProductSections to process
        # If QuerySet is too large, may need to use iterator() to disable QuerySet caching
        if vectorize_in_docker:
            sections = ProductSection.objects.filter(label_product__drug_label__source=agency).all()
            self.total_sections = sections.count()

            start = datetime.now()
            subset = sections[0:1000]
            # TODO use Asyncio and find out why vectorization within Docker is abysmally slow
            for section in subset:
                section.bert_vector = json.dumps(
                    compute_section_embedding(
                        section.section_text, model=self.model, normalize=True
                    )
                )
                section.save()
            end = datetime.now()
            elapsed = end - start
            print(
                f"------------- computed {subset.count()} sections { int(elapsed.total_seconds()) } seconds"
            )

        # Only try to do this if we haven't already imported vectors from the file
        # TODO use bulk API for ingest
        if (vector_filename or vectorize_in_docker) and elasticingest:
            logger.info("Ingesting vectors into Elasticsearch")
            es = get_client()
            # Only ingest ProductSections with existing vector representations
            sections_w_vectors = ProductSection.objects.filter(
                label_product__drug_label__source=agency
            ).filter(bert_vector__isnull=False)
            for section in tqdm(sections_w_vectors):
                es.index(index="productsection", document=section.as_search_document, id=section.id)

        # Results - not parallelized - containerized with 6CPU / 16GB RAM, 4GB for ES and 1GB for Kibana so ~11GB for Django ...
        # Ridiculously long. Like ~7.5 minutes to do a single section, without saving to DB

        # Results - Jupyter Notebook, not parallelized
        # 51:31 for 500 labels / 11275 sections
        # 500 drug labels processed: 6.182 seconds per drug
        # 11275 sections processed: 0.27414634146341466 seconds per section

        # Results - Jupyter Notebook, Asyncio
        # 26:41 for 500 labels / 11593 sections
        # 500 drug labels processed: 3.202 seconds per drug
        # 11593 sections processed: 0.13810057793496075 seconds per section
