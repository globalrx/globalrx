

# declaring variables here for now, can parameterize
# update `dle/dle/settings.py` to match the values used here
DB_NAME='dle'
DB_USER='dle_user'
DB_USER_PW='uDyvfMXHIKCJ'

# not needed for normal operations, for db-admin
ROOT_USER_PW='XjRjhRTT5djqSQZQ'

########

# Want to setup a MariaDB Server Instance
# Using Amazon Linux 2 AMI - arm

sudo yum update -y

# Linux Kernel Paramaters
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

# TOOD https://dlm.mariadb.com/2142618/MariaDB/mariadb-10.6.7/yum/centos/mariadb-10.6.7-rhel-7-aarch64-rpms.tar

# using MariaDB 10.6
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

# columnstore-engine, requires jemalloc
cd /tmp
wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo rpm -Uvh epel-release*rpm
sudo yum install jemalloc -y
cd ~/

sudo yum install MariaDB-server MariaDB-backup \
   MariaDB-shared MariaDB-client \
   MariaDB-columnstore-engine -y

sudo systemctl start mariadb-columnstore
sudo systemctl enable mariadb-columnstore

sudo systemctl start mariadb
sudo systemctl enable mariadb

# simulate: sudo mariadb-secure-installation

sudo mysql --user=root --password='' <<EOF
/* set root password */
UPDATE mysql.user SET Password=PASSWORD('$ROOT_USER_PW') WHERE User='root';
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

# setup the db user
sudo mysql --user=root --password='$ROOT_USER_PW' <<EOF
DROP USER IF EXISTS $DB_USER;
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME DEFAULT CHARACTER SET UTF8;
CREATE USER '$DB_USER'@'%' IDENTIFIED BY '$DB_USER_PW';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF

# setup the cross_engine user
sudo mysql --user=root --password='$ROOT_USER_PW' <<EOF
CREATE USER 'cross_engine'@'127.0.0.1' IDENTIFIED BY "cross_engine_passwd";
CREATE USER 'cross_engine'@'localhost' IDENTIFIED BY "cross_engine_passwd";
GRANT SELECT, PROCESS ON *.* TO 'cross_engine'@'127.0.0.1';
GRANT SELECT, PROCESS ON *.* TO 'cross_engine'@'localhost';
EOF

# update my.cnf settings
sudo tee /etc/my.cnf.d/z-custom-mariadb.cnf > /dev/null <<EOF
[mariadb]
log_error = mariadbd.err
character_set_server = utf8
collation_server = utf8_general_ci
columnstore_use_import_for_batchinsert = ALWAYS
default_storage_engine = ColumnStore
# TODO additional setup
EOF

# note logs here: /var/log/mariadb/columnstore

sudo systemctl restart mariadb
sudo systemctl restart mariadb-columnstore


