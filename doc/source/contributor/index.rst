==================
Contribution Guide
==================

.. toctree::
   :maxdepth: 2

   welcome
   project_info
   development.environment
   first_patch
   first_review
   launchpad
   gerrit
   jenkins
   reviewer_guide
   running_tests
   test_suite

Modules reference
~~~~~~~~~~~~~~~~~

Zaqar is composed of two layers:

.. toctree::
   :maxdepth: 1

   transport
   storage

The **transport drivers** are responsible for interacting with Zaqar clients.
Every query made by clients is processed by the transport layer, which is in
charge of passing this information to the backend and then returning the
response in a format understandable by the client.

The **storage drivers** are responsible for interacting with the storage
backends and, that way, store or retrieve the data coming from the transport
layer.

In order to keep these layers decoupled, we have established that
**checks should be performed in the appropriate layer**. In other words,
transport drivers must guarantee that the incoming data is well-formed and
storage drivers must enforce their data model stays consistent.
