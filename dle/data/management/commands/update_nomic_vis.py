# Description: This script updates the Nomic vectors visualization with the latest Django data
import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import nomic
import numpy as np
from nomic import atlas
from tqdm import tqdm

from data.models import ProductSection


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update the Nomic vectors visualization with the latests data"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)

    def handle(self, *args, **options):
        try:
            # Get all the sections with vectors
            all_sections = ProductSection.objects.filter(bert_vector__isnull=False)
            # Create lists for embeddings and corresponding metadata
            embeddings = []
            metadata = []
            key = settings.NOMIC_KEY

            nomic.login(key)
            # Iterate over all sections and append to lists
            # This takes a long time - several hours - could try to parallelize?
            for i, ps in enumerate(tqdm(all_sections)):
                embeddings.append(np.array(json.loads(ps.bert_vector)))
                doc = dict(ps.as_search_document())
                doc.pop("text_embedding")
                metadata.append(doc)
            # Embeddings has to be a numpy array
            arr = np.array(embeddings)
            # Update the Nomic project
            # Project is under Cole's account, update this if you want to change it to a different Nomic project
            # TODO use `add_datums_if_exists` instead of `reset_project_if_exists` so we can update the project incrementally
            # See: https://docs.nomic.ai/atlas_api.html
            project = atlas.map_embeddings(
                embeddings=arr,
                data=metadata,
                id_field="id",
                colorable_fields=["drug_label_source", "section_name"],
                topic_label_field="section_text",
                name="SearchRx",
                description="Embeddings of drug label sections",
                # deletes the data before uploading it
                reset_project_if_exists=True,
            )
            logger.info(f"Updated Nomic project: {project}")

        except Exception as e:
            logger.error(e)
            raise CommandError(e)
