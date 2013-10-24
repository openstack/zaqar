Marconi
=======

Message queuing service for `OpenStack`_

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

    $ cp marconi/etc/marconi-proxy.conf-sample ~/.marconi/marconi-proxy.conf
    $ cp marconi/etc/marconi-queues.conf-sample ~/.marconi/marconi-queues.conf
    $ cp marconi/etc/logging.conf-sample ~/.marconi/logging.conf

3. Find the ``[drivers:storage:mongodb]`` section in
   ``~/.marconi/marconi-queues.conf`` and modify the URI to point
   to your local mongod instance::

    uri = mongodb://$MONGODB_HOST:$MONGODB_PORT

4. For logging, find the ``[DEFAULT]`` section in
   ``~/.marconi/marconi-queues.conf`` and modify as desired::

    log_file = server.log

5. Change directories back to your local copy of the repo::

    $ cd marconi

6. Run the following so you can see the results of any changes you
   make to the code without having to reinstall the package each time::

    $ pip install -e .

7. Start the Marconi server::

    $ marconi-server

8. Test out that Marconi is working by creating a queue::

    $ curl -i -X PUT http://127.0.0.1:8888/v1/queues/samplequeue -H
    "Content-type: application/json" -d '{"metadata": "Sample Queue"}'

You should get an **HTTP 201** along with some headers that will look
similar to this::

    HTTP/1.0 201 Created
    Date: Fri, 25 Oct 2013 15:34:37 GMT
    Server: WSGIServer/0.1 Python/2.7.3
    Content-Length: 0
    Location: /v1/queues/samplequeue


.. _`OpenStack` : http://openstack.org/
.. _`MongoDB` : http://docs.mongodb.org/manual/installation/
.. _`pyenv` : https://github.com/yyuu/pyenv/
.. _`virtualenv` : https://pypi.python.org/pypi/virtualenv/

