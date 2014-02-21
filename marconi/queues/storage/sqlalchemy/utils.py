# Copyright (c) 2014 Rackspace, Inc.
#
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
#
# See the License for the specific language governing permissions and
# limitations under the License.
import functools

from sqlalchemy import exc

import marconi.openstack.common.log as logging
from marconi.queues.storage import errors


LOG = logging.getLogger(__name__)


def raises_conn_error(func):
    """Handles sqlalchemy DisconnectionError

    When sqlalchemy detects a disconnect from the database server, it
    retries a number of times. After failing that number of times, it
    will convert the internal DisconnectionError into an
    InvalidRequestError. This decorator handles that error.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc.InvalidRequestError as ex:
            LOG.exception(ex)
            raise errors.ConnectionError()

    return wrapper
