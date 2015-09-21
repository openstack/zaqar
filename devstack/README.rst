====================
Enabling in Devstack
====================

1. Download DevStack

2. Add this repo as an external repository::

     > cat local.conf
     [[local|localrc]]
     enable_plugin zaqar https://github.com/openstack/zaqar

3. Run ``stack.sh``
