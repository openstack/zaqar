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


_AUTO_CONFIRM = False
for arg in sys.argv:
    if arg == '--auto-confirm':
        _AUTO_CONFIRM = True
        sys.argv.remove(arg)
        break

if len(sys.argv) > 2:
    PORT = int(sys.argv[2])
elif len(sys.argv) > 1:
    PORT = int(sys.argv[1])
else:
    PORT = 5678


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """This is the sample service for wsgi subscription.

    """

    # TODO(wangxiyuan): support websocket.
    def do_POST(self):
        logging.warning('=================== POST =====================')
        data_string = str(
            self.rfile.read(int(self.headers['Content-Length'])))
        self.data = json.loads(data_string)
        if _AUTO_CONFIRM:
            self._send_confirm_request()
            message = 'OK'
            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)
        logging.warning(self.headers)
        logging.warning(self.data)
        return

    def _send_confirm_request(self):
        url = self.data['WSGISubscribeURL']
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Project-ID': self.data['X-Project-ID'],
            'Client-ID': uuidutils.generate_uuid(),
            'URL-Methods': self.data['URL-Methods'],
            'URL-Signature': self.data['URL-Signature'],
            'URL-Paths': self.data['URL-Paths'],
            'URL-Expires': self.data['URL-Expires'],
        }
        data = {'confirmed': True}
        requests.put(url=url, data=json.dumps(data), headers=headers)

Handler = ServerHandler
httpd = SocketServer.TCPServer(("", PORT), Handler)
httpd.serve_forever()
