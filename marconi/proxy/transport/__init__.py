"""Marconi Proxy Transport Drivers"""

from marconi.common import config
from marconi.proxy.transport import base

CFG = config.project('marconi').from_options()

# Hoist into package namespace
DriverBase = base.DriverBase
