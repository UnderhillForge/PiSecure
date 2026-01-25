"""
NodeInterface - Abstract node operations

Defines the contract for node operations (peers, synchronization, etc.)
without exposing implementation details.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PeerInfo:
    """Information about a peer."""

    host: str
    port: int
    node_id: str
    version: str
    last_seen: float
    latency_ms: float


@dataclass
class NetworkStats:
    """Network statistics."""

    connected_peers: int
    pending_transactions: int
    active_miners: int
    network_difficulty: int
    sync_status: str


class NodeInterface(ABC):
    """
    Abstract interface for node operations.

    Implementations should handle:
    - Peer discovery and connection
    - P2P synchronization
    - Network propagation
    - Health checks
    """

    @abstractmethod
    def get_peer_list(self) -> List[PeerInfo]:
        """Get list of connected peers."""
        pass

    @abstractmethod
    def connect_peer(self, host: str, port: int) -> Tuple[bool, str]:
        """
        Connect to a peer.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def disconnect_peer(self, peer_id: str) -> bool:
        """Disconnect from a peer."""
        pass

    @abstractmethod
    def sync_with_peers(self) -> Tuple[bool, str]:
        """
        Synchronize blockchain with peers.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def get_network_stats(self) -> NetworkStats:
        """Get network statistics."""
        pass

    @abstractmethod
    def is_synced(self) -> bool:
        """Check if node is synced with network."""
        pass

    @abstractmethod
    def get_sync_progress(self) -> float:
        """Get sync progress as percentage (0.0-100.0)."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Get comprehensive health check information."""
        pass

    @abstractmethod
    def broadcast_transaction(self, transaction: Dict[str, Any]) -> None:
        """Broadcast a transaction to the network."""
        pass

    @abstractmethod
    def broadcast_block(self, block: Dict[str, Any]) -> None:
        """Broadcast a block to the network."""
        pass

    @abstractmethod
    def discover_peers(self) -> List[Tuple[str, int]]:
        """Discover new peers in the network."""
        pass
