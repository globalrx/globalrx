import logging
import os

from django.conf import settings

from sentence_transformers import SentenceTransformer


logger = logging.getLogger("")

def load_bert_model(huggingface_model: str) -> str:
    """ Pre-loads ML models for use in the app.
    Takes a HuggingFace model, e.g. 'pritamdeka/S-PubMedBert-MS-MARCO'.
    If a model does not already exist, it is downloaded.
    """
    print(f"Model to be loaded: {huggingface_model}")

    username, repo = [str(i) for i in huggingface_model.split("/")]
    MODEL_PATH = os.path.join(settings.NLP_MODELS, repo)
    if os.path.exists(MODEL_PATH):
        logger.info(f"{huggingface_model} already exists at {MODEL_PATH}")
        return MODEL_PATH
    else:
        logger.info("Model doesn't exist, downloading")
        os.makedirs(MODEL_PATH)
        model = SentenceTransformer(huggingface_model)
        model.save(MODEL_PATH)
        logger.info(f"Saved {huggingface_model} to {MODEL_PATH}")
        return MODEL_PATH
    # TODO catch any errors if the model doesn't DL correctly
