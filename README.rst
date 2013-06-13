**Marconi - Queue and Notification service for OpenStack**

*Steps to run Marconi server locally with MongoDB*

1. `Install mongodb`_ locally
2. Start your local MongoDB instance::

       mongod

3. Clone the Marconi repo::

       git clone https://github.com/stackforge/marconi.git

4. cd to your local copy of the repo
5. Copy the Marconi config files to the directory ~/.marconi::

       cp -r marconi/etc/*.conf-sample ~/.marconi
6. Update the [drivers:storage:mongodb] section in ~/.marconi/marconi.conf

   6a. Comment out the uri pointing to replicaset::

   	   	;uri = mongodb://db1.example.net,db2.example.net:2500/?replicaSet=test&ssl=true&w=majority
   6b. Add a new line with uri pointing to the local mongoDB instance::

   		uri = mongodb://localhost
7. Run the following command::

       python setup.py develop
8. Start the marconi server::

       marconi-server

.. _`Install mongodb` : http://docs.mongodb.org/manual/installation/