Marconi Benchmarking
====================

Structure
---------
The Benchmark tool fires up both a Producer Process and a Consumer Process, while
accepting CLI parameters for the number of processes, number of workers and duration of test.

The Producer Process publishes messages to a given queue, while the Consumer consumes the messages
claiming and deleting them.

Need of the Benchmark
---------------------

Marconi is a performance oriented API. Any changes made need to performance tested, and this tool
helps by a being quick way to test that.

Setup
-----
Benchmark dependencies need to be pip installed::

 pip install -r bench-requirements.txt

Make sure you have a running instance of Marconi after following `README`_ for
setting up Marconi running at port 8888::

Export an environment variable called MESSAGES_PATH and set it to the path of messages.json
in marconi/bench

Note: This allows benchmarking with different set of messages rather than those specified in
      messages.json

    $ marconi-bench-pc -p {Number of Processes} -w {Number of Workers} -t {Duration in Seconds}


.. _`README` : https://github.com/openstack/marconi/blob/master/README.rst