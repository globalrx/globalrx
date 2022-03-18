

# TODO: declare variables here (or in other file) for easy modification
# TODO: move files from ~/ to /var/www

# Want to setup a LAMP-ish box: Linux, Apache, MariaDB, Python
# + Django
# + Certbot SSL cert

# running on Amazon Linux 2 box on x86
# running as ec2-user

sudo yum update -y

# need Python 3.8, 3.9 or 3.10 for Django 4.0
# installing python3.8 from amazon-linux-extras
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
# sudo vi /etc/httpd/conf/httpd.conf
# inserted on line 58: LoadModule wsgi_module modules/mod_wsgi.so
# esc : wq enter

# start apache
sudo service httpd start


# MariaDB 10.6 - might just need the client on this box
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

______

# TODO this needs to be modified slightly to run via script

##### Setup our Application

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

sudo service httpd restart

# rm these notes after verification
#I ran into some issues with permissions:
#Document root
#chown :apache /home/ec2-user
#sudo chmod 755 /home/ec2-user
#added WSGIPythonHome in httpd.conf

sudo systemctl start httpd && sudo systemctl enable httpd

______

# SSL / TLS setup
sudo yum install mod_ssl -y
# our domain is: druglabelexplorer.org
# ssl.conf is here: /etc/httpd/conf.d/ssl.conf
cd /etc/pki/tls/certs
sudo ./make-dummy-cert localhost.crt

# TODO: had to comment out this in ssl.conf
#SSLCertificateKeyFile /etc/pki/tls/private/localhost.key

# certbot for Let's Encrypt SSL cert
sudo yum install python2-certbot-apache.noarch -y

sudo certbot --apache

# needs virtal host setup on port 80 first

# needs Apache running first
sudo certbot --apache -d druglabelexplorer.org -d www.druglabelexplorer.org -m druglabelexplorer@gmail.com -n --agree-tos

_____

# TODO need a few changes to get this working in the script without manual modifications

# copy our Apache conf file
cp dle.conf /etc/httpd/conf.d/dle.conf

# /etc/httpd/conf.d/ssl.conf
# /etc/httpd/conf/httpd.conf
# /etc/httpd/conf.d/dle.conf

# this likely didn't help the issue I was having, might be good in general
# changed mpm in /etc/httpd/conf.modules.d/00-mpm.conf

# /etc/pki/tls/certs/localhost.crt
# /etc/pki/tls/private/localhost.key

# /etc/httpd/conf.d/dle-le-ssl.conf
# /etc/letsencrypt/live/druglabelexplorer.org/fullchain.pem
# /etc/letsencrypt/live/druglabelexplorer.org/privkey.pem

# There was an issue I ran into. Needed to comment out:
#<IfModule mod_ssl.c>
#Listen 443
#</IfModule>

______

# TODO need to setup: `sudo certbot renew`

______

