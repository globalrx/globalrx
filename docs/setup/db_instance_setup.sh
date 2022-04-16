
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
sudo apt install mariadb-server mariadb-backup libmariadb3 \
  mariadb-client mariadb-plugin-columnstore -y

##### Setup a custom config file

sudo tee /etc/mysql/mariadb.conf.d/z-custom-my.cnf > /dev/null <<EOF
[mariadb]
log_error = mariadbd.err
character_set_server = utf8
collation_server = utf8_general_ci
# columnstore_use_import_for_batchinsert = ALWAYS
# default_storage_engine = ColumnStore
# TODO additional setup

# 4GB RAM on box
innodb_buffer_pool_size = 2G
innodb_buffer_pool_instances = 4
innodb_buffer_pool_chunk_size = 128M

# override settings from /etc/mysql/mariadb.conf.d/50-server.cnf
[mysqld]
bind-address = 0.0.0.0

EOF

##### Start and enable the services

sudo systemctl start mariadb
sudo systemctl enable mariadb

sudo systemctl start mariadb-columnstore
sudo systemctl enable mariadb-columnstore

##### Optimize Linux Kernel Paramaters

sudo tee /etc/sysctl.d/90-mariadb-columnstore.conf > /dev/null <<EOF
# minimize swapping
vm.swappiness = 1

# Increase the TCP max buffer size
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Increase the TCP buffer limits
# min, default, and max number of bytes to use
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# don't cache ssthresh from previous connection
net.ipv4.tcp_no_metrics_save = 1

# for 1 GigE, increase this to 2500
# for 10 GigE, increase this to 30000
net.core.netdev_max_backlog = 2500
EOF

sudo sysctl --load=/etc/sysctl.d/90-mariadb-columnstore.conf

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

# setup the cross_engine user
sudo mysql <<EOF
CREATE USER 'cross_engine'@'127.0.0.1' IDENTIFIED BY "cross_engine_passwd";
CREATE USER 'cross_engine'@'localhost' IDENTIFIED BY "cross_engine_passwd";
GRANT SELECT, PROCESS ON *.* TO 'cross_engine'@'127.0.0.1';
GRANT SELECT, PROCESS ON *.* TO 'cross_engine'@'localhost';
EOF

##### Cross Engine Support

sudo mcsSetConfig CrossEngineSupport Host 127.0.0.1
sudo mcsSetConfig CrossEngineSupport Port 3306
sudo mcsSetConfig CrossEngineSupport User cross_engine
sudo mcsSetConfig CrossEngineSupport Password cross_engine_passwd

##### Restart the services

sudo systemctl restart mariadb
sudo systemctl restart mariadb-columnstore

#####
