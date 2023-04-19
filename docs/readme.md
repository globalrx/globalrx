# SearchRx Setup

## Local Development
The project is containerized so that it can be run locally or deployed to a cloud environment.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)

### Setup
1. Clone the repository

2. Set up `pre-commit` for linting
    - Install `pre-commit` on your local machine using `pip` or `brew`. See: https://pre-commit.com/
    - Install the `pre-commit` hook. This runs `black`, `flake8`, and `isort` linting based on configurations in `pyproject.toml` and `.flake8` (there is currently no single config file format that all three linters agree upon). The `pre-commit` config is in `.pre-commit-config.yaml` and will install the hook in `.git/hooks/pre-commit`.
    - Potentially, run `pre-commit run --all-files` to run against everything in the repo rather than everything `diffed`. But probably not necessary.
    - From now on, the `precommit` hook will try to update all your files before committing them so that your merges pass the linting Action (`.github/workflows/check.yml`).

3. Set environment variables; see [env.example](./env.example) for a list of required variables. Some of these variables control whether setup scripts (e.g. Django migrations) are run.
    - Copy `env.example` to `.env` and update the values
    - For a first run, set `MIGRATE`, `LOAD`, and `INIT_SUPERUSER` to `True`
        - This will take a long time. Check out what is happening in the `entrypoint` script:
            - Wait for PSQL to be ready
            - Django migrations: `makemigrations` and `migrate`
            - Copy assets: `collectstatic`
            - Create superuser
            - Load data (EMA, FDA, TGA, HC right now) and `update_latest_drug_labels`. This can take a really long time to run all the way through.
            - Potentially load vectors, if you have pre-computed them (too slow to vectorize within Docker)
            - Run the application server with `runserver` or `Gunicorn` + `nginx`
    - After data is loaded, set `LOAD` and `INIT_SUPERUSER` to `False`
    - Make sure `ES_AUTO_SYNC=False`
    - ~~If you are working on BERT model, you will need to start an Elasticsearch trial license; you can either try to set the `LICENSE` variable to `trial`, or POST this to Elasticsearch after it starts up either in Kibana: or via `curl`: `/_license/start_trial?acknowledge=true`~~ We are no longer using Elastic's NLP pipeline. Set `LICENSE=basic`
    - The API app will run `load_bert_model` and download PubMedBERT from HuggingFace if you don't already have it. We preload the model for reuse in `api.apps.py`. Unfortunately this makes Django take a lot longer to startup, but vectorization of search terms at the `/vectorize` endpoint is pretty snappy.

4. Run `docker compose up` to start the application. This will take a long time the first time. Steps that occur:
    - Builds the Django container from `Dockerfile.dev`
        - `python:3.10.10-slim-buster` base image
        - Installs some system dependencies
        - Installs Python dependencies from `requirements.txt`
        - Does not copy the source code into the container - instead, mounts the source code as a volume so you can make changes on your local machine and have them reflected in the container
    - Pulls Postgres 14 image
    - Pulls Elasticsearch 8 image and Kibana image, which are used for the `es01` (only running 1 node for now), `elastic-setup`, and `kibana` services
    - Starts all the services, which provisions Elasticsearch and Kibana
    - Runs Django entrypoint script
        - Waits for Postgres connection to succeed
        - Runs Django migrations if `MIGRATE` is set to `True`
        - Collects static files if `MIGRATE` is set to `True` (possibly have another env variable for this?)
        - Creates a superuser if `INIT_SUPERUSER` is set to `True` and `SUPERUSER_USERNAME` and `SUPERUSER_PASSWORD` are set
        - Loads data if `LOAD` is set to `True`
            - This step takes a long time
            - Runs EMA (`load_ema_data --type full`) and FDA (`load_fda_data --type full`) data loaders
            - Runs `update_latest_drug_labels`
        - Runs a local webserver for Django on port 8000

5. Services:
    - Django: http://localhost:8000
    - Elasticsearch: https://localhost:9200
        - you may need to accept the self-signed certificate
        - when `curling` you can use `-k` to ignore certificate errors
        - otherwise you can use `--cacert` to specify a certificate - copy it from container to your local machine with `docker cp <containerId>:/usr/share/elasticsearch/config/certs/ca/ca.crt .`)
        - or use Kibana console to interact with Elasticsearch instead
    - Kibana: http://localhost:5601

6. Create Elasticsearch index and mappings
    - Create ES index
        - The `elasticsearch-django` library supposedly has a CLI command to do this but I have not been able to get it to work (`python3 manage.py create_search_index <INDEX_NAME>`)
        - Instead I have been using Kibana console to create indices
        - `PUT productsection` creates the index
    - The mappings are defined in `search/mappings.py`; PUT the mappings like so:
        ```
        PUT /productsection/_mapping {
            "properties": {
                "drug_label_generic_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "drug_label_id": {
                    "type": "long"
                },
                "drug_label_link": {
                    "type": "text"
                },
                "drug_label_marketer": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "drug_label_product_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "drug_label_source": {
                    "type": "keyword"
                },
                "drug_label_source_product_number": {
                    "type": "text"
                },
                "drug_label_version_date": {
                    "type": "date"
                },
                "id": {
                    "type": "long"
                },
                "label_product_id": {
                    "type": "long"
                },
                "section_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "section_text": {
                    "type": "text"
                },
                "text_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": true,
                    "similarity": "dot_product"
                }
            }
        }
        ```
    - Make sure your mappings look good and the `text_embedding` mapping in particular is of type `dense_vector`
        - Run `GET /productsection/_mapping` to see your index schema

7. Load vector data into Postgres and Elasticsearch
    - Either create your own vectors, or download existing vector JSON from S3
        - If using pre-computed vectors, you will need to make sure that `version_date` of those vectors matches the `version_date` of your Postgres / Django `DrugLabel` objects. You may need to use the Django ORM to modify the version date - this is at least the case for EMA labels currently. Peter's EMA fix may have resolved this but haven't tried re-ingesting EMA labels or re-creating EMA vectors after that fix.
        - If creating vectors, check out the `docs/section_mapping/vectorize.ipynb` notebook. You should use `django_extensions` to run the notebooks with the Django context, but on your local machine rather than within Docker. YMMV but it seems that for some reason vectorization is agonizingly slow within Docker.
    - Place the vectors into `media` folder.
    - Exec into the Django container - from `dle`, `docker compose exec django bash`
    - Run the management command to ingest: `python3 manage.py vectorize --elasticingest True --vector_file "ema_vectors.json" --agency EMA`
        - `elasticingest` defaults to true, this will put vectors from PSQL to Elasticsearch
        - If `vector_file` is passed, it will try to load the data from your JSON file into Elasticsearch after loading into Postgres
    

## Deployment

### Architecture