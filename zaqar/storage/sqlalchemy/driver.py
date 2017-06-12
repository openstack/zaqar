# Copyright (c) 2013 Red Hat, Inc.
# Copyright 2014 Catalyst IT Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from oslo_db.sqlalchemy import engines
from osprofiler import profiler
from osprofiler import sqlalchemy as sa_tracer
import sqlalchemy as sa

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import options


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)
        self.conf.register_opts(options.MANAGEMENT_SQLALCHEMY_OPTIONS,
                                group=options.MANAGEMENT_SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[options.MANAGEMENT_SQLALCHEMY_GROUP]

    def _mysql_on_connect(self, conn, record):
        # NOTE(flaper87): This is necessary in order
        # to ensure that all date operations in mysql
        # happen in UTC, `now()` for example.
        conn.query('SET time_zone = "+0:00"')

    @decorators.lazy_property(write=False)
    def engine(self):
        uri = self.sqlalchemy_conf.uri
        engine = engines.create_engine(uri, sqlite_fk=True)

        if (uri.startswith('mysql://') or
                uri.startswith('mysql+pymysql://')):
            # oslo_db.create_engine makes a test connection, throw that out
            # first.   mysql time_zone can be added to oslo_db as a
            # startup option
            engine.dispose()
            sa.event.listen(engine, 'connect',
                            self._mysql_on_connect)

        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            sa_tracer.add_tracing(sa, engine, "db")

        return engine

    # TODO(cpp-cabrera): expose connect/close as a context manager
    # that acquires the connection to the DB for the desired scope and
    # closes it once the operations are completed
    # TODO(wangxiyuan): we should migrate to oslo.db asap.
    def run(self, *args, **kwargs):
        return self.engine.execute(*args, **kwargs)

    def close(self):
        pass

    @property
    def pools_controller(self):
        controller = controllers.PoolsController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("sqlalchemy_pools_"
                                      "controller")(controller)
        else:
            return controller

    @property
    def queue_controller(self):
        controller = controllers.QueueController(self)
        if (self.conf.profiler.enabled and
                (self.conf.profiler.trace_message_store or
                    self.conf.profiler.trace_management_store)):
            return profiler.trace_cls("sqlalchemy_queue_"
                                      "controller")(controller)
        else:
            return controller

    @property
    def catalogue_controller(self):
        controller = controllers.CatalogueController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("sqlalchemy_catalogue_"
                                      "controller")(controller)
        else:
            return controller

    @property
    def flavors_controller(self):
        controller = controllers.FlavorsController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("sqlalchemy_flavors_"
                                      "controller")(controller)
        else:
            return controller
