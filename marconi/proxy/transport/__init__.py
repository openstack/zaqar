"""Marconi Proxy Transport Drivers"""

from oslo.config import cfg

from marconi.proxy.transport import base

# NOTE(flaper87): Not sure
# what this is for.
CFG = cfg.CONF

# Hoist into package namespace
DriverBase = base.DriverBase
