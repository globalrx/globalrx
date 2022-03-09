
## WIP

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

##### Basic Django Linux server installation

```
# need Python 3.8, 3.9 or 3.10 for Django 4.0
# running on Amazon Linux 2 box
# running as ec2-user

# installing python3.8 from amazon-linux-extras
sudo yum update -y
sudo amazon-linux-extras enable python3.8
sudo yum install python3.8 -y
sudo yum install python38-devel -y

# links python3.8 to python3 command
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# setup the virtualenv
python3 -m venv django/venv

# activate the virtualenv
source ~/django/venv/bin/activate

# automatically activate virtualenv on admin sign-in
echo "source ${HOME}/django/venv/bin/activate" >> ${HOME}/.bashrc

# install python packages
# TODO use the requirements.txt
# pip install -r requirements.txt
pip3 install numpy
pip3 install requests
pip3 install Django==4.0.2

# deactivate the virtualenv
deactivate

# Install Apache
sudo yum install httpd -y
sudo yum install httpd-devel -y

# install mod_wsgi, needs devel versions of python and apache
sudo yum install gcc -y
wget https://github.com/GrahamDumpleton/mod_wsgi/archive/refs/tags/4.9.0.tar.gz
tar -xzf 4.9.0.tar.gz
cd mod_wsgi-4.9.0
./configure --with-python=/usr/bin/python3.8
sudo make install
make clean
cd ~/
sudo rm -rf mod_wsgi-4.9.0
rm 4.9.0.tar.gz

# update httpd.conf
# TODO load this file differently + will have more configurations
sudo vi /etc/httpd/conf/httpd.conf
# inserted on line 58
LoadModule wsgi_module modules/mod_wsgi.so
# esc : wq enter

# start apache
sudo service httpd start

# test apache
# apache error log: sudo cat /var/log/httpd/error_log
# sudo vi /var/www/html/index.html
# insert "Hello World!"
# TODO update permissions
http://34.218.101.115/
http://druglabelexplorer.org/
http://www.druglabelexplorer.org/

```

Ref:

[Django Quick Install Guide](https://docs.djangoproject.com/en/4.0/intro/install/)

[How to Install Django](https://docs.djangoproject.com/en/4.0/topics/install/)

[Python Installation](https://techviewleo.com/how-to-install-python-on-amazon-linux/)

[virtualenv setup](https://aws.amazon.com/premiumsupport/knowledge-center/ec2-linux-python3-boto3/)

[mod_wsgi installation](https://modwsgi.readthedocs.io/en/develop/user-guides/quick-installation-guide.html)

#### Setup our Application

> Need to move this earlier in the flow, grab the requirements.txt and httpd, etc from the repo

```
sudo yum install git -y

mkdir django # this dir already exists
cd django
git clone https://github.com/DrugLabelExplorer/dle.git
cd dle
# git checkout ky/create-search-form

# our repo is here: /home/ec2-user/django/dle/
# our venv is here: /home/ec2-user/django/venv/

sudo vi /etc/httpd/conf/httpd.conf

# added at line 161:

Alias /robots.txt /home/ec2-user/django/dle/static/robots.txt
Alias /favicon.ico /home/ec2-user/django/dle/static/favicon.ico

Alias /media/ /home/ec2-user/django/dle/media/
Alias /static/ /home/ec2-user/django/dle/static/

<Directory /home/ec2-user/django/dle/static>
Require all granted
</Directory>

<Directory /home/ec2-user/django/dle/media>
Require all granted
</Directory>

WSGIScriptAlias / /home/ec2-user/django/dle/dle/dle/wsgi.py

WSGIDaemonProcess dle python-home=/home/ec2-user/django/venv python-path=/home/ec2-user/django/dle/dle
WSGIProcessGroup dle

# doesn't use this with daemon mode
# WSGIPythonHome /home/ec2-user/django/venv
# WSGIPythonPath /home/ec2-user/django/dle

<Directory /home/ec2-user/django/dle/dle >
<Files wsgi.py>
Require all granted
</Files>
</Directory>

```
in settings.py
import os
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
# need to overwrite this line
ALLOWED_HOSTS = ['34.218.101.115']

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic


```
# set file permissions
sudo usermod -a -G apache ec2-user
sudo chown -R ec2-user:apache /home/ec2-user/django
sudo chmod 2775 /home/ec2-user/django && find /home/ec2-user/django -type d -exec sudo chmod 2775 {} \;
### DONT DO THIS, it messes up the venv/bin
find /home/ec2-user/django -type f -exec sudo chmod 0664 {} \;
```

https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

sudo service httpd restart

        SSLCertificateFile /etc/letsencrypt/live/tester.com/cert.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/tester.com/privkey.pem
        Include /etc/letsencrypt/options-ssl-apache.conf
        SSLCertificateChainFile /etc/letsencrypt/live/tester.com/chain.pem

sudo apachectl configtest

# TODO
```
# install mysql client on application server

```
Using MariaDB 10.6

for the amazon-linux-2/x86
```
cat > MariaDB.repo <<EOF
# MariaDB 10.6 CentOS repository list
# https://mariadb.org/download/
[mariadb]
name = MariaDB
baseurl = https://mirrors.gigenet.com/mariadb/yum/10.6/centos7-amd64
gpgkey=https://mirrors.gigenet.com/mariadb/yum/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
sudo chown root:root MariaDB.repo
sudo mv MariaDB.repo /etc/yum.repos.d/MariaDB.repo
sudo yum makecache 
sudo yum install MariaDB-server MariaDB-client -y

pip install mysqlclient
```
______

#### Setup database server

##### Using Maria DB

https://docs.djangoproject.com/en/4.0/ref/databases/

______

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

Login to instance

# setup db instance
Amazon Linux 2 AMI - arm
```
sudo yum update -y
cat > MariaDB.repo <<EOF
# MariaDB 10.6 CentOS repository list
# https://mariadb.org/download/
[mariadb]
name = MariaDB
baseurl = https://mirrors.gigenet.com/mariadb/yum/10.6/centos7-aarch64
gpgkey=https://mirrors.gigenet.com/mariadb/yum/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
sudo chown root:root MariaDB.repo
sudo mv MariaDB.repo /etc/yum.repos.d/MariaDB.repo
sudo yum makecache 
sudo yum install MariaDB-server MariaDB-client -y
```

```
sudo systemctl start mariadb
sudo systemctl enable mariadb

# simulate: sudo mariadb-secure-installation

# maybe works?
sudo mysql --user=root --password='' <<EOF
/* set root password */
UPDATE mysql.user SET Password=PASSWORD('MaryHadALittleLamb1!') WHERE User='root';
/* delete anonymous users */
DELETE FROM mysql.user WHERE User='';
/* root user cannot login remotely */
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
/* drop test database */
DROP DATABASE test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\_%';
/* flush privileges */
FLUSH PRIVILEGES;
EOF


DROP USER IF EXISTS dle_user;
DROP DATABASE IF EXISTS dle;
CREATE DATABASE dle DEFAULT CHARACTER SET UTF8;
CREATE USER 'dle_user'@'localhost' IDENTIFIED BY 'uDyvfMXHIKCJ';
GRANT ALL PRIVILEGES ON dle.* TO 'dle_user'@'localhost';
FLUSH PRIVILEGES;

```

update settings.py

    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'dle',
        'USER': 'dle_user',
        'PASSWORD': 'uDyvfMXHIKCJ',
        'HOST': '44.238.69.61',   # Or an IP Address that your DB is hosted on
        'PORT': '3306',
    }

Need to update my.cnf

https://mariadb.com/kb/en/configuring-mariadb-for-remote-client-access/


### Setup a Maria DB Instance using ColumnStore Storage Engine

Ref: 

[Installing MariaDB with yum](https://mariadb.com/kb/en/yum/)

[Install MariaDB 10.7 on Amazon Linux 2](https://techviewleo.com/how-to-install-mariadb-server-on-amazon-linux/)

[MySQL Secure Install Script](https://bertvv.github.io/notes-to-self/2015/11/16/automating-mysql_secure_installation/)

[Configure SSL/TLS on Amazon Linux 2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/SSL-on-amazon-linux-2.html)

https://docs.djangoproject.com/en/4.0/ref/databases/

Document root
chown :apache /home/ec2-user
sudo chmod 755 /home/ec2-user
added WSGIPythonHome in httpd.conf

issue with venv permissions, delete and recreate

http://druglabelexplorer.org/search/

