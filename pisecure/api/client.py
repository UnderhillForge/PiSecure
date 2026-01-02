"""
PiSecure Client Library - Python
================================

Python client library for interacting with PiSecure blockchain nodes
via REST API. Provides easy-to-use methods for blockchain operations,
wallet management, and transaction handling.

Features:
- Automatic peer discovery and load balancing
- Connection pooling and retry logic
- Type hints and modern Python support
- Comprehensive error handling
- Async support for high-performance applications

Usage:
    from pisecure.api.client import PiSecureClient

    client = PiSecureClient()
    balance = client.get_wallet_balance('your_wallet_address')
    print(f"Balance: {balance} tokens")
"""

import time
import json
import requests
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
import random

from .discovery import PeerDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PiSecureClient:
    """
    Python client for PiSecure blockchain API.

    Automatically discovers available nodes and provides load-balanced
    access to blockchain functionality.
    """

    def __init__(self, bootstrap_peers: Optional[List[str]] = None,
                 api_version: str = "v1", timeout: int = 30,
                 max_retries: int = 3):
        """
        Initialize the PiSecure client.

        Args:
            bootstrap_peers: List of bootstrap peer URLs
            api_version: API version to use
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize peer discovery
        self.peer_discovery = PeerDiscovery(bootstrap_peers or [
            "https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/peers.json"
        ])

        # Discover available API endpoints
        self.api_endpoints = self._discover_api_endpoints()

        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.timeout = timeout

    def _discover_api_endpoints(self) -> List[str]:
        """Discover available API endpoints from known peers."""
        endpoints = []

        try:
            # Get known peers
            peers = self.peer_discovery.get_known_peers()

            # Test each peer for API availability
            for peer_url in peers.keys():
                # Convert peer URL to API endpoint
                if peer_url.startswith('http'):
                    api_base = f"{peer_url.rstrip('/')}:3142"
                else:
                    # Assume it's an IP:port format
                    api_base = f"http://{peer_url}"

                # Test API health
                try:
                    response = requests.get(f"{api_base}/api/{self.api_version}/health",
                                          timeout=5)
                    if response.status_code == 200:
                        endpoints.append(api_base)
                        logger.info(f"✅ Found active API endpoint: {api_base}")
                except:
                    continue

        except Exception as e:
            logger.warning(f"Peer discovery failed: {e}")

        # Fallback to known endpoints if discovery fails
        if not endpoints:
            endpoints = [
                "http://localhost:3142",  # Local development
                "http://pisecure-node.local:3142",  # mDNS discovery
            ]
            logger.info("Using fallback API endpoints")

        return endpoints

    def _get_api_url(self, endpoint: str) -> str:
        """Get full API URL with load balancing."""
        if not self.api_endpoints:
            raise ConnectionError("No available API endpoints")

        # Simple load balancing - rotate through endpoints
        base_url = random.choice(self.api_endpoints)
        return urljoin(base_url + '/', f'api/{self.api_version}/{endpoint.lstrip("/")}')

    def _make_request(self, method: str, endpoint: str,
                     data: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request data for POST/PUT
            **kwargs: Additional request parameters

        Returns:
            Response data as dictionary

        Raises:
            ConnectionError: If all endpoints fail
            ValueError: If API returns error
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                url = self._get_api_url(endpoint)
                logger.debug(f"{method} {url}")

                if data:
                    response = self.session.request(method, url, json=data, **kwargs)
                else:
                    response = self.session.request(method, url, **kwargs)

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

                # Try next endpoint
                if attempt < self.max_retries - 1:
                    continue

            except json.JSONDecodeError as e:
                last_error = e
                logger.error(f"Invalid JSON response: {e}")

        # All retries failed
        raise ConnectionError(f"Failed to connect to PiSecure API after {self.max_retries} attempts: {last_error}")

    # Blockchain Operations

    def get_blockchain_info(self) -> Dict[str, Any]:
        """
        Get comprehensive blockchain information.

        Returns:
            Dictionary containing blockchain status
        """
        return self._make_request('GET', 'blockchain/info')

    def get_block(self, block_index: int) -> Dict[str, Any]:
        """
        Get specific block by index.

        Args:
            block_index: Block index to retrieve

        Returns:
            Block data
        """
        return self._make_request('GET', f'blockchain/block/{block_index}')

    def get_blocks(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Get latest blocks with pagination.

        Args:
            limit: Maximum number of blocks to return (max 100)
            offset: Block offset for pagination

        Returns:
            List of block data
        """
        params = {'limit': min(limit, 100), 'offset': offset}
        response = self._make_request('GET', 'blockchain/blocks', params=params)
        return response if isinstance(response, list) else []

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data
        """
        return self._make_request('GET', f'blockchain/transaction/{tx_hash}')

    # Wallet Operations

    def get_wallet_balance(self, address: str) -> float:
        """
        Get wallet balance by address.

        Args:
            address: Wallet address

        Returns:
            Balance in tokens
        """
        response = self._make_request('GET', f'wallet/{address}/balance')
        return float(response.get('balance', 0))

    def get_wallet_transactions(self, address: str, limit: int = 20) -> List[Dict]:
        """
        Get transaction history for wallet.

        Args:
            address: Wallet address
            limit: Maximum transactions to return

        Returns:
            List of transactions
        """
        response = self._make_request('GET', f'wallet/{address}/transactions',
                                    params={'limit': min(limit, 100)})
        return response.get('transactions', [])

    def create_wallet(self, name: Optional[str] = None,
                     display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new wallet.

        Args:
            name: Wallet name (auto-generated if None)
            display_name: Human-readable display name

        Returns:
            Wallet creation result
        """
        data = {}
        if name:
            data['name'] = name
        if display_name:
            data['display_name'] = display_name

        return self._make_request('POST', 'wallet', data=data)

    def list_wallets(self) -> List[Dict]:
        """
        List available wallets.

        Returns:
            List of wallet information
        """
        response = self._make_request('GET', 'wallets')
        return response.get('wallets', [])

    # Transaction Operations

    def submit_transaction(self, tx_data: Dict[str, Any]) -> str:
        """
        Submit transaction to the blockchain.

        Args:
            tx_data: Transaction data dictionary

        Returns:
            Transaction hash
        """
        response = self._make_request('POST', 'transaction', data=tx_data)
        return response.get('transaction_hash', '')

    def create_transfer_transaction(self, from_wallet: str, to_address: str,
                                  amount: float, memo: str = "") -> Dict[str, Any]:
        """
        Create a transfer transaction (helper method).

        Args:
            from_wallet: Source wallet name/ID
            to_address: Destination address
            amount: Amount to transfer
            memo: Optional transaction memo

        Returns:
            Transaction data ready for submission
        """
        transaction = {
            'type': 'transfer',
            'from_wallet': from_wallet,
            'to_address': to_address,
            'amount': amount,
            'memo': memo,
            'timestamp': time.time(),
            'data': {
                'recipient': to_address,
                'amount': amount,
                'memo': memo
            }
        }

        # Note: In a real implementation, this would be signed
        # For now, return unsigned transaction
        return transaction

    # Network Operations

    def get_network_status(self) -> Dict[str, Any]:
        """
        Get network status and peer information.

        Returns:
            Network status data
        """
        return self._make_request('GET', 'network/status')

    def get_network_peers(self) -> List[str]:
        """
        Get list of known network peers.

        Returns:
            List of peer addresses
        """
        response = self._make_request('GET', 'network/peers')
        return response.get('peers', [])

    # Update Operations

    def verify_update(self, manifest: Dict[str, Any],
                     signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify update package signatures.

        Args:
            manifest: Update manifest
            signatures: List of signatures

        Returns:
            Verification result
        """
        data = {
            'manifest': manifest,
            'signatures': signatures
        }
        return self._make_request('POST', 'update/verify', data=data)

    # Utility Methods

    def get_api_docs(self) -> Dict[str, Any]:
        """
        Get API documentation.

        Returns:
            API documentation
        """
        return self._make_request('GET', 'docs')

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on connected nodes.

        Returns:
            Health status
        """
        return self._make_request('GET', 'health')

    def refresh_peers(self):
        """Refresh peer discovery and API endpoints."""
        self.api_endpoints = self._discover_api_endpoints()
        logger.info(f"Refreshed API endpoints: {len(self.api_endpoints)} available")


# Convenience functions for quick usage

def get_balance(address: str) -> float:
    """
    Quick function to get wallet balance.

    Args:
        address: Wallet address

    Returns:
        Balance in tokens
    """
    client = PiSecureClient()
    return client.get_wallet_balance(address)


def submit_tx(tx_data: Dict[str, Any]) -> str:
    """
    Quick function to submit transaction.

    Args:
        tx_data: Transaction data

    Returns:
        Transaction hash
    """
    client = PiSecureClient()
    return client.submit_transaction(tx_data)


# Example usage and testing
if __name__ == '__main__':
    # Example usage
    client = PiSecureClient()

    try:
        # Health check
        health = client.health_check()
        print(f"✅ API Health: {health}")

        # Get blockchain info
        info = client.get_blockchain_info()
        print(f"📊 Blockchain: {info['blocks']} blocks, {info['pending_transactions']} pending TX")

        # Get network status
        network = client.get_network_status()
        print(f"🌐 Network: {network['connected_peers']} peers")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure a PiSecure API server is running on port 3142")