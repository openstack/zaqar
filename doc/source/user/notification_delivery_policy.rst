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

======================================
The Notification Delivery Policy Guide
======================================

Support notification delivery policy in webhook type. It will work when
the notification is sent from Zaqar to the subscriber failed.
This guide shows how to use this feature:

Webhook
-------

.. note::

   You should make sure that the message notification is enabled. By default,
   the ``message_pipeline`` config option in [storage] section should be set
   like: message_pipeline = zaqar.notification.notifier

1. Create the queue with _retry_policy metadata like this:

.. code:: json

    {
        "_retry_policy": {
            "retries_with_no_delay": "<Integer value, optional>",
            "minimum_delay_retries": "<Integer value, optional>",
            "minimum_delay": "<Interger value, optional>",
            "maximum_delay": "<Interger value, optional>",
            "maximum_delay_retries": "<Integer value, optional>",
            "retry_backoff_function": "<String value, optional>",
            "ignore_subscription_override": "<Bool value, optional>"}
    }

-  'minimum_delay' and 'maximum_delay' mean delay time in seconds.
-  'retry_backoff_function' mean name of retry backoff function.
   There will be a enum in Zaqar that contain all valid values.
   Zaqar now supports retry backoff function including 'linear',
   'arithmetic','geometric' and 'exponential'.
-  'minimum_delay_retries' and 'maximum_delay_retries' mean the number of
   retries with 'minimum_delay' or 'maximum_delay' delay time.

If value of retry_policy is empty dict, that Zaqar will use default
value to those keys:

-  retries_with_no_delay=3
-  minimum_delay_retries=3
-  minimum_delay=5
-  maximum_delay=30
-  maximum_delay_retries=3
-  retry_backoff_function=linear
-  ignore_subscription_override=False

2. Create a subscription with options like queue's metadata below. If user
   don't set the options, Zaqar will use the retry policy in queue's metadata.
   If user do it, Zaqar will use the retry policy in options by default, if
   user still want to use retry policy in queue's metadata, then can set the
   ignore_subscription_override = True.
