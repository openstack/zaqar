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

=================
Running benchmark
=================

Introduction
------------

This document describes how to run benchmarking tool.

Zaqar Contributors can use this tool to test how the particular code change
affects Zaqar's performance.

Usage
-----

1. First install and run zaqar-server.

   For example, you can setup Zaqar in development environment.

   See :doc:`../contributor/development.environment`.

2. In your terminal cd into your local Zaqar repo and install additional
   requirements:

   .. code-block:: console

     $ pip install -r bench-requirements.txt

3. Copy the configuration file to ~/.zaqar:

   .. code-block:: console

     $ cp etc/zaqar-benchmark.conf.sample ~/.zaqar/zaqar-benchmark.conf

4. In this configuration file specify where zaqar-server can be found:

   .. code-block:: ini

     server_url = http://localhost:8888

5. The benchmarking tool needs a set of messages to work with. Specify the path
   to the file with messages in the configuration file. Alternatively, put
   it in the directory with the configuration file and name it
   ``zaqar-benchmark-messages.json``.
   As a starting point, you can use the sample file from the etc directory:

   .. code-block:: console

     $ cp etc/zaqar-benchmark-messages.json ~/.zaqar/

   If the file is not found or no file is specified, a single hard-coded
   message is used for all requests.

6. Run the benchmarking tool using the following command:

   .. code-block:: console

     $ zaqar-bench

   By default, the command will run a performance test for 5 seconds, using one
   producer process with 10 greenlet workers, and one observer process with 5
   workers. The consumer role is disabled by default.

   You can override these defaults in the config file or on the command line
   using a variety of options. For example, the following command runs a
   performance test for 30 seconds using 4 producer processes with 20 workers
   each, plus 4 consumer processes with 20 workers each.

   Note that the observer role is also disabled in this example by setting its
   number of workers to zero:

   .. code-block:: console

     $ zaqar-bench -pp 4 -pw 10 -cp 4 -cw 20 -ow 0 -t 30

   By default, the results are in human-readable format. For JSON output add
   the ``--noverbose`` flag. The non-verbose output looks similar to the
   following:

   .. code-block:: console

     $ zaqar-bench --noverbose
     Using 'envvars' credentials
     Using 'keystone' authentication method
     Benchmarking Zaqar API v2...
     {"params": {"consumer": {"processes": 1, "workers": 0}, "observer": {"processes": 1, "workers": 5}, "producer": {"processes": 1, "workers": 10}}, "consumer": {"claim_total_requests": 0, "ms_per_claim": 0, "total_reqs": 0, "reqs_per_sec": 0, "successful_reqs": 0, "duration_sec": 0, "ms_per_delete": 0, "messages_processed": 0}, "producer": {"duration_sec": 8.569170951843262, "ms_per_req": 201.715140507139, "total_reqs": 29, "successful_reqs": 29, "reqs_per_sec": 3.384224700729303}, "observer": {"duration_sec": 8.481178045272827, "ms_per_req": 407.40778711107043, "total_reqs": 18, "successful_reqs": 18, "reqs_per_sec": 2.122346672115049}}

   By default, zaqar-bench is benchmarking Zaqar API version 2. To run
   benchmark against other API versions use ``-api`` parameter. For
   example:

   .. code-block:: console

     $ zaqar-bench -api 1.1

Configuring zaqar-bench to use Keystone authentication
######################################################

It's possible to use zaqar-bench with Keystone authentication, if your Zaqar is
configured to use Keystone authentication method and the Keystone service is
running. For example, this is always true when running DevStack_ with
unmodified ``zaqar.conf``.

Let's configure zaqar-bench too to use Keystone:

#. Set zaqar-bench's authentication method to Keystone.

   By default zaqar-bench is using ``noauth`` method. This can be changed by
   setting the environment variable ``OS_AUTH_STRATEGY`` to ``keystone``.

   To set this environment variable:

   * temporarily, run:

        .. code-block:: console

           $ export OS_AUTH_STRATEGY=keystone

   * permanently, add this line to your ``~/bashrc`` file:

        .. code-block:: bash

           export OS_AUTH_STRATEGY=keystone

     Reboot your computer or just run in the terminal where you will start
     zaqar-bench:

        .. code-block:: console

           $ source ~/.bashrc

#. Set Keystone credentials for zaqar-bench.

   * If you're running Zaqar under DevStack, **you can omit this step**,
     because zaqar-bench will automatically get administrator or user
     credentials from the one of the files created by DevStack: either from
     ``/etc/openstack/clouds.yaml`` file or from
     ``~/.config/openstack/clouds.yaml`` file, if it exists.

   * If you're running manually configured Zaqar with manually configured
     Keystone (not under DevStack):

     Add these lines to your ``~/.bashrc`` file and specify the valid Keystone
     credentials:

        .. code-block:: bash

           export OS_AUTH_URL="http://<your keystone endpoint>/v2.0"
           export OS_USERNAME="<keystone user name>"
           export OS_PASSWORD="<the user's password>"
           export OS_PROJECT_NAME="<keystone project name for the user>"

     Reboot your computer or just run in the terminal where you will start
     zaqar-bench:

        .. code-block:: console

           $ source ~/.bashrc

#. Run zaqar-bench as usual, for example:

   .. code-block:: console

     $ zaqar-bench

   If everything is properly configured, zaqar-bench must show the line
   ``Using 'keystone' authentication method`` and execute without
   authentication errors.


.. _DevStack: https://docs.openstack.org/devstack/latest/
