.. _basic-configuration:

Basic Configuration
===================

The ``zaqar.conf`` configuration file is an
`INI file format <https://en.wikipedia.org/wiki/INI_file>`_.

This file is located in ``/etc/zaqar``. If there is a file ``zaqar.conf`` in
``~/.zaqar`` directory, it is used instead of the one in ``/etc/zaqar``
directory. When you manually install the Message service, you must generate
the zaqar.conf file using the config samples generator located inside Zaqar
installation directory and customize it according to your preferences.

To generate the sample configuration file ``zaqar/etc/zaqar.conf.sample``:

.. code-block:: console

   # pip install tox
   $ cd zaqar
   $ tox -e genconfig

Where :samp:`{zaqar}` is your Message service installation directory.

Then copy Message service configuration sample to the directory ``/etc/zaqar``:

.. code-block:: console

   # cp etc/zaqar.conf.sample /etc/zaqar/zaqar.conf

For a list of configuration options, see the tables in this guide.

.. important::

   Do not specify quotes around configuration options.


Message API configuration
-------------------------

The Message service has two APIs: the HTTP REST API for WSGI transport driver,
and the Websocket API for Websocket transport driver. The Message service can
use only one transport driver at the same time.

The functionality and behavior of the APIs are defined by API versions. For
example, the Websocket API v2 acts the same as the HTTP REST API v2. For now
there are v1, v1.1 and v2 versions of HTTP REST API and only v2 version of
Websocket API.

Permission control options in each API version:

* The v1 does not have any permission options.
* The v1.1 has only ``admin_mode`` option which controls the global
  permission to access the pools and flavors functionality.
* The v2 has only:

  * RBAC policy options: ``policy_default_rule``, ``policy_dirs``,
    ``policy_file`` which controls the permissions to access each type of
    functionality for different types of users.

    .. warning::

       JSON formatted policy file is deprecated since Zaqar 12.0.0 (Wallaby).
       This `oslopolicy-convert-json-to-yaml`__ tool will migrate your existing
       JSON-formatted policy file to YAML in a backward-compatible way.

    .. __: https://docs.openstack.org/oslo.policy/latest/cli/oslopolicy-convert-json-to-yaml.html

  * ``secret_key`` option which defines a secret key to use for signing
    special URLs. These are called pre-signed URLs and give temporary
    permissions to outsiders of the system.


Authentication and authorization
--------------------------------

All requests to the API may only be performed by an authenticated agent.

The preferred authentication system is the OpenStack Identity service,
code-named keystone.

Identity service authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To authenticate, an agent issues an authentication request to an Identity
service endpoint. In response to valid credentials, Identity service responds
with an authentication token and a service catalog that contains a list of
all services and endpoints available for the given token.

Multiple endpoints may be returned for Message service according to physical
locations and performance/availability characteristics of different
deployments.

Normally, Identity service middleware provides the ``X-Project-Id`` header
based on the authentication token submitted by the Message service client.

For this to work, clients must specify a valid authentication token in the
``X-Auth-Token`` header for each request to the Message service API. The API
validates authentication tokens against Identity service before servicing each
request.

No authentication
~~~~~~~~~~~~~~~~~

If authentication is not enabled, clients must provide the ``X-Project-Id``
header themselves.


Notifications options
---------------------

The notifications feature in the Message service can be enabled by adding
``zaqar.notification.notifier`` stage to the message storage layer pipeline. To
do it, ensure that ``zaqar.notification.notifier`` is added to
``message_pipeline`` option in the ``[storage]`` section of ``zaqar.conf``:

.. code-block:: ini

   [storage]
   message_pipeline = zaqar.notification.notifier



Pooling options
---------------

The Message service supports pooling.

Pooling aims to make the Message service highly scalable without losing any of
its flexibility by allowing users to use multiple back ends.



Storage drivers options
-----------------------

Storage back ends
~~~~~~~~~~~~~~~~~

The Message service supports several different storage back ends (storage
drivers) for storing management information, messages and their metadata. The
recommended storage back end is MongoDB. For information on how to specify the
storage back ends.

When the storage back end is chosen, the corresponding back-end options become
active. For example, if Redis is chosen as the management storage back end, the
options in ``[drivers:management_store:redis]`` section become active.

Storage layer pipelines
~~~~~~~~~~~~~~~~~~~~~~~

A pipeline is a set of stages needed to process a request. When a new request
comes to the Message service, first it goes through the transport layer
pipeline and then through one of the storage layer pipelines depending on the
type of operation of each particular request. For example, if the Message
service receives a request to make a queue-related operation, the storage
layer pipeline will be ``queue pipeline``. The Message service always has the
actual storage controller as the final storage layer pipeline stage.

By setting the options in the ``[storage]`` section of ``zaqar.conf``,
you can add additional stages to these storage layer pipelines:

* **Claim pipeline**
* **Message pipeline** with built-in stage available to use:

  * ``zaqar.notification.notifier`` - sends notifications to the queue
    subscribers on each incoming message to the queue, in other words, enables
    notifications functionality.
* **Queue pipeline**
* **Subscription pipeline**

The storage layer pipelines options are empty by default, because additional
stages can affect the performance of the Message service. Depending on the
stages, the sequence in which the option values are listed does matter or not.

You can add external stages to the storage layer pipelines. For information how
to write and add your own external stages, see
`Writing stages for the storage pipelines
<https://docs.openstack.org/zaqar/latest/admin/writing_pipeline_stages.html>`_
tutorial.


Messaging log files
-------------------

The corresponding log file of each Messaging service is stored in the
``/var/log/zaqar/`` directory of the host on which each service runs.

.. list-table:: Log files used by Messaging services
   :widths: 35 35
   :header-rows: 1

   * - Log filename
     - Service that logs to the file
   * - ``server.log``
     - Messaging service

