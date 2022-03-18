
### Drug Label Explorer Setup

#### DNS

- register druglabelexplorer.org on AWS / Route 53

- allocate Elastic IP in EC2
> 34.218.101.115

- in Route 53, use Hosting Zone created for the domain name

- create 'A' record to route traffic to the Elastic IP address we created: create two: one for 'www' and one for ''

- maybe takes a bit for the DNS changes, esp new domain name...

#### Application Server

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

#### Application Server Setup

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

#### Setup database server

Maria DB Instance

Allocate Elastic IP Address

> 44.238.69.61

Launch EC2 Instance

Amazon Linux 2 AMI
arm
m6g.medium
16GB gp3 disk
Tags: 'Name' => 'dle-maria'
Create Security Group (maria-dev): open 22, 3306 to all incomming traffic
Create key-pair (dle-dev) # using existing key-pair
Launch Instance

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

##### enable TLS for db traffic *** Not doing this yet, using private network IP
/etc/my.cnf
```
[mariadb]
...
tls_version = TLSv1.2,TLSv1.3
ssl_cert = /etc/my.cnf.d/certificates/server-cert.pem
ssl_key = /etc/my.cnf.d/certificates/server-key.pem
ssl_ca = /etc/my.cnf.d/certificates/ca.pem
```
# file settings for db encryption at rest
/etc/my.cnf.d/enable_encryption.preset

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

_____

TODO: https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

_____


