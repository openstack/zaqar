Zaqar Functional Tests
======================

Zaqar's functional tests treat Zaqar as a black box. In other
words, the API calls attempt to simulate an actual user. Unlike unit tests,
the functional tests do not use mockendpoints.


Running functional tests (With Tox)
-----------------------------------

#. Setup a Zaqar server. Refer to the Zaqar `README`_ on
   how to run Zaqar locally, or simply use an existing server.

#. Run tests. ::

   $ tox

#. Filter tests. ::

   $ tox -- zaqar.tests.functional.wsgi.v1.test_messages

#. Run tests for specific environments. ::

   $ tox -epy27,pep8

Running the Functional Tests (Without Tox)
------------------------------------------

#. Setup a Zaqar server. Refer to the Zaqar `README`_ on
   how to run Zaqar locally, or simply use an existing server.

#. Install functional tests dependencies. ::

     pip install -r requirements.txt
     pip install -r test-requirements.txt

#. cd to the tests/etc directory

#. If leaving keystone auth enabled, update functional-tests.conf with a
   valid set of credentials.

#. Now, to run the system tests, simply use the nosetests commands, e.g.:

    Run all test suites: ::

        nosetests -v

Adding New Tests
----------------

#. Add test case to an appropriate  test case file: ::

    queue/test_queue.py
    messages/test_messages.py
    claim/test_claims.py

Using a custom MongoDB instance
-------------------------------

If you need to run the tests against a non-default MongoDB installation, you
can set the ZAQAR_TEST_MONGODB_URL environemment variable. For example: ::

     export ZAQAR_TEST_MONGODB_URL=mongodb://remote-server:27017


.. _README : https://github.com/openstack/zaqar/blob/master/README.rst
.. _requests : https://pypi.python.org/pypi/requests
