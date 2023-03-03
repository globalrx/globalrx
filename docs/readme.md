# GlobalRx Setup

## Local Development
The project is containerized so that it can be run locally or deployed to a cloud environment.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)

### Setup
1. Clone the repository
2. Set environment variables; see [env.example](./env.example) for a list of required variables. Some of these variables control whether setup scripts (e.g. Django migrations) are run.
    a. Copy `env.example` to `.env` and update the values
    b. For a first run, set `MIGRATE`, `LOAD`, and `INIT_SUPERUSER` to `True`
    c. If you are working on BERT model, you will need to start an Elasticsearch trial license; you can either try to set the `LICENSE` variable to `trial`, or POST this to Elasticsearch after it starts up either in Kibana: or via `curl`: `/_license/start_trial?acknowledge=true`
3. Run `docker compose up` to start the application. This will take a long time the first time. Steps that occur:
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
4. Services:
    - Django: http://localhost:8000
    - Elasticsearch: https://localhost:9200
        - you may need to accept the self-signed certificate
        - when `curling` you can use `-k` to ignore certificate errors
        - otherwise you can use `--cacert` to specify a certificate - copy it from container to your local machine with `docker cp <containerId>:/usr/share/elasticsearch/config/certs/ca/ca.crt .`)
        - or use Kibana console to interact with Elasticsearch instead
    - Kibana: http://localhost:5601

5. Load Elasticsearch data
    - TODO maybe move this into entrypoint script as an option
    - Once all services are up, enter the Docker container for `django`: `docker compose exec django bash`
    - Create ES indices
        - The `elasticsearch-django` library supposedly has a CLI command to do this but I have not been able to get it to work (`python3 manage.py create_search_index <INDEX_NAME>`)
        - Instead I have been using Kibana console to create indices
            - `PUT druglabel`
            - `PUT productsection`
            - The mappings are defined in `search/mappings.py`; otherwise you can post dummy documents like so:
                ```
                POST druglabel/_doc/1
                {
                    "source": "test",
                    "product_name": "name",
                    "generic_name": "generic name",
                    "version_date": "version date",
                    "source_product_number": "123456789",
                    "raw_text": "a long lot of text will go here",
                    "marketer": "a marketer",
                    "link": "https://fakeurl.com"
                }
                ```
                ```
                POST productsection/_doc/1
                {
                    "label_product": "product",
                    "section_name": "name",
                    "section_text": "text field here to be indexed",
                    "id": 3243
                }
                ```
    - Set up BERT pipeline (requires Elasticsearch trial license and ML features enabled; may not work well locally due to resource constraints)
        - See https://www.elastic.co/blog/how-to-deploy-nlp-text-embeddings-and-vector-search
        - From the `Django` service, run `eland_import_hub_model --ca-certs /usr/share/elasticsearch/config/certs/ca/ca.crt --url https://elastic:<YOUR PASSWORD></YOUR>@es01:9200/ --hub-model-id Charangan/MedBERT --task-type text_embedding --start` to import the MedBERT model into Elasticsearch
        - In Kibana, create the pipeline:
            ```
            PUT _ingest/pipeline/medbert
            {
                "description": "Text embedding pipeline using HuggingFace Charangan/MedBERT",
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
    - Set the index default pipeline
        ```
        PUT /productsection/_settings
        {
            "index" : {
                "default_pipeline": "medbert"
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