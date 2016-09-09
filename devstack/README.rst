====================
Enabling in Devstack
====================

1. Download DevStack::

     $ git clone https://git.openstack.org/openstack-dev/devstack
     $ cd devstack

2. Add the following repo as an external repository::

     [[local|localrc]]
     enable_plugin zaqar https://git.openstack.org/openstack/zaqar

3. Run ``./stack.sh``
