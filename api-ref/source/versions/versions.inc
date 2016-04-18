============
API Versions
============

Concepts
========

The Zaqar API only supports ''major versions'' expressed in request URLs.


List Major Versions
===================

.. rest_method::  GET /

This fetches all the information about all known major API versions in
the deployment. Links to more specific information will be provided
for each API version.


Normal response codes: 300
Error response codes: serviceUnavailable (503)

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - versions: versions

Response Example
----------------

.. literalinclude:: samples/versions-list-response.json
   :language: javascript
