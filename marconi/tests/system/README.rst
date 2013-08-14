Marconi System Tests
====================

Marconi's system tests treat Marconi as a black box. In other
words, the API calls attempt to simulate an actual user. For
example, unlike unit tests, the system tests do not use mock
endpoints.


Running the System Tests
------------------------

#. Setup a Marconi server. Refer to the Marconi `README`_ on
   how to run Marconi locally, or simply use an existing server.

#. System tests require the `requests` package. Run
   the following to install it: ::

     pip install -r system-test-requirements.txt

#. cd to the marconi/tests/system directory

#. Copy etc/system-tests.conf-sample to one of the following locations::

     ~/.marconi/system-tests.conf
     /etc/marconi/system-tests.conf

#. Update the config file to point to the Marconi server you want to run
   the tests against

#. If leaving keystone auth enabled, update system-tests.conf with a
   valid set of credentials.

#. Now, to run the sytem tests, simply use the nosetests commands, 
   from the marconi/tests/system directory. e.g.:

    Run all test suites: ::

        nosetests -v

Adding New Tests
----------------

#. Add test case to an appropriate  test case file: ::

    queue/test_queue.py
    messages/test_messages.py
    claim/test_claims.py

#. Add any validation logic you might need, to the following utility modules:

    * corresponing \*fnlib.py (e.g. queue/queuefnlib.py)
    * common/functionlib.py  (i.e., if the code can be used
      across multiple test suites)



.. _README : https://github.com/stackforge/marconi/blob/master/README.rst
.. _requests : https://pypi.python.org/pypi/requests
