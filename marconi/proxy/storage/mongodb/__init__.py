"""MongoDB Proxy Storage Driver for Marconi"""

from marconi.proxy.storage.mongodb import driver

# Hoist classes into package namespace
Driver = driver.Driver
