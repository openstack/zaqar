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

   See :doc:`devref/development.environment`.

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
   performance test for 30 seconds using 4 producer processes with 20
   workers each, plus 4 consumer processes with 20 workers each.

   Note that the observer role is also disabled in this example by setting its
   number of workers to zero:

   .. code-block:: console

     $ zaqar-bench -pp 4 -pw 10 -cp 4 -cw 20 -ow 0 -t 30

   By default, the results are in JSON.
   For more human-readable output add the :option:`--verbose` flag.
   Verbose output looks similar to the following:

   .. code-block:: console

     $ zaqar-bench --verbose

     Starting producer (pp=1 , pw=10)...

     Starting observer (op=1 , ow=5)...

     Producer
     ========
     duration_sec: 5.1
     ms_per_req: 2.9
     reqs_per_sec: 344.5
     successful_reqs: 1742.0
     total_reqs: 1742.0

     Observer
     ========
     duration_sec: 5.0
     ms_per_req: 2.9
     reqs_per_sec: 339.3
     successful_reqs: 1706.0
     total_reqs: 1706.0
