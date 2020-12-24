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

==============================
The subscription Confirm Guide
==============================

The subscription confirm feature now supports webhook and email with both
mongoDB and redis backend.
This guide shows how to use this feature:

Webhook
-------

.. note::

   You should make sure that the message notification is enabled. By default,
   the ``message_pipeline`` config option in [storage] section should be set
   like: message_pipeline = zaqar.notification.notifier

1. Set the config option "require_confirmation" and add the policy to the
policy.yaml file. Then restart Zaqar-wsgi service::

    In the config file:
    [notification]
    require_confirmation = True

    In the policy.yaml file:
    "subscription:confirm": ""

2. Create a subscription.

Here used zaqar/samples/zaqar/subscriber_service_sample.py be the subscriber
endpoint for example.So before the step 2, you should start the subscriber
service first.
The service could be started simply by the command::

    python zaqar/samples/zaqar/subscriber_service_sample.py

The service's default port is 5678. If you want to use a new port, the command
will be like::

    python zaqar/samples/zaqar/subscriber_service_sample.py new_port_number

The service will not confirm the subscription automatically by default. If you
want to do that, the command will be like::

    python zaqar/samples/zaqar/subscriber_service_sample.py --auto-confirm

Then create a subscription::

    curl -i -X POST http://10.229.47.217:8888/v2/queues/test/subscriptions \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4" \
    -d '{"subscriber":"http://10.229.47.217:5678", "ttl":3600, "options":{}}'

The response::

    HTTP/1.1 201 Created
    content-length: 47
    content-type: application/json; charset=UTF-8
    location: http://10.229.47.217:8888/v2/queues/test/subscriptions
    Connection: close
    {"subscription_id": "576256b03990b480617b4063"}

At the same time, If the subscriber sample service is not start by
"--auto confirm", you will receive a POST request in the subscriber sample
service, the request is like::

    WARNING:root:{"UnsubscribeBody": {"confirmed": false}, "URL-Methods": "PUT",
    "X-Project-ID": "51be2c72393e457ebf0a22a668e10a64",
    "URL-Paths": "/v2/queues/test/subscriptions/576256b03990b480617b4063/confirm",
    "URL-Expires": "2016-07-06T04:35:56", "queue_name": "test",
    "SubscribeURL": ["/v2/queues/test/subscriptions/576256b03990b480617b4063/confirm"],
    "SubscribeBody": {"confirmed": true},
    "URL-Signature": "d4038a40589cdb61cd13d5a6997472f5be779db441dd8fe0c597a6e465f30c41",
    "Message": "You have chosen to subscribe to the queue: test",
    "Message_Type": "SubscriptionConfirmation"}
    10.229.47.217 - - [06/Jul/2016 11:35:56] "POST / HTTP/1.1" 200 -

If you start the sample service with "--auto confirm", please go to step 6
directly, because the step 5 will be done by the service automatically.

3. Get the subscription.
The request::

    curl -i -X GET http://10.229.47.217:8888/v2/queues/test/subscriptions/576256b03990b480617b4063 \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4"

The response::

    HTTP/1.1 200 OK
    content-length: 154
    content-type: application/json; charset=UTF-8
    Connection: close
    {"confirmed": false, "age": 73, "id": "576256b03990b480617b4063",
    "subscriber": "http://10.229.47.217:5678", "source": "test", "ttl": 3600, "options": {}}

You can find that the "confirmed" property is false by default.

4. Post a message to the subscription's queue
The request::

    curl -i -X POST http://10.229.47.217:8888/v2/queues/test/messages \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4" \
    -d '{"messages": [{"ttl": 3600,"body": "test123"}]}'

The response::

    HTTP/1.1 201 Created
    content-length: 68
    content-type: application/json; charset=UTF-8
    location: http://10.229.47.217:8888/v2/queues/test/messages?ids=57624dee3990b4634d71bb4a
    Connection: close
    {"resources": ["/v2/queues/test/messages/57624dee3990b4634d71bb4a"]}

The subscriber received nothing and you will find a log info in zaqar-wsgi.::

    2016-07-06 11:37:57.929 98400 INFO zaqar.notification.notifier
    [(None,)2473911afe2642c0b74d7e1200d9bba7 51be2c72393e457ebf0a22a668e10a64 - - -]
    The subscriber http://10.229.47.217:5678 is not confirmed.

5. Use the information showed in step3 to confirm the subscription
The request::

    curl -i -X PUT http://10.229.47.217:8888/v2/queues/test/subscriptions/576256b03990b480617b4063/confirm \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "URL-Methods: PUT" -H "X-Project-ID: 51be2c72393e457ebf0a22a668e10a64" \
    -H "URL-Signature: d28dced4eabbb09878a73d9a7a651df3a3ce5434fcdb6c3727decf6c7078b282" \
    -H "URL-Paths: /v2/queues/test/subscriptions/576256b03990b480617b4063/confirm" \
    -H "URL-Expires: 2016-06-16T08:35:12" -d '{"confirmed": true}'

The response::

    HTTP/1.1 204 No Content
    location: /v2/queues/test/subscriptions/576256b03990b480617b4063/confirm
    Connection: close

6. Repeat step3 to get the subscription
The request::

    curl -i -X GET http://10.229.47.217:8888/v2/queues/test/subscriptions/576256b03990b480617b4063 \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4"

The response::

    HTTP/1.1 200 OK
    content-length: 155
    content-type: application/json; charset=UTF-8
    Connection: close
    {"confirmed": true, "age": 1370, "id": "576256b03990b480617b4063",
    "subscriber": "http://10.229.47.217:5678", "source": "test", "ttl": 3600,
    "options": {}}

The subscription is confirmed now.

7. Repeat step4 to post a new message.
The request::

    curl -i -X POST http://10.229.47.217:8888/v2/queues/test/messages \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4" \
    -d '{"messages": [{"ttl": 3600,"body": "test123"}]}'

The response::

    HTTP/1.1 201 Created
    content-length: 68
    content-type: application/json; charset=UTF-8
    location: http://10.229.47.217:8888/v2/queues/test/messages?ids=5762526d3990b474c80d5483
    Connection: close
    {"resources": ["/v2/queues/test/messages/5762526d3990b474c80d5483"]}

Then in subscriber sample service, you will receive a request::

    WARNING:root:{"body": {"event": "BackupStarted"}, "queue_name": "test",
    "Message_Type": "Notification", "ttl": 3600}
    10.229.47.217 - - [06/Jul/2016 13:19:07] "POST / HTTP/1.1" 200 -

8. Unsubscription.
The request::

    curl -i -X PUT http://10.229.47.217:8888/v2/queues/test/subscriptions/576256b03990b480617b4063/confirm \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "URL-Methods: PUT" -H "X-Project-ID: 51be2c72393e457ebf0a22a668e10a64" \
    -H "URL-Signature: d28dced4eabbb09878a73d9a7a651df3a3ce5434fcdb6c3727decf6c7078b282" \
    -H "URL-Paths: /v2/queues/test/subscriptions/576256b03990b480617b4063/confirm" \
    -H "URL-Expires: 2016-06-16T08:35:12" -d '{"confirmed": false}'

The response::

    HTTP/1.1 204 No Content
    location: /v2/queues/test/subscriptions/576256b03990b480617b4063/confirm
    Connection: close

Then try to post a message. The subscriber will not receive the notification
any more.

Email
-----

1. For the email confirmation way, also need to set the config option
"external_confirmation_url", "subscription_confirmation_email_template" and
"unsubscribe_confirmation_email_template".

The confirmation page url that will be used in email subscription confirmation
before notification, this page is not hosted in Zaqar server, user should
build their own web service to provide this web page.

The subscription_confirmation_email_template let user to customize the
subscription confirmation email content, including topic, body and sender.

The unsubscribe_confirmation_email_template let user to customize the
unsubscribe confirmation email content, including topic, body and sender too::

    In the config file:
    [notification]
    require_confirmation = True
    external_confirmation_url = http://web_service_url/
    subscription_confirmation_email_template = topic:Zaqar Notification - Subscription Confirmation,\
                                              body:'You have chosen to subscribe to the queue: {0}. This queue belongs to project: {1}. To confirm this subscription, click or visit this link below: {2}',\
                                              sender:Zaqar Notifications <no-reply@openstack.org>
    unsubscribe_confirmation_email_template = topic: Zaqar Notification - Unsubscribe Confirmation,\
                                              body:'You have unsubscribed successfully to the queue: {0}. This queue belongs to project: {1}. To resubscribe this subscription, click or visit this link below: {2}',\
                                              sender:Zaqar Notifications <no-reply@openstack.org>

    In the policy.yaml file:
    "subscription:confirm": ""

2. Create a subscription.
For email confirmation, you should create a subscription like this::

    curl -i -X POST http://10.229.47.217:8888/v2/queues/test/subscriptions \
    -H "Content-type: application/json" \
    -H "Client-ID: de305d54-75b4-431b-adb2-eb6b9e546014" \
    -H "X-Auth-Token: 440b677561454ea8a7f872201dd4e2c4" \
    -d '{"subscriber":"your email address", "ttl":3600, "options":{}}'

The response::

    HTTP/1.1 201 Created
    content-length: 47
    content-type: application/json; charset=UTF-8
    location: http://10.229.47.217:8888/v2/queues/test/subscriptions
    Connection: close
    {"subscription_id": "576256b03990b480617b4063"}

After the subscription created, Zaqar will send a email to the email address
of subscriber. The email specifies how to confirm the subscription.

3. Click the confirmation page link in the email body

4. The confirmation page will send the subscription confirmation request to
Zaqar server automatically. User also can choose to unsubscribe by clicking
the unsubscription link in this page, that will cause Zaqar to cancel this
subscription and send another email to notify this unsubscription action.
Zaqar providers two examples of those web pages that will help user to build
their own pages::

    zaqar/sample/html/subscriptionConfirmation.html
    zaqar/sample/html/unsubscriptionConfirmation.html

User can place those pages in web server like Apache to access them by browser,
so the external_confirmation_url will be like this::

    http://127.0.0.1:8080/subscriptionConfirmation.html

For CORS, here used zaqar/samples/html/confirmation_web_service_sample.py
be a simple web service for example, it will relay the confirmation request to
Zaqar Server. So before Step 3, you should start the web service first.
The service could be started simply by the command::

    python zaqar/samples/html/confirmation_web_service_sample.py

The service's default port is 5678. If you want to use a new port, the command
will be like::

    python zaqar/samples/html/confirmation_web_service_sample.py new_port_number
