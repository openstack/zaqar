.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Messaging service,
code-named zaqar.

This section assumes that you already have a working OpenStack environment with
at least Identity service installed.

Note that installation and configuration vary by distribution.

.. toctree::

   install-obs.rst
   install-rdo.rst
   install-ubuntu.rst

Possible Minimum Scalable HA Setup
----------------------------------

Scalable HA (High availability) setup is out of scope in this chapter.

For a HA setup, a load balancer has to be placed in front of the web servers.

To provide high availability with minimum administration overhead for storage
use ``MongoDB`` driver and for transport use ``wsgi`` driver.

To have a small footprint while providing HA, you can use two web servers which
will host the application and three ``MongoDB`` servers (configured as
replica-set) which will host Messaging service's management store and
message store databases. At larger scale, the management store database and the
message store database are advised to be hosted on different ``MongoDB``
replica sets.
