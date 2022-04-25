
## Setup MariaDB Server Instance

# Using Amazon Linux 2 AMI - arm

##### declaring variables here for now, can parameterize

# update `dle/dle/settings.py` to match the values used here
DB_NAME='dle'
DB_USER='dle_user'
DB_USER_PW='uDyvfMXHIKCJ'

# NOTE: Also need to set the HOST using the Private IP address of "this" server

##### Install MariaDB

sudo yum update -y

# using MariaDB 10.6
sudo tee /etc/yum.repos.d/MariaDB.repo > /dev/null <<EOF
# MariaDB 10.6 CentOS repository list
# https://mariadb.org/download/
[mariadb]
name = MariaDB
baseurl = https://mirrors.gigenet.com/mariadb/yum/10.6/centos7-aarch64
gpgkey=https://mirrors.gigenet.com/mariadb/yum/RPM-GPG-KEY-MariaDB
gpgcheck=1
EOF
sudo yum makecache 
sudo yum install MariaDB-server MariaDB-client MariaDB-devel -y

##### Setup a custom config file

sudo tee /etc/my.cnf.d/z-custom-my.cnf > /dev/null <<EOF
[mariadb]
log_error = mariadbd.err
character_set_server = utf8
collation_server = utf8_general_ci

# https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html
# 32GB RAM on the server
innodb_buffer_pool_size = 24G
innodb_flush_method = O_DIRECT
innodb_flush_log_at_trx_commit=2

# override settings from /etc/mysql/mariadb.conf.d/50-server.cnf
[mysqld]
bind-address = 0.0.0.0

EOF

##### Start and enable the services

sudo systemctl start mariadb
sudo systemctl enable mariadb

##### Create db +  user

sudo mysql <<EOF
DROP USER IF EXISTS $DB_USER;
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME DEFAULT CHARACTER SET UTF8;
CREATE USER '$DB_USER'@'%' IDENTIFIED BY '$DB_USER_PW';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';
GRANT ALL PRIVILEGES ON test_$DB_NAME.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF

##### Restart the services

sudo systemctl restart mariadb

#####
