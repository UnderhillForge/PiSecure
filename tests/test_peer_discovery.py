"""
PiSecure Peer Discovery Tests
=============================

Comprehensive unit tests for the PeerDiscovery component.
"""

import pytest
import time
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from pisecure.network.discovery import PeerDiscovery


class TestPeerDiscovery:

    @pytest.fixture
    def temp_peer_file(self, tmp_path):
        """Create a temporary peer file for testing"""
        peer_file = tmp_path / "test_peers.json"
        return peer_file

    @pytest.fixture
    def peer_discovery(self, temp_peer_file):
        """Create a PeerDiscovery instance with temporary file"""
        return PeerDiscovery(
            node_id="test_node_123",
            listen_port=3142,
            peer_file=str(temp_peer_file)
        )

    def test_initialization(self, peer_discovery, temp_peer_file):
        """Test PeerDiscovery initialization"""
        assert peer_discovery.node_id == "test_node_123"
        assert peer_discovery.listen_port == 3142
        assert peer_discovery.peer_file == temp_peer_file
        assert isinstance(peer_discovery.known_peers, dict)
        assert isinstance(peer_discovery.connected_peers, set)
        assert peer_discovery.lock is not None

    def test_initialization_with_existing_file(self, temp_peer_file):
        """Test initialization with existing peer file"""
        # Create a peer file with existing data
        existing_peers = {
            "peer1": {
                "address": "192.168.1.100",
                "port": 3142,
                "last_seen": time.time() - 3600,
                "connected": False
            }
        }

        with open(temp_peer_file, 'w') as f:
            json.dump(existing_peers, f)

        # Initialize PeerDiscovery
        discovery = PeerDiscovery(peer_file=str(temp_peer_file))

        # Should load existing peers
        assert "peer1" in discovery.known_peers
        assert discovery.known_peers["peer1"]["address"] == "192.168.1.100"

    def test_add_peer_new(self, peer_discovery):
        """Test adding a new peer"""
        peer_discovery.add_peer(
            peer_id="peer1",
            address="192.168.1.100",
            port=3142
        )

        assert "peer1" in peer_discovery.known_peers
        peer_info = peer_discovery.known_peers["peer1"]
        assert peer_info["address"] == "192.168.1.100"
        assert peer_info["port"] == 3142
        assert peer_info["connected"] == False  # Not marked as connected yet
        assert "last_seen" in peer_info

    def test_add_peer_update_existing(self, peer_discovery):
        """Test updating an existing peer"""
        # Add peer initially
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)

        # Update peer with new info
        old_last_seen = peer_discovery.known_peers["peer1"]["last_seen"]
        time.sleep(0.01)  # Small delay to ensure different timestamp

        peer_discovery.add_peer("peer1", "192.168.1.101", 3143)

        # Should update address and port, and last_seen
        peer_info = peer_discovery.known_peers["peer1"]
        assert peer_info["address"] == "192.168.1.101"
        assert peer_info["port"] == 3143
        assert peer_info["last_seen"] > old_last_seen

    def test_add_peer_with_timestamp(self, peer_discovery):
        """Test adding a peer with explicit timestamp"""
        custom_time = time.time() - 1000
        peer_discovery.add_peer(
            peer_id="peer1",
            address="192.168.1.100",
            port=3142,
            last_seen=custom_time
        )

        assert peer_discovery.known_peers["peer1"]["last_seen"] == custom_time

    def test_remove_peer_existing(self, peer_discovery):
        """Test removing an existing peer"""
        # Add a peer first
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        assert "peer1" in peer_discovery.known_peers

        # Remove the peer
        peer_discovery.remove_peer("peer1")

        assert "peer1" not in peer_discovery.known_peers

    def test_remove_peer_nonexistent(self, peer_discovery):
        """Test removing a nonexistent peer (should not crash)"""
        # Should not crash
        peer_discovery.remove_peer("nonexistent_peer")
        assert "nonexistent_peer" not in peer_discovery.known_peers

    def test_get_known_peers(self, peer_discovery):
        """Test getting all known peers"""
        # Add some peers
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        peer_discovery.add_peer("peer2", "192.168.1.101", 3143)

        peers = peer_discovery.get_known_peers()

        assert isinstance(peers, dict)
        assert "peer1" in peers
        assert "peer2" in peers
        assert len(peers) == 2

        # Should return a copy, not the original
        peers["peer1"]["address"] = "modified"
        assert peer_discovery.known_peers["peer1"]["address"] == "192.168.1.100"

    def test_get_connected_peers(self, peer_discovery):
        """Test getting list of connected peers"""
        # Initially no connected peers
        assert peer_discovery.get_connected_peers() == []

        # Mark a peer as connected
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        peer_discovery.mark_peer_connected("peer1")

        connected = peer_discovery.get_connected_peers()
        assert "peer1" in connected
        assert len(connected) == 1

    def test_mark_peer_connected(self, peer_discovery):
        """Test marking a peer as connected"""
        # Add a peer
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        assert not peer_discovery.known_peers["peer1"]["connected"]

        # Mark as connected
        peer_discovery.mark_peer_connected("peer1")

        assert peer_discovery.known_peers["peer1"]["connected"]
        assert "peer1" in peer_discovery.connected_peers

        # Should update last_seen timestamp
        assert peer_discovery.known_peers["peer1"]["last_seen"] is not None

    def test_mark_peer_connected_nonexistent(self, peer_discovery):
        """Test marking a nonexistent peer as connected"""
        # Should not crash
        peer_discovery.mark_peer_connected("nonexistent")
        assert "nonexistent" not in peer_discovery.connected_peers

    def test_mark_peer_disconnected(self, peer_discovery):
        """Test marking a peer as disconnected"""
        # Add and connect a peer
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        peer_discovery.mark_peer_connected("peer1")
        assert peer_discovery.known_peers["peer1"]["connected"]

        # Mark as disconnected
        peer_discovery.mark_peer_disconnected("peer1")

        assert not peer_discovery.known_peers["peer1"]["connected"]
        assert "peer1" not in peer_discovery.connected_peers

    def test_mark_peer_disconnected_nonexistent(self, peer_discovery):
        """Test marking a nonexistent peer as disconnected"""
        # Should not crash
        peer_discovery.mark_peer_disconnected("nonexistent")

    def test_discover_peers_basic(self, peer_discovery):
        """Test basic peer discovery cleanup"""
        # Add some peers with old timestamps
        old_time = time.time() - (25 * 60 * 60)  # 25 hours ago
        peer_discovery.known_peers = {
            "old_peer": {
                "address": "192.168.1.100",
                "port": 3142,
                "last_seen": old_time,
                "connected": False
            },
            "recent_peer": {
                "address": "192.168.1.101",
                "port": 3143,
                "last_seen": time.time(),
                "connected": True
            }
        }

        # Run discovery (which should clean up old peers)
        peer_discovery.discover_peers()

        # Old peer should be removed
        assert "old_peer" not in peer_discovery.known_peers
        # Recent peer should remain
        assert "recent_peer" in peer_discovery.known_peers

    def test_persistence_save_load(self, peer_discovery, temp_peer_file):
        """Test saving and loading peers to/from file"""
        # Add some peers
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)
        peer_discovery.add_peer("peer2", "192.168.1.101", 3143)
        peer_discovery.mark_peer_connected("peer1")

        # Should save to file automatically
        assert temp_peer_file.exists()

        # Create new instance with same file
        new_discovery = PeerDiscovery(peer_file=str(temp_peer_file))

        # Should load the peers
        assert "peer1" in new_discovery.known_peers
        assert "peer2" in new_discovery.known_peers
        assert new_discovery.known_peers["peer1"]["connected"]
        assert not new_discovery.known_peers["peer2"]["connected"]

    def test_persistence_corrupt_file(self, temp_peer_file):
        """Test handling of corrupt peer file"""
        # Write invalid JSON
        with open(temp_peer_file, 'w') as f:
            f.write("invalid json content")

        # Should handle gracefully and start with empty peers
        discovery = PeerDiscovery(peer_file=str(temp_peer_file))
        assert discovery.known_peers == {}

    def test_thread_safety(self, peer_discovery):
        """Test thread safety of peer operations"""
        import threading
        import time

        results = []

        def add_peers_thread(peer_prefix, count):
            for i in range(count):
                peer_id = f"{peer_prefix}_{i}"
                peer_discovery.add_peer(peer_id, f"192.168.1.{i}", 3142 + i)
                results.append(peer_id)

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=add_peers_thread,
                args=(f"thread_{i}", 5)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have all peers added
        assert len(peer_discovery.known_peers) == 15
        assert len(results) == 15

    def test_peer_file_permissions(self, tmp_path):
        """Test handling of peer file permission issues"""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        readonly_file = readonly_dir / "peers.json"

        discovery = PeerDiscovery(peer_file=str(readonly_file))

        # Try to add a peer (should handle permission error gracefully)
        discovery.add_peer("peer1", "192.168.1.100", 3142)

        # Should still have the peer in memory even if save failed
        assert "peer1" in discovery.known_peers

    def test_large_peer_list(self, peer_discovery):
        """Test handling of large peer lists"""
        # Add many peers
        for i in range(1000):
            peer_discovery.add_peer(f"peer_{i}", f"192.168.1.{i % 256}", 3142 + (i % 100))

        assert len(peer_discovery.known_peers) == 1000

        # Getting peers should work efficiently
        peers = peer_discovery.get_known_peers()
        assert len(peers) == 1000

    def test_peer_info_completeness(self, peer_discovery):
        """Test that peer info contains all required fields"""
        peer_discovery.add_peer("peer1", "192.168.1.100", 3142)

        peer_info = peer_discovery.known_peers["peer1"]
        required_fields = ["address", "port", "last_seen", "connected"]

        for field in required_fields:
            assert field in peer_info

        assert isinstance(peer_info["address"], str)
        assert isinstance(peer_info["port"], int)
        assert isinstance(peer_info["last_seen"], (int, float))
        assert isinstance(peer_info["connected"], bool)


if __name__ == "__main__":
    pytest.main([__file__])