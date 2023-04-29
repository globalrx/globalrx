# SearchRx Setup

## Local Development
The project is containerized so that it can be run locally or deployed to a cloud environment.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)

### Commands
Get into a docker container; replace `django` with the container name you want to access
`docker exec -it dle-django-1 /bin/bash` or `docker compose exec django bash`

PSQL CLI
`docker compose exec postgres bash`
From within the container, run: `psql -U postgres`

Example of copying a file into a docker container. This shouldn't be necessary as we are mounting the code into the container, but it's useful to know.
`docker cp foo.txt container_id:/foo.txt`

Django shell (easily run Django ORM commands to manipulate models)
`docker compose exec django bash`
`python3 manage.py shell`

Run a management command (e.g. `makemigrations` or `load_fda_data`):
`docker compose exec django bash`
`python3 manage.py makemigrations` or any management command

### Setup
1. Clone the repository

2. Set up `pre-commit` for linting
    - Install `pre-commit` on your local machine using `pip` or `brew`. See: https://pre-commit.com/
    - Install the `pre-commit` hook. This runs `black`, `flake8`, and `isort` linting based on configurations in `pyproject.toml` and `.flake8` (there is currently no single config file format that all three linters agree upon). The `pre-commit` config is in `.pre-commit-config.yaml` and will install the hook in `.git/hooks/pre-commit`.
    - Potentially, run `pre-commit run --all-files` to run against everything in the repo rather than everything `diffed`. But probably not necessary.
    - From now on, the `precommit` hook will try to update all your files before committing them so that your merges pass the linting Action (`.github/workflows/check.yml`).

3. Set environment variables; see [env.example](../dle/env.example) for a list of required variables. Some of these variables control whether setup scripts (e.g. Django migrations) are run.
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
        - `python:3.11-slim-buster` base image
        - Installs some system dependencies
        - Installs Python dependencies from `requirements.txt`
        - Does not copy the source code into the container - instead, mounts the source code as a volume so you can make changes on your local machine and have them reflected in the container. For ECS deploys, code is copied into the container.
        - At some point either in this step or a bit later, if you have not already downloaded the `PubMedBERT` model, it will be downloaded from HuggingFace and saved to `api/bert_model/`. That adds a couple minutes.
        - Estimated time: ~20 minutes
    - Pulls Postgres 14 image
    - Pulls Elasticsearch 8.x (currently 8.7) image and Kibana image, which are used for the `es01` (only running 1 node for now), `elastic-setup`, and `kibana` services
    - Starts all the services, which provisions Elasticsearch and Kibana (not with our schema yet)
    - Runs Django entrypoint script
        - Waits for Postgres connection to succeed
        - Runs Django migrations if `MIGRATE` is set to `True`
        - Collects static files if `MIGRATE` is set to `True` (possibly have another env variable for this?)
        - Creates a superuser if `INIT_SUPERUSER` is set to `True` and `SUPERUSER_USERNAME` and `SUPERUSER_PASSWORD` are set. This uses a custom command so it doesn't fail if the user already exists.
        - Loads data:
            - There are multiple options to get data loaded. Data needs to exist both in Django and Elasticsearch; it is first loaded into Django, then indexed into Elasticsearch. Data needs to both be scraped and parsed from agency websites, XML files, or PDFs and then vectorized. We track when each label was last scraped in order to be able to speed up future scrape + ingest jobs; if we only want to update monthly, then the script is parameterized to allow us to skip labels updated more recently than that threshold. The default is to update labels scraped within the past week. Additionally, we save parsing errors so we can skip labels that have known errors; again, this can be overriden, but the combination of these two approaches (skipping errors and recently scraped labels) speeds up many jobs substantially.
            - The following options are mutually exclusive (no need to load data from multiple sources)
                - Option 1: create the data yourself
                    - Set `LOAD` to `True` and `VECTORIZE` to `True`
                    - This takes the longest but generates data from scratch. Probably a couple of days total. Estimated scraping time:
                        - EMA:
                        - TGA:
                        - OpenFDA:
                        - HC:
                    - Estimated vectorization time:
                    - You can also not set `LOAD` to `True`, and instead run `load_<agency>_data` commands manually to scrape just one agency. Make sure to run `update_latest_drug_labels` as well.
                - Option 2: load data from a fixture
                    - Set `LOAD_FIXTURES` to `True` and place the appropriate fixture files in `/app/data/fixtures`. These are in the S3 bucket.
                    - This is fairly fast and does not wipe your local database the same way that loading a `PSQL` dump does, but it does potentially use a lot of RAM. Estimated time: 30 minutes
                - Option 3: load data from a PSQL dump. This is the fastest option but it will wipe your local database.
                    - Obtain a PSQL dump from the S3 bucket and place it in `/app/media/psql.dump`
                    - Set `LOAD_PSQL_DUMP` to `True`
                    - Loads both data and vectors. Estimated time:
        - Ingest data from Django into Elasticsearch
            - Set `PROVISION_ES` to `True` to provision Elasticsearch with the `productsection` index and mappings
            - Uses the mapping file at `search/mappings/provision.json` to create the index with our schema
            - Then ingests all the agency data from Django to Elasticsearch
            - Estimted time: 20-30 minutes for 150k sections (TGA, EMA, HC). No estimate for OpenFDA, couldn't run that locally.
        - Runs a webserver for Django
            - Set `USE_NGINX` to `True` for production deployments with Nginx + Gunicorn
            - Otherwise uses Django's built-in `runserver` command on port `8000`

5. Services:
    - Django: http://localhost:8000
    - Elasticsearch: https://localhost:9200
        - you may need to accept the self-signed certificate
        - when `curling` you can use `-k` to ignore certificate errors
        - otherwise you can use `--cacert` to specify a certificate - copy it from container to your local machine with `docker cp <containerId>:/usr/share/elasticsearch/config/certs/ca/ca.crt .`)
        - or use Kibana console to interact with Elasticsearch instead
    - Kibana: http://localhost:5601
    - Postgres: http://localhost:5432
        - Exec into the container with `docker compose exec postgres bash`
        - Enter the PSQL CLI with `psql -U postgres`

#### Optional or manual steps

- We used to manually create Elasticsearch index and mappings
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

- We used to more manually load vector data into Postgres and Elasticsearch
    - Either create your own vectors, or download existing pre-computed vectors (JSON) from S3
        - If using pre-computed vectors, you will need to make sure that `version_date` of those vectors matches the `version_date` of your Postgres / Django `DrugLabel` objects. You may need to use the Django ORM to modify the version date - this is at least the case for EMA labels currently. Peter's EMA fix may have resolved this but haven't tried re-ingesting EMA labels or re-creating EMA vectors after that fix. This is pretty brittle and didn't work well because of misses on nested composite keys (`DrugLabel.source_product_number` + `dl.version_date` + `section_name`).
        - If creating vectors, check out the `docs/section_mapping/vectorize.ipynb` notebook. You should use `django_extensions` to run the notebooks with the Django context, but on your local machine rather than within Docker. YMMV but it seems that for some reason vectorization is agonizingly slow within Docker for Mac.
    - Place the vectors into `media` folder.
    - Exec into the Django container - from `dle`, `docker compose exec django bash`
    - Run the management command to ingest: `python3 manage.py vectorize --elasticingest True --vector_file "ema_vectors.json" --agency EMA`
        - `elasticingest` defaults to true, this will put vectors from PSQL to Elasticsearch
        - If `vector_file` is passed, it will try to load the data from your JSON file into Elasticsearch after loading into Postgres

### Tests
- We use `pytest` and `pytest-docker` for testing. Tests are located in `dle/tests` and configured in `pyproject.toml`. They run using `tests/docker-compose-tests.yml` and the environment variables defined in `tests/test.env`.
- To run tests:
    - Locally:
        - Install `pyenv` and `python3.11`
        - Create a virtual environment. From the root of the project, run `python3.11 -m venv dle-env`
        - Activate the virtual environment. Run `source dle-env/bin/activate`
        - Install dependencies. Run `pip install -r requirements.txt` and `pip install -r tests/pytest_requirements.txt`
        - Run tests: `python3.11 -m pytest -vv -s`
    - Running these tests in Docker is technically possible (Docker in Docker) but have not explored this yet.
- To write tests:
    - Check out `pytest` documentation: https://docs.pytest.org/en/7.3.x/
    - Check out `pytest-docker` documentation: https://github.com/avast/pytest-docker
    - Place tests in `dle/tests/unit` or create new directories if adding integration, load, or functional tests
    - Test files should be prefaced with `test_` and end with `.py`. Typically use one file per Django app.
    
## Deployment

### AWS Architecture