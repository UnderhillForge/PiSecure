"""
PiSecure Interfaces Module

Defines abstract boundaries between major components:
- Chain: Blockchain operations
- Wallet: Wallet operations
- Node: Node operations
- Mining: Mining operations
- Storage: Data persistence
- Init: Service initialization

These interfaces enable independent testing, multiprocess architecture,
and swappable implementations without tight coupling.
"""

from .chain import ChainInterface
from .wallet import WalletInterface
from .node import NodeInterface
from .mining import MiningInterface
from .storage import StorageInterface
from .init import InitFactory

__all__ = [
    "ChainInterface",
    "WalletInterface",
    "NodeInterface",
    "MiningInterface",
    "StorageInterface",
    "InitFactory",
]
