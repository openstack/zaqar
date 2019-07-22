=====================
Getting Started Guide
=====================

Overview
--------

Messaging service is a RESTful API-based messaging
service. It supports distributed web applications,and is based on the
OpenStack Zaqar project.

Messaging service is a vital component of large, distributed
web applications. You can use Messaging service for public,
private, and hybrid cloud environments.

As you develop distributed web applications, you often have multiple
agents set up to complete sets of tasks for those applications. These
tasks can be anything from creating users to deleting blocks of storage.
Messaging service provides a simple interface that creates these tasks as
queues, messages, and claims. The interface then posts, claims, reads,
and deletes them as the tasks are needed and performed.

Messaging service handles the distribution of tasks, but it does not
necessarily manage the order of the tasks. Applications handle the
workflow at a higher level.

This guide explains how to access and start using the API so that you
can begin to use Messaging service for your applications. Instructions are
given for how to properly enter the necessary URLs, using cURL, to set
up and use a basic set of Messaging service operations.

Prerequisites for Running Examples
----------------------------------

In order to run the examples in this guide, you must have the following
prerequisites:

-  A Cloud account

-  A username and password, as specified during registration

-  Prior knowledge of HTTP/1.1 conventions

-  Basic familiarity with Cloud and RESTful APIs

How Messaging service Works
---------------------------

Following is an overview of how Messaging service works. For definitions
of Messaging service terms, see the below glossary.

1. You create a queue to which producers or publishers post messages.

2. Workers (consumers or subscribers) claim or get a message from the
   queue, complete the work in that message, and delete the message.

   If a worker will be off-line before it completes the work in a
   message, the worker can retire the claim's time to live (TTL),
   putting the message back into the queue for another worker to claim.

3. Subscribers monitor the claims from these queues to track activity
   and help troubleshoot errors.

For the majority of use cases, Messaging service is not responsible for
the ordering of messages. However, if there is only a single producer,
Messaging service ensures that messages are handled in a First In, First
Out (FIFO) order.

Messaging Patterns
------------------

The Messaging service API supports a variety of messaging patterns
including the following:

-  Task distribution

-  Event broadcasting

-  Point-to-point messaging

Task distribution
-----------------

The task distribution pattern has the following characteristics:

-  A producer is programmed to send messages to a queue.

-  Multiple workers (or consumers) are programmed to monitor a queue.

-  Only one worker can claim a message so that no other worker can claim
   the message and duplicate the work.

-  The worker must delete the message when work is done.

-  TTL restores a message to an unclaimed state if the worker never
   finishes.

This pattern is ideal for dispatching jobs to multiple processors.

Event Broadcasting
------------------

Characteristics of the event broadcasting pattern are:

-  The publisher sends messages to a queue.

-  Multiple observers (or subscribers) get the messages in the queue.

-  Multiple observers take action on each message.

-  Observers send a marker to skip messages already seen.

-  TTL eventually deletes messages.

This pattern is ideal for notification of events to multiple observers
at once.

Point-to-point messaging
------------------------

Characteristics of the point-to-point messaging pattern are:

-  The publisher sends messages to a queue.

-  The consumer gets the messages in the queue.

-  The consumer can reply with the result of processing a message by
   sending another message to the same queue (queues are duplex by
   default).

-  The publisher gets replies from the queue.

-  The consumer sends a marker to skip messages already seen.

-  TTL eventually deletes messages.

This pattern is ideal for communicating with a specific client,
especially when a reply is desired from that client.

Messaging service Operations
----------------------------

This section lists all of the operations that are available in the
Messaging service API. This document uses some of the most common
operations in `OpenStack API Reference <https://docs.openstack.org/api-quick-start/index.html>`__..

For details about all of the operations, see the Messaging service API v2
Reference.

Home Document
~~~~~~~~~~~~~

The following operation is available for the home document:

-  Get Home Document

Queues
~~~~~~

The following operations are available for queues:

-  Create Queue

-  List Queues

-  Get Queue

-  Update Queue

-  Get Queue Stats

-  Delete Queue

Messages
~~~~~~~~

The following operations are available for messages:

-  Post Message

-  Get Messages

-  Get a Specific Message

-  Get a Set of Messages by ID

-  Delete Message

-  Delete a Set of Messages by ID

Claims
~~~~~~

The following operations are available for claims:

-  Claim Messages

-  Get Claim

-  Update Claim

-  Release Claim

Subscriptions
~~~~~~~~~~~~~

The following operations are available for subscriptions:

-  Create Subscriptions

-  List Subscriptions

-  Get Subscription

-  Update Subscription

-  Delete Subscription


Pools
~~~~~

The following operations are available for Pools:

-  Create Pools

-  List Pools

-  Get Pool

-  Update Pool

-  Delete Pool

Flavors
~~~~~~~

The following operations are available for Flavors:

-  Create Flavors

-  List Flavors

-  Get Flavor

-  Update Flavors

-  Delete Flavors


Health
~~~~~~

The following operations are available for Health:

- Ping for basic health status

- Get detailed health status


Use Cases
---------

Queuing systems are used to coordinate tasks within an application. Here
are some examples:

-  **Backup**: A backup application might use a queuing system to
   connect the actions that users do in the a control panel to the
   customer's backup agent on a server. When a customer wants to start a
   backup, they simply choose "start backup" on a panel. Doing so causes
   the producer to put a "startBackup" message into the queue. Every few
   minutes, the agent on the customers server (the worker) checks the
   queue to see if it has any new messages to act on. The agent claims
   the "startBackup" message and kicks off the backup on the customer's
   server.

-  **Storage**: Gathering statistics for a large, distributed storage
   system can be a long process. The storage system can use a queuing
   system to ensure that jobs complete, even if one initially fails.
   Since messages are not deleted until after the worker has completed
   the job, the storage system can make sure that no job goes undone. If
   the worker fails to complete the job, the message stays in the queue
   to be completed by another server. In this case, a worker claims a
   message to perform a statistics job, but the claim's TTL expired and
   the message is put back into the queue when the job took too long to
   complete (meaning that it most likely failed). By giving the claim a
   TTL, applications can protect themselves from workers going off-line
   while processing a message. After a claim's TTL expires, the message
   is put back into the queue for another worker to claim.

-  **Email**: The team for an email application is constantly migrating
   customer email from old versions to newer ones, so they develop a
   tool to let customers do it themselves. The migrations take a long
   time, so they cannot be done with single API calls, or by a single
   server. When a user starts a migration job from their portal, the
   migration tool sends messages to the queue with details of how to run
   the migration. A set of migration engines, the consumers in this
   case, periodically check the queues for new migration tasks, claim
   the messages, perform the migration, and update a database with the
   migration details. This process allows a set of servers to work
   together to accomplish large migrations in a timely manner.

Following are some generic use cases for Messaging service:

-  Distribute tasks among multiple workers (transactional job queues)

-  Forward events to data collectors (transactional event queues)

-  Publish events to any number of subscribers (event broadcasting)

-  Send commands to one or more agents (point-to-point messaging or
   event broadcasting)

-  Request an action or get information from a Remote Procedure Call
   (RPC) agent (point-to-point messaging)

Additional Resources
--------------------

For more information about using the API, see the Messaging service API v2
Reference. All you need to get started with Messaging service is the
getting started guide, the reference, and your Cloud account.

For information about the OpenStack Zaqar API, see
`OpenStack API Reference <https://docs.openstack.org/api-quick-start/index.html>`__.

This API uses standard HTTP 1.1 response codes as documented at
`www.w3.org/Protocols/rfc2616/rfc2616-sec10.html <http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html>`__.

Glossary
--------

**Claim**
The process of a worker checking out a message to perform a task.
Claiming a message prevents other workers from attempting to process the
same messages.

**Claim TTL**
Defines how long a message will be in claimed state. A message can be
claimed by one worker at a time.

**Consumer**
A server that claims messages from the queue.

**Message**
A task, a notification, or any meaningful data that a producer or
publisher sends to the queue. A message exists until it is deleted by a
recipient or automatically by the system based on a TTL (time-to-live)
value.

**Message TTL**
Defines how long a message will be accessible.

**Producer**
A server or application that sends messages to the queue.

**Producer - Consumer**
A pattern where each worker application that reads the queue has to
claim the message in order to prevent duplicate processing. Later, when
work is done, the worker is responsible for deleting the message. If
message is not deleted in a predefined time, it can be claimed by other
workers.

**Publisher**
A server or application that posts messages to the queue with the intent
to distribute information or updates to multiple subscribers.

**Publisher - Subscriber**
A pattern where all worker applications have access to all messages in
the queue. Workers cannot delete or update messages.

**Queue**
The entity that holds messages. Ideally, a queue is created per work
type. For example, if you want to compress files, you would create a
queue dedicated to this job. Any application that reads from this queue
would only compress files.

**Subscriber**
An observer that watches messages like an RSS feed but does not claim
any messages.

**TTL**
Time-to-live value.

**Worker**
A client that claims messages from the queue and performs actions based
on those messages.
