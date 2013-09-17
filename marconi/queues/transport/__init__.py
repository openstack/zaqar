"""Marconi Transport Drivers"""

from marconi.common import config
from marconi.queues.transport import base

OPTIONS = {
    'auth_strategy': ""
}

CFG = config.project('marconi').from_options(**OPTIONS)

# Hoist into package namespace
DriverBase = base.DriverBase
