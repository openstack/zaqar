=====
Zaqar
=====

Zaqar is a multi-tenant cloud messaging and notification service for web
and mobile developers.
It combines the ideas pioneered by Amazon's SQS product with additional
semantics to support event broadcasting.

The service features a fully RESTful API, which developers can use to send
messages between various components of their SaaS and mobile applications, by
using a variety of communication patterns. Underlying this API is an efficient
messaging engine designed with scalability and security in mind.

Other OpenStack components can integrate with Zaqar to surface events to end
users and to communicate with guest agents that run in the "over-cloud" layer.
Cloud operators can leverage Zaqar to provide equivalents of SQS and SNS to
their customers.

General information is available in wiki:

    https://wiki.openstack.org/wiki/Zaqar

The API v1.1 (stable) specification and documentation are available at:

    https://wiki.openstack.org/wiki/Zaqar/specs/api/v1.1

Zaqar Contributor Documentation, the source of which is in ``doc/source/``, is
available at:

    http://docs.openstack.org/developer/zaqar/

Contributors are encouraged to join IRC (``#openstack-zaqar`` channel on
``irc.freenode.net``):

    https://wiki.openstack.org/wiki/IRC

Information on how to run unit and functional tests is available at:

    http://docs.openstack.org/developer/zaqar/running_tests.html

Information on how to run benchmarking tool is available at:

    http://docs.openstack.org/developer/zaqar/running_benchmark.html

Using Zaqar
-----------

If you are new to Zaqar and just want to try it, you can set up Zaqar in
the development environment.

Using Zaqar in production environment:

    Coming soon!

Using Zaqar in development environment:

    The instruction is available at:

        http://docs.openstack.org/developer/zaqar/devref/development.environment.html

    This will allow you to run local Zaqar server with MongoDB as database.

    This way is the easiest, quickest and most suitable for beginners.