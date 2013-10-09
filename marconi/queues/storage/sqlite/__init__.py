"""
In-memory reference Storage Driver for Marconi.

Useful for automated testing and for prototyping storage driver concepts.
"""

from marconi.queues.storage.sqlite import driver

# Hoist classes into package namespace
ControlDriver = driver.ControlDriver
DataDriver = driver.DataDriver
