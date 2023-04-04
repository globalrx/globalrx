# Tests were crashing: ValueError: Path /github_workspace/api/bert_models/S-PubMedBert-MS-MARCO not found
# For some reason, hitting the Django setup before the entrypoint ran? Or entrypoint not running?
# Trying to load the model in Dockerfile.tests setup

import os

from sentence_transformers import SentenceTransformer


model_repo = "pritamdeka/S-PubMedBert-MS-MARCO"
username, repo = [str(i) for i in model_repo.split("/")]
model_dir = "/app/api/bert_models/S-PubMedBert-MS-MARCO"
if os.path.exists(model_dir):
    print(f"{model_repo} already exists at {model_dir}")
else:
    os.makedirs(model_dir)
    model = SentenceTransformer(model_repo)
    model.save(model_dir)
    print(f"Saved {model_repo} to {model_dir}")
