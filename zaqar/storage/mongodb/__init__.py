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
MongoDB Storage Driver for Zaqar.

About the store
---------------

MongoDB is a nosql, eventually consistent, reliable database with support for
horizontal-scaling and capable of handling different levels of throughputs.

Supported Features
------------------

- FIFO
- Unlimited horizontal-scaling [1]_
- Reliability [2]_

.. [1] This is only possible with a sharding environment
.. [2] Write concern must be equal or higher than 2

Supported Deployments
---------------------

MongoDB can be deployed in 3 different ways. The first and most simple one is
to deploy a standalone `mongod` node. The second one is to use a Replica Sets
which gives a master-slave deployment but cannot be scaled unlimitedly. The
third and last one is a sharded cluster.

The second and third methods are the ones recommended for production
environments where durability and scalability are a must-have. The driver
itself forces operators to use such environments by checking whether it is
talking to a replica-set or sharded cluster. Such enforcement can be disabled
by running Zaqar in an unreliable mode.

Replica Sets
------------

When running on a replica-set, Zaqar won't try to be smart and it'll rely as
much as possible on the database and pymongo.

Sharded Cluster
---------------

TBD
"""

from zaqar.storage.mongodb import driver

# Hoist classes into package namespace
ControlDriver = driver.ControlDriver
DataDriver = driver.DataDriver
FIFODataDriver = driver.FIFODataDriver
