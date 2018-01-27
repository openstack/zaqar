# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

r"""
Zaqar backed by Redis.

Redis?
------

Redis is sometimes called a "data structure store" because it makes common
data structures like hashes, lists, and sets available in shared, in-memory
storage. Zaqar chose redis because it has strong consistency and its Lua
scripting allows for semi-complex transactions to be built atop the primitives
it provides.

Supported Features
------------------

- FIFO
- Claims
- High Throughput[1]_
- At-least-once Delivery

.. [1] This depends on the backing Redis store performance. For more
information, see `Redis' benchmarks <http://redis.io/topics/benchmarks>`_.

Redis can be used both a storage driver and management driver.
For the management driver, you need to enable the redis storage options
in redis.conf. Redis persistent storage supports two ways: RDB and AOF.
The following is RDB way:
The configuration is as follows:
save <seconds> <changes>
E.g
save 900 1
save 300 10
save 60 10000

NOTE: save time, the above means that a changed key interval 900s
for persistent storage; 10 changed  keys 300s for storage;
10000 changed keys 60s for storage.


Unsupported Features
--------------------

- Durability[2]_

.. [2] As an in-memory store, Redis doesn't support the durability guarantees
       the MongoDB or SQLAlchemy backends do.


"""

from zaqar.storage.redis import driver

# Hoist classes into package namespace
ControlDriver = driver.ControlDriver
DataDriver = driver.DataDriver
