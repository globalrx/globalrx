

# TODO: declare variables here (or in other file) for easy modification


# Want to setup a MariaDB Server Instance
# Using Amazon Linux 2 AMI - arm

sudo yum update -y

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
sudo yum install MariaDB-server MariaDB-client -y

sudo systemctl start mariadb
sudo systemctl enable mariadb

# simulate: sudo mariadb-secure-installation

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

# setup the db user
DROP USER IF EXISTS dle_user;
DROP DATABASE IF EXISTS dle;
CREATE DATABASE dle DEFAULT CHARACTER SET UTF8;
CREATE USER 'dle_user'@'%' IDENTIFIED BY 'uDyvfMXHIKCJ';
GRANT ALL PRIVILEGES ON dle.* TO 'dle_user'@'%';
FLUSH PRIVILEGES;

# TODO update /etc/my.cnf


