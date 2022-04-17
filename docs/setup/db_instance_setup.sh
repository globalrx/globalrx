
## Setup MariaDB Server Instance

# Using Ubuntu 18.04 - x86

##### declaring variables here for now, can parameterize

# update `dle/dle/settings.py` to match the values used here
DB_NAME='dle'
DB_USER='dle_user'
DB_USER_PW='uDyvfMXHIKCJ'

# NOTE: Also need to set the HOST using the Private IP address of "this" server

##### Install MariaDB

sudo apt-get install software-properties-common dirmngr apt-transport-https -y
sudo apt-key adv --fetch-keys 'https://mariadb.org/mariadb_release_signing_key.asc'
sudo add-apt-repository 'deb [arch=amd64,arm64,ppc64el] https://mirrors.xtom.com/mariadb/repo/10.7/ubuntu bionic main'

sudo apt update
sudo apt install libjemalloc1 -y
sudo apt install mariadb-server mariadb-backup libmariadb3 mariadb-client -y

##### Setup a custom config file

sudo tee /etc/mysql/mariadb.conf.d/z-custom-my.cnf > /dev/null <<EOF
[mariadb]
log_error = mariadbd.err
character_set_server = utf8
collation_server = utf8_general_ci

# https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html
innodb_buffer_pool_size = 12G
innodb_flush_method = O_DIRECT
innodb_flush_log_at_trx_commit=2

# override settings from /etc/mysql/mariadb.conf.d/50-server.cnf
[mysqld]
bind-address = 0.0.0.0

EOF

##### Start and enable the services

sudo systemctl start mariadb
sudo systemctl enable mariadb

##### Set the locale

sudo localedef -i en_US -f UTF-8 en_US.UTF-8

##### Setup db users

# setup the db user
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
