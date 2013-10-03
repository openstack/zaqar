"""WSGI Transport Driver"""

from marconi.queues.transport.wsgi import configs  # NOQA
from marconi.queues.transport.wsgi import driver

# Hoist into package namespace
Driver = driver.Driver
