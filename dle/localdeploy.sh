#!/bin/bash
mv .env.example .env
sed '/MEM_LIMIT.*/d' .env > .env.tmp
mv .env.tmp .env
sed '/PROVISION_ES.*/d' .env > .env.tmp
mv .env.tmp .env

# Uncomment these if database has never been created. May take several hours.
#echo "LOAD=True" >> .env
#echo "PROVISION_ES=True" >> .env

echo "MEM_LIMIT=4294967296" >> .env
echo "KIBANA_MEM_LIMIT=1073741824" >> .env
docker-compose up

