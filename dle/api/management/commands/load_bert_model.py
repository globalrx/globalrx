import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Preloads any BERT models used by the project"

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        root_logger = logging.getLogger("")
        root_logger.setLevel(logging.INFO)

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            help="A HuggingFace BERT model repo optimized for vectorization tasks",
            default="pritamdeka/S-PubMedBert-MS-MARCO"
        )

    def handle(self, *args, **options):
        model_repo = options["model"]

        # See if it already exists
        username, repo = [str(i) for i in model_repo.split("/")]
        model_dir = os.path.join(settings.NLP_MODELS, repo)
        if os.path.exists(model_dir):
            logger.info(f"{model_repo} already exists at {model_dir}")
        else:
            os.makedirs(model_dir)
            model = SentenceTransformer(model_repo)
            model.save(model_dir)
            logger.info(f"Saved {model_repo} to {model_dir}")
