============
API Versions
============

The Zaqar API only supports ''major versions'' expressed in request URLs.


List major versions
===================

.. rest_method:: GET /

Gets the home document.

This operation gets the home document.

The entire API is discoverable from a single starting point, the home document. To explore the entire API, you need to know only this one URI. This document is cacheable.

The home document lets you write clients by using relational links, so clients do not have to construct their own URLs. You can click through and view the JSON doc in your browser.

For more information about home documents, see `http://tools.ietf.org/html/draft-nottingham-json-home-02 <http://tools.ietf.org/html/draft-nottingham-json-home-02>`__.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 300

.. rest_status_code:: error status.yaml

   - 503

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - versions: versions

Response Example
----------------

.. literalinclude:: samples/versions-list-response.json
   :language: javascript
