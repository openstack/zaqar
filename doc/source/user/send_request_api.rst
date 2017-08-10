Send Requests to the API
========================

You have several options for sending requests through an API:

-  Developers and testers may prefer to use cURL, the command-line tool
   from http://curl.haxx.se/.

   With cURL you can send HTTP requests and receive responses back from
   the command line.

-  If you like to use a more graphical interface, the REST client for
   Firefox also works well for testing and trying out commands, see
   https://addons.mozilla.org/en-US/firefox/addon/restclient/.

-  You can also download and install rest-client, a Java application to
   test RESTful web services, from
   https://github.com/wiztools/rest-client.

Sending API Requests Using cURL
-------------------------------

cURL is a command-line tool that is available in UNIX® system-based
environments and Apple Mac OS X® systems, and can be downloaded for
Microsoft Windows® to interact with the REST interfaces. For more
information about cURL, visit http://curl.haxx.se/.

cURL enables you to transmit and receive HTTP requests and responses
from the command line or from within a shell script. As a result, you
can work with the REST API directly without using one of the client
APIs.

The following cURL command-line options are used in this guide to run
the examples.

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Option
     - Description
   * - ``-d``
     - Sends the specified data in a ``POST`` request to the HTTP server.
   * - ``-i``
     - Includes the HTTP header in the output.
   * - ``-H HEADER``
     - Specifies an HTTP header in the request.
   * - ``-X``
     - Specifies the request method to use when communicating with the HTTP
       server. The specified request is used instead of the default
       method, which is GET. For example, ``-X PUT`` specifies to use
       the ``PUT`` request method.

**Note**  If you have the tools, you can run the cURL JSON request examples
with the following options to format the output from cURL:
``<curl JSON request example> | python -mjson.tool``.

Copying and Pasting cURL Request Examples into a Terminal Window
----------------------------------------------------------------

To run the cURL request examples shown in this guide on Linux or Mac
systems, perform the following actions:

1. Copy and paste each example from the HTML version of this guide into
   an ASCII text editor (for example, vi or TextEdit). You can click on
   the small document icon to the right of each request example to
   select it.

2. Modify each example with your required account information and so
   forth, as detailed in this guide.

3. After you are finished modifying the text for the cURL request
   example with your information (for example, ``your_username``
   and ``your_api_key``), paste it into your terminal window.

4. Press Enter to run the cURL command.

    **Note**

    The carriage returns in the cURL request examples that are part of
    the cURL syntax are escaped with a backslash (\\) in order to avoid
    prematurely terminating the command. However, you should not escape
    carriage returns inside the JSON message within the command.

    **Tip**

    If you have trouble copying and pasting the examples as described,
    try typing the entire example on one long line, removing all the
    backslash line continuation characters.
