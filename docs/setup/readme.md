
### Drug Label Explorer Setup

#### Overview

This document contains information relating to deploying the DLE system in AWS.

#### DLE Deployment

The current architecture of DLE includes 2 EC2 instances (one for Django server and one for MariaDB server), and uses Route 53 for the domain name and DNS.

There are currently 2 scripts that are provided that can assist with the deployment of the instances: `server_instance_setup.sh`, and `db_instance_setup.sh`.

Overview of current procedure:

- Configure hosts in Route 53
- Launch DB Server
- Launch Django Server


#### Configure DNS, hosts in AWS / Route 53

- Overview
  - Register public domain name
  - Allocate Elastic IP addresses in EC2
  - Assign IP addresses to the domain names chosen

- First, we register a domain name on Route 53 (using druglabelexplorer.org)
- Then, we allocate 2 Elastic IP addresses (one for django-server and one for db-server) in EC2. These can be tagged / named (django-server and db-server) to more easily identify them in the future.
- In the Hosting Zone created for the chosen domain name (druglabelexplorer.org), create two 'A' records to route traffic to the public Elastic IP address we created for the django-server: create one for 'www' and one for ''.
- Create a private Hosted Zone for the DB (using drug-label-db.org), specify the VPC that will host the instances
- Create an 'A' record for the db – specify the private IP from from the Elastic IP allocated for the db-instance. Record name can be ''.
- Note the public host name created for the website (druglabelexplorer.org) and the private host name created for the database (drug-label-db.org).

#### Configure parameters

- Main parameters for system setup are: host, db\_host, db\_password
  - host: the public url for the website
  - db\_host: the private url that the django instance will use to connect to the db instance
  - db\_password: the password for the db_user

- These parameters need to be specified in the following files: 
	- [`dle/dle/settings.py`](../../dle/dle/settings.py) in (`ALLOWED_HOSTS` and `DATABASES` (`NAME`, `USER`, `PASSWORD`, `HOST`))
	- [`dle.conf`](./dle.conf) in (`ServerName`, `ServerAlias` and `ServerAdmin`)
	- [`server_instance_setup.sh`](./server_instance_setup.sh) (in `HOST`, `HOST_ALIAS`, `HOST_EMAIL`)
	- [`db_instance_setup.sh`](./db_instance_setup.sh) in (`DB_NAME`, `DB_USER`, `DB_USER_PW`)


#### Launch and Setup Database Server

Launch EC2 Instance
(using these settings for now, may modify)

```
Amazon Linux 2 AMI
arm
r6g.large
50GB gp3 disk
Tags: 'Name' => 'dle-maria'
Create Security Group (maria-dev): open 22, 3306 to all incomming traffic
Create key-pair (dle-dev) # using existing key-pair
Launch Instance
```

- Associate Elastic IP with Instance (private IP address for db-server)

##### ssh/login to the server
```
# 'cd' to the directory that contains the private key

# need to update the permissions for the downloaded private key
chmod 600 dle-dev.pem

ssh -i dle-dev.pem ec2-user@34.218.101.115
```

- Run the [`db_instance_setup.sh`](./db_instance_setup.sh) script on the server.


#### Launch and Setup Django Application Server

- NOTE that the `server_instance_setup.sh` script pulls the source code from the DLE repository here: [https://github.com/DrugLabelExplorer/dle](https://github.com/DrugLabelExplorer/dle). Changes to the files in the 'Configure parameters' section should be checked into VCS to be pulled by this script. Alternatively, the url for the repository can be modified in the script to point to a different fork or branch of the code.

Launch EC2 Instance
(using these settings for now, may modify)

```
Amazon Linux 2 AMI
X86
t2.micro
16GB gp3 disk
Tags: 'Name' => 'dle-django'
Create Security Group (dev): open 22, 80, 443 to all incomming traffic
Create key-pair (dle-dev)
Launch Instance
```

- Associate Elastic IP with Instance (public IP address for django-server)


##### ssh/login to the server
```
# 'cd' to the directory that contains the private key

# need to update the permissions for the downloaded private key
chmod 600 dle-dev.pem

ssh -i dle-dev.pem ec2-user@34.218.101.115
```

- Run the [`server_instance_setup.sh`](./server_instance_setup.sh) script on the server.


#### Verify Setup

- Should be able to view the website on the specified domain name: [https://druglabelexplorer.org](https://druglabelexplorer.org)


##### connect to db - cli
```
# on the db-server
sudo mariadb

# on the django-server, using the private host
mysql --user=dle_user --password=12345 --host=drug-label-db.org --port=3306 dle
```

##### View the Apache logs (see if any errors)

```
# on the django-server
sudo apachectl configtest # tests for typos in the Apache config
sudo tail -n 100 /var/log/httpd/error_log # apache error log
sudo tail -n 100 /var/log/httpd/ssl_error_log # ssl error log
```

______
______

References: 

[Django Quick Install Guide](https://docs.djangoproject.com/en/4.0/intro/install/)

[How to Install Django](https://docs.djangoproject.com/en/4.0/topics/install/)

[Python Installation](https://techviewleo.com/how-to-install-python-on-amazon-linux/)

[virtualenv setup](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-linux-python3-boto3/)

[mod_wsgi installation](https://modwsgi.readthedocs.io/en/develop/user-guides/quick-installation-guide.html)

[setup Django to use TLS](https://stackoverflow.com/q/4323737/1807627)

[setup MariaDB to use TLS](https://mariadb.com/kb/en/securing-connections-for-client-and-server/)

[Installing MariaDB with yum](https://mariadb.com/kb/en/yum/)

[Install MariaDB 10.7 on Amazon Linux 2](https://techviewleo.com/how-to-install-mariadb-server-on-amazon-linux/)

[MySQL Secure Install Script](https://bertvv.github.io/notes-to-self/2015/11/16/automating-mysql_secure_installation/)

[Configure SSL/TLS on Amazon Linux 2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/SSL-on-amazon-linux-2.html)

[Using Lets Encrypt on Amazon Linux 2](https://aws.amazon.com/blogs/compute/extending-amazon-linux-2-with-epel-and-lets-encrypt/)

[Using CertBot](https://eff-certbot.readthedocs.io/en/stable/using.html)

[ELB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-application-load-balancer.html)

[MariaDB ColumnStore Tables](https://mariadb.com/docs/multi-node/columnstore/schema-design/create-table/)

[MariaDB Deployment](https://mariadb.com/docs/deploy/)

[MariaDB ColumnStore configuration](https://mariadb.com/docs/deploy/topologies/columnstore-object-storage/enterprise-server-10-6/)

[MariaDB ColumnStore test installation](https://fromdual.com/create-a-single-node-mariadb-columnstore-test-installation)

[MariaDB ColumnStore Deployment](https://mariadb.com/docs/deploy/topologies/single-node/community-columnstore-cs10-6/)
_____

[TODO](https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/)

_____