# Copyright (c) 2017 ZTE Corporation..
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
# See the License for the specific language governing permissions and
# limitations under the License.

"""Redis storage controller for the queues catalogue.

Serves to construct an association between a project + queue -> pool.

::

    {
        'p_q': project_queue :: str,
        's': pool_identifier :: str
    }
"""
from oslo_log import log as logging
import redis

from zaqar.i18n import _
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.redis import utils

LOG = logging.getLogger(__name__)

CATALOGUE_SUFFIX = 'catalogue'
COUNTING_BATCH_SIZE = 100


class CatalogueController(base.CatalogueBase):
    """Implements Catalogue resource operations using Redis.

    * Project Index (Redis sorted set):

        Set of all queue_ids for the given project, ordered by name.

        Key: <project_id>.catalogue

        +--------+-----------------------------+
        |  Id    |  Value                      |
        +========+=============================+
        |  name  |  <project_id>.<queue_name>  |
        +--------+-----------------------------+

    * Queue and pool Information (Redis hash):

        Key: <project_id>.<queue_name>.catalogue

        +----------------------+---------+
        |  Name                |  Field  |
        +======================+=========+
        |  Project             |  p      |
        +----------------------+---------+
        |  Queue               |  p_q    |
        +----------------------+---------+
        |  Pool                |  p_p     |
        +----------------------+---------+
    """

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _insert(self, project, queue, pool):
        queue_key = utils.scope_queue_name(queue, project)
        catalogue_project_key = utils.scope_pool_catalogue(project,
                                                           CATALOGUE_SUFFIX)
        catalogue_queue_key = utils.scope_pool_catalogue(queue_key,
                                                         CATALOGUE_SUFFIX)
        # Check if the queue already exists.
        if self._exists(queue, project):
            return False

        catalogue = {
            'p': project,
            'p_q': queue,
            'p_p': pool
        }
        # Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.zadd(catalogue_project_key, {queue_key: 1})
            pipe.hmset(catalogue_queue_key, catalogue)

            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                msgtmpl = _(u'CatalogueController:insert %(prj)s:'
                            '%(queue)s  %(pool)s failed')
                LOG.exception(msgtmpl,
                              {'prj': project, 'queue': queue, 'pool': pool})
                return False
        msgtmpl = _(u'CatalogueController:insert %(prj)s:%(queue)s'
                    ':%(pool)s, success')
        LOG.info(msgtmpl,
                 {'prj': project, 'queue': queue, 'pool': pool})
        return True

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def list(self, project):

        catalogue_project_key = utils.scope_pool_catalogue(project,
                                                           CATALOGUE_SUFFIX)

        ctlgs = []
        offset = 0
        while True:
            queues = self._client.zrange(catalogue_project_key, offset,
                                         offset + COUNTING_BATCH_SIZE - 1)
            if not queues:
                break

            offset += len(queues)

            for queue in queues:
                catalogue_queue_key =\
                    utils.scope_pool_catalogue(queue,
                                               CATALOGUE_SUFFIX)
                ctlg = self._client.hgetall(catalogue_queue_key)
                ctlgs.append(ctlg)
        return (_normalize(v) for v in ctlgs)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get(self, project, queue):
        queue_key = utils.scope_queue_name(queue, project)
        catalogue_queue_key = \
            utils.scope_pool_catalogue(queue_key,
                                       CATALOGUE_SUFFIX)
        ctlg = self._client.hgetall(catalogue_queue_key)
        if ctlg is None or len(ctlg) == 0:
            raise errors.QueueNotMapped(queue, project)

        return _normalize(ctlg)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _exists(self, project, queue):
        queue_key = utils.scope_queue_name(queue, project)
        catalogue_queue_key = \
            utils.scope_pool_catalogue(queue_key,
                                       CATALOGUE_SUFFIX)
        return self._client.exists(catalogue_queue_key)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def exists(self, project, queue):
        return self._exists(project, queue)

    def insert(self, project, queue, pool):
        self._insert(project, queue, pool)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, project, queue):
        # (gengchc): Check if the queue already exists.
        if not self._exists(project, queue):
            return True

        queue_key = utils.scope_queue_name(queue, project)
        catalogue_project_key = utils.scope_pool_catalogue(project,
                                                           CATALOGUE_SUFFIX)
        catalogue_queue_key = utils.scope_pool_catalogue(queue_key,
                                                         CATALOGUE_SUFFIX)
        # (gengchc) Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.zrem(catalogue_project_key, queue_key)
            pipe.delete(catalogue_queue_key)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                msgtmpl = _(u'CatalogueController:delete %(prj)s'
                            ':%(queue)s failed')
                LOG.info(msgtmpl,
                         {'prj': project, 'queue': queue})
                return False
        msgtmpl = _(u'CatalogueController:delete %(prj)s:%(queue)s success')
        LOG.info(msgtmpl,
                 {'prj': project, 'queue': queue})

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _update(self, project, queue, pool):
        # Check if the queue already exists.
        if not self._exists(project, queue):
            raise errors.QueueNotMapped(queue, project)

        queue_key = utils.scope_queue_name(queue, project)
        catalogue_queue_key = utils.scope_pool_catalogue(queue_key,
                                                         CATALOGUE_SUFFIX)
        with self._client.pipeline() as pipe:
            pipe.hset(catalogue_queue_key, "pl", pool)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                msgtmpl = _(u'CatalogueController:_update %(prj)s'
                            ':%(queue)s:%(pool)s failed')
                LOG.exception(msgtmpl,
                              {'prj': project, 'queue': queue, 'pool': pool})
                return False
        msgtmpl = _(u'CatalogueController:_update %(prj)s:%(queue)s'
                    ':%(pool)s')
        LOG.info(msgtmpl,
                 {'prj': project, 'queue': queue, 'pool': pool})

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def update(self, project, queue, pool=None):
        if pool is None:
            return False
        self._update(project, queue, pool)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def drop_all(self):
        allcatalogueobj_key = self._client.keys(pattern='*catalog')
        if len(allcatalogueobj_key) == 0:
            return
        with self._client.pipeline() as pipe:
            for key in allcatalogueobj_key:
                pipe.delete(key)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                return False


def _normalize(entry):
    return {
        'queue': str(entry['p_q']),
        'project': str(entry['p']),
        'pool': str(entry['p_p'])
    }
