import logging
import os

from django.apps import AppConfig
from django.conf import settings

from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    # TODO script this startup so it doesn't download multiple times]
    if settings.TESTS==True:
        pubmedbert_model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    else:
        # TODO allow for some configuration rather than hardcoding S-PubMedBert
        model_repo = "pritamdeka/S-PubMedBert-MS-MARCO"
        username, repo = [str(i) for i in model_repo.split("/")]
        MODEL_PATH = os.path.join(settings.NLP_MODELS, repo)
        if os.path.exists(MODEL_PATH):
            print(f"{model_repo} already exists at {MODEL_PATH}")
            logger.info(f"{model_repo} already exists at {MODEL_PATH}")
        else:
            print("Model doesn't exist, downloading")
            os.makedirs(MODEL_PATH)
            model = SentenceTransformer(model_repo)
            model.save(MODEL_PATH)
            logger.info(f"Saved {model_repo} to {MODEL_PATH}")
        pubmedbert_model = SentenceTransformer(MODEL_PATH)
