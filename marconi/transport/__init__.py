"""Marconi Transport Drivers"""

from marconi.common import config
from marconi.transport import base

OPTIONS = {
    "auth_strategy": ""
}

cfg = config.project('marconi').from_options(**OPTIONS)

MAX_QUEUE_METADATA_SIZE = 64 * 1024
"""Maximum metadata size per queue when serialized as JSON"""


# Hoist into package namespace
DriverBase = base.DriverBase
