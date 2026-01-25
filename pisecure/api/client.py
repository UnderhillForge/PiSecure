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
import os
import json
import requests
import logging
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
import random

from .discovery import PeerDiscovery

try:
    # Try relative imports first (for package installation)
    from ..core.nat_traversal import node_discovery
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core.nat_traversal import node_discovery

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
                 max_retries: int = 3, enable_peer_exchange: bool = False):
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
        self.enable_peer_exchange = enable_peer_exchange

        # Initialize peer discovery with known bootstrap nodes
        # Note: PiSecure bootstrap system uses intelligent handshake and registry
        # rather than static peer files. We'll use known bootstrap endpoints.
        default_bootstrap_endpoints = [
            "https://bootstrap.pisecure.org",  # Primary bootstrap server
            "https://bootstrap-secondary-01.pisecure.org",  # Secondary if available
        ]

        # Use provided endpoints or defaults
        self.bootstrap_endpoints = bootstrap_peers or default_bootstrap_endpoints

        # Initialize peer discovery for local peer management and caching
        self.peer_discovery = PeerDiscovery()

        # Discover available API endpoints
        self.api_endpoints = self._discover_api_endpoints()

        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.timeout = timeout

    def _discover_api_endpoints(self) -> List[str]:
        """Discover available API endpoints using multiple bootstrap methods."""
        endpoints = []

        # Method 1: Try static peers.json from bootstrap servers
        try:
            logger.info("🔍 Trying static peer discovery from bootstrap servers...")

            for bootstrap_url in self.bootstrap_endpoints:
                try:
                    # Try the static peers.json endpoint
                    peers_url = f"{bootstrap_url}/peers.json"
                    response = requests.get(peers_url, timeout=5)

                    if response.status_code == 200:
                        peer_list = response.json()
                        logger.info(f"✅ Retrieved {len(peer_list)} peers from {bootstrap_url}")

                        # Process peer list and save to cache
                        bootstrap_peers = self._process_static_peer_list(peer_list, bootstrap_url)

                        # Test each peer for API availability
                        for peer_url in bootstrap_peers:
                            try:
                                response = requests.get(f"{peer_url}/api/{self.api_version}/health", timeout=3)
                                if response.status_code == 200:
                                    endpoints.append(peer_url)
                                    logger.info(f"✅ Active peer: {peer_url}")
                            except:
                                continue

                        if endpoints:
                            break  # Found working peers, no need to try other bootstrap servers

                except Exception as e:
                    logger.debug(f"Static peer discovery failed for {bootstrap_url}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Static peer discovery failed: {e}")

        # Method 2: Try intelligent bootstrap API
        if not endpoints:
            try:
                logger.info("🔍 Trying intelligent bootstrap API...")

                for bootstrap_url in self.bootstrap_endpoints:
                    try:
                        # Try the intelligent peers endpoint
                        peers_response = self._get_bootstrap_peers(bootstrap_url)
                        if peers_response and "peers" in peers_response:
                            peer_list = peers_response["peers"]

                            # Process intelligent peer list
                            intelligent_peers = self._process_intelligent_peer_list(peer_list)

                            # Test each peer
                            for peer_url in intelligent_peers:
                                try:
                                    response = requests.get(f"{peer_url}/api/{self.api_version}/health", timeout=3)
                                    if response.status_code == 200:
                                        endpoints.append(peer_url)
                                        logger.info(f"✅ Active intelligent peer: {peer_url}")
                                except:
                                    continue

                            if endpoints:
                                break

                    except Exception as e:
                        logger.debug(f"Intelligent peer discovery failed for {bootstrap_url}: {e}")
                        continue

            except Exception as e:
                logger.debug(f"Intelligent peer discovery failed: {e}")

            # Special handling: Add bootstrap URLs themselves as API endpoints
            # (bootstrap servers support /api/v1/ endpoints directly)
            if not endpoints:
                for bootstrap_url in self.bootstrap_endpoints:
                    try:
                        # Try health check on bootstrap itself
                        response = requests.get(f"{bootstrap_url}/api/{self.api_version}/health", timeout=5)
                        if response.status_code == 200:
                            endpoints.append(bootstrap_url)
                            logger.info(f"✅ Using bootstrap server directly: {bootstrap_url}")
                    except Exception as e:
                        logger.debug(f"Bootstrap health check failed for {bootstrap_url}: {e}")

        # Method 3: Try local peer cache as fallback
        if not endpoints:
            try:
                logger.info("🔄 Bootstrap unavailable, trying local peer cache...")
                cached_peers = self.peer_discovery.get_known_peers()

                for peer_id, peer_info in cached_peers.items():
                    peer_url = peer_info.get('address', '')
                    if peer_url.startswith('http'):
                        api_base = f"{peer_url.rstrip('/')}:3142"
                    else:
                        api_base = f"http://{peer_url}:3142"

                    try:
                        response = requests.get(f"{api_base}/api/{self.api_version}/health", timeout=2)
                        if response.status_code == 200:
                            endpoints.append(api_base)
                            logger.info(f"✅ Active cached peer: {api_base}")
                    except:
                        continue

            except Exception as e:
                logger.debug(f"Local peer cache discovery failed: {e}")

        # Method 4: Final fallback to development endpoints
        if not endpoints:
            endpoints = [
                "http://localhost:3142",  # Local development
                "http://pisecure-node.local:3142",  # mDNS discovery
            ]
            logger.info("⚠️ Using development fallback endpoints - network may be unavailable")

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
                result = response.json()

                # Successful request - optionally exchange peers with this node
                if self.enable_peer_exchange:
                    try:
                        self.exchange_peers(url.replace('/api/v1/', ''))  # Remove API path to get base URL
                    except Exception as e:
                        logger.debug(f"Peer exchange failed after successful request: {e}")

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

                # Try next endpoint
                if attempt < self.max_retries - 1:
                    continue

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
    def get_mempool(self, network: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch pending transactions (mempool) from the network.

        Args:
            network: Network identifier (e.g., "mainnet", "testnet"). If None, attempts to infer.
            limit: Optional maximum number of transactions to return (server may cap).

        Returns:
            Dictionary with mempool summary: {network, pending_count, pending, timestamp}
        """
        params = {}
        try:
            if network:
                params['network'] = network
            else:
                # Attempt to infer network from environment or blockchain info
                env_net = None
                try:
                    env_net = os.environ.get('PISECURE_TESTNET')
                except Exception:
                    env_net = None
                if env_net:
                    params['network'] = 'testnet' if env_net in ('1', 'true', 'True') else 'mainnet'
            if limit is not None:
                params['limit'] = int(limit)
        except Exception:
            # Fallback: no params
            params = {}

        response = self._make_request('GET', 'mempool', params=params)
        # Normalize shape
        if isinstance(response, dict):
            if 'pending' not in response and 'transactions' in response:
                response['pending'] = response.get('transactions', [])
                response['pending_count'] = len(response['pending'])
            if 'pending_count' not in response and 'pending' in response:
                response['pending_count'] = len(response.get('pending', []))
        return response

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

    # Bootstrap System Integration

    def bootstrap_handshake(self, node_id: str, services: List[str] = None,
                           capabilities: List[str] = None, region: str = "unknown") -> Dict[str, Any]:
        """
        Perform bootstrap handshake with bootstrap nodes.

        Args:
            node_id: Unique node identifier
            services: List of services provided
            capabilities: List of node capabilities
            region: Geographic region

        Returns:
            Handshake result
        """
        if services is None:
            services = ["p2p_sync"]
        if capabilities is None:
            capabilities = ["blockchain_sync"]

        handshake_data = {
            "node_id": node_id,
            "address": "127.0.0.1",  # Will be detected by bootstrap
            "port": 3142,
            "services": services,
            "capabilities": capabilities,
            "region": region,
            "version": "0.1.0",
            "reliability_score": 0.95,
            "load_factor": 0.2
        }

        # Try handshake with each bootstrap endpoint
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.post(
                    f"{bootstrap_url}/api/{self.api_version}/bootstrap/handshake",
                    json=handshake_data,
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Bootstrap handshake successful with {bootstrap_url}")

                    # Save bootstrap node to local peer cache for future fallback
                    self._save_bootstrap_to_peer_cache(bootstrap_url)

                    return result
            except Exception as e:
                logger.debug(f"Bootstrap handshake failed with {bootstrap_url}: {e}")
                continue

        logger.warning("All bootstrap handshake attempts failed")
        return {"handshake_accepted": False, "error": "No bootstrap nodes available"}

    def get_bootstrap_registry(self) -> Dict[str, Any]:
        """
        Get the bootstrap node registry.

        Returns:
            Bootstrap registry data
        """
        # Try each bootstrap endpoint
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.get(
                    f"{bootstrap_url}/api/{self.api_version}/bootstrap/registry",
                    timeout=10
                )
                if response.status_code == 200:
                    registry = response.json()
                    logger.info(f"✅ Retrieved bootstrap registry from {bootstrap_url}")
                    return registry
            except Exception as e:
                logger.debug(f"Failed to get registry from {bootstrap_url}: {e}")
                continue

        logger.warning("Failed to retrieve bootstrap registry")
        return {"error": "No bootstrap nodes available"}

    def get_network_intelligence(self, service_type: str = "p2p_sync") -> Dict[str, Any]:
        """
        Get network intelligence for optimal peer routing.

        Args:
            service_type: Type of service needed

        Returns:
            Intelligence data for routing optimization
        """
        available_nodes = []

        # Get active peers from bootstrap registry
        registry = self.get_bootstrap_registry()
        if "secondary_nodes" in registry:
            for node in registry["secondary_nodes"]:
                available_nodes.append({
                    "node_id": node["node_id"],
                    "location": node.get("region", "unknown"),
                    "load_factor": node.get("load_factor", 0.5),
                    "reliability_score": node.get("reliability_score", 0.5)
                })

        if not available_nodes:
            return {"error": "No nodes available for intelligence"}

        # Request routing optimization
        intelligence_request = {
            "available_nodes": available_nodes,
            "service_type": service_type
        }

        # Try intelligence API on bootstrap nodes
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.post(
                    f"{bootstrap_url}/api/{self.api_version}/intelligence/optimize",
                    json=intelligence_request,
                    timeout=10
                )
                if response.status_code == 200:
                    intelligence = response.json()
                    logger.info(f"✅ Retrieved network intelligence from {bootstrap_url}")
                    return intelligence
            except Exception as e:
                logger.debug(f"Intelligence request failed with {bootstrap_url}: {e}")
                continue

        logger.warning("Failed to retrieve network intelligence")
        return {"error": "Intelligence service unavailable"}

    def advertise_services(self, node_id: str, services: List[str],
                          status: str = "active") -> Dict[str, Any]:
        """
        Advertise node services to bootstrap network.

        Args:
            node_id: Node identifier
            services: Services to advertise
            status: Node status

        Returns:
            Advertisement result
        """
        advertise_data = {
            "node_id": node_id,
            "services": services,
            "status": status,
            "load_factor": 0.2,
            "current_connections": 1,
            "health_metrics": {
                "cpu_usage": 15.0,
                "memory_usage": 45.0,
                "network_latency": 25.0
            },
            "service_endpoints": {
                "p2p_sync": "/api/v1/blockchain/info",
                "health_check": "/api/v1/health"
            }
        }

        # Try advertisement with each bootstrap endpoint
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.post(
                    f"{bootstrap_url}/api/{self.api_version}/bootstrap/advertise",
                    json=advertise_data,
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Service advertisement successful with {bootstrap_url}")
                    return result
            except Exception as e:
                logger.debug(f"Service advertisement failed with {bootstrap_url}: {e}")
                continue

        logger.warning("All service advertisement attempts failed")
        return {"advertisement_accepted": False, "error": "No bootstrap nodes available"}

    # Peer Caching and Fallback Methods

    def _save_bootstrap_to_peer_cache(self, bootstrap_url: str):
        """Save bootstrap server to local peer cache for fallback."""
        try:
            # Extract domain from bootstrap URL
            from urllib.parse import urlparse
            parsed = urlparse(bootstrap_url)
            bootstrap_domain = parsed.netloc

            # Save bootstrap server as a peer
            peer_id = f"bootstrap_{bootstrap_domain.replace('.', '_')}"
            self.peer_discovery.add_peer(
                peer_id=peer_id,
                address=bootstrap_domain,
                port=443 if parsed.scheme == 'https' else 80
            )

            logger.debug(f"💾 Saved bootstrap server to cache: {bootstrap_domain}")

        except Exception as e:
            logger.debug(f"Failed to save bootstrap to cache: {e}")

    def _save_registry_peers_to_cache(self, registry: Dict[str, Any]):
        """Save peers from bootstrap registry to local cache."""
        try:
            if "secondary_nodes" not in registry:
                return

            saved_count = 0
            for node in registry["secondary_nodes"]:
                if node.get("status") == "active" and node.get("address"):
                    node_address = node["address"]
                    node_id = node.get("node_id", f"registry_peer_{saved_count}")

                    # Save to peer discovery cache
                    self.peer_discovery.add_peer(
                        peer_id=node_id,
                        address=node_address,
                        port=3142  # Standard PiSecure port
                    )

                    saved_count += 1

            if saved_count > 0:
                logger.debug(f"💾 Saved {saved_count} registry peers to local cache")

        except Exception as e:
            logger.debug(f"Failed to save registry peers to cache: {e}")

    def _save_peer_to_cache(self, peer_url: str, peer_id: str = None):
        """Save successfully connected peer to local cache."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(peer_url)

            # Generate peer ID if not provided
            if not peer_id:
                peer_id = f"discovered_{parsed.hostname}_{int(time.time())}"

            # Save peer to discovery cache
            self.peer_discovery.add_peer(
                peer_id=peer_id,
                address=parsed.hostname,
                port=parsed.port or 3142
            )

            logger.debug(f"💾 Saved active peer to cache: {parsed.hostname}")

        except Exception as e:
            logger.debug(f"Failed to save peer to cache: {e}")

    def get_cached_peers(self) -> Dict[str, Dict]:
        """Get all cached peers for inspection."""
        return self.peer_discovery.get_known_peers()

    def clear_peer_cache(self):
        """Clear local peer cache (useful for testing or reset)."""
        try:
            self.peer_discovery.clear_cache()
            logger.info("🗑️ Cleared peer cache")
        except Exception as e:
            logger.error(f"Failed to clear peer cache: {e}")

    def exchange_peers(self, connected_peer_url: str):
        """
        Exchange peer lists with a connected peer to build local cache.

        Args:
            connected_peer_url: URL of peer to exchange with
        """
        try:
            # Get peer list from connected peer
            response = requests.get(f"{connected_peer_url}/api/{self.api_version}/network/peers",
                                  timeout=5)

            if response.status_code == 200:
                peer_data = response.json()
                known_peers = peer_data.get('peers', [])

                # Save new peers to local cache
                saved_count = 0
                for peer_addr in known_peers:
                    if peer_addr and peer_addr != "127.0.0.1:3142":  # Skip self
                        peer_id = f"exchanged_{peer_addr.replace(':', '_')}_{int(time.time())}"
                        self.peer_discovery.add_peer(
                            peer_id=peer_id,
                            address=peer_addr.split(':')[0],
                            port=int(peer_addr.split(':')[1]) if ':' in peer_addr else 3142
                        )
                        saved_count += 1

                if saved_count > 0:
                    logger.debug(f"🔄 Exchanged {saved_count} peers with {connected_peer_url}")

        except Exception as e:
            logger.debug(f"Peer exchange failed with {connected_peer_url}: {e}")

    def _process_static_peer_list(self, peer_list: List[Dict], bootstrap_url: str) -> List[str]:
        """Process static peer list from /peers.json and return API endpoints."""
        api_endpoints = []

        for peer in peer_list:
            # Handle direct bootstrap nodes
            if 'host' in peer and 'port' in peer:
                host = peer['host']
                port = peer['port']
                api_endpoints.append(f"http://{host}:{port}")

                # Save to local cache
                peer_id = f"static_{host.replace('.', '_')}"
                self.peer_discovery.add_peer(peer_id=peer_id, address=host, port=port)

            # Handle dynamic peer sources (like GitHub fallback)
            elif 'url' in peer and peer.get('type') == 'dynamic':
                try:
                    # Try to fetch dynamic peer list
                    dynamic_response = requests.get(peer['url'], timeout=5)
                    if dynamic_response.status_code == 200:
                        dynamic_peers = dynamic_response.json()
                        if isinstance(dynamic_peers, list):
                            # Recursively process dynamic peers
                            dynamic_endpoints = self._process_static_peer_list(dynamic_peers, peer['url'])
                            api_endpoints.extend(dynamic_endpoints)
                except Exception as e:
                    logger.debug(f"Failed to fetch dynamic peers from {peer['url']}: {e}")

        return api_endpoints

    def _process_intelligent_peer_list(self, peer_list: List[Dict]) -> List[str]:
        """Process intelligent peer list from /api/v1/bootstrap/peers."""
        api_endpoints = []

        for peer in peer_list:
            # Intelligent peers have filtering and scoring
            if peer.get('status') == 'active' and peer.get('address'):
                address = peer['address']
                port = peer.get('port', 3142)

                # Apply basic filtering (could be enhanced with ML scoring)
                reliability = peer.get('reliability_score', 0.5)
                load_factor = peer.get('load_factor', 0.5)

                # Only include reliable peers with reasonable load
                if reliability >= 0.3 and load_factor <= 0.8:
                    api_endpoints.append(f"http://{address}:{port}")

                    # Save to local cache with metadata
                    peer_id = peer.get('node_id', f"intelligent_{address.replace('.', '_')}")
                    self.peer_discovery.add_peer(peer_id=peer_id, address=address, port=port)

        return api_endpoints

    def _get_bootstrap_peers(self, bootstrap_url: str) -> Optional[Dict[str, Any]]:
        """Get peers from intelligent bootstrap API."""
        try:
            response = requests.get(f"{bootstrap_url}/api/{self.api_version}/bootstrap/peers", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Intelligent bootstrap peers request failed: {e}")
        return None

    def get_bootstrap_intelligence(self, intelligence_type: str = "attacks") -> Optional[Dict[str, Any]]:
        """Get intelligence data from bootstrap server"""
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.get(f"{bootstrap_url}/api/v1/intelligence/{intelligence_type}", timeout=10)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                continue
        return None

    def optimize_routing(self, available_nodes: List[Dict]) -> Optional[Dict[str, Any]]:
        """Get routing optimization from bootstrap server"""
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                response = requests.post(
                    f"{bootstrap_url}/api/v1/intelligence/optimize",
                    json={"available_nodes": available_nodes},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                continue
        return None

    def get_bootstrap_node_list(self, filters: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get registered nodes from bootstrap server"""
        for bootstrap_url in self.bootstrap_endpoints:
            try:
                url = f"{bootstrap_url}/api/v1/nodes/list"
                if filters:
                    params = '&'.join(f"{k}={v}" for k, v in filters.items())
                    url += f"?{params}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                continue
        return None


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