
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
Tags: 'name' => 'dle-django'
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
python3 -m venv dle/env

# activate the virtualenv
source ~/dle/env/bin/activate

# automatically activate virtualenv on admin sign-in
echo "source ${HOME}/dle/env/bin/activate" >> ${HOME}/.bashrc

# install python packages
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


https://docs.djangoproject.com/en/4.0/intro/install/
https://docs.djangoproject.com/en/4.0/topics/install/
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/modwsgi/

https://medium.com/saarthi-ai/ec2apachedjango-838e3f6014ab
https://medium.com/@shivansht9211/how-to-deploy-django-applications-on-aws-ec2-using-apache-server-f6ae2e1effc4
https://stackoverflow.com/questions/62531052/how-to-install-latest-2020-django-to-aws-ec2-linux-2-instance-and-serve-w-apa
https://www.marek.tokyo/2018/08/apache-24-modwsgi-python-37-django.html




