#!/usr/bin/env python3
"""
PiSecure Bootstrap Server Management
====================================

Robust bootstrap server discovery, registration, and status reporting system.
Handles dynamic bootstrap server discovery, health monitoring, and failover.
"""

import time
import json
import threading
import requests
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BootstrapRegistry:
    """
    Dynamic bootstrap server registry with health monitoring and discovery.

    Maintains a list of known bootstrap servers, tracks their health,
    and discovers new servers dynamically.
    """

    def __init__(self, registry_file: str = "/var/lib/pisecure/bootstrap_registry.json"):
        self.registry_file = Path(registry_file)
        self.bootstrap_servers: Dict[str, Dict[str, Any]] = {}
        self.peer_cache: Dict[str, Any] = {}
        self.cache_timeout = 1800  # 30 minutes
        self.health_check_interval = 300  # 5 minutes
        self._load_registry()
        self._initialize_default_servers()

    def _initialize_default_servers(self):
        """Initialize with known bootstrap servers"""
        default_servers = {
            "https://bootstrap.pisecure.org": {
                "priority": 1,
                "capabilities": ["register", "status", "peers", "registry"],
                "health_score": 1.0,
                "last_seen": time.time(),
                "consecutive_failures": 0,
                "total_requests": 0,
                "successful_requests": 0,
                "response_time": None,
                "source": "default"
            },
            "https://pisecure-bootstrap-production.up.railway.app": {
                "priority": 2,
                "capabilities": ["register", "status", "peers", "registry"],
                "health_score": 1.0,
                "last_seen": time.time(),
                "consecutive_failures": 0,
                "total_requests": 0,
                "successful_requests": 0,
                "response_time": None,
                "source": "default"
            }
        }

        for url, info in default_servers.items():
            if url not in self.bootstrap_servers:
                self.bootstrap_servers[url] = info

        self._save_registry()

    def _load_registry(self):
        """Load registry from disk"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    self.bootstrap_servers = data.get('servers', {})
                    self.peer_cache = data.get('peer_cache', {})
        except Exception as e:
            logger.warning(f"Failed to load bootstrap registry: {e}")

    def _save_registry(self):
        """Save registry to disk"""
        try:
            data = {
                'servers': self.bootstrap_servers,
                'peer_cache': self.peer_cache,
                'last_updated': time.time()
            }
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save bootstrap registry: {e}")

    def discover_bootstrap_servers(self) -> int:
        """
        Discover additional bootstrap servers from known healthy servers.

        Returns the number of new servers discovered.
        """
        discovered_count = 0
        healthy_servers = self.get_healthy_servers()

        for server_url in healthy_servers[:3]:  # Query top 3 healthy servers
            try:
                response = requests.get(
                    f"{server_url}/api/v1/bootstrap/registry",
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()

                    # Add secondary nodes to registry
                    for node_info in data.get('secondary_nodes', []):
                        node_url = node_info.get('address') or node_info.get('url')
                        if node_url and node_url not in self.bootstrap_servers:
                            self.bootstrap_servers[node_url] = {
                                "priority": 3,  # Lower priority for discovered servers
                                "capabilities": node_info.get('services', []),
                                "health_score": 0.8,  # Start with decent health
                                "last_seen": time.time(),
                                "consecutive_failures": 0,
                                "total_requests": 0,
                                "successful_requests": 0,
                                "response_time": None,
                                "region": node_info.get('region', 'unknown'),
                                "source": "discovered"
                            }
                            discovered_count += 1

                    self.update_server_health(server_url, success=True, response_time=response.elapsed.total_seconds())

            except Exception as e:
                logger.debug(f"Failed to discover from {server_url}: {e}")
                self.update_server_health(server_url, success=False)

        if discovered_count > 0:
            self._save_registry()
            logger.info(f"Discovered {discovered_count} new bootstrap servers")

        return discovered_count

    def update_server_health(self, url: str, success: bool, response_time: Optional[float] = None):
        """Update health metrics for a bootstrap server"""
        if url not in self.bootstrap_servers:
            return

        server = self.bootstrap_servers[url]
        server['total_requests'] += 1

        if success:
            server['successful_requests'] += 1
            server['last_seen'] = time.time()
            server['consecutive_failures'] = 0
            if response_time:
                server['response_time'] = response_time
        else:
            server['consecutive_failures'] += 1

        # Calculate health score
        if server['total_requests'] > 0:
            success_rate = server['successful_requests'] / server['total_requests']
            recency_factor = min(1.0, (time.time() - server['last_seen']) / (24 * 3600))  # 24 hour decay
            server['health_score'] = success_rate * (1 - recency_factor * 0.5)  # Health decays over time
        else:
            server['health_score'] = 0.5  # Default for new servers

        # Mark as inactive if too many failures or very low health
        server['is_active'] = server['health_score'] > 0.1 and server['consecutive_failures'] < 5

        self._save_registry()

    def get_healthy_servers(self) -> List[str]:
        """Get list of healthy bootstrap servers sorted by priority"""
        healthy = [
            url for url, info in self.bootstrap_servers.items()
            if info.get('is_active', True) and info['health_score'] > 0.3
        ]

        # Sort by priority (lower number first), then by health score
        healthy.sort(key=lambda url: (
            self.bootstrap_servers[url]['priority'],
            -self.bootstrap_servers[url]['health_score']
        ))

        return healthy

    def get_peer_list(self, limit: int = 50, network: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get peer list from healthy bootstrap servers.

        Returns a list of unique peers from all bootstrap servers.
        """
        peers = []

        for server_url in self.get_healthy_servers():
            try:
                # Check cache first
                cache_key = (server_url, network or 'default')
                cached = self.peer_cache.get(cache_key)
                if cached and time.time() - cached['timestamp'] < self.cache_timeout:
                    peers.extend(cached['peers'])
                    continue

                url = f"{server_url}/api/v1/bootstrap/peers"
                if network:
                    url = f"{url}?network={network}"
                response = requests.get(url, timeout=90)

                if response.status_code == 200:
                    data = response.json()
                    server_peers = data.get('peers', [])

                    # Cache the result (network-aware)
                    self.peer_cache[cache_key] = {
                        'peers': server_peers,
                        'timestamp': time.time()
                    }

                    peers.extend(server_peers)
                    self.update_server_health(server_url, success=True, response_time=response.elapsed.total_seconds())

            except Exception as e:
                logger.debug(f"Failed to get peers from {server_url}: {e}")
                self.update_server_health(server_url, success=False)

        # Remove duplicates based on address:port
        unique_peers = []
        seen = set()
        for peer in peers:
            peer_key = f"{peer.get('address')}:{peer.get('port')}"
            if peer_key not in seen:
                seen.add(peer_key)
                unique_peers.append(peer)

        return unique_peers[:limit]


class RobustMinerReporter:
    """
    Robust miner registration and status reporting with bootstrap failover.

    Handles miner registration with bootstrap servers and sends status reports
    with automatic failover and retry logic.
    """

    def __init__(self, bootstrap_registry: BootstrapRegistry, node_id: str):
        self.registry = bootstrap_registry
        self.node_id = node_id
        self.registered = False
        self.registration_attempts = 0
        self.last_registration_attempt = 0
        self.registration_cooldown = 300  # 5 minutes between registration attempts

    def ensure_registered(self) -> bool:
        """
        Ensure the miner is registered with at least one bootstrap server.

        Returns True if registered, False otherwise.
        """
        if self.registered:
            return True

        # Don't attempt registration too frequently
        if time.time() - self.last_registration_attempt < self.registration_cooldown:
            return self.registered

        self.last_registration_attempt = time.time()
        self.registration_attempts += 1

        registration_data = {
            "node_id": self.node_id,
            "node_type": "miner",
            "services": ["mining", "p2p_sync"],
            "capabilities": ["block_mining", "status_reporting"],
            "location": "unknown",  # Could be enhanced with geo detection
            "wallet_address": None,  # Set if available
            "version": "0.1.0"
        }

        healthy_servers = self.registry.get_healthy_servers()

        for server_url in healthy_servers:
            try:
                response = requests.post(
                    f"{server_url}/api/v1/nodes/register",
                    json=registration_data,
                    timeout=90  # Increased to handle 60-90s server response times
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('registration_success'):
                        self.registered = True
                        self.registry.update_server_health(server_url, success=True, response_time=response.elapsed.total_seconds())
                        logger.info(f"✅ Successfully registered with {server_url}")
                        return True

                self.registry.update_server_health(server_url, success=False)

            except Exception as e:
                logger.debug(f"Registration failed with {server_url}: {e}")
                self.registry.update_server_health(server_url, success=False)

        # Don't log warning on first attempt - registration is async
        if self.registration_attempts > 2:
            logger.warning(f"⚠️ Failed to register with bootstrap servers (attempt {self.registration_attempts})")
        return False

    def send_status_report(self, status_data: Dict[str, Any]) -> bool:
        """
        Send comprehensive status report to healthy bootstrap servers for intelligence processing.

        Includes all fields required for optimal network intelligence and 314ST rewards.
        Returns True if at least one server accepted the report.
        """
        if not self.registered:
            # Try to register first
            self.ensure_registered()

        # Calculate uptime percentage based on session start time
        uptime_percentage = 100.0  # Default for new sessions
        if status_data.get('session_start_time'):
            session_duration = time.time() - status_data['session_start_time']
            if session_duration > 0:
                # Assume 95% uptime minimum for established sessions
                uptime_percentage = min(100.0, 95.0 + (session_duration / 86400))  # Slight bonus for long sessions

        # Get actual peer count (would be passed from mining system)
        peers_connected = status_data.get('peers_connected', 0)

        # Syndicate membership (would be configurable)
        syndicate_membership = status_data.get('syndicate_membership')

        is_testnet = os.environ.get('PISECURE_TESTNET') == '1'
        status_payload = {
            # Required fields
            "node_id": self.node_id,
            "status": "active",
            "mining_active": status_data.get('mining_active', False),
            "hashrate": status_data.get('hashrate', 0),

            # Mining metrics for intelligence
            "blocks_mined": status_data.get('blocks_mined', 0),
            "peers_connected": peers_connected,
            "uptime_percentage": uptime_percentage,

            # Syndicate information (if applicable)
            "syndicate_membership": syndicate_membership,

            # System monitoring data
            "temperature": status_data.get('temperature'),
            "memory_usage": status_data.get('memory_usage'),

            # Session and identity data
            "session_start_time": status_data.get('session_start_time'),
            "wallet_address": status_data.get('wallet_address'),
            "location": status_data.get('location', 'unknown'),
            "hardware_model": status_data.get('hardware_model', 'unknown'),

            # Metadata
            "reported_at": time.time(),
            "intelligence_enabled": True,  # Indicate this report includes intelligence data
            "network": "testnet" if is_testnet else "mainnet"
        }

        # Remove None values to keep payload clean
        status_payload = {k: v for k, v in status_payload.items() if v is not None}

        healthy_servers = self.registry.get_healthy_servers()
        success_count = 0

        for server_url in healthy_servers[:3]:  # Try top 3 servers
            try:
                response = requests.post(
                    f"{server_url}/api/v1/nodes/status",
                    json=status_payload,
                    timeout=90  # Increased to handle 60-90s server response times
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('status_update_accepted'):
                        success_count += 1
                        self.registry.update_server_health(server_url, success=True, response_time=response.elapsed.total_seconds())
                    else:
                        self.registry.update_server_health(server_url, success=False)
                else:
                    self.registry.update_server_health(server_url, success=False)

            except Exception as e:
                logger.debug(f"Status report failed to {server_url}: {e}")
                self.registry.update_server_health(server_url, success=False)

        if success_count > 0:
            logger.debug(f"✅ Status report sent to {success_count} bootstrap server(s)")
            return True
        else:
            logger.debug("⚠️ Status report failed to all bootstrap servers")
            return False


class BackgroundStatusReporter:
    """
    Background status reporting system that doesn't block mining operations.

    Queues status reports and sends them asynchronously to prevent mining interruptions.
    """

    def __init__(self, miner_reporter: RobustMinerReporter):
        self.miner_reporter = miner_reporter
        self.report_queue: List[Dict[str, Any]] = []
        self.max_queue_size = 10
        self.running = True
        self.thread = threading.Thread(target=self._reporting_worker, daemon=True)
        self.thread.start()

    def queue_status_report(self, status_data: Dict[str, Any]):
        """Queue a status report for background sending"""
        if len(self.report_queue) >= self.max_queue_size:
            # Remove oldest report if queue is full
            self.report_queue.pop(0)

        self.report_queue.append(status_data)

    def _reporting_worker(self):
        """Background worker that sends queued status reports"""
        while self.running:
            try:
                if self.report_queue:
                    # Send the most recent report
                    status_data = self.report_queue[-1]
                    success = self.miner_reporter.send_status_report(status_data)

                    if success:
                        # Clear the queue on success
                        self.report_queue.clear()
                    else:
                        # Keep the report for retry, but don't spam
                        time.sleep(60)  # Wait before retry
                else:
                    # No reports to send, wait
                    time.sleep(30)

            except Exception as e:
                logger.warning(f"Status reporting worker error: {e}")
                time.sleep(60)

    def stop(self):
        """Stop the background reporter"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=5)


# Global instances
_bootstrap_registry = None
_miner_reporter = None
_status_reporter = None

def get_bootstrap_registry() -> BootstrapRegistry:
    """Get global bootstrap registry instance"""
    global _bootstrap_registry
    if _bootstrap_registry is None:
        _bootstrap_registry = BootstrapRegistry()
    return _bootstrap_registry

def get_miner_reporter(node_id: str) -> RobustMinerReporter:
    """Get global miner reporter instance"""
    global _miner_reporter
    if _miner_reporter is None or _miner_reporter.node_id != node_id:
        registry = get_bootstrap_registry()
        _miner_reporter = RobustMinerReporter(registry, node_id)
    return _miner_reporter

def get_status_reporter(node_id: str) -> BackgroundStatusReporter:
    """Get global background status reporter instance"""
    global _status_reporter
    if _status_reporter is None:
        reporter = get_miner_reporter(node_id)
        _status_reporter = BackgroundStatusReporter(reporter)
    return _status_reporter