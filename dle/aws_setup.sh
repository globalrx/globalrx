#!/bin/bash
#
#

DB_ENDPOINT=`aws ssm get-parameters --names db_endpointdev --region us-east-1 | jq -r '.Parameters[0].Value'`
ECS_LB=`aws ssm get-parameters --names ecs_lb --region us-east-1 | jq -r '.Parameters[0].Value'`
#"lb-LoadBala-7N50H575NERW-21ffc23ad96ff98e.elb.us-east-1.amazonaws.com"
EC2_IP=`aws ssm get-parameters --names ec2_ip_dev --region us-east-1 | jq -r '.Parameters[0].Value'`


mv .env.example .env

sed '/DATABASE.*/d' -i .env
sed '/MEM_LIMIT.*/d' -i .env
sed '/PROVISION_ES.*/d' -i .env
sed '/ELASTICSEARCH_URL.*/d' -i .env


echo "DATABASE_URL=\"postgres://postgres:fghyucvsafd@$DB_ENDPOINT:5432/postgres\"" >> .env
echo "API_ENDPOINT=\"$EC2_IP\"" >> .env
echo "ALLOWED_HOSTS=\"$EC2_IP, $ECS_LB\">> .env
echo "MEM_LIMIT=4294967296" >> .env
echo "PROVISION_ES=True" >> .env
echo "ELASTICSEARCH_URL=https://$EC2_IP:9200" >> .env

echo "KIBANA_MEM_LIMIT=1073741824" >> .env

