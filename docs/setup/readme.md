
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

- First, we register a domain name on Route 53 (using druglabelexplorer.org)
- Then, we allocate 2 Elastic IP addresses (one for django-server and one for db-server) in EC2. These can be tagged / named (django-server and db-server) to more easily identify them in the future.
- In the Hosting Zone created for the chosen domain name (druglabelexplorer.org), create two 'A' records to route traffic to the public Elastic IP address we created for the django-server: create one for 'www' and one for ''.
- Create a private Hosted Zone for the DB (using drug-label-db.org), specify the VPC that will host the instances
- Create an 'A' record for the db – specify the private IP from from the Elastic IP allocated for the db-instance. Record name can be ''.
- Note the public host name created for the website (druglabelexplorer.org) and the private host name created for the database (drug-label-db.org).

#### Configure parameters
#### Launch DB Server
#### Launch Django Server


- Main parameters for system setup are: host, db\_host, db\_password
  - host: the public url for the website
  - db\_host: the private url that the django instance will use to connect to the db instance
  - db\_password: the password for the db_user
- Hosts need to be configured. Using AWS -> Route 53
  - Register public domain name
  - Allocate Elastic IP addresses in EC2
  - Assign IP addresses to the domain names chosen
- Configure settings in `dle/dle/settings.py`, `dle.conf`, `server_instance_setup.sh`, `db_instance_setup.sh`
- Launch Server Instance
- Launch DB Instance
- Verify setup



#### Launch and Setup Application Server

- in EC2, Launch Instance
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

- Associate Elastic IP with Instance


##### ssh/login to the server
```
# 'cd' to the directory that contains the private key

# need to update the permissions for the downloaded private key
chmod 600 dle-dev.pem

ssh -i dle-dev.pem ec2-user@34.218.101.115
```

##### [Basic Django Linux server installation](./server_instance_setup.sh)

##### Apache help notes

```
sudo apachectl configtest # tests for typos in the Apache config
sudo tail -n 100 /var/log/httpd/error_log # apache error log
sudo tail -n 100 /var/log/httpd/ssl_error_log # ssl error log
```

______

#### Launch and Setup Database Server

Maria DB Instance

Allocate Elastic IP Address

> 44.238.69.61

Launch EC2 Instance

```
Ubuntu 18.04
x86
t2.medium
16GB gp3 disk
Tags: 'Name' => 'dle-maria'
Create Security Group (maria-dev): open 22, 3306 to all incomming traffic
Create key-pair (dle-dev) # using existing key-pair
Launch Instance
```

Associate Elastic IP address

##### [Maria DB Server Setup](./db_instance_setup.sh)

##### connect to db - Django

Update settings.py to match server
```
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'dle',
        'USER': 'dle_user',
        'PASSWORD': 'uDyvfMXHIKCJ',
        'HOST': '44.238.69.61',
        'PORT': '3306',
    }
```

##### connect to db - cli
```
# this 'should' allow to connect to MariaDB after we setup the user and password
mysql --user=dle_user --password=uDyvfMXHIKCJ --host=44.238.69.61 --port=3306 dle

# this works for root user before setting a pw
sudo mysql --user=root --password=''

# can use private IP address from "in network computer"
mysql --user=dle_user --password=uDyvfMXHIKCJ --host=172.31.56.135 --port=3306 dle
```

##### enable TLS for db traffic *** Not doing this, using private network IP

> /etc/my.cnf

```
[mariadb]
...
tls_version = TLSv1.2,TLSv1.3
ssl_cert = /etc/my.cnf.d/certificates/server-cert.pem
ssl_key = /etc/my.cnf.d/certificates/server-key.pem
ssl_ca = /etc/my.cnf.d/certificates/ca.pem
```
Also see:
> /etc/my.cnf.d/enable_encryption.preset

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

TODO: https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

_____


