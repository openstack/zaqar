"""Marconi Transport Drivers"""

from oslo.config import cfg

from marconi.queues.transport import base

_TRANSPORT_OPTIONS = [
    cfg.StrOpt('auth_strategy', default='')
]

cfg.CONF.register_opts(_TRANSPORT_OPTIONS)

# Hoist into package namespace
DriverBase = base.DriverBase
