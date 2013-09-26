"""WSGI Proxy Transport Driver"""

from marconi.proxy.transport.wsgi import driver

# Hoist into package namespace
Driver = driver.DriverBase
