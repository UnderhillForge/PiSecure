"""
PiSecure Developer API
======================

Platform-independent blockchain integration for developers.

This module provides REST API endpoints and client libraries that allow
developers to interact with the PiSecure blockchain from any platform
without running mining nodes or PiSecure servers locally.

Features:
- RESTful API for blockchain operations
- Client SDKs for JavaScript/TypeScript, Python, etc.
- Decentralized peer discovery
- Wallet operations and transaction management
- Real-time blockchain data access

Usage:
    # As a server (on PiSecure nodes)
    from pisecure.api.server import BlockchainAPI
    api = BlockchainAPI()
    api.run()

    # As a client (in any application)
    from pisecure.api.client import PiSecureClient
    client = PiSecureClient()
    balance = client.get_wallet_balance(address)
"""

from .server import BlockchainAPI
from .client import PiSecureClient
from .discovery import PeerDiscovery

__all__ = [
    'BlockchainAPI',
    'PiSecureClient',
    'PeerDiscovery'
]