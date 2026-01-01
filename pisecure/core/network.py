"""
PiSecure P2P Network & Peer Discovery
=====================================

Decentralized peer discovery and network communication for the PiSecure blockchain.
Supports multiple discovery methods: mDNS, DHT, IPFS PubSub, and DNS seeds.
"""

import asyncio
import json
import socket
import time
import threading
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import logging

try:
    import zeroconf
    MDNS_AVAILABLE = True
except ImportError:
    MDNS_AVAILABLE = False

try:
    import aioipfs
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False

try:
    import bencode.py as bencode
    BENCODE_AVAILABLE = True
except ImportError:
    BENCODE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeerInfo:
    """Information about a network peer"""

    def __init__(self, address: str, port: int = 3141, node_id: str = None,
                 capabilities: List[str] = None, last_seen: float = None):
        self.address = address
        self.port = port
        self.node_id = node_id or self._generate_node_id()
        self.capabilities = capabilities or ['validation']
        self.last_seen = last_seen or time.time()
        self.connection_attempts = 0
        self.last_attempt = 0

    def _generate_node_id(self) -> str:
        """Generate a unique node identifier"""
        data = f"{self.address}:{self.port}:{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'address': self.address,
            'port': self.port,
            'node_id': self.node_id,
            'capabilities': self.capabilities,
            'last_seen': self.last_seen,
            'connection_attempts': self.connection_attempts
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        """Create from dictionary"""
        peer = cls(
            address=data['address'],
            port=data.get('port', 3141),
            node_id=data.get('node_id'),
            capabilities=data.get('capabilities', ['validation']),
            last_seen=data.get('last_seen')
        )
        peer.connection_attempts = data.get('connection_attempts', 0)
        return peer

    def is_alive(self, timeout: int = 1800) -> bool:
        """Check if peer is considered alive"""
        return (time.time() - self.last_seen) < timeout

    def can_attempt_connection(self, min_interval: int = 30) -> bool:
        """Check if we can attempt connection to this peer"""
        return (time.time() - self.last_attempt) > min_interval


class DecentralizedPeerDiscovery:
    """Multi-method decentralized peer discovery"""

    def __init__(self, network_config: Dict[str, Any] = None):
        self.config = network_config or self._default_config()
        self.known_peers: Dict[str, PeerInfo] = {}
        self.discovery_methods = []
        self._load_known_peers()

        # Initialize discovery methods
        self._setup_discovery_methods()

    def _default_config(self) -> Dict[str, Any]:
        """Default network configuration"""
        return {
            'discovery': {
                'methods': ['mdns', 'dht', 'ipfs_pubsub'],
                'mdns_service_type': '_pisecure._tcp.local.',
                'dht_bootstrap_nodes': ['dht1.pisecure.io:6881'],
                'ipfs_topics': ['pisecure/peers']
            },
            'peers': {
                'max_known_peers': 1000,
                'peer_timeout': 1800,
                'connection_timeout': 30
            }
        }

    def _setup_discovery_methods(self):
        """Initialize available discovery methods"""
        methods = self.config['discovery']['methods']

        if 'mdns' in methods and MDNS_AVAILABLE:
            self.discovery_methods.append(MDNSDiscovery(self.config))
        else:
            logger.warning("mDNS discovery not available (zeroconf not installed)")

        if 'dht' in methods and BENCODE_AVAILABLE:
            self.discovery_methods.append(DHTDiscovery(self.config))
        else:
            logger.warning("DHT discovery not available (bencode not installed)")

        if 'ipfs_pubsub' in methods and IPFS_AVAILABLE:
            self.discovery_methods.append(IPFSPubSubDiscovery(self.config))
        else:
            logger.warning("IPFS PubSub discovery not available (aioipfs not installed)")

    def discover_peers(self, timeout: int = 30) -> List[PeerInfo]:
        """Discover peers using all available methods"""
        logger.info("Starting decentralized peer discovery...")

        discovered_peers = set()
        all_peers = []

        # Run all discovery methods concurrently
        async def run_discovery():
            tasks = []
            for method in self.discovery_methods:
                tasks.append(method.discover_peers(timeout))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Discovery method failed: {result}")
                elif isinstance(result, list):
                    all_peers.extend(result)

        # Run async discovery
        try:
            asyncio.run(run_discovery())
        except Exception as e:
            logger.error(f"Peer discovery failed: {e}")

        # Filter and deduplicate peers
        for peer in all_peers:
            peer_key = f"{peer.address}:{peer.port}"
            if peer_key not in discovered_peers:
                discovered_peers.add(peer_key)
                self._add_peer(peer)

        logger.info(f"Discovered {len(discovered_peers)} unique peers")
        return list(self.known_peers.values())

    def _add_peer(self, peer: PeerInfo):
        """Add a peer to the known peers list"""
        peer_key = f"{peer.address}:{peer.port}"
        self.known_peers[peer_key] = peer

        # Limit known peers to prevent memory issues
        max_peers = self.config['peers']['max_known_peers']
        if len(self.known_peers) > max_peers:
            # Remove oldest peers
            sorted_peers = sorted(self.known_peers.items(),
                                key=lambda x: x[1].last_seen)
            peers_to_remove = sorted_peers[:len(sorted_peers) - max_peers]
            for peer_key, _ in peers_to_remove:
                del self.known_peers[peer_key]

    def _load_known_peers(self):
        """Load known peers from persistent storage"""
        peer_file = Path("/var/lib/pisecure/known_peers.json")
        if peer_file.exists():
            try:
                with open(peer_file, 'r') as f:
                    peer_data = json.load(f)
                    for peer_dict in peer_data:
                        peer = PeerInfo.from_dict(peer_dict)
                        self._add_peer(peer)
                logger.info(f"Loaded {len(self.known_peers)} known peers")
            except Exception as e:
                logger.error(f"Failed to load known peers: {e}")

    def save_known_peers(self):
        """Save known peers to persistent storage"""
        peer_file = Path("/var/lib/pisecure/known_peers.json")
        peer_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            peer_data = [peer.to_dict() for peer in self.known_peers.values()]
            with open(peer_file, 'w') as f:
                json.dump(peer_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save known peers: {e}")

    def get_active_peers(self, max_age: int = 1800) -> List[PeerInfo]:
        """Get currently active peers"""
        return [peer for peer in self.known_peers.values() if peer.is_alive(max_age)]

    def get_connection_candidates(self) -> List[PeerInfo]:
        """Get peers that can be attempted for connection"""
        return [peer for peer in self.known_peers.values()
                if peer.can_attempt_connection()]


class MDNSDiscovery:
    """mDNS-based local network peer discovery"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_type = config['discovery']['mdns_service_type']
        self.zeroconf = None
        self.listener = None

    async def discover_peers(self, timeout: int = 30) -> List[PeerInfo]:
        """Discover peers using mDNS"""
        if not MDNS_AVAILABLE:
            return []

        discovered_peers = []

        try:
            # Create zeroconf instance
            self.zeroconf = zeroconf.Zeroconf()
            self.listener = MDNSListener()

            # Browse for services
            browser = zeroconf.ServiceBrowser(
                self.zeroconf, self.service_type, self.listener)

            # Wait for discovery
            await asyncio.sleep(timeout)

            # Get discovered services
            for service in self.listener.services:
                try:
                    info = self.zeroconf.get_service_info(
                        self.service_type, service)
                    if info:
                        address = socket.inet_ntoa(info.addresses[0])
                        port = info.port

                        # Extract node info from TXT records
                        node_id = None
                        capabilities = ['validation']

                        if info.properties:
                            node_id = info.properties.get(b'node_id', b'').decode()
                            caps = info.properties.get(b'capabilities', b'validation').decode()
                            capabilities = caps.split(',')

                        peer = PeerInfo(
                            address=address,
                            port=port,
                            node_id=node_id,
                            capabilities=capabilities
                        )
                        discovered_peers.append(peer)

                except Exception as e:
                    logger.error(f"Failed to process mDNS service {service}: {e}")

        except Exception as e:
            logger.error(f"mDNS discovery failed: {e}")
        finally:
            if self.zeroconf:
                self.zeroconf.close()

        return discovered_peers


class MDNSListener:
    """Zeroconf service listener"""

    def __init__(self):
        self.services = set()

    def add_service(self, zeroconf, service_type, name):
        """Called when a service is discovered"""
        self.services.add(name)

    def remove_service(self, zeroconf, service_type, name):
        """Called when a service is removed"""
        self.services.discard(name)


class DHTDiscovery:
    """BitTorrent DHT-based peer discovery"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bootstrap_nodes = config['discovery']['dht_bootstrap_nodes']
        self.pisecure_infohash = self._generate_infohash()

    def _generate_infohash(self) -> bytes:
        """Generate infohash for PiSecure network"""
        # Use a deterministic infohash based on network name
        network_id = "PiSecure Mainnet v0.1.0"
        return hashlib.sha1(network_id.encode()).digest()

    async def discover_peers(self, timeout: int = 30) -> List[PeerInfo]:
        """Discover peers using DHT"""
        if not BENCODE_AVAILABLE:
            return []

        discovered_peers = []

        # This is a simplified DHT implementation
        # In production, this would use a full DHT library

        try:
            # Connect to bootstrap nodes
            for bootstrap_node in self.bootstrap_nodes:
                try:
                    host, port = bootstrap_node.split(':')
                    port = int(port)

                    # Query DHT node (simplified)
                    peers = await self._query_dht_node(host, port, timeout)

                    for peer_addr, peer_port in peers:
                        peer = PeerInfo(
                            address=peer_addr,
                            port=peer_port or 3141,
                            capabilities=['mining', 'validation']
                        )
                        discovered_peers.append(peer)

                except Exception as e:
                    logger.error(f"Failed to query DHT node {bootstrap_node}: {e}")

        except Exception as e:
            logger.error(f"DHT discovery failed: {e}")

        return discovered_peers

    async def _query_dht_node(self, host: str, port: int, timeout: int) -> List[Tuple[str, int]]:
        """Query a DHT node for peers (simplified)"""
        # This is a placeholder - real implementation would use proper DHT protocol
        # For now, return some mock peers for demonstration
        await asyncio.sleep(0.1)  # Simulate network delay

        # Mock response - in reality this would parse actual DHT responses
        return [
            ("192.168.1.100", 3141),
            ("10.0.0.50", 3141),
            ("203.0.113.1", 3141)
        ]


class IPFSPubSubDiscovery:
    """IPFS PubSub-based peer discovery"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.topics = config['discovery']['ipfs_topics']
        self.ipfs_client = None

    async def discover_peers(self, timeout: int = 30) -> List[PeerInfo]:
        """Discover peers using IPFS PubSub"""
        if not IPFS_AVAILABLE:
            return []

        discovered_peers = []

        try:
            # Connect to IPFS (this would need a running IPFS node)
            self.ipfs_client = aioipfs.AsyncIPFS()

            # Subscribe to topics and listen for peer announcements
            for topic in self.topics:
                try:
                    # Subscribe to topic
                    async for message in self.ipfs_client.pubsub.sub(topic):
                        try:
                            # Parse peer announcement
                            peer_data = json.loads(message['data'].decode())

                            peer = PeerInfo(
                                address=peer_data['address'],
                                port=peer_data.get('port', 3141),
                                node_id=peer_data.get('node_id'),
                                capabilities=peer_data.get('capabilities', ['validation'])
                            )

                            discovered_peers.append(peer)

                            # Limit discovery time
                            if time.time() - time.monotonic() > timeout:
                                break

                        except json.JSONDecodeError:
                            continue
                        except KeyError:
                            continue

                except Exception as e:
                    logger.error(f"Failed to subscribe to IPFS topic {topic}: {e}")

        except Exception as e:
            logger.error(f"IPFS PubSub discovery failed: {e}")
        finally:
            if self.ipfs_client:
                await self.ipfs_client.close()

        return discovered_peers


class GitHubBootstrap:
    """GitHub-based bootstrap for initial blockchain state"""

    def __init__(self):
        self.repo_url = "https://api.github.com/repos/UnderhillForge/PiSecure"
        self.raw_base = "https://raw.githubusercontent.com/UnderhillForge/PiSecure/main"

    async def download_initial_state(self) -> Dict[str, Any]:
        """Download initial blockchain state from GitHub"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            # Download genesis block
            genesis_url = f"{self.raw_base}/blockchain/genesis.json"
            async with session.get(genesis_url) as response:
                genesis_data = await response.json()

            # Download network config
            config_url = f"{self.raw_base}/network/config.json"
            async with session.get(config_url) as response:
                config_data = await response.json()

            # Download checksums
            checksums_url = f"{self.raw_base}/blockchain/checksums.sha256"
            async with session.get(checksums_url) as response:
                checksums_text = await response.text()

        return {
            'genesis': genesis_data,
            'config': config_data,
            'checksums': checksums_text
        }

    def verify_initial_state(self, state: Dict[str, Any]) -> bool:
        """Verify integrity of downloaded initial state"""
        try:
            # Verify genesis block structure
            genesis = state['genesis']
            required_fields = ['genesis', 'block', 'metadata']
            if not all(field in genesis for field in required_fields):
                return False

            # Verify genesis block hash
            block = genesis['block']
            calculated_hash = hashlib.sha256(
                json.dumps(block, sort_keys=True).encode()
            ).hexdigest()

            if calculated_hash != block['hash']:
                logger.error("Genesis block hash verification failed")
                return False

            # Additional verification logic would go here
            return True

        except Exception as e:
            logger.error(f"Initial state verification failed: {e}")
            return False


class NetworkManager:
    """Manages P2P network connections and communication"""

    def __init__(self, peer_discovery: DecentralizedPeerDiscovery):
        self.peer_discovery = peer_discovery
        self.connected_peers: Dict[str, asyncio.StreamWriter] = {}
        self.message_handlers = {}
        self.running = False

    async def start_network(self):
        """Start the P2P network"""
        self.running = True

        # Start peer discovery
        discovery_task = asyncio.create_task(self._run_peer_discovery())

        # Start connection management
        connection_task = asyncio.create_task(self._manage_connections())

        # Start message handling
        message_task = asyncio.create_task(self._handle_messages())

        await asyncio.gather(discovery_task, connection_task, message_task)

    async def _run_peer_discovery(self):
        """Continuously discover new peers"""
        while self.running:
            try:
                peers = await asyncio.get_event_loop().run_in_executor(
                    None, self.peer_discovery.discover_peers, 30)

                # Attempt connections to new peers
                for peer in peers:
                    if peer.address not in self.connected_peers:
                        asyncio.create_task(self._connect_to_peer(peer))

                await asyncio.sleep(300)  # Discover every 5 minutes

            except Exception as e:
                logger.error(f"Peer discovery error: {e}")
                await asyncio.sleep(60)

    async def _connect_to_peer(self, peer: PeerInfo):
        """Connect to a peer"""
        try:
            reader, writer = await asyncio.open_connection(
                peer.address, peer.port)

            peer_key = f"{peer.address}:{peer.port}"
            self.connected_peers[peer_key] = writer

            # Send version handshake
            version_msg = {
                'type': 'version',
                'version': '0.1.0',
                'node_id': self._get_node_id(),
                'capabilities': ['mining', 'validation'],
                'best_height': 0  # Would get from blockchain
            }

            await self._send_message(writer, version_msg)

            logger.info(f"Connected to peer: {peer.address}:{peer.port}")

        except Exception as e:
            logger.error(f"Failed to connect to peer {peer.address}:{peer.port}: {e}")

    async def _manage_connections(self):
        """Manage active connections"""
        while self.running:
            # Check connection health, handle timeouts, etc.
            await asyncio.sleep(60)

    async def _handle_messages(self):
        """Handle incoming messages from peers"""
        # Message handling logic would go here
        while self.running:
            await asyncio.sleep(1)

    async def _send_message(self, writer: asyncio.StreamWriter, message: Dict[str, Any]):
        """Send a message to a peer"""
        try:
            data = json.dumps(message).encode()
            writer.write(data)
            await writer.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def _get_node_id(self) -> str:
        """Get this node's ID"""
        # Would generate or load node ID
        return hashlib.sha256(socket.gethostname().encode()).hexdigest()[:32]

    def broadcast_transaction(self, transaction: Dict[str, Any]):
        """Broadcast a transaction to all connected peers"""
        # Implementation would broadcast to all peers
        pass

    def request_blockchain_sync(self, peer_address: str):
        """Request blockchain synchronization from a peer"""
        # Implementation would request sync from specific peer
        pass