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

====================
Test suite structure
====================

Test types
----------

There are three types of tests for Zaqar:

Unit tests
    Unit tests check modules separately. For example, there
    are checks for each individual method that the storage layer provides.

Functional tests
    Functional tests verify that the service works as expected. In particular,
    in Zaqar they exercise the API endpoints and validate that the API
    responses conform to the specs.  These include positive and negative tests.

Tempest tests
    Tempest tests are integration tests for OpenStack [#f1]_.

    Tempest tests for Zaqar are available in the `Tempest repository`_.

Refer to :doc:`running_tests` document for details on how to run Unit and
Functional tests.

Refer to the `Tempest repository`_ for details on how to run Tempest tests.

Code structure
--------------

The test suite lives in ``zaqar/tests`` directory of Zaqar:

* ``zaqar/tests/etc``
   Contains various configuration files for Zaqar. They help to test how Zaqar
   works in different configurations.

* ``zaqar/tests/functional``
   Contains functional tests.

* ``zaqar/tests/unit``
   Contains unit tests.

The base class of all test classes is located in the ``zaqar/tests/base.py``
file.

Test invocation
---------------

When you run tests via ``tox -e py27`` command in the root directory of Zaqar:

#. Tox program executes:

   #. Looks for ``tox.ini`` file.
   #. Creates ``.tox`` directory for storing python environments.
   #. Parses this file and finds parameters for py27 testing environment.
   #. Sets this environment up and activates it.
   #. Sets environment variables for this environment that are described in
      ``tox.ini``
   #. In case of Zaqar it invokes Testr program in the environment.

   You can find more information about Tox in `OpenStack Tox testing manual`_
   and in official `Tox documentation`_.

#. Testr (Test Repository) program executes:

   #. Looks for ``testr.ini`` file.
   #. Parses this file and finds parameters for executing tests.
   #. Creates ``.testrepository`` directory for storing statistics of
      executing tests.
   #. In case of Zaqar it invokes ``Subunit`` program which finds all tests and
      executes it.

   You can find more information about Testr in `OpenStack Testr manual`_.

.. rubric:: Footnotes

.. [#f1] See https://docs.openstack.org/tempest/latest/#overview

.. _`OpenStack Tox testing manual` : https://wiki.openstack.org/wiki/Testing#Unit_Testing_with_Tox
.. _`Tox documentation` : https://tox.readthedocs.org/en/latest/
.. _`OpenStack Testr manual` : https://wiki.openstack.org/wiki/Testr
.. _`Tempest repository` : https://git.openstack.org/cgit/openstack/tempest
