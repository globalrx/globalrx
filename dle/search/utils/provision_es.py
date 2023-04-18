import json
import logging

from django.http import JsonResponse

from elasticsearch.helpers import streaming_bulk
from elasticsearch_django.settings import get_client
from tqdm import tqdm

from data.models import AGENCY_CHOICES, ProductSection


logger = logging.getLogger(__name__)


def create_index(index_name: str, mapping_file: str) -> JsonResponse:
    es = get_client()
    # open mapping_file
    with open(mapping_file, "r") as f:
        mapping = json.load(f)
    if not es.indices.exists(index=index_name):
        logger.info(
            f"Creating index {index_name} with the following schema: {json.dumps(mapping, indent=2)}"
        )
        settings = {"index": {"routing.allocation.total_shards_per_node": 5}}
        res = es.indices.create(index=index_name, mappings=mapping, settings=settings)
        return JsonResponse(dict(res))
    else:
        return JsonResponse({})


def populate_index(index_name: str = "productsection", agency: str = "all"):
    """Populate the index with the given agency's sections
    Only vectorized sections are ingested.
    """
    if agency == "all":
        sections_w_vectors = ProductSection.objects.filter(bert_vector__isnull=False)
    else:
        # check to see if the agency is valid using AGENCY_CHOICES
        if agency not in [choice[0] for choice in AGENCY_CHOICES]:
            raise ValueError(f"{agency} is not a valid agency. Please use one of {AGENCY_CHOICES}")
        sections_w_vectors = ProductSection.objects.filter(
            label_product__drug_label__source=agency
        ).filter(bert_vector__isnull=False)

    def generate_actions():
        """For each agency's section that has a BERT vector, yield a document"""
        # Only ingest ProductSections with existing vector representations
        # Use iterator to avoid loading all sections into memory which was causing the job to get killed
        for section in sections_w_vectors.iterator():
            doc = section.as_search_document()
            doc["_id"] = section.id
            yield doc

    logger.info(f"Ingesting {sections_w_vectors.count()} sections with vectors into Elasticsearch")
    es = get_client()

    progress = tqdm(unit="docs", total=sections_w_vectors.count())
    successes = 0
    for ok, action in streaming_bulk(
        client=es,
        index=index_name,
        actions=generate_actions(),
        chunk_size=1000,
        max_retries=3,
        max_backoff=60,
        raise_on_exception=False,
        raise_on_error=False,
    ):
        if not ok:
            logger.error(f"Failed to index document: {action}")
        progress.update(1)
        successes += ok
    logger.info((f"Indexed {successes} out of {sections_w_vectors.count()} documents"))
