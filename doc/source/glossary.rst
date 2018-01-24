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

========
Glossary
========

Messaging Service Concepts
==========================
The Messaging Service is a multi-tenant, message queue implementation that
utilizes a RESTful HTTP interface to provide an asynchronous communications
protocol, which is one of the main requirements in today's scalable
applications.

.. glossary::

   Queue
     Queue is a logical entity that groups messages. Ideally a queue is created
     per work type. For example, if you want to compress files, you would create
     a queue dedicated for this job. Any application that reads from this queue
     would only compress files.

   Message
     Message is sent through a queue and exists until it is deleted by a recipient
     or automatically by the system based on a TTL (time-to-live) value.

   Claim
     Claim is a mechanism to mark messages so that other workers will not process the same message.

   Worker
     Worker is an application that reads one or multiple messages from the queue.

   Producer
     Producer is an application that creates messages in one or multiple queues.

   Publish - Subscribe
     Publish - Subscribe is a pattern where all worker applications have access
     to all messages in the queue. Workers can not delete or update messages.

   Producer - Consumer
     Producer - Consumer is a pattern where each worker application that reads
     the queue has to claim the message in order to prevent duplicate processing.
     Later, when the work is done, the worker is responsible for deleting the
     message. If message is not deleted in a predefined time (claim TTL), it can
     be claimed by other workers.

   Message TTL
     Message TTL is time-to-live value and defines how long a message will be accessible.

   Claim TTL
     Claim TTL is time-to-live value and defines how long a message will be in
     claimed state. A message can be claimed by one worker at a time.

   Queues Database
     Queues database stores the information about the queues and the messages
     within these queues. Storage layer has to guarantee durability and availability of the data.

   Pooling
     If pooling enabled, queuing service uses multiple queues databases in order
     to scale horizontally. A pool (queues database) can be added anytime without
     stopping the service. Each pool has a weight that is assigned during the
     creation time but can be changed later. Pooling is done by queue which
     indicates that all messages for a particular queue can be found in the same pool (queues database).

   Catalog Database
     If pooling is enabled, catalog database has to be created. Catalog database
     maintains ``queues`` to ``queues database`` mapping. Storage layer has
     to guarantee durability and availability of data.
