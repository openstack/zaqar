..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Installing and Configuring
============================

System Requirements
~~~~~~~~~~~~~~~~~~~

Before you install the OpenStack Queuing Service, you must meet the following system requirements::

- OpenStack Compute Installation.
- Enable the Identity Service for user and project management.
- Python 2.6 or 2.7

Installing from Packages
~~~~~~~~~~~~~~~~~~~~~~~~

Before you install and configure queuing service, ensure you meet the
requirements in the section above called "System Requirements". The following
instructions assume installation on a RedHat based operating system (CentOS,
Fedora, etc.).

Install MongoDB on Database Servers
###################################

Install MongoDB on three servers and setup the replica-set.

Configure Package Management System (YUM)
#########################################

Create a ``/etc/yum.repos.d/mongodb.repo`` file to hold the following
configuration information for the MongoDB repository:

If you are running a 64-bit system, use the following configuration::

    [mongodb]
    name=MongoDB Repository
    baseurl=http://downloads-distro.mongodb.org/repo/redhat/os/x86_64/
    gpgcheck=0
    enabled=1

If you are running a 32-bit system, which is not recommended for production
deployments, use the following configuration::

    [mongodb]
    name=MongoDB Repository
    baseurl=http://downloads-distro.mongodb.org/repo/redhat/os/i686/
    gpgcheck=0
    enabled=1

Install Packages
################

Issue the following command (as root or with sudo) to install the latest stable
version of MongoDB and the associated tools::

    #yum install mongo-10gen mongo-10gen-server

Edit ``/etc/sysconfig/mongod``::

    logpath=/var/log/mongo/mongod.log
    logappend=true
    fork = true
    dbpath=/var/lib/mongo
    pidfilepath = /var/run/mongodb/mongod.pid
    replSet = catalog
    nojournal = true
    profile = 1
    slowms = 200
    oplogSize = 2048

Start MongoDB on all database servers::

    mydb# service mongodb start

Configure Replica Set
#####################

Once you've installed MongoDB on three servers and assuming that the primary
MongoDB server hostname is ``mydb0.example-queues.net``, go to ``mydb0``
and run these commands::

    mydb0# mongo local --eval "printjson(rs.initiate())"
    mydb0# rs.add("mydb1.example-queues.net")
    mydb0# rs.add("mydb2.example-queues.net")

To check if the replica-set is established run this command::

    mydb0# mongo local --eval "printjson(rs.status())"

Install memcached on Web Servers
################################

Install memcached on web servers in order to cache identity tokens and catalog mappings::

    web# yum install memcached

Start memcached service::

    web# service memcached start

Install uwsgi on web servers::

    web# yum -y install python-pip
    web# pip install uwsgi

Configure OpenStack Marconi
###########################

On the web servers run these commands::

    web# git clone https://github.com/openstack/marconi.git .
    web# pip install . -r ./requirements.txt --upgrade --log /tmp/marconi-pip.log

Create ``/srv/marconi`` folder to store related configuration files.

Create ``/srv/marconi/marconi_uwsgi.py`` with the following content::

    from keystoneclient.middleware import auth_token
    from marconi.transport.wsgi import app

    app = auth_token.AuthProtocol(app.app, {})

Create ``/srv/marconi/uwsgi.ini`` file with the following content::

    [uwsgi]
    http = 192.168.192.168:80
    daemonize = /var/log/marconi.log
    pidfile = /var/run/marconi.pid
    gevent = 2000
    gevent-monkey-patch = true
    listen = 1024
    enable-threads = true
    module = marconi_uwsgi:app
    workers = 4

The uwsgi configuration options above can be modified for different performance requirements.

Create a Marconi configuration file ``/etc/marconi.conf`` with the following content::

    [DEFAULT]
    # Show more verbose log output (sets INFO log level output)
    #verbose = False

    # Show debugging output in logs (sets DEBUG log level output)
    #debug = False

    # Pooling and admin mode configs
    pooling      = True
    admin_mode    = True

    # Log to this file!
    log_file = /var/log/marconi-queues.log
    debug    = False
    verbose  = False

    # This is taken care of in our custom app.py, so disable here
    ;auth_strategy = keystone

    [keystone_authtoken]
    admin_password = < admin password >
    admin_tenant_name = < admin tenant name >
    admin_user = < admin user >
    auth_host = < identity service host >
    auth_port = '443'
    auth_protocol = 'https'
    auth_uri = < identity service uri >
    auth_version = < auth version >
    token_cache_time = < token cache time >
    memcache_servers = 'localhost:11211'

    [oslo_cache]
    cache_backend = memcached
    memcache_servers = 'localhost:11211'

    [drivers]
    # Transport driver module (e.g., wsgi, zmq)
    transport = wsgi
    # Storage driver module (e.g., mongodb, sqlite)
    storage = mongodb

    [drivers:storage:mongodb]
    uri = mongodb://mydb0,mydb1,mydb2:27017/?replicaSet=catalog&w=2&readPreference=secondaryPreferred
    database = marconi
    partitions = 8

    # Maximum number of times to retry a failed operation. Currently
    # only used for retrying a message post.
    ;max_attempts = 1000

    # Maximum sleep interval between retries (actual sleep time
    # increases linearly according to number of attempts performed).
    ;max_retry_sleep = 0.1

    # Maximum jitter interval, to be added to the sleep interval, in
    # order to decrease probability that parallel requests will retry
    # at the same instant.
    ;max_retry_jitter = 0.005

    # Frequency of message garbage collections, in seconds
    ;gc_interval = 5 * 60

    # Threshold of number of expired messages to reach in a given
    # queue, before performing the GC. Useful for reducing frequent
    # locks on the DB for non-busy queues, or for worker queues
    # which process jobs quickly enough to keep the number of in-
    # flight messages low.
    #
    # Note: The higher this number, the larger the memory-mapped DB
    # files will be.
    ;gc_threshold = 1000

    [limits:transport]
    queue_paging_uplimit = 1000
    metadata_size_uplimit = 262144
    message_paging_uplimit = 10
    message_size_uplimit = 262144
    message_ttl_max = 1209600
    claim_ttl_max = 43200
    claim_grace_max = 43200

    [limits:storage]
    default_queue_paging = 10
    default_message_paging = 10

Start the queuing service::

    #/usr/bin/uwsgi --ini /srv/marconi/uwsgi.ini


Configure Pools
~~~~~~~~~~~~~~~~

To have a functional queuing service, we need to define a pool. On one of the
web servers run this command::

    curl -i -X PUT -H 'X-Auth-Token: $TOKEN' -d '{"weight": 100, "uri": "mongodb://mydb0,mydb1,mydb2:27017/?replicaSet=catalog&w=2&readPreference=secondaryPreferred", "options": {"partitions": 8}}' http://localhost:8888/v1/pools/pool1

The above ``$TOKEN`` variable is the authentication token retrieved from
identity service. If you choose not to enable Keystone authentication you won't
have to pass a token.

Reminder: In larger deployments, catalog database and queues databases (pools)
are going to be on different MongoDB replica-sets.
