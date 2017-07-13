# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
import json
import logging
from oslo_utils import uuidutils
import requests
import sys

try:
    import SimpleHTTPServer
    import SocketServer
except Exception:
    from http import server as SimpleHTTPServer
    import socketserver as SocketServer


if len(sys.argv) > 2:
    PORT = int(sys.argv[2])
elif len(sys.argv) > 1:
    PORT = int(sys.argv[1])
else:
    PORT = 5678


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """This is the sample service for email subscription confirmation.

    """

    def do_OPTIONS(self):
        logging.warning('=================== OPTIONS =====================')
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', self.headers['origin'])
        self.send_header('Access-Control-Allow-Methods', 'PUT')
        self.send_header('Access-Control-Allow-Headers',
                         'client-id,confirmation-url,content-type,url-expires,'
                         'url-methods,url-paths,url-signature,x-project-id,'
                         'confirm')
        self.end_headers()
        logging.warning(self.headers)
        return

    def do_PUT(self):
        logging.warning('=================== PUT =====================')
        self._send_confirm_request()
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', self.headers['origin'])
        self.end_headers()
        message = "{\"message\": \"ok\"}"
        self.wfile.write(message)
        logging.warning(self.headers)
        return

    def _send_confirm_request(self):
        url = self.headers['confirmation-url']
        confirmed_value = True
        try:
            if self.headers['confirm'] == "false":
                confirmed_value = False
        except KeyError:
            pass
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Project-ID': self.headers['x-project-id'],
            'Client-ID': uuidutils.generate_uuid(),
            'URL-Methods': self.headers['url-methods'],
            'URL-Signature': self.headers['url-signature'],
            'URL-Paths': self.headers['url-paths'],
            'URL-Expires': self.headers['url-expires'],
        }
        data = {'confirmed': confirmed_value}
        requests.put(url=url, data=json.dumps(data), headers=headers)

Handler = ServerHandler
httpd = SocketServer.TCPServer(("", PORT), Handler)
httpd.serve_forever()
