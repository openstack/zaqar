..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

==========
CORS Guide
==========

Zaqar supports Cross-Origin Resource Sharing (CORS) now. The function is
provided by oslo.middleware. Please see `Official Doc`_ and `OpenStack Spec`_
for more detail. This guide is mainly tell users how to use it in Zaqar.


New Config Options
------------------

There are some new config options.

**allowed_origin**

Indicate whether this resource may be shared with the domain received in the
requests "origin" header. Format: "<protocol>://<host>[:<port>]", no trailing
slash. Example: https://horizon.example.com'.

**allow_credentials**

Indicate that the actual request can include user credentials. The default
value is True.

**expose_headers**

Indicate which headers are safe to expose to the API. Defaults to HTTP Simple
Headers. The default value is [].

**max_age**

Maximum cache age of CORS preflight requests. The default value is 3600.

**allow_methods**

Indicate which methods can be used during the actual request. The default value
is ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'PATCH'].

**allow_headers**

Indicate which header field names may be used during the actual request. The
default value is [].


Request and Response example
----------------------------
The CORS feature is enabled by default in Zaqar. Here is a config example:::

  [cors]
  allowed_origin = http://example
  allow_methods = GET

the above example config options mean that Zaqar only receive the GET request
from http://example domain. Here are some example request:
1. Zaqar will do nothing if the request doesn't contain "Origin" header::

  # curl -I -X GET http://10.229.47.217:8888 -H "Accept: application/json"

  HTTP/1.1 300 Multiple Choices
  content-length: 668
  content-type: application/json; charset=UTF-8
  Connection: close

2. Zaqar will return nothing in response headers if the "Origin" is not in
``allowed_origin``::

  # curl -I -X GET http://10.229.47.217:8888 -H "Accept: application/json" -H "Origin: http://"

  HTTP/1.1 300 Multiple Choices
  content-length: 668
  content-type: application/json; charset=UTF-8
  Connection: close

In the Zaqar log, we can see a message::

  CORS request from origin 'http://' not permitted.

3. Zaqar will return CORS information if the "Origin" header is in
``allowed_origin``::

  # curl -I -X GET http://10.229.47.217:8888 -H "Accept: application/json" -H "Origin: http://example"

  HTTP/1.1 300 Multiple Choices
  content-length: 668
  content-type: application/json; charset=UTF-8
  Vary: Origin
  Access-Control-Allow-Origin: http://example
  Access-Control-Allow-Credentials: true
  Connection: close

4. Zaqar will return more information if the request doesn't follow Zaqar's\
CORS rule::

  # curl -I -X PUT http://10.229.47.217:8888 -H "Accept: application/json" -H "Origin: http://example"
  HTTP/1.1 405 Method Not Allowed
  content-length: 0
  content-type: application/json; charset=UTF-8
  allow: GET, OPTIONS
  Vary: Origin
  Access-Control-Allow-Origin: http://example
  Access-Control-Allow-Credentials: true
  Connection: close

.. _Official Doc: https://docs.openstack.org/oslo.middleware/latest/reference/cors.html
.. _OpenStack Spec: https://specs.openstack.org/openstack/openstack-specs/specs/cors-support.html
