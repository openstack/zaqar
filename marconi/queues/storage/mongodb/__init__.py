"""MongoDB Storage Driver for Marconi"""

from marconi.queues.storage.mongodb import driver

# Hoist classes into package namespace
ControlDriver = driver.ControlDriver
DataDriver = driver.DataDriver
