Marconi
=======

Message queuing service for OpenStack

Running a local Marconi server with MongoDB
-------------------------------------------

1. `Install MongoDB`_
2. Start a MongoDB instance::

    mongod

3. Clone the Marconi repo::

    git clone https://github.com/openstack/marconi.git

4. cd to your local copy of the repo
5. Copy the Marconi config files to the directory **~/.marconi**::

    cp -r marconi/etc/*.conf-sample ~/.marconi/marconi.conf

6. Find the ``[drivers:storage:mongodb]`` section in 
   **~/.marconi/marconi-queues.conf** and modify the URI to point 
   to your local mongod instance::

    uri = mongodb://localhost

7. Run the following so you can see the results of any changes you make 
   to the code, without having to reinstall the package each time::

    pip install -e .

8. Start the marconi server::

    marconi-server


.. _`Install mongodb` : http://docs.mongodb.org/manual/installation/
