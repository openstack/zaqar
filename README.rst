Zaqar
=====

Message queuing service for `OpenStack`_.
To find more information read our `wiki`_.

Running a local Zaqar server with MongoDB
-----------------------------------------

**Note:** These instructions are for running a local instance of Zaqar and
not all of these steps are required. It is assumed you have `MongoDB`_
installed and running.

1. From your home folder create the ``~/.zaqar`` folder and clone the repo::

    $ cd
    $ mkdir .zaqar
    $ git clone https://github.com/openstack/zaqar.git

2. Copy the Zaqar config files to the directory ``~/.zaqar``::

    $ cp zaqar/etc/zaqar.conf.sample ~/.zaqar/zaqar.conf
    $ cp zaqar/etc/logging.conf.sample ~/.zaqar/logging.conf

3. Find ``[drivers]`` section in ``~/.zaqar/zaqar.conf``
   and specify to use mongodb storage::

    storage = mongodb

   Then find the ``[drivers:storage:mongodb]`` section
   and modify the URI to point to your local mongod instance::

    uri = mongodb://$MONGODB_HOST:$MONGODB_PORT

   By default, you will have::

    uri = mongodb://127.0.0.1:27017

4. For logging, find the ``[DEFAULT]`` section in
   ``~/.zaqar/zaqar.conf`` and modify as desired::

    log_file = server.log

5. Change directories back to your local copy of the repo::

    $ cd zaqar

6. Run the following so you can see the results of any changes you
   make to the code without having to reinstall the package each time::

    $ pip install -e .

7. Start the Zaqar server with logging level set to INFO so you can see
   the port on which the server is listening::

    $ zaqar-server -v

8. Test out that Zaqar is working by creating a queue::

    $ curl -i -X PUT http://127.0.0.1:8888/v1/queues/samplequeue -H
    "Content-type: application/json"

You should get an **HTTP 201** along with some headers that will look
similar to this::

    HTTP/1.0 201 Created
    Date: Fri, 25 Oct 2013 15:34:37 GMT
    Server: WSGIServer/0.1 Python/2.7.3
    Content-Length: 0
    Location: /v1/queues/samplequeue

Running tests
-------------

First install additional requirements::

    $ pip install tox

And then run tests::

    $ tox -e py27

You can read more about running functional tests in separate `TESTS_README`_.

Running the benchmarking tool
-----------------------------

First install and run zaqar-server (see above).

Then install additional requirements::

    $ pip install -r bench-requirements.txt

Copy the configuration file to ``~/.zaqar``::

    $ cp etc/zaqar-benchmark.conf.sample ~/.zaqar/zaqar-benchmark.conf

In the configuration file specify where zaqar-server can be found::

    server_url = http://localhost:8888

The benchmarking tool needs a set of messages to work with. Specify the path
to the file with messages in the configuration file. Alternatively, put it in
the directory with the configuration file and name it ``zaqar-benchmark-
messages.json``. As a starting point, you can use the sample file from the
``etc`` directory::

    $ cp etc/zaqar-benchmark-messages.json ~/.zaqar/

If the file is not found or no file is specified, a single hard-coded message
is used for all requests.

Run the benchmarking tool using the following command::

    $ zaqar-bench

By default, the command will run a performance test for 5 seconds, using one
producer process with 10 greenlet workers, and one observer process with
5 workers. The consumer role is disabled by default.

You can override these defaults in the config file or on the command line
using a variety of options. For example, the following command runs a
performance test for 30 seconds using 4 producer processes with
20 workers each, plus 4 consumer processes with 20 workers each. Note that
the observer role is also disabled in this example by setting its number of
workers to zero::

    $ zaqar-bench -pp 4 -pw 10 -cp 4 -cw 20 -ow 0 -t 30

By default, the results are in JSON. For more human-readable output add
the ``--verbose`` flag. Verbose output looks similar to the following::

    $ zaqar-bench --verbose

    Starting producer (pp=1 , pw=10)...

    Starting observer (op=1 , ow=5)...

    Producer
    ========
    duration_sec: 5.1
    ms_per_req: 2.9
    reqs_per_sec: 344.5
    successful_reqs: 1742.0
    total_reqs: 1742.0

    Observer
    ========
    duration_sec: 5.0
    ms_per_req: 2.9
    reqs_per_sec: 339.3
    successful_reqs: 1706.0
    total_reqs: 1706.0


.. _`OpenStack` : http://openstack.org/
.. _`MongoDB` : http://docs.mongodb.org/manual/installation/
.. _`pyenv` : https://github.com/yyuu/pyenv/
.. _`virtualenv` : https://pypi.python.org/pypi/virtualenv/
.. _`wiki` : https://wiki.openstack.org/wiki/Zaqar
.. _`TESTS_README` : https://github.com/openstack/zaqar/blob/master/tests/functional/README.rst

