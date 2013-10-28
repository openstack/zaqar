"""Marconi Storage Drivers"""

from marconi.queues.storage import base
from marconi.queues.storage import errors  # NOQA

# Hoist classes into package namespace
ControlDriverBase = base.ControlDriverBase
DataDriverBase = base.DataDriverBase
CatalogueBase = base.CatalogueBase
ClaimBase = base.ClaimBase
MessageBase = base.MessageBase
QueueBase = base.QueueBase
ShardsBase = base.ShardsBase
