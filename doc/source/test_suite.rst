Test suite structure
====================

There are three types of tests for Zaqar:

Unit tests
    Unit tests check modules separately. For example, there
    are checks for each individual method that the storage layer provides.

Functional tests
    Functional tests verify that the service works as expected. In particular,
    in Zaqar they exercise the API endpoints and validate that the API responses
    conform to the specs.  These include positive and negative tests.

Tempest tests
    Tempest tests are integration tests for Openstack [#f1]_.
    Tempest tests for Zaqar are available at https://github.com/openstack/tempest.

This document focuses on the unit and functional tests.  Please refer to the
Tempest repository for details on how to run these tests.

Code structure
--------------

The test suite lives in two directories:

- ``zaqar/tests`` contains all base classes and defines tests for APIs (on both storage and transport levels).
- ``tests`` usually contains implementations for specific drivers and additional tests.

Thus base class and all common tests for storage drivers are located in the ``zaqar/tests/queues/storage/base.py`` file.
The specific instances of the base classes for any particular storage driver are located at the
``tests/unit/queues/storage/`` directory. See ``tests/unit/queues/storage/test_impl_mongodb.py`` for example.

Similarly, unit tests for the transport layer are located in ``zaqar/tests/queues/transport``
and are run from classes located in the ``tests/unit/queues/transport`` directory.

All functional tests for Zaqar are located in the ``tests/functional`` directory.

.. rubric:: Footnotes

.. [#f1] See http://docs.openstack.org/developer/tempest/overview.html
