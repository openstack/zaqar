.. _install-rdo:

Install and configure for Red Hat Enterprise Linux and CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Messaging service,
code-named ``zaqar`` for Red Hat Enterprise Linux 7 and CentOS 7.

This section assumes that you already have a working OpenStack environment with
at least Identity service installed.

Here you can find instructions and recommended settings for installing
Messaging service in small configuration: one web server with Messaging service
configured to use replica-set of three ``MongoDB`` database servers. Because
only one web server is used, the Messaging service installed by using these
instructions can't be considered as high available, see :doc:`install`.

In this tutorial these server names are used as examples:

* Web server with Messaging service: ``WEB0.EXAMPLE-MESSAGES.NET``.
* Database servers: ``MYDB0.EXAMPLE-MESSAGES.NET``,
  ``MYDB1.EXAMPLE-MESSAGES.NET``, ``MYDB2.EXAMPLE-MESSAGES.NET``.
* Identity service server: ``IDENTITY.EXAMPLE-MESSAGES.NET``.

Prerequisites
-------------

Before you install Messaging service, you must meet the following system
requirements:

* Installed Identity service for user and project management.
* Python 2.7.

Before you install and configure Messaging, you must create a ``MongoDB``
replica-set of three database servers. Also you need to create service
credentials and API endpoints in Identity.

#. Install and configure ``MongoDB`` replica-set on database servers:

   #. Install ``MongoDB`` on the database servers:

      On each database server follow the official `MongoDB installation
      instructions`_.

      .. note::

         Messaging service works with ``MongoDB`` versions >= 2.4

   #. Configure ``MongoDB`` on the database servers:

      On each database server edit configuration file: ``/etc/mongod.conf`` and
      modify as needed:

      .. code-block:: ini

         # MongoDB sample configuration for Messaging service.
         # (For MongoDB version >= 2.6)
         # Edit according to your needs.
         systemLog:
           destination: file
           logAppend: true
           path: /var/log/mongodb/mongod.log

         storage:
           dbPath: /var/lib/mongo
           journal:
             enabled: false

         processManagement:
           fork: true  # fork and run in background
           pidFilePath: /var/run/mongodb/mongod.pid  # location of pidfile

         net:
           port: 27017
           # bindIp: 127.0.0.1  # Listen to local interface only, comment to listen on all interfaces.

         operationProfiling:
            slowOpThresholdMs: 200
            mode: slowOp

         replication:
            oplogSizeMB: 2048
            replSetName: catalog

      .. note::

         In case of older ``MongoDB`` versions (2.4 and 2.5) the configuration
         file should be written in different format. For information about
         format for different versions see the official `MongoDB configuration
         reference`_.

      .. warning::

         Additional steps are required to secure ``MongoDB`` installation. You
         should modify this configuration for your security requirements. See
         the official `MongoDB security reference`_.

   #. Start ``MongoDB`` on the database servers:

      Start ``MongoDB`` service on all database servers:

      .. code-block:: console

         # systemctl start mongod

      Make ``MongoDB`` service start automatically after reboot:

      .. code-block:: console

         # systemctl enable mongod

   #. Configure ``MongoDB`` Replica Set on the database servers:

      Once you've installed ``MongoDB`` on three servers and assuming that the
      primary ``MongoDB`` server hostname is ``MYDB0.EXAMPLE-MESSAGES.NET``, go
      to ``MYDB0`` and run these commands:

      .. code-block:: console

         # mongo local --eval "printjson(rs.initiate())"
         # mongo local --eval "printjson(rs.add('MYDB1.EXAMPLE-MESSAGES.NET'))"
         # mongo local --eval "printjson(rs.add('MYDB2.EXAMPLE-MESSAGES.NET'))"

      .. note::

         The database servers must have access to each other and also be
         accessible from the Messaging service web server. Configure firewalls
         on all database servers to accept incoming connections to port
         ``27017`` from the needed source.

      To check if the replica-set is established see the output of this
      command:

      .. code-block:: console

         # mongo local --eval "printjson(rs.status())"

#. Source the ``admin`` credentials to gain access to admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   #. Create the ``zaqar`` user:

      .. code-block:: console

         $ openstack user create --domain default --password-prompt zaqar
         User Password:
         Repeat User Password:
         +-----------+----------------------------------+
         | Field     | Value                            |
         +-----------+----------------------------------+
         | domain_id | default                          |
         | enabled   | True                             |
         | id        | 7b0ffc83097148dab6ecbef6ddcc46bf |
         | name      | zaqar                            |
         +-----------+----------------------------------+

   #. Add the ``admin`` role to the ``zaqar`` user:

      .. code-block:: console

         $ openstack role add --project service --user zaqar admin

      .. note::

         This command provides no output.

   #. Create the ``zaqar`` service entity:

      .. code-block:: console

         $ openstack service create --name zaqar --description "Messaging" messaging
         +-------------+----------------------------------+
         | Field       | Value                            |
         +-------------+----------------------------------+
         | description | Messaging                        |
         | enabled     | True                             |
         | id          | b39c22818be5425ba2315dd4b10cd57c |
         | name        | zaqar                            |
         | type        | messaging                        |
         +-------------+----------------------------------+

#. Create the Messaging service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne messaging public http://WEB0.EXAMPLE-MESSAGES.NET:8888
      +--------------+---------------------------------------+
      | Field        | Value                                 |
      +--------------+---------------------------------------+
      | enabled      | True                                  |
      | id           | aabca78860e74c4db0bcb36167bfe106      |
      | interface    | public                                |
      | region       | RegionOne                             |
      | region_id    | RegionOne                             |
      | service_id   | b39c22818be5425ba2315dd4b10cd57c      |
      | service_name | zaqar                                 |
      | service_type | messaging                             |
      | url          | http://WEB0.EXAMPLE-MESSAGES.NET:8888 |
      +--------------+---------------------------------------+

      $ openstack endpoint create --region RegionOne messaging internal http://WEB0.EXAMPLE-MESSAGES.NET:8888
      +--------------+---------------------------------------+
      | Field        | Value                                 |
      +--------------+---------------------------------------+
      | enabled      | True                                  |
      | id           | 07f9524613de4fd3905e13a87f81fd3f      |
      | interface    | internal                              |
      | region       | RegionOne                             |
      | region_id    | RegionOne                             |
      | service_id   | b39c22818be5425ba2315dd4b10cd57c      |
      | service_name | zaqar                                 |
      | service_type | messaging                             |
      | url          | http://WEB0.EXAMPLE-MESSAGES.NET:8888 |
      +--------------+---------------------------------------+

      $ openstack endpoint create --region RegionOne messaging admin http://WEB0.EXAMPLE-MESSAGES.NET:8888
      +--------------+---------------------------------------+
      | Field        | Value                                 |
      +--------------+---------------------------------------+
      | enabled      | True                                  |
      | id           | 686f7b19428f4b5aa1425667dfe4f49d      |
      | interface    | admin                                 |
      | region       | RegionOne                             |
      | region_id    | RegionOne                             |
      | service_id   | b39c22818be5425ba2315dd4b10cd57c      |
      | service_name | zaqar                                 |
      | service_type | messaging                             |
      | url          | http://WEB0.EXAMPLE-MESSAGES.NET:8888 |
      +--------------+---------------------------------------+

Install and configure Messaging web server
------------------------------------------

Install and configure ``memcached``, ``uWSGI`` and Messaging on the web server
``WEB0.EXAMPLE-MESSAGES.NET``.

#. Install ``memcached`` on web server ``WEB0.EXAMPLE-MESSAGES.NET`` in order
   to cache Identity service tokens and catalog mappings:

   .. code-block:: console

      # yum install memcached

   Start ``memcached`` service:

   .. code-block:: console

      # systemctl start memcached

   Make ``memcached`` service start automatically after reboot:

   .. code-block:: console

      # systemctl enable memcached

#. Install Messaging service and ``uWSGI``:

   .. code-block:: console

      # yum install python-pip
      # git clone https://git.openstack.org/openstack/zaqar.git
      # cd zaqar
      # pip install . -r ./requirements.txt --upgrade --log /tmp/zaqar-pip.log
      # pip install --upgrade pymongo gevent uwsgi

#. Create Zaqar configiration directory ``/etc/zaqar/``:

   .. code-block:: console

      # mkdir /etc/zaqar

#. Customize the policy file:

    .. code-block:: console

      # oslopolicy-sample-generator --config-file etc/zaqar-policy-generator.conf
      # cp etc/zaqar.policy.yaml.sample /etc/zaqar/policy.yaml

    Edit any item as needed in policy.yaml.

    .. note::

      By default, if you do not need custom policy file, you do not need to
      perform the above steps, then zaqar will use the code's default policy.

#. Create log file:

   .. code-block:: console

      # touch /var/log/zaqar-server.log
      # chown ZAQARUSER:ZAQARUSER /var/log/zaqar-server.log
      # chmod 600 /var/log/zaqar-server.log

   Replace ``ZAQARUSER`` with the name of the user in system under which the
   Messaging service will run.

#. Create ``/srv/zaqar`` folder to store ``uWSGI`` configuration files:

   .. code-block:: console

      # mkdir /srv/zaqar

#. Create ``/srv/zaqar/zaqar_uwsgi.py`` with the following content:

   .. code-block:: python

      from keystonemiddleware import auth_token
      from zaqar.transport.wsgi import app

      app = auth_token.AuthProtocol(app.app, {})

#. Increase backlog listen limit from default (128):

   .. code-block:: console

      # echo "net.core.somaxconn=2048" | sudo tee --append /etc/sysctl.conf

#. Create ``/srv/zaqar/uwsgi.ini`` file with the following content and modify
   as needed:

   .. code-block:: ini

      [uwsgi]
      https = WEB0.EXAMPLE-MESSAGES.NET:8888,PATH_TO_SERVER_CRT,PATH_TO_SERVER_PRIVATE_KEY
      pidfile = /var/run/zaqar.pid
      gevent = 2000
      gevent-monkey-patch = true
      listen = 1024
      enable-threads = true
      chdir = /srv/zaqar
      module = zaqar_uwsgi:app
      workers = 4
      harakiri = 60
      add-header = Connection: close

   Replace ``PATH_TO_SERVER_CRT`` with path to the server's certificate
   (``*.crt``) and ``PATH_TO_SERVER_PRIVATE_KEY`` with path to the server's
   private key (``*.key``).

   .. note::

      The ``uWSGI`` configuration options above can be modified for different
      security and performance requirements including load balancing. See the
      official `uWSGI configuration reference`_.

#. Create pid file:

   .. code-block:: console

      # touch /var/run/zaqar.pid
      # chown ZAQARUSER:ZAQARUSER /var/run/zaqar.pid

   Replace ``ZAQARUSER`` with the name of the user in system under which the
   Messaging service will run.

#. Create Messaging service's configuration file ``/etc/zaqar/zaqar.conf``
   with the following content:

   .. code-block:: ini

      [DEFAULT]
      # Show debugging output in logs (sets DEBUG log level output)
      #debug = False

      # Pooling and admin mode configs
      pooling      = True
      admin_mode    = True

      # Log to file
      log_file = /var/log/zaqar-server.log

      # This is taken care of in our custom app.py, so disable here
      ;auth_strategy = keystone

      # Modify to make it work with your Identity service.
      [keystone_authtoken]
      project_domain_name = Default
      user_domain_name = Default
      project_domain_id = default
      project_name = service
      user_domain_id = default
      # File path to a PEM encoded Certificate Authority to use when verifying
      # HTTPs connections. Defaults to system CAs if commented.
      cafile = PATH_TO_CA_FILE
      # Messaging service user name in Identity service.
      username = ZAQARIDENTITYUSER
      # Messaging service password in Identity service.
      password = ZAQARIDENTITYPASSWORD
      # Complete public Identity API endpoint (HTTPS protocol is more preferable
      # than HTTP).
      www_authenticate_uri = HTTPS://IDENTITY.EXAMPLE-MESSAGES.NET:5000
      # Complete admin Identity API endpoint (HTTPS protocol is more preferable
      # than HTTP).
      identity_uri = HTTPS://IDENTITY.EXAMPLE-MESSAGES.NET:5000
      # Token cache time in seconds.
      token_cache_time = TOKEN_CACHE_TIME
      memcached_servers = 127.0.0.1:11211

      [cache]
      # Dogpile.cache backend module. It is recommended that Memcache with
      # pooling (oslo_cache.memcache_pool) or Redis (dogpile.cache.redis) be
      # used in production deployments. Small workloads (single process)
      # like devstack can use the dogpile.cache.memory backend. (string
      # value)
      backend = dogpile.cache.memory
      memcache_servers = 127.0.0.1:11211

      [drivers]
      transport = wsgi
      message_store = mongodb
      management_store = mongodb

      [drivers:management_store:mongodb]
      # Mongodb Connection URI. If ssl connection enabled, then ssl_keyfile,
      # ssl_certfile, ssl_cert_reqs, ssl_ca_certs options need to be set
      # accordingly.
      uri = mongodb://MYDB0.EXAMPLE-MESSAGES.NET,MYDB1.EXAMPLE-MESSAGES.NET,MYDB2.EXAMPLE-MESSAGES.NET:27017/?replicaSet=catalog&w=2&readPreference=secondaryPreferred

      # Name for the database on mongodb server.
      database = zaqarmanagementstore

      # Number of databases across which to partition message data, in order
      # to reduce writer lock %. DO NOT change this setting after initial
      # deployment. It MUST remain static. Also, you should not need a large
      # number of partitions to improve performance, esp. if deploying
      # MongoDB on SSD storage. (integer value)
      partitions = 8

      # Uncomment any options below if needed.

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

      [drivers:message_store:mongodb]
      # This section has same set of available options as
      # "[drivers:management_store:mongodb]" section.
      #
      # If pooling is enabled, all pools inherit values from options in these
      # settings unless overridden in pool creation request. Also "uri" option
      # value isn't used in case of pooling.
      #
      # If ssl connection enabled, then ssl_keyfile, ssl_certfile, ssl_cert_reqs,
      # ssl_ca_certs options need to be set accordingly.

      # Name for the database on MondoDB server.
      database = zaqarmessagestore

      [transport]
      max_queues_per_page = 1000
      max_queue_metadata = 262144
      max_mesages_per_page = 10
      max_messages_post_size = 262144
      max_message_ttl = 1209600
      max_claim_ttl = 43200
      max_claim_grace = 43200

      [signed_url]
      # Secret key used to encrypt pre-signed URLs. (string value)
      secret_key = SOMELONGSECRETKEY

   Edit any options as needed, especially the options with capitalized values.

#. Create a service file for Messaging service
   ``/etc/systemd/system/zaqar.uwsgi.service``:

   .. code-block:: ini

      [Unit]
      Description=uWSGI Zaqar
      After=syslog.target

      [Service]
      ExecStart=/usr/bin/uwsgi --ini /srv/zaqar/uwsgi.ini
      # Requires systemd version 211 or newer
      RuntimeDirectory=uwsgi
      Restart=always
      KillSignal=SIGQUIT
      Type=notify
      StandardError=syslog
      NotifyAccess=all
      User=ZAQARUSER
      Group=ZAQARUSER

      [Install]
      WantedBy=multi-user.target

   Replace ``ZAQARUSER`` with the name of the user in system under which the
   Messaging service will run.

Finalize installation
---------------------

Now after you have configured the web server and the database servers to have a
functional Messaging service, you need to start the service, make the service
automatically start with the system and define the created ``MongoDB``
replica-set as Messaging's pool.

#. Start Messaging service on the web server:

   .. code-block:: console

      # systemctl start zaqar.uwsgi.service

#. Make Messaging service start automatically after reboot on the web server:

   .. code-block:: console

      # systemctl enable zaqar.uwsgi.service

#. Configure pool:

   .. code-block:: console

      # curl -i -X PUT https://WEB0.EXAMPLE-MESSAGES.NET:8888/v2/pools/POOL1 \
                 -d '{"weight": 100, "uri": "mongodb://MYDB0.EXAMPLE-MESSAGES.NET,MYDB1.EXAMPLE-MESSAGES.NET,MYDB2.EXAMPLE-MESSAGES.NET:27017/?replicaSet=catalog&w=2&readPreference=secondaryPreferred", "options": {"partitions": 8}}' \
                 -H "Client-ID: CLIENT_ID" \
                 -H "X-Auth-Token: TOKEN" \
                 -H "Content-type: application/json" \

   Replace ``POOL1`` variable with the desired name of a pool.

   Replace ``CLIENT_ID`` variable with the universally unique identifier (UUID)
   which can be generated by, for example, ``uuidgen`` utility.

   Replace ``TOKEN`` variable with the authentication token retrieved from
   Identity service. If you choose not to enable Keystone authentication you
   won't have to pass a token.

   .. note::

      The ``options`` key in curl request above overrides any options
      (specified in configuration file or default) in
      ``[drivers:message_store:mongodb]`` Messaging service configuration
      file's section.

.. tip::

   In larger deployments, there should be many load balanced web servers. Also
   the management store databases and the message store databases (pools)
   should be on different ``MongoDB`` replica-sets.

.. _`MongoDB installation instructions`: https://docs.mongodb.org/manual/tutorial/install-mongodb-on-red-hat/
.. _`MongoDB configuration reference`: https://docs.mongodb.org/v3.0/reference/configuration-options/
.. _`MongoDB security reference`: https://docs.mongodb.org/manual/security/
.. _`uWSGI configuration reference`: http://uwsgi-docs.readthedocs.io/en/latest/
