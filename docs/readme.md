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
    - After data is loaded, set `LOAD` and `INIT_SUPERUSER` to `False`
    - If you are working on BERT model, you will need to start an Elasticsearch trial license; you can either try to set the `LICENSE` variable to `trial`, or POST this to Elasticsearch after it starts up either in Kibana: or via `curl`: `/_license/start_trial?acknowledge=true`
    - Set USE_BERT to True to download the BERT model. Unfortunately once we include the model in `api.app` it makes the app take a lot longer to startup, but it does mean that vectorization of search terms is quite quick 
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

6. Load Elasticsearch data
    - TODO maybe move this into entrypoint script as an option
    - Once all services are up, enter the Docker container for `django`: `docker compose exec django bash`
    - Create ES indices
        - If you have `ES_AUTO_SYNC=True` this might just work out of the box. I tried replicating and it didn't, not sure why.
        - The `elasticsearch-django` library supposedly has a CLI command to do this but I have not been able to get it to work (`python3 manage.py create_search_index <INDEX_NAME>`)
        - Instead I have been using Kibana console to create indices
            - `PUT productsection`
            - The mappings are defined in `search/mappings.py`; PUT the mappings like so:
                ```
                PUT /productsection/_mapping
                {
                "properties": {
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
                    "drug_label_id": {
                        "type": "long"
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
                    "drug_label_generic_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "drug_label_version_date": {
                        "type": "date"
                    },
                    "drug_label_source_product_number": {
                        "type": "text"
                    },
                    "drug_label_link": {
                        "type": "text"
                    }
                }
                }
                ```
    - Optional: Set up BERT pipeline
        - Gotchas:
            - Requires Elasticsearch trial license and ML features enabled
            - May not work well locally due to resource constraints
            - We are working to vectorize externally and then import the vectors. Trying to vectorize with ES will take ages.
            - Currently not scripted
        - See https://www.elastic.co/blog/how-to-deploy-nlp-text-embeddings-and-vector-search
        - Model: [`pritamdeka/S-PubMedBert-MS-MARCO`](https://huggingface.co/pritamdeka/S-PubMedBert-MS-MARCO)
        - From the `Django` service, run `eland_import_hub_model --ca-certs /usr/share/elasticsearch/config/certs/ca/ca.crt --url https://elastic:<YOUR PASSWORD>@es01:9200/ --hub-model-id <MODELID> --task-type text_embedding --start`
        - For Elastic Cloud: `eland_import_hub_model --cloud-id <CLOUDID> --hub-model-id <MODELID> --task-type text_embedding --start`
        - In Kibana, create the pipeline:
            ```
            PUT _ingest/pipeline/pubmedbert
            {
                "description": "Text embedding pipeline using HuggingFace pritamdeka/S-PubMedBert-MS-MARCO",
                "processors": [
                    {
                        "inference": {
                            "model_id": "charangan__medbert",
                            "target_field": "text_embedding",
                            "field_map": {
                                "section_text": "text_field"
                            }
                        }
                    }
                ],
                "on_failure": [
                    {
                        "set": {
                            "description": "Index document to 'failed-<index>'",
                            "field": "_index",
                            "value": "failed-{{{_index}}}"
                        }
                    },
                    {
                        "set": {
                            "description": "Set error message",
                            "field": "ingest.failure",
                            "value": "{{_ingest.on_failure_message}}"
                        }
                    }
                ]
            }
            ```
    - Deploy the model. Can be 2/2 or 1/4 on a 6 CPU setup; threads must be power of 2 and not exceed allocated processors
        ```
        POST _ml/trained_models/pritamdeka__s-pubmedbert-ms-marco/deployment/_start
        {
            "number_of_allocations": 2,
            "threads_per_allocation": 2
        }
        ```
    - Set the index default pipeline
        ```
        PUT /productsection/_settings
        {
            "index" : {
                "default_pipeline": "pubmedbert"
            }
        }
        ```
    - Index Django data into Elasticsearch
        - Run `python3 manage.py update_search_index druglabel` to index all drug labels (~43k March 2023)
            - This should run fairly quickly, no vectorization
        - Run `python3 manage.py update_search_index productsection` to index all product sections (~958k March 2023)
            - This took between 20 minutes and an hour before vectorization and is too slow to run locally with ~10GB RAM, MEM_LIMIT for ES at 8GB, and 4CPUs (~20s per document) with a batch size of 5 (vs 500...) and timeout at 180s. Will need a bigger machine to run this.
            - If you too are experiencing this slow of indexing, you can remove the default pipeline and index the data without vectorization, then rerun `update_search_index` without the pipeline:
            ```
            PUT /productsection/_settings
            {
                "index" : {
                    "default_pipeline": null
                }
            }
            ```

## Deployment

### Architecture