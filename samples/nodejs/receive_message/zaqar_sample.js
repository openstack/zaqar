/*
 * Licensed under the Apache License, Version 2.0 (the 'License'); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:9000');

ws.on('message', (data, flags) => {
    const msg = JSON.parse(data);
 
    if (msg.body.messages)
      console.log(msg.body.messages[0].body);

});

ws.on('open', () => {
    ws.send('{"action": "authenticate", "headers": {"X-Auth-Token": \
        "8444886dd9b04a1b87ddb502b508261c", "X-Project-ID": \
        "7530fad032ca431e9dc8ed4a5de5d99c"}}'); // refer to bug #1553398

    ws.send('{"action": "claim_create", "body": {"queue_name": "SampleQueue"}, \
        "headers": {"Client-ID": "355186cd-d1e8-4108-a3ac-a2183697232a", \
        "X-Project-ID": "7530fad032ca431e9dc8ed4a5de5d99c"}}');
});
