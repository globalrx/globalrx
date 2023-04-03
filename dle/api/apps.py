import os

from django.apps import AppConfig
from django.conf import settings

from sentence_transformers import SentenceTransformer


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    # TODO script this startup so it doesn't download multiple times
    # pubmedbert_model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    MODEL_PATH = os.path.join(settings.NLP_MODELS, "S-PubMedBert-MS-MARCO")
    pubmedbert_model = SentenceTransformer(MODEL_PATH)
