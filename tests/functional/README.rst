Marconi Functional Tests
====================

Marconi's functional tests treat Marconi as a black box. In other
words, the API calls attempt to simulate an actual user. Unlike unit tests,
the functional tests do not use mockendpoints.


Running the Functional Tests
------------------------

#. Setup a Marconi server. Refer to the Marconi `README`_ on
   how to run Marconi locally, or simply use an existing server.

#. Install functional tests dependencies. ::

     pip install -r functional-test-requirements.txt

#. cd to the marconi/tests/functional directory

#. Copy marconi/tests/etc/functional-tests.conf-sample to one of the following locations::

     ~/.marconi/functional-tests.conf
     /etc/marconi/functional-tests.conf

#. Update the config file to point to the Marconi server you want to run
   the tests against

#. If leaving keystone auth enabled, update system-tests.conf with a
   valid set of credentials.

#. Now, to run the sytem tests, simply use the nosetests commands, e.g.:

    Run all test suites: ::

        nosetests --tests tests.functional -v

Adding New Tests
----------------

#. Add test case to an appropriate  test case file: ::

    queue/test_queue.py
    messages/test_messages.py
    claim/test_claims.py

.. _README : https://github.com/stackforge/marconi/blob/master/README.rst
.. _requests : https://pypi.python.org/pypi/requests
