"""Marconi Transport Drivers"""

from marconi.transport import base


MAX_QUEUE_METADATA_SIZE = 64 * 1024
"""Maximum metadata size per queue when serialized as JSON"""


# Hoist into package namespace
DriverBase = base.DriverBase
