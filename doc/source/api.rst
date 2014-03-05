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

Using Marconi's Public APIs
===========================

Marconi fully implements version 1.0 of the OpenStack Messaging API by now. 
Generally, you can use any HTTP client to talk with Marconi public REST API,
though Marconi client is the recommended approach.


Marconi Client
############################################
We can easily access the Marconi REST API via Marconi client. Below is an example
to create a queue, post messages to it and finally delete it::

    from marconiclient.queues.v1 import client

    URL = 'http://localhost:8888'
    messages = [{'body': {'id': idx}, 'ttl': 360} for idx in range(20)]

    cli = client.Client(URL)
    queue = cli.queue('myqueue')
    queue.post(messages)

    for msg in queue.messages(echo=True):
        print(msg.body)
        msg.delete()

    queue.delete()


curl
####

Define these variables::

    # USERNAME=my identity username
    # APIKEY=my-long-api-key
    # ENDPOINT=test-queue.mydomain.com < keystone endpoint >
    # QUEUE=test-queue
    # CLIENTID=c5a6114a-523c-4085-84fb-533c5ac40789
    # HTTP=http
    # PORT=80
    # TOKEN=9abb6d47de3143bf80c9208d37db58cf < your token here >

Create the queue::

    # curl -i -X PUT $HTTP://$ENDPOINT:$PORT/v1/queues/$QUEUE -H "X-Auth-Token: $TOKEN" -H "Client-ID: $CLIENTID"
    HTTP/1.1 201 Created
    content-length: 0
    location: /v1/queues/test-queue

```HTTP/1.1 201 Created``` response proves that service is functioning properly.