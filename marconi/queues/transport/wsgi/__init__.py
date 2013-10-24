"""WSGI Transport Driver"""

from marconi.queues.transport.wsgi import driver

# Hoist into package namespace
Driver = driver.DriverBase
