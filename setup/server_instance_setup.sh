
# parameters

HOST='druglabelexplorer.org'
HOST_ALIAS='www.druglabelexplorer.org'
HOST_EMAIL='druglabelexplorer@gmail.com'

#####

# Overview
# 
# Want to setup a LAMP-ish box: Linux, Apache, MariaDB, Python
# + Django
# + Certbot SSL cert
# running on Amazon Linux 2 box on x86
# running as ec2-user OR root user
#
#
# Note the following steps:
# 
# - Set parameters
# - Download Apache
# - Download MariaDB client
# - Download Python

# - clone git repo
# - Set file permissions
# - Setup Python venv
# - Apache configuration
# - SSL Cert Setup
# - Setup cron entries

#####

# - Set parameters
# Before running this script, verify the parameters are set properly in `dle/dle/settings.py`, `dle.conf` and `server_instance_setup.sh` (at the top of this script)

#####

# - Download Apache

sudo yum update -y
sudo yum install httpd -y
sudo yum install httpd-devel -y

#####

# - Download MariaDB client

sudo tee /etc/yum.repos.d/MariaDB.repo > /dev/null <<EOF
# MariaDB 10.6 CentOS repository list
# https://mariadb.org/download/
[mariadb]
name = MariaDB
baseurl = https://mirrors.gigenet.com/mariadb/yum/10.6/centos7-amd64
gpgkey=https://mirrors.gigenet.com/mariadb/yum/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
sudo yum makecache 
sudo yum install MariaDB-server MariaDB-client MariaDB-devel -y

#####

# - Download Python

# need Python 3.8, 3.9 or 3.10 for Django 4.0
# installing python3.8 from amazon-linux-extras
sudo amazon-linux-extras enable python3.8
sudo yum install python3.8 -y
sudo yum install python38-devel -y

# links python3.8 to python3 command
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# install mod_wsgi, needs devel versions of python and apache
sudo yum install gcc -y
cd /tmp
wget https://github.com/GrahamDumpleton/mod_wsgi/archive/refs/tags/4.9.0.tar.gz
tar -xzf 4.9.0.tar.gz
cd mod_wsgi-4.9.0
./configure --with-python=/usr/bin/python3.8
sudo make install
make clean
cd ..
sudo rm -rf mod_wsgi-4.9.0
rm 4.9.0.tar.gz

#####

# - clone git repo

sudo yum install git -y
cd /var/www
sudo mkdir django
cd django
sudo git clone https://github.com/DrugLabelExplorer/dle.git

#####

# - Set file permissions

sudo usermod -a -G apache ec2-user
sudo chown -R ec2-user:apache /var/www/django
sudo chmod 2775 /var/www/django && find /var/www/django -type d -exec sudo chmod 2775 {} \;
find /var/www/django -type f -exec sudo chmod 0664 {} \;
sudo chown :apache /var/www

#####

# - Setup Python venv

# setup the virtualenv
python3 -m venv /var/www/django/venv

# activate the virtualenv
source /var/www/django/venv/bin/activate

# automatically activate virtualenv on admin sign-in
echo "source /var/www/django/venv/bin/activate" >> /home/ec2-user/.bashrc

# install python packages
pip install -r /var/www/django/dle/dle/requirements.txt

#####

# - Apache configuration

sudo cp /var/www/django/dle/setup/dle.conf /etc/httpd/conf.d/dle.conf

sudo systemctl start httpd
sudo systemctl enable httpd

#####

# - SSL / TLS Setup

sudo yum install mod_ssl -y
cd /etc/pki/tls/certs
sudo ./make-dummy-cert localhost.crt
sudo cp /var/www/django/dle/setup/ssl.conf /etc/httpd/conf.d/ssl.conf

# certbot for Let's Encrypt SSL cert
sudo amazon-linux-extras install epel -y
sudo yum install python2-certbot-apache.noarch -y

cp /var/www/django/dle/setup/httpd.conf /etc/httpd/conf/httpd.conf
sudo systemctl restart httpd

# needs virtal host setup on port 80 first
# needs Apache running first
sudo certbot --apache -d $HOST -d $HOST_ALIAS -m $HOST_EMAIL -n --agree-tos

sudo systemctl restart httpd

#####

# - Setup cron entries

python /var/www/django/dle/dle/manage.py makemigrations
python /var/www/django/dle/dle/manage.py migrate
sudo certbot renew

# TODO make a file with the commands to run
# run once a month
line="1 1 1 * * /path/to/command"
# append to crontab
(crontab -u $(whoami) -l; echo "$line" ) | crontab -u $(whoami) -
# ref: https://askubuntu.com/a/58582

#####


