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

This section describes how to setup a working Python development
environment that you can use in developing Zaqar on Ubuntu or Fedora.
These instructions assume that you are familiar with
Git. Refer to GettingTheCode_ for additional information.

.. _GettingTheCode: http://wiki.openstack.org/GettingTheCode


Virtual environments
--------------------

Use virtualenv_ to track and manage Python dependencies
for developing and testing Zaqar.
Using virtualenv_ enables you to install Python dependencies
in an isolated virtual environment, instead of installing the
packages at the system level.

.. _virtualenv: http://pypi.python.org/pypi/virtualenv

.. note::

   Virtualenv is useful for development purposes, but is not
   typically used for full integration testing or production usage.
   If you want to learn about production best practices, check out
   the `OpenStack Operations Guide`_.

   .. _`OpenStack Operations Guide`: http://docs.openstack.org/ops/

Install GNU/Linux system dependencies
#####################################

.. note::

  This section is tested for Zaqar on Ubuntu 14.04 (Trusty) and
  Fedora-based (RHEL 6.1) distributions. Feel free to add notes
  and change according to your experiences or operating system.
  Learn more about contributing to Zaqar documentation in the
  `Write the Docs!`_ wiki.

  .. _`Write the Docs!`: https://wiki.openstack.org/wiki/Write_the_Docs!_(Zaqar)

Install the prerequisite packages.

On Ubuntu::

  $ sudo apt-get install gcc python-pip libxml2-dev libxslt1-dev python-dev zlib1g-dev

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS)::

  $ sudo yum install gcc python-pip libxml2-devel libxslt-devel python-devel

Install MongoDB
###############

You also need to have MongoDB_ installed and running.

.. _MongoDB: http://www.mongodb.org

On Ubuntu, follow the instructions in the `MongoDB on Ubuntu Installation Guide`_.

.. _`MongoDB on Ubuntu installation guide`: http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

On Fedora-based distributions, follow the instructions in the
`MongoDB on Red Hat Enterprise, CentOS, Fedora, or Amazon Linux Installation Guide`_.

.. _`MongoDB on Red Hat Enterprise, CentOS, Fedora, or Amazon Linux installation guide`: http://docs.mongodb.org/manual/tutorial/install-mongodb-on-red-hat-centos-or-fedora-linux/

Getting the code
################

Get the code from GitHub::

    $ git clone https://github.com/openstack/zaqar.git

Configuration
#############

1. From your home folder create the ~/.zaqar folder. This directory holds the configuration files for Zaqar::

    $ mkdir ~/.zaqar

2. Generate the sample configuration file zaqar/etc/zaqar.conf.sample::

    $ pip install tox
    $ cd zaqar
    $ tox -e genconfig

3. Copy the Zaqar configuration samples to the directory ~/.zaqar/::

    $ cp etc/zaqar.conf.sample ~/.zaqar/zaqar.conf
    $ cp etc/logging.conf.sample ~/.zaqar/logging.conf

4. Find the [drivers] section in ~/.zaqar/zaqar.conf and specify mongodb as the message store::

    message_store = mongodb
    management_store = mongodb

5. Find the [drivers:message_store:mongodb] section and modify the URI to point to your local mongod instance::

    uri = mongodb://$MONGODB_HOST:$MONGODB_PORT  # default = mongodb://localhost:27017

6. For logging, find the [handler_file] section in ~/.zaqar/logging.conf and modify as desired::

    args=('zaqar.log', 'w')

Installing and using virtualenv
###############################

1. Install virtualenv by running::

    $ pip install virtualenv

2. Create and activate a virtual environment::

    $ virtualenv zaqarenv
    $ source zaqarenv/bin/activate

3. Install Zaqar::

    $ pip install -e .

4. Install the required Python binding for MongoDB::

    $ pip install pymongo

5. Start the Zaqar server::

    $ zaqar-server -v

6. Verify Zaqar is running by creating a queue::

    $ curl -i -X PUT http://localhost:8888/v1/queues/samplequeue -H "Content-type: application/json"

7. Get ready to code!

.. note::

  You can run the Zaqar server in the foreground by passing the
  --nodaemon flag::

        $ zaqar-server -v --nodaemon

  With this method you get immediate visual feedback and it is
  easier to kill and restart the process.

  If you do so, you have to run the cURL test (step 5) in a
  separate terminal.

DevStack
--------

If you want to use Zaqar in an integrated OpenStack developing
environment, you can add it to your DevStack_ deployment.

To do this, you first need to add the following setting
to your local.conf::

    enable_plugin zaqar https://github.com/openstack/zaqar

Then run the stack.sh script as usual.

After running the DevStack_ script, you can start the Zaqar server
and test it by following steps 5 and 6 from the previous section.

.. _DevStack: http://docs.openstack.org/developer/devstack/

Running unit tests
------------------

See :doc:`running_tests` for details.

Contributing your work
----------------------

Once your work is complete, you may wish to contribute it to the project.
Zaqar uses the Gerrit code review system. For information on how to submit
your branch to Gerrit, see GerritWorkflow_.

.. _GerritWorkflow: http://docs.openstack.org/infra/manual/developers.html#development-workflow
