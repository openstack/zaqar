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

====================================
Setting up a development environment
====================================

This section describes how to setup a working Python development environment
that you can use in developing Zaqar on Ubuntu or Fedora. These instructions
assume that you are familiar with Git. Refer to GettingTheCode_ for
additional information.

.. _GettingTheCode: https://wiki.openstack.org/wiki/Getting_The_Code


Virtual environments
--------------------

Use virtualenv_ to track and manage Python dependencies for developing and
testing Zaqar.
Using virtualenv_ enables you to install Python dependencies in an isolated
virtual environment, instead of installing the packages at the system level.

.. _virtualenv: https://pypi.org/project/virtualenv

.. note::

   Virtualenv is useful for development purposes, but is not typically used for
   full integration testing or production usage. If you want to learn about
   production best practices, check out the `OpenStack Operations Guide`_.

   .. _`OpenStack Operations Guide`: https://wiki.openstack.org/wiki/OpsGuide

Install GNU/Linux system dependencies
#####################################

.. note::

  This section is tested for Zaqar on Ubuntu 14.04 (Trusty) and Fedora-based
  (RHEL 6.1) distributions. Feel free to add notes and change according to your
  experiences or operating system. Learn more about contributing to Zaqar
  documentation in the :doc:`welcome` manual.

Install the prerequisite packages.

On Ubuntu:

.. code-block:: console

  $ sudo apt-get install gcc python-pip libxml2-dev libxslt1-dev python-dev zlib1g-dev

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS):

.. code-block:: console

  $ sudo yum install gcc python-pip libxml2-devel libxslt-devel python-devel

Install MongoDB
###############

You also need to have MongoDB_ installed and running.

.. _MongoDB: http://www.mongodb.org

On Ubuntu, follow the instructions in the
`MongoDB on Ubuntu Installation Guide`_.

.. _`MongoDB on Ubuntu installation guide`: http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

On Fedora-based distributions, follow the instructions in the
`MongoDB on Red Hat Enterprise, CentOS, Fedora, or Amazon Linux
Installation Guide`_.

.. _`MongoDB on Red Hat Enterprise, CentOS, Fedora, or Amazon Linux installation guide`: http://docs.mongodb.org/manual/tutorial/install-mongodb-on-red-hat-centos-or-fedora-linux/

.. note::

  If you are Contributor and plan to run Unit tests on Zaqar, you may want to
  add this line to mongodb configuration file (``etc/mongod.conf`` or
  ``etc/mongodb.conf`` depending on distribution):

  .. code-block:: ini

    smallfiles = true

  Many Zaqar's Unit tests do not clean up their testing databases after
  executing. And database files consume much disk space even if they do not
  contain any records. This behavior will be fixed soon.

Getting the code
################

Get the code from git.openstack.org to create a local repository with Zaqar:

.. code-block:: console

  $ git clone https://git.openstack.org/openstack/zaqar.git

Configuration
#############

#. From your home folder create the ``~/.zaqar`` folder. This directory holds
   the configuration files for Zaqar:

   .. code-block:: console

     $ mkdir ~/.zaqar

#. Generate the sample configuration file ``zaqar/etc/zaqar.conf.sample``:

   .. code-block:: console

     $ pip install tox
     $ cd zaqar
     $ tox -e genconfig

#. Copy the Zaqar configuration samples to the directory ``~/.zaqar/``:

   .. code-block:: console

     $ cp etc/zaqar.conf.sample ~/.zaqar/zaqar.conf
     $ cp etc/logging.conf.sample ~/.zaqar/logging.conf

#. Find the ``[drivers]`` section in ``~/.zaqar/zaqar.conf`` and specify
   ``mongodb`` as the message store:

   .. code-block:: ini

     message_store = mongodb
     management_store = mongodb

#. Then find ``[drivers:message_store:mongodb]`` and
   ``[drivers:management_store:mongodb]`` sections and specify the
   :samp:`{URI}` to point to your local mongodb instance by adding this line
   to both the sections:

   .. code-block:: ini

     uri = mongodb://$MONGODB_HOST:$MONGODB_PORT

   By default you will have:

   .. code-block:: ini

     uri = mongodb://127.0.0.1:27017

   This :samp:`{URI}` points to single mongodb node which of course is not
   reliable, so you need to set in the ``[default]`` section of configuration
   file:

   .. code-block:: ini

     unreliable = True

   For your reference, you can omit this parameter or set it to False only
   if the provided :samp:`{URI}` to your mongodb is actually the URI to mongodb
   Replica Set or Mongos. Also it must have "Write concern" parameter set to
   ``majority`` or to a number more than ``1``.

   For example, :samp:`{URI}` to reliable mongodb can look like this:

   .. code-block:: ini

     uri = mongodb://mydb0,mydb1,mydb2:27017/?replicaSet=foo&w=2

   Where ``mydb0``, ``mydb1``, ``mydb2`` are addresses of the configured
   mongodb Replica Set nodes, ``replicaSet`` (Replica Set name) parameter is
   set to ``foo``, ``w`` (Write concern) parameter is set to ``2``.

#. For logging, find the ``[handler_file]`` section in
   ``~/.zaqar/logging.conf`` and modify as desired:

   .. code-block:: ini

     args=('zaqar.log', 'w')

Installing and using virtualenv
###############################

#. Install virtualenv by running:

   .. code-block:: console

     $ pip install virtualenv

#. Create and activate a virtual environment:

   .. code-block:: console

     $ virtualenv zaqarenv
     $ source zaqarenv/bin/activate

#. Install Zaqar:

   .. code-block:: console

     $ pip install -e .

#. Install the required Python binding for MongoDB:

   .. code-block:: console

     $ pip install pymongo

#. Start Zaqar server in ``info`` logging mode:

   .. code-block:: console

     $ zaqar-server -v

   Or you can start Zaqar server in ``debug`` logging mode:

   .. code-block:: console

     $ zaqar-server -d

#. Verify Zaqar is running by creating a queue via curl. In a separate
   terminal run:

   .. code-block:: console

     $ curl -i -X PUT http://localhost:8888/v2/queues/samplequeue -H "Content-type: application/json" -H 'Client-ID: 123e4567-e89b-12d3-a456-426655440000' -H 'X-PROJECT-ID: 12345'

   .. note::

     ``Client-ID`` expects a valid UUID.

     ``X-PROJECT-ID`` expects a user-defined project identifier.


#. Get ready to code!

.. note::

  You can run the Zaqar server in the background by passing the
  ``--daemon`` flag:

  .. code-block:: console

    $ zaqar-server -v --daemon

  But with this method you will not get immediate visual feedback and it will
  be harder to kill and restart the process.

Troubleshooting
^^^^^^^^^^^^^^^

No handlers found for zaqar.client (...)
""""""""""""""""""""""""""""""""""""""""

This happens because the current user cannot create the log file (for the
default configuration in ``/var/log/zaqar/server.log``). To solve it, create
the folder:

.. code-block:: console

  $ sudo mkdir /var/log/zaqar

Create the file:

.. code-block:: console

  $ sudo touch /var/log/zaqar/server.log

And try running the server again.

DevStack
--------

If you want to use Zaqar in an integrated OpenStack developing environment, you
can add it to your DevStack_ deployment.

To do this, you first need to add the following setting to your ``local.conf``:

.. code-block:: bash

  enable_plugin zaqar https://git.openstack.org/openstack/zaqar

Then run the ``stack.sh`` script as usual.

.. _DevStack: https://docs.openstack.org/devstack/latest/

Running tests
-------------

See :doc:`running_tests` for details.

Running the benchmarking tool
-----------------------------

See :doc:`../admin/running_benchmark` for details.

Contributing your work
----------------------

See :doc:`welcome` and :doc:`first_patch` for details.
