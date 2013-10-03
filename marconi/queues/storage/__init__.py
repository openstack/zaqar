"""Marconi Storage Drivers"""

from oslo.config import cfg

from marconi.queues.storage import base
from marconi.queues.storage import exceptions  # NOQA

_STORAGE_LIMITS_OPTIONS = [
    cfg.IntOpt('default_queue_paging', default=10,
               help='Default queue pagination size'),

    cfg.IntOpt('default_message_paging', default=10,
               help='Default message pagination size')
]

cfg.CONF.register_opts(_STORAGE_LIMITS_OPTIONS, group='queues:limits:storage')

# Hoist classes into package namespace
ClaimBase = base.ClaimBase
DriverBase = base.DriverBase
MessageBase = base.MessageBase
QueueBase = base.QueueBase
