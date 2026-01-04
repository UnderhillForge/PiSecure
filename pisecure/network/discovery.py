"""
PiSecure Peer Discovery
=======================

Basic peer discovery implementation for PiSecure network.
"""

import time
import json
import threading
from typing import Dict, List, Set, Optional
from pathlib import Path


class PeerDiscovery:
    """
    Basic peer discovery for PiSecure network.

    This is a simplified implementation that maintains a list of known peers
    and can be extended with more sophisticated discovery mechanisms.
    """

    def __init__(self, node_id: str = None, listen_port: int = 3142,
                 peer_file: str = "/var/lib/pisecure/peers.json"):
        """
        Initialize peer discovery.

        Args:
            node_id: Unique identifier for this node
            listen_port: Port this node listens on
            peer_file: File to store known peers
        """
        self.node_id = node_id or f"node_{int(time.time())}"
        self.listen_port = listen_port
        self.peer_file = Path(peer_file)
        self.known_peers: Dict[str, Dict] = {}
        self.connected_peers: Set[str] = set()
        self.lock = threading.Lock()

        # Load existing peers
        self._load_peers()

    def _load_peers(self):
        """Load known peers from file."""
        try:
            if self.peer_file.exists():
                with open(self.peer_file, 'r') as f:
                    self.known_peers = json.load(f)
        except Exception:
            # If loading fails, start with empty peer list
            self.known_peers = {}

    def _save_peers(self):
        """Save known peers to file."""
        try:
            self.peer_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.peer_file, 'w') as f:
                json.dump(self.known_peers, f, indent=2)
        except Exception:
            pass  # Silently fail if we can't save

    def add_peer(self, peer_id: str, address: str, port: int = 3142,
                 last_seen: Optional[float] = None):
        """
        Add a peer to the known peers list.

        Args:
            peer_id: Unique peer identifier
            address: Peer IP address or hostname
            port: Peer port
            last_seen: Timestamp when peer was last seen
        """
        with self.lock:
            self.known_peers[peer_id] = {
                'address': address,
                'port': port,
                'last_seen': last_seen or time.time(),
                'connected': peer_id in self.connected_peers
            }
            self._save_peers()

    def remove_peer(self, peer_id: str):
        """Remove a peer from the known peers list."""
        with self.lock:
            if peer_id in self.known_peers:
                del self.known_peers[peer_id]
                self.connected_peers.discard(peer_id)
                self._save_peers()

    def get_known_peers(self) -> Dict[str, Dict]:
        """Get all known peers."""
        import copy
        with self.lock:
            return copy.deepcopy(self.known_peers)

    def get_connected_peers(self) -> List[str]:
        """Get list of currently connected peers."""
        with self.lock:
            return list(self.connected_peers)

    def mark_peer_connected(self, peer_id: str):
        """Mark a peer as connected."""
        with self.lock:
            if peer_id in self.known_peers:
                self.known_peers[peer_id]['connected'] = True
                self.known_peers[peer_id]['last_seen'] = time.time()
                self.connected_peers.add(peer_id)
                self._save_peers()

    def mark_peer_disconnected(self, peer_id: str):
        """Mark a peer as disconnected."""
        with self.lock:
            if peer_id in self.known_peers:
                self.known_peers[peer_id]['connected'] = False
                self.connected_peers.discard(peer_id)
                self._save_peers()

    def discover_peers(self):
        """
        Basic peer discovery mechanism.

        This is a placeholder that can be extended with:
        - DNS seeding
        - Peer exchange
        - DHT-based discovery
        - Local network scanning
        """
        # For now, just clean up old peers
        current_time = time.time()
        cutoff_time = current_time - (24 * 60 * 60)  # 24 hours ago

        with self.lock:
            peers_to_remove = []
            for peer_id, peer_info in self.known_peers.items():
                if peer_info.get('last_seen', 0) < cutoff_time:
                    peers_to_remove.append(peer_id)

            for peer_id in peers_to_remove:
                del self.known_peers[peer_id]

            if peers_to_remove:
                self._save_peers()

    def start_discovery(self):
        """Start the peer discovery process."""
        # Start cleanup thread
        def cleanup_worker():
            while True:
                self.discover_peers()
                time.sleep(300)  # Clean up every 5 minutes

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    def stop_discovery(self):
        """Stop the peer discovery process."""
        # For now, just a placeholder
        pass