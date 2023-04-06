import os

from django.apps import AppConfig
from django.conf import settings

from sentence_transformers import SentenceTransformer

from api.util import load_bert_model


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    huggingface_model_name = "pritamdeka/S-PubMedBert-MS-MARCO"

    # TODO see if we can get rid of this - directly loading for Github Actions tests
    if settings.TESTS==True:
        pubmedbert_model = SentenceTransformer(huggingface_model_name)
    else:
       pubmedbert_model = SentenceTransformer(load_bert_model(huggingface_model=huggingface_model_name))
