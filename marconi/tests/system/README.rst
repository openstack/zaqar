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

#. System tests require the `requests`_ & `robot`_ packages. Run
   the following to install them: ::

     pip install -r tools/system-test-requires

#. cd to the marconi/tests/system directory

#. Copy etc/system-tests.conf-sample to one of the following locations::

     ~/.marconi/system-tests.conf
     /etc/marconi/system-tests.conf

#. Update the config file to point to the Marconi server you want to run
   the tests against

#. If leaving keystone auth enabled, update system-tests.conf with a
   valid set of credentials.

#. Now, to run the sytem tests, simply use the pybot commands, e.g.:

    Run all test suites: ::

        pybot queue/queue_tests.txt messages/messages_tests.txt claim/claim_tests.txt

    Run test suites individually: ::

        pybot queue/queue_tests.txt
        pybot messages/messages_tests.txt
        pybot claim/claim_tests.txt

    Note: pybot will generate ``report.html`` & ``log.html`` after the
    test run is complete.


Adding New Tests
----------------

*See also the Robot* `user guide`_ *for more details on writing test cases.*

#. Add a test case definition to an appropriate robot test case file: ::

    queue/queue_tests.txt
    messages/messages_tests.txt
    claim/claim_tests.txt).

#. Add test data to the test_data.csv in the same directory as the test case
   file you updated above (eg. queue/test_data.csv)

#. Add any validation logic you might need, to the following utility modules:

    * corresponing \*fnlib.py (e.g. queue/queuefnlib.py)
    * common/functionlib.py  (i.e., if the code can be used
      across multiple test suites)



.. _README : https://github.com/stackforge/marconi/blob/master/README.rst
.. _requests : https://pypi.python.org/pypi/requests
.. _robot : https://pypi.python.org/pypi/robotframework
.. _user guide : http://robotframework.googlecode.com/hg/doc/userguide/RobotFrameworkUserGuide.html?r=#.7.7#creating-test-cases


