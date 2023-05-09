#!/bin/bash

DB_ENDPOINT=`aws ssm get-parameters --names rds_endpoint --region us-east-1 | jq -r '.Parameters[0].Value'`
ECS_LB=`aws ssm get-parameters --names ecs_lb --region us-east-1 | jq -r '.Parameters[0].Value'`
EC2_IP=`aws ssm get-parameters --names ec2_ip --region us-east-1 | jq -r '.Parameters[0].Value'`
RDS_PW=`aws ssm get-parameters --names rds_pword --region us-east-1 | jq -r '.Parameters[0].Value'`
ELASTIC_PW=`aws ssm get-parameters --names elastic_pw --region us-east-1 | jq -r '.Parameters[0].Value'`
KIBANA_PW=`aws ssm get-parameters --names kibana_pw --region us-east-1 | jq -r '.Parameters[0].Value'`


cp .env.example .env

sed '/DATABASE.*/d' -i .env
sed '/PROVISION_ES.*/d' -i .env
sed '/ELASTICSEARCH_URL.*/d' -i .env
sed '/API_ENDPOINT.*/d' -i .env
sed '/ALLOWED_HOSTS.*/d' -i .env
sed '/MEM_LIMIT.*/d' -i .env
sed '/ELASTIC_PASSWORD.*/d' -i .env
sed '/KIBANA_PASSWORD.*/d' -i .env


sed '/.*ca_certs.*/d' -i dle/settings.py
sed '/.*ssl.TLSVersion.TLSv1_2.*/d' -i dle/settings.py


echo "" >> .env
echo "DATABASE_URL=\"postgres://postgres:$RDS_PW@$DB_ENDPOINT:5432/postgres\"" >> .env
echo "ELASTICSEARCH_URL=http://$EC2_IP:9200" >> .env
echo "MEM_LIMIT=8589934592" >> .env
echo "KIBANA_MEM_LIMIT=1073741824" >> .env
echo "ELASTIC_PASSWORD=$ELASTIC_PW" >> .env
echo "KIBANA_PASSWORD=$KIBANA_PW" >> .env