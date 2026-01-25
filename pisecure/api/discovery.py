"""
PiSecure Peer Discovery
=======================

Decentralized peer discovery system for PiSecure blockchain network.
Automatically discovers available nodes and API endpoints for client
applications to connect to.

Features:
- Bootstrap peer lists for initial discovery
- DHT-based peer discovery (future)
- mDNS/local network discovery
- Peer health monitoring and ranking
- Automatic failover and load balancing

This module ensures that client applications can always find available
PiSecure nodes without manual configuration.
"""

import time
import json
import requests
import logging
import socket
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urljoin
import hashlib
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeerDiscovery:
    """
    Decentralized peer discovery for PiSecure network.

    Maintains a list of known peers and their capabilities,
    automatically discovering new peers and pruning unhealthy ones.
    """

    def __init__(self, bootstrap_peers: Optional[List[str]] = None,
                 cache_file: str = "/tmp/pisecure_peers.json",
                 peer_timeout: int = 30):
        """
        Initialize peer discovery.

        Args:
            bootstrap_peers: List of bootstrap peer URLs
            cache_file: File to cache discovered peers
            peer_timeout: Timeout for peer health checks
        """
        self.bootstrap_peers = bootstrap_peers or []
        self.cache_file = cache_file
        self.peer_timeout = peer_timeout

        # Generate unique node ID for this client
        self.node_id = str(uuid.uuid4())

        # Peer storage: {peer_url: peer_info}
        self.known_peers: Dict[str, Dict[str, Any]] = {}
        self.connected_peers: Set[str] = set()

        # Load cached peers
        self._load_peer_cache()

        # Discover initial peers
        if not self.known_peers:
            self._bootstrap_discovery()

    def _load_peer_cache(self):
        """Load previously discovered peers from cache."""
        try:
            if hasattr(self, 'cache_file') and self.cache_file:
                with open(self.cache_file, 'r') as f:
                    cached_data = json.load(f)

                    # Check if cache is recent (within 24 hours)
                    if time.time() - cached_data.get('timestamp', 0) < 86400:
                        self.known_peers = cached_data.get('peers', {})
                        logger.info(f"Loaded {len(self.known_peers)} peers from cache")

        except (FileNotFoundError, json.JSONDecodeError):
            pass  # No cache or invalid cache

    def _save_peer_cache(self):
        """Save discovered peers to cache."""
        try:
            if self.cache_file:
                cache_data = {
                    'timestamp': time.time(),
                    'peers': self.known_peers
                }
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save peer cache: {e}")

    def _bootstrap_discovery(self):
        """Initial peer discovery from bootstrap sources."""
        logger.info("Starting bootstrap peer discovery...")

        # Try bootstrap URLs
        for bootstrap_url in self.bootstrap_peers:
            try:
                response = requests.get(bootstrap_url, timeout=10)
                if response.status_code == 200:
                    peer_data = response.json()

                    # Handle different peer list formats
                    if isinstance(peer_data, list):
                        peers = peer_data
                    elif isinstance(peer_data, dict) and 'peers' in peer_data:
                        peers = peer_data['peers']
                    else:
                        continue

                    # Add discovered peers
                    for peer_info in peers:
                        if isinstance(peer_info, str):
                            # Simple URL format
                            self._add_peer(peer_info, {'source': 'bootstrap'})
                        elif isinstance(peer_info, dict):
                            # Extended peer info
                            peer_url = peer_info.get('url') or peer_info.get('address')
                            if peer_url:
                                self._add_peer(peer_url, peer_info)

                    logger.info(f"Discovered {len(peers)} peers from {bootstrap_url}")

            except Exception as e:
                logger.warning(f"Failed to fetch bootstrap peers from {bootstrap_url}: {e}")

        # Try local network discovery
        self._local_network_discovery()

        # Save discovered peers
        self._save_peer_cache()

    def _local_network_discovery(self):
        """Discover peers on local network using mDNS and common ports."""
        logger.info("Scanning local network for PiSecure nodes...")

        # Common PiSecure ports
        ports_to_check = [3141, 3142, 5000, 80]

        # Get local IP range (rough approximation)
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Get subnet (first 3 octets)
            ip_parts = local_ip.split('.')
            subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."

            # Scan common local IPs (not recommended for production)
            # This is a simplified version - real implementation would use proper network scanning
            for i in range(100, 110):  # Check .100-.109
                ip = f"{subnet}{i}"
                for port in ports_to_check:
                    try:
                        # Quick connection test
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((ip, port))
                        sock.close()

                        if result == 0:
                            peer_url = f"http://{ip}:{port}"
                            self._add_peer(peer_url, {
                                'source': 'local_scan',
                                'ip': ip,
                                'port': port
                            })
                            logger.info(f"Found local peer: {peer_url}")

                    except:
                        continue

        except Exception as e:
            logger.debug(f"Local network discovery failed: {e}")

    def _add_peer(self, peer_url: str, peer_info: Optional[Dict[str, Any]] = None):
        """
        Add a peer to the known peers list.

        Args:
            peer_url: Peer URL or address
            peer_info: Additional peer information
        """
        if not peer_url:
            return

        # Normalize URL
        if not peer_url.startswith(('http://', 'https://')):
            peer_url = f"http://{peer_url}"

        # Initialize peer info
        if peer_url not in self.known_peers:
            self.known_peers[peer_url] = {
                'url': peer_url,
                'added_at': time.time(),
                'last_seen': 0,
                'health_score': 0,
                'response_time': 0,
                'capabilities': [],
                'source': 'unknown'
            }

        # Update peer info
        if peer_info:
            self.known_peers[peer_url].update(peer_info)

    def _check_peer_health(self, peer_url: str) -> Dict[str, Any]:
        """
        Check health of a specific peer.

        Args:
            peer_url: Peer URL to check

        Returns:
            Health check results
        """
        health_info = {
            'healthy': False,
            'response_time': 0,
            'capabilities': [],
            'error': None
        }

        try:
            start_time = time.time()

            # Try health check endpoint
            health_url = urljoin(peer_url + '/', 'api/v1/health')
            response = requests.get(health_url, timeout=self.peer_timeout)

            response_time = time.time() - start_time

            if response.status_code == 200:
                health_data = response.json()
                health_info.update({
                    'healthy': True,
                    'response_time': response_time,
                    'capabilities': ['api'],  # Basic API capability
                    'version': health_data.get('version', 'unknown')
                })

                # Check for additional capabilities
                if self._check_api_capabilities(peer_url):
                    health_info['capabilities'].append('full_api')

        except requests.exceptions.Timeout:
            health_info['error'] = 'timeout'
        except requests.exceptions.ConnectionError:
            health_info['error'] = 'connection_failed'
        except Exception as e:
            health_info['error'] = str(e)

        return health_info

    def _check_api_capabilities(self, peer_url: str) -> bool:
        """
        Check if peer supports full API capabilities.

        Args:
            peer_url: Peer URL to check

        Returns:
            True if full API is supported
        """
        try:
            docs_url = urljoin(peer_url + '/', 'api/v1/docs')
            response = requests.get(docs_url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def update_peer_health(self):
        """Update health status of all known peers."""
        logger.info(f"Checking health of {len(self.known_peers)} peers...")

        healthy_count = 0

        for peer_url, peer_info in list(self.known_peers.items()):
            health = self._check_peer_health(peer_url)

            if health['healthy']:
                # Update peer info with health data
                peer_info.update({
                    'last_seen': time.time(),
                    'response_time': health['response_time'],
                    'capabilities': health['capabilities'],
                    'health_score': min(100, peer_info.get('health_score', 0) + 10)
                })
                healthy_count += 1
            else:
                # Reduce health score for unhealthy peers
                peer_info['health_score'] = max(0, peer_info.get('health_score', 0) - 20)

                # Remove peers with very low health scores
                if peer_info['health_score'] <= 0:
                    logger.info(f"Removing unhealthy peer: {peer_url}")
                    del self.known_peers[peer_url]

        logger.info(f"Health check complete: {healthy_count} healthy peers")

        # Save updated peer cache
        self._save_peer_cache()

    def get_known_peers(self, min_health: int = 0) -> Dict[str, Dict]:
        """
        Get all known peers, optionally filtered by health score.

        Args:
            min_health: Minimum health score required

        Returns:
            Dictionary of peer URLs to peer info
        """
        if min_health > 0:
            return {
                url: info for url, info in self.known_peers.items()
                if info.get('health_score', 0) >= min_health
            }
        return self.known_peers.copy()

    def get_healthy_peers(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of healthy peer URLs, sorted by health score.

        Args:
            limit: Maximum number of peers to return

        Returns:
            List of healthy peer URLs
        """
        healthy_peers = [
            (url, info.get('health_score', 0))
            for url, info in self.known_peers.items()
            if info.get('health_score', 0) > 50  # Consider healthy if score > 50
        ]

        # Sort by health score (highest first)
        healthy_peers.sort(key=lambda x: x[1], reverse=True)

        # Return URLs only
        peer_urls = [url for url, score in healthy_peers]

        if limit:
            return peer_urls[:limit]

        return peer_urls

    def get_connected_peers(self) -> Set[str]:
        """
        Get set of currently connected peer URLs.

        Returns:
            Set of connected peer URLs
        """
        return self.connected_peers.copy()

    def add_peer(self, peer_url: str, peer_info: Optional[Dict[str, Any]] = None):
        """
        Manually add a peer.

        Args:
            peer_url: Peer URL to add
            peer_info: Additional peer information
        """
        self._add_peer(peer_url, peer_info)
        self._save_peer_cache()

    def remove_peer(self, peer_url: str):
        """
        Remove a peer from known peers.

        Args:
            peer_url: Peer URL to remove
        """
        if peer_url in self.known_peers:
            del self.known_peers[peer_url]
            self._save_peer_cache()
            logger.info(f"Removed peer: {peer_url}")

    def discover_peers_from_peer(self, peer_url: str):
        """
        Ask a peer for its known peers (peer exchange).

        Args:
            peer_url: Peer to query for additional peers
        """
        try:
            peers_url = urljoin(peer_url + '/', 'api/v1/network/peers')
            response = requests.get(peers_url, timeout=10)

            if response.status_code == 200:
                peer_data = response.json()
                known_peers = peer_data.get('peers', [])

                new_peers = 0
                for peer_addr in known_peers:
                    if peer_addr not in self.known_peers:
                        self._add_peer(peer_addr, {'source': f'peer_exchange:{peer_url}'})
                        new_peers += 1

                if new_peers > 0:
                    logger.info(f"Discovered {new_peers} new peers from {peer_url}")
                    self._save_peer_cache()

        except Exception as e:
            logger.debug(f"Peer exchange failed for {peer_url}: {e}")

    def refresh_discovery(self):
        """Perform full peer discovery refresh."""
        logger.info("Refreshing peer discovery...")

        # Update health of existing peers
        self.update_peer_health()

        # Try to discover new peers from existing healthy peers
        healthy_peers = self.get_healthy_peers(limit=5)  # Query top 5 healthy peers

        for peer_url in healthy_peers:
            self.discover_peers_from_peer(peer_url)

        # Re-run bootstrap if we have very few peers
        if len(self.known_peers) < 5:
            self._bootstrap_discovery()

        logger.info(f"Discovery refresh complete: {len(self.known_peers)} known peers")


# Utility functions

def find_nearest_pisecure_node() -> Optional[str]:
    """
    Find the nearest PiSecure API node.

    Returns:
        URL of nearest node, or None if not found
    """
    discovery = PeerDiscovery()
    healthy_peers = discovery.get_healthy_peers(limit=1)

    if healthy_peers:
        # Convert peer URL to API endpoint
        peer_url = healthy_peers[0]
        if peer_url.startswith('http'):
            return f"{peer_url.rstrip('/')}:3142"
        else:
            return f"http://{peer_url}"

    return None


def get_network_stats() -> Dict[str, Any]:
    """
    Get network-wide statistics.

    Returns:
        Network statistics
    """
    discovery = PeerDiscovery()

    peers = discovery.get_known_peers()
    healthy_peers = discovery.get_healthy_peers()

    return {
        'total_known_peers': len(peers),
        'healthy_peers': len(healthy_peers),
        'network_health_score': len(healthy_peers) / max(1, len(peers)) * 100,
        'last_updated': time.time()
    }


# Example usage
if __name__ == '__main__':
    # Initialize peer discovery
    discovery = PeerDiscovery()

    print(f"Node ID: {discovery.node_id}")
    print(f"Known peers: {len(discovery.get_known_peers())}")
    print(f"Healthy peers: {len(discovery.get_healthy_peers())}")

    # Perform health check
    discovery.update_peer_health()

    # Show healthy peers
    healthy = discovery.get_healthy_peers(limit=5)
    print(f"Top healthy peers: {healthy}")

    # Network stats
    stats = get_network_stats()
    print(f"Network stats: {stats}")