#!/bin/sh

echo `date`

export PYTHONPATH=/usr/local/lib/python3.11/site-packages/
export PATH=$PATH:/usr/local/bin/
cd /app

echo "Beginning the Django data ingest"

echo "Loading EMA (EU) data"
python3.11 manage.py load_ema_data --type full
echo "Finished loading EMA (EU) data"

echo "Loading FDA (US) data"
python3.11 manage.py load_fda_data --type full
echo "Finished loading FDA (US) data"

echo "Loading TGA (Australia) data"
python3.11 manage.py load_tga_data --type full
echo "Finished loading TGA (Australia) data"
echo "Updating latest drug labels"

echo "Loading HC (Health Canada) data"
python3.11 manage.py load_hc_data --type full
echo "Finished loading HC (Health Canada) data"

python3.11 manage.py update_latest_drug_labels
echo "Finished updating latest drug labels"
echo "Ended the Django data ingest"

echo "Begin vectorizing labels"
python3.11 manage.py vectorize --agency all
echo "Done vectorizing labels"

echo "Begin indexing to ES"
python3.11 manage.py provision_elastic --agency all --mapping_file "/app/search/mappings/provision.json"
echo "Done indexing"

echo "Weekly update done"