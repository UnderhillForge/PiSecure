"""
PiSecure Node Module

Provides node-level services and configuration.

Exposes NodeContext (centralized state) and Scheduler utilities
for coordinating background tasks and graceful shutdown.
"""

from .context import NodeContext
from .scheduler import Scheduler, create_default_scheduler

__all__ = ["NodeContext", "Scheduler", "create_default_scheduler"]
