"""WSGI Proxy Transport Driver"""

from marconi.queues.transport.wsgi import driver

# Hoist into package namespace
Driver = driver.Driver
