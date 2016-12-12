Generate an Authentication Token
================================

You can use `cURL <http://curl.haxx.se/>`__ to try the authentication
process in two steps: get a token, and send the token to a service.

1. Get an authentication token by providing your user name and either
   your API key or your password. Here are examples of both approaches:

   You can request a token by providing your user name and your
   password.

   ::

       $ curl -X POST https://localhost:5000/v2.0/tokens -d '{"auth":{"passwordCredentials":{"username": "joecool", "password":"coolword"}, "tenantId":"5"}}' -H 'Content-type: application/json'

   Successful authentication returns a token which you can use as
   evidence that your identity has already been authenticated. To use
   the token, pass it to other services as an ``X-Auth-Token`` header.

   Authentication also returns a service catalog, listing the endpoints
   you can use for Cloud services.

2. Use the authentication token to send a ``GET`` to a service you would
   like to use.

Authentication tokens are typically valid for 24 hours. Applications
should be designed to re-authenticate after receiving a 401
(Unauthorized) response from a service endpoint.

    **Note**

    If you programmatically parse an authentication response, be aware
    that service names are stable for the life of the particular service
    and can be used as keys. You should also be aware that a user's
    service catalog can include multiple uniquely-named services that
    perform similar functions.
