Marconi
=======

Message queuing service for `OpenStack`_.
To find more information read our `wiki`_.

Running a local Marconi server with MongoDB
-------------------------------------------

**Note:** These instructions are for running a local instance of Marconi and
not all of these steps are required. It is assumed you have `MongoDB`_
installed and running.

1. From your home folder create the ``~/.marconi`` folder and clone the repo::

    $ cd
    $ mkdir .marconi
    $ git clone https://github.com/openstack/marconi.git

2. Copy the Marconi config files to the directory ``~/.marconi``::

    $ cp marconi/etc/marconi.conf.sample ~/.marconi/marconi.conf
    $ cp marconi/etc/logging.conf.sample ~/.marconi/logging.conf

3. Find ``[drivers]`` section in ``~/.marconi/marconi.conf``
   and specify to use mongodb storage::

    storage = mongodb

   Then find the ``[drivers:storage:mongodb]`` section
   and modify the URI to point to your local mongod instance::

    uri = mongodb://$MONGODB_HOST:$MONGODB_PORT

   By default, you will have::

    uri = mongodb://127.0.0.1:27017

4. For logging, find the ``[DEFAULT]`` section in
   ``~/.marconi/marconi.conf`` and modify as desired::

    log_file = server.log

5. Change directories back to your local copy of the repo::

    $ cd marconi

6. Run the following so you can see the results of any changes you
   make to the code without having to reinstall the package each time::

    $ pip install -e .

7. Start the Marconi server with logging level set to INFO so you can see
   the port on which the server is listening::

    $ marconi-server -v

8. Test out that Marconi is working by creating a queue::

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

    pip install tox

And then run tests::

    tox -e py27

You can read more about running functional tests in separate `TESTS_README`_.

.. _`OpenStack` : http://openstack.org/
.. _`MongoDB` : http://docs.mongodb.org/manual/installation/
.. _`pyenv` : https://github.com/yyuu/pyenv/
.. _`virtualenv` : https://pypi.python.org/pypi/virtualenv/
.. _`wiki` : https://wiki.openstack.org/wiki/Marconi
.. _`TESTS_README` : https://github.com/openstack/marconi/blob/master/tests/functional/README.rst

