"""Marconi proxy storage drivers"""

from marconi.proxy.storage import base


# NOTE(cpp-cabrera): Hoist classes into package namespace
CatalogueBase = base.CatalogueBase
DriverBase = base.DriverBase
PartitionsBase = base.PartitionsBase
