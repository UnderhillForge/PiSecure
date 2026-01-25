"""
CLI Commands Module

Organized command implementations by domain.

Submodules:
- blockchain.py    - Chain and block operations
- mining.py        - Mining operations
- wallet.py        - Wallet operations
- network.py       - Network and peer operations
- monitoring.py    - Health monitoring
- admin.py         - Administrative operations

Use register_all(cli) to attach available command sets to the main CLI.
"""

from .blockchain import register as register_blockchain
from .network import register as register_network
from .wallet import register as register_wallet
from .mining import register as register_mining
from .monitoring import register as register_monitoring

__all__ = [
    "register_all",
    "register_blockchain",
    "register_network",
    "register_wallet",
    "register_mining",
    "register_monitoring",
]


def register_all(cli):
    """Attach all available command groups to the root CLI."""
    register_blockchain(cli)
    register_network(cli)
    register_wallet(cli)
    register_mining(cli)
    register_monitoring(cli)
    return cli
