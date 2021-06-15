========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/zaqar.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

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

The API v2.0 (stable) specification and documentation are available at:

    https://wiki.openstack.org/wiki/Zaqar/specs/api/v2.0

Zaqar's Documentation, the source of which is in ``doc/source/``, is
available at:

    https://docs.openstack.org/zaqar/latest

Zaqar's Release notes are available at:

    https://docs.openstack.org/releasenotes/zaqar/

Contributors are encouraged to join IRC (``#openstack-zaqar`` channel on
``OFTC``):

    https://wiki.openstack.org/wiki/IRC

Information on how to run unit and functional tests is available at:

    https://docs.openstack.org/zaqar/latest/contributor/running_tests.html

Information on how to run benchmarking tool is available at:

    https://docs.openstack.org/zaqar/latest/admin/running_benchmark.html

Zaqar's design specifications is tracked at:

    https://specs.openstack.org/openstack/zaqar-specs/

Using Zaqar
-----------

If you are new to Zaqar and just want to try it, you can set up Zaqar in
the development environment.

Using Zaqar in production environment:

    Coming soon!

Using Zaqar in development environment:

    The instruction is available at:

        https://docs.openstack.org/zaqar/latest/contributor/development.environment.html

    This will allow you to run local Zaqar server with MongoDB as database.

    This way is the easiest, quickest and most suitable for beginners.
