#!/bin/bash

mv .env.example .env
sed '/MEM_LIMIT.*/d' .env > .env.tmp
mv .env.tmp .env

sed '/PROVISION_ES.*/d' .env > .env.tmp
mv .env.tmp .env

echo "MEM_LIMIT=4294967296" >> .env
echo "KIBANA_MEM_LIMIT=1073741824" >> .env

export PATH=$PATH:/Applications/Docker.app/Contents/Resources/bin/
docker-compose up