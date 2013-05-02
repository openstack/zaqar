**Marconi System Tests**

The System tests treat Marconi as a black box.
The API calls are made similar to how an user would make them.
Unlike unit tests, the system tests do not use mock endpoints.

**Running the System Tests**

1. Setup the Marconi server, to run the tests against.
   Refer to the Marconi `README`_ on how to run Marconi locally.
   (If you are running the tests against an existing server, skip this step.)

2. System tests require the `requests`_ & `robot`_ packages. Run the following to install them ::

     pip install -r tools/system-test-requires

3. cd to the marconi/tests/system directory

4. Copy etc/system-tests.conf-sample to one of the following locations::

     ~/.marconi/system-tests.conf
     /etc/marconi/system-tests.conf

5. Update the config file to point to the Marconi server you want to run the tests against

6. If keystone auth is enabled, update system-tests.conf with the credentials.

7. To run tests use the pybot commands,

    Run all test suites ::

      pybot marconi/tests/system/queue/queue_tests.txt marconi/tests/system/messages/messages_tests.txt marconi/tests/system/claim/claim_tests.txt

    Run a specific test suite ::

      pybot marconi/tests/system/queue/queue_tests.txt

      pybot marconi/tests/system/messages/messages_tests.txt

      pybot marconi/tests/system/claim/claim_tests.txt

  pybot will generate report.html & log.html after the test run is complete.


**To Add new tests**


1. Add test case definition to the robot test case file (queue/queue_tests.txt, messages/messages_tests.txt, claim/claim_tests.txt)
   See `here`_ for more details on writing test cases.

2. Add test data to the test_data.csv in the same directory as the test case file you updated above (eg. queue/test_data.csv)

3. Add any validation logic you might need, to one of the following:

      * corresponing \*fnlib.py (eg. queue/queuefnlib.py)
      * common/functionlib.py  (If the code can be used across multiple test suites)

.. _README : https://github.com/stackforge/marconi/blob/master/README.rst
.. _requests : https://pypi.python.org/pypi/requests
.. _robot : https://pypi.python.org/pypi/robotframework
.. _here : http://robotframework.googlecode.com/hg/doc/userguide/RobotFrameworkUserGuide.html?r=2.7.7#creating-test-cases


