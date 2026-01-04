#!/usr/bin/env python3
"""
PiSecure P2P Protocol Implementation
====================================

Full peer-to-peer protocol for PiSecure network communication,
consensus, and data synchronization.
"""

import time
import json
import hashlib
import threading
import socket
import select
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import secrets

from .blockchain import SignChain
from .p2p_sync import P2PSyncManager

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """P2P message types"""
    HANDSHAKE = "handshake"
    PEER_LIST = "peer_list"
    BLOCK_ANNOUNCE = "block_announce"
    BLOCK_REQUEST = "block_request"
    BLOCK_RESPONSE = "block_response"
    TRANSACTION_ANNOUNCE = "transaction_announce"
    TRANSACTION_REQUEST = "transaction_request"
    MINING_SHARE = "mining_share"
    TEAM_UPDATE = "team_update"
    CONSENSUS_VOTE = "consensus_vote"
    HEARTBEAT = "heartbeat"
    DISCONNECT = "disconnect"

class ConsensusState(Enum):
    """Consensus states"""
    FOLLOWING = "following"
    CANDIDATE = "candidate"
    LEADER = "leader"
    SYNCHRONIZING = "synchronizing"

@dataclass
class P2PMessage:
    """P2P message structure"""
    message_id: str
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str]
    timestamp: float
    ttl: int  # Time to live in hops
    payload: Dict[str, Any]
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'P2PMessage':
        """Create from dictionary"""
        data_copy = data.copy()
        data_copy['message_type'] = MessageType(data['message_type'])
        return cls(**data_copy)

    def calculate_hash(self) -> str:
        """Calculate message hash for integrity"""
        message_string = json.dumps({
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'timestamp': self.timestamp,
            'payload': self.payload
        }, sort_keys=True)
        return hashlib.sha256(message_string.encode()).hexdigest()

class P2PConnection:
    """Individual P2P connection to a peer"""

    def __init__(self, peer_id: str, socket_obj: socket.socket,
                 address: Tuple[str, int], protocol: 'PiSecureP2P'):
        self.peer_id = peer_id
        self.socket = socket_obj
        self.address = address
        self.protocol = protocol

        self.connected = True
        self.last_heartbeat = time.time()
        self.sent_messages: Set[str] = set()  # Track sent message IDs
        self.received_messages: Set[str] = set()  # Track received message IDs

        # Connection statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0

    def send_message(self, message: P2PMessage) -> bool:
        """Send message to peer"""
        try:
            # Avoid sending duplicate messages
            if message.message_id in self.sent_messages:
                return True

            message_data = message.to_dict()
            json_data = json.dumps(message_data).encode('utf-8')

            # Send message length first (4 bytes)
            length_bytes = len(json_data).to_bytes(4, 'big')
            self.socket.sendall(length_bytes)

            # Send message data
            self.socket.sendall(json_data)

            self.sent_messages.add(message.message_id)
            self.messages_sent += 1
            self.bytes_sent += len(json_data) + 4
            self.last_heartbeat = time.time()

            logger.debug(f"Sent message {message.message_type.value} to {self.peer_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to {self.peer_id}: {e}")
            self.connected = False
            return False

    def receive_message(self) -> Optional[P2PMessage]:
        """Receive message from peer"""
        try:
            # Read message length (4 bytes)
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                # Connection closed
                self.connected = False
                return None

            message_length = int.from_bytes(length_bytes, 'big')

            # Read message data
            message_data = b''
            while len(message_data) < message_length:
                chunk = self.socket.recv(min(4096, message_length - len(message_data)))
                if not chunk:
                    self.connected = False
                    return None
                message_data += chunk

            # Parse JSON
            message_dict = json.loads(message_data.decode('utf-8'))
            message = P2PMessage.from_dict(message_dict)

            # Avoid processing duplicate messages
            if message.message_id in self.received_messages:
                return None

            self.received_messages.add(message.message_id)
            self.messages_received += 1
            self.bytes_received += len(message_data) + 4
            self.last_heartbeat = time.time()

            logger.debug(f"Received message {message.message_type.value} from {self.peer_id}")
            return message

        except Exception as e:
            logger.error(f"Failed to receive message from {self.peer_id}: {e}")
            self.connected = False
            return None

    def close(self):
        """Close connection"""
        self.connected = False
        try:
            self.socket.close()
        except:
            pass

class PiSecureP2P:
    """
    PiSecure P2P Protocol Implementation

    Handles:
    - Peer discovery and connection management
    - Message routing and gossip protocol
    - Consensus coordination
    - Block and transaction propagation
    """

    def __init__(self, node_id: str, listen_port: int = 3142,
                 blockchain: Optional[SignChain] = None,
                 p2p_sync: Optional[P2PSyncManager] = None):
        """
        Initialize P2P protocol

        Args:
            node_id: Unique identifier for this node
            listen_port: Port to listen for incoming connections
            blockchain: SignChain instance for consensus
            p2p_sync: P2PSyncManager for data synchronization
        """
        self.node_id = node_id
        self.listen_port = listen_port
        self.blockchain = blockchain or SignChain()
        self.p2p_sync = p2p_sync

        # Network state
        self.consensus_state = ConsensusState.FOLLOWING
        self.leader_id: Optional[str] = None
        self.term = 0  # Consensus term
        self.voted_for: Optional[str] = None

        # Connections
        self.connections: Dict[str, P2PConnection] = {}
        self.server_socket: Optional[socket.socket] = None
        self.running = False

        # Message handling
        self.message_handlers = {
            MessageType.HANDSHAKE: self._handle_handshake,
            MessageType.PEER_LIST: self._handle_peer_list,
            MessageType.BLOCK_ANNOUNCE: self._handle_block_announce,
            MessageType.BLOCK_REQUEST: self._handle_block_request,
            MessageType.BLOCK_RESPONSE: self._handle_block_response,
            MessageType.TRANSACTION_ANNOUNCE: self._handle_transaction_announce,
            MessageType.MINING_SHARE: self._handle_mining_share,
            MessageType.TEAM_UPDATE: self._handle_team_update,
            MessageType.CONSENSUS_VOTE: self._handle_consensus_vote,
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.DISCONNECT: self._handle_disconnect,
        }

        # Threads
        self.server_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.consensus_thread: Optional[threading.Thread] = None

        # Protocol statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connections_accepted': 0,
            'connections_established': 0,
            'blocks_propagated': 0,
            'transactions_propagated': 0
        }

        logger.info(f"🔗 PiSecure P2P Protocol initialized (Node: {node_id})")

    def start(self):
        """Start P2P protocol"""
        if self.running:
            return

        self.running = True

        # Start server thread
        self.server_thread = threading.Thread(
            target=self._server_loop,
            daemon=True,
            name="P2PServer"
        )
        self.server_thread.start()

        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="P2PHeartbeat"
        )
        self.heartbeat_thread.start()

        # Start consensus thread
        self.consensus_thread = threading.Thread(
            target=self._consensus_loop,
            daemon=True,
            name="P2PConsensus"
        )
        self.consensus_thread.start()

        logger.info(f"🚀 P2P protocol started on port {self.listen_port}")

    def stop(self):
        """Stop P2P protocol"""
        self.running = False

        # Close all connections
        for conn in list(self.connections.values()):
            conn.close()
        self.connections.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        # Wait for threads
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        if self.consensus_thread and self.consensus_thread.is_alive():
            self.consensus_thread.join(timeout=5)

        logger.info("🛑 P2P protocol stopped")

    def connect_to_peer(self, peer_id: str, address: str, port: int) -> bool:
        """Connect to a peer"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((address, port))

            # Create connection
            connection = P2PConnection(peer_id, sock, (address, port), self)
            self.connections[peer_id] = connection

            # Send handshake
            self._send_handshake(connection)

            self.stats['connections_established'] += 1
            logger.info(f"✅ Connected to peer {peer_id} at {address}:{port}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to peer {peer_id}: {e}")
            return False

    def broadcast_message(self, message: P2PMessage, exclude_peer: Optional[str] = None):
        """Broadcast message to all connected peers"""
        successful_sends = 0

        for peer_id, connection in self.connections.items():
            if peer_id != exclude_peer and connection.connected:
                if connection.send_message(message):
                    successful_sends += 1
                else:
                    # Remove failed connection
                    connection.close()
                    del self.connections[peer_id]

        logger.debug(f"Broadcasted message to {successful_sends}/{len(self.connections)} peers")

    def send_message_to_peer(self, peer_id: str, message: P2PMessage) -> bool:
        """Send message to specific peer"""
        connection = self.connections.get(peer_id)
        if connection and connection.connected:
            return connection.send_message(message)

        logger.debug(f"Cannot send message to {peer_id}: not connected")
        return False

    def _server_loop(self):
        """Main server loop accepting connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(50)
            self.server_socket.setblocking(False)

            logger.info(f"Listening for P2P connections on port {self.listen_port}")

            while self.running:
                try:
                    # Use select for non-blocking accept
                    ready, _, _ = select.select([self.server_socket], [], [], 1.0)

                    if ready and self.server_socket in ready:
                        try:
                            client_socket, address = self.server_socket.accept()
                            client_socket.setblocking(True)

                            # Start client handler thread
                            threading.Thread(
                                target=self._handle_client,
                                args=(client_socket, address),
                                daemon=True,
                                name=f"P2PClient-{address}"
                            ).start()

                        except Exception as e:
                            logger.error(f"Error accepting connection: {e}")

                    # Handle existing connections
                    self._handle_connections()

                except Exception as e:
                    logger.error(f"Server loop error: {e}")

        except Exception as e:
            logger.error(f"Failed to start P2P server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle incoming client connection"""
        peer_id = f"peer_{address[0]}_{address[1]}"
        connection = P2PConnection(peer_id, client_socket, address, self)

        # Wait for handshake
        handshake_message = connection.receive_message()
        if not handshake_message or handshake_message.message_type != MessageType.HANDSHAKE:
            connection.close()
            return

        # Process handshake
        response = self._handle_handshake(handshake_message)
        if response:
            # Send handshake response
            connection.send_message(response)

            # Add to connections
            self.connections[peer_id] = connection
            self.stats['connections_accepted'] += 1

            logger.info(f"🤝 Accepted connection from {peer_id}")

            # Handle messages from this peer
            while self.running and connection.connected:
                message = connection.receive_message()
                if message:
                    self._handle_message(message, connection)
                else:
                    break

        connection.close()
        if peer_id in self.connections:
            del self.connections[peer_id]

    def _handle_connections(self):
        """Handle messages from existing connections"""
        # This is called from the server loop
        # Messages are handled in individual client threads
        pass

    def _heartbeat_loop(self):
        """Send periodic heartbeats to peers"""
        while self.running:
            try:
                current_time = time.time()

                # Send heartbeats and check for dead connections
                dead_peers = []

                for peer_id, connection in self.connections.items():
                    # Send heartbeat
                    heartbeat = P2PMessage(
                        message_id=f"heartbeat_{self.node_id}_{current_time}",
                        message_type=MessageType.HEARTBEAT,
                        sender_id=self.node_id,
                        receiver_id=peer_id,
                        timestamp=current_time,
                        ttl=1,
                        payload={
                            'node_id': self.node_id,
                            'connections': len(self.connections),
                            'consensus_state': self.consensus_state.value
                        }
                    )

                    if not connection.send_message(heartbeat):
                        dead_peers.append(peer_id)
                        continue

                    # Check if peer is still alive
                    if current_time - connection.last_heartbeat > 60:  # 60 seconds timeout
                        dead_peers.append(peer_id)

                # Remove dead connections
                for peer_id in dead_peers:
                    if peer_id in self.connections:
                        self.connections[peer_id].close()
                        del self.connections[peer_id]
                        logger.info(f"❌ Removed dead connection to {peer_id}")

            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

            time.sleep(30)  # Heartbeat every 30 seconds

    def _consensus_loop(self):
        """Run consensus protocol"""
        while self.running:
            try:
                if self.consensus_state == ConsensusState.FOLLOWING:
                    # Check if we should start election
                    if self._should_start_election():
                        self._start_election()
                elif self.consensus_state == ConsensusState.CANDIDATE:
                    # Run election
                    self._run_election()
                elif self.consensus_state == ConsensusState.LEADER:
                    # Send heartbeats as leader
                    self._send_leader_heartbeats()

            except Exception as e:
                logger.error(f"Consensus loop error: {e}")

            time.sleep(1)  # Check every second

    def _should_start_election(self) -> bool:
        """Check if we should start a leader election"""
        # Simplified: start election if no leader heartbeat in 5 seconds
        return self.leader_id is None or (time.time() - getattr(self, 'last_leader_heartbeat', 0)) > 5

    def _start_election(self):
        """Start leader election"""
        self.consensus_state = ConsensusState.CANDIDATE
        self.term += 1
        self.voted_for = self.node_id

        # Request votes from peers
        vote_request = P2PMessage(
            message_id=f"vote_request_{self.node_id}_{self.term}",
            message_type=MessageType.CONSENSUS_VOTE,
            sender_id=self.node_id,
            receiver_id=None,  # Broadcast
            timestamp=time.time(),
            ttl=3,
            payload={
                'type': 'vote_request',
                'term': self.term,
                'candidate_id': self.node_id,
                'last_log_index': len(self.blockchain.chain),
                'last_log_term': self.term
            }
        )

        self.broadcast_message(vote_request)
        logger.info(f"🗳️ Started election for term {self.term}")

    def _run_election(self):
        """Run leader election"""
        # Simplified election logic
        # In production, this would collect votes and check quorum
        votes_received = 1  # Vote for self
        quorum = max(1, len(self.connections) // 2 + 1)

        if votes_received >= quorum:
            self.consensus_state = ConsensusState.LEADER
            self.leader_id = self.node_id
            logger.info(f"👑 Became leader for term {self.term}")
        else:
            # Election timeout, return to follower
            self.consensus_state = ConsensusState.FOLLOWING
            logger.info("📉 Election failed, returning to follower state")

    def _send_leader_heartbeats(self):
        """Send leader heartbeats"""
        heartbeat = P2PMessage(
            message_id=f"leader_heartbeat_{self.node_id}_{time.time()}",
            message_type=MessageType.CONSENSUS_VOTE,
            sender_id=self.node_id,
            receiver_id=None,
            timestamp=time.time(),
            ttl=1,
            payload={
                'type': 'leader_heartbeat',
                'term': self.term,
                'leader_id': self.node_id
            }
        )

        self.broadcast_message(heartbeat)
        self.last_leader_heartbeat = time.time()

    def _handle_message(self, message: P2PMessage, connection: P2PConnection):
        """Handle incoming message"""
        try:
            handler = self.message_handlers.get(message.message_type)
            if handler:
                response = handler(message)
                if response:
                    connection.send_message(response)
            else:
                logger.warning(f"No handler for message type: {message.message_type}")

        except Exception as e:
            logger.error(f"Error handling message {message.message_id}: {e}")

    def _send_handshake(self, connection: P2PConnection):
        """Send handshake to new connection"""
        handshake = P2PMessage(
            message_id=f"handshake_{self.node_id}_{time.time()}",
            message_type=MessageType.HANDSHAKE,
            sender_id=self.node_id,
            receiver_id=connection.peer_id,
            timestamp=time.time(),
            ttl=1,
            payload={
                'node_id': self.node_id,
                'protocol_version': '1.0',
                'capabilities': ['p2p_sync', 'mining', 'consensus'],
                'blockchain_height': len(self.blockchain.chain),
                'connections': len(self.connections)
            }
        )

        connection.send_message(handshake)

    def _handle_handshake(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle handshake message"""
        # Respond with our handshake
        response = P2PMessage(
            message_id=f"handshake_response_{self.node_id}_{time.time()}",
            message_type=MessageType.HANDSHAKE,
            sender_id=self.node_id,
            receiver_id=message.sender_id,
            timestamp=time.time(),
            ttl=1,
            payload={
                'node_id': self.node_id,
                'protocol_version': '1.0',
                'capabilities': ['p2p_sync', 'mining', 'consensus'],
                'blockchain_height': len(self.blockchain.chain),
                'connections': len(self.connections),
                'consensus_state': self.consensus_state.value,
                'leader_id': self.leader_id
            }
        )

        return response

    def _handle_peer_list(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle peer list message"""
        # Update our peer knowledge
        peers = message.payload.get('peers', [])
        for peer_info in peers:
            # Add peer to discovery system
            if self.p2p_sync:
                self.p2p_sync.peer_discovery.add_peer(
                    peer_id=peer_info['node_id'],
                    address=peer_info['address'],
                    port=peer_info['port'],
                    capabilities=peer_info.get('capabilities', [])
                )

        return None

    def _handle_block_announce(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle block announcement"""
        block_hash = message.payload.get('block_hash')
        block_height = message.payload.get('block_height')

        # Request full block if we don't have it
        if block_hash and block_height > len(self.blockchain.chain):
            request = P2PMessage(
                message_id=f"block_request_{self.node_id}_{time.time()}",
                message_type=MessageType.BLOCK_REQUEST,
                sender_id=self.node_id,
                receiver_id=message.sender_id,
                timestamp=time.time(),
                ttl=3,
                payload={
                    'block_hash': block_hash,
                    'block_height': block_height
                }
            )

            # Send directly to announcer
            self.send_message_to_peer(message.sender_id, request)

        return None

    def _handle_block_request(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle block request"""
        block_hash = message.payload.get('block_hash')

        # Find block and send it
        for block in self.blockchain.chain:
            if block.hash == block_hash:
                response = P2PMessage(
                    message_id=f"block_response_{self.node_id}_{time.time()}",
                    message_type=MessageType.BLOCK_RESPONSE,
                    sender_id=self.node_id,
                    receiver_id=message.sender_id,
                    timestamp=time.time(),
                    ttl=1,
                    payload={
                        'block': block.to_dict()
                    }
                )

                return response

        return None

    def _handle_block_response(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle block response"""
        block_data = message.payload.get('block')
        if block_data and self.p2p_sync:
            # Add block through P2P sync
            self.p2p_sync._validate_and_add_blocks([block_data])

        return None

    def _handle_transaction_announce(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle transaction announcement"""
        tx_hash = message.payload.get('transaction_hash')

        # Request full transaction if we don't have it
        if tx_hash not in [self._calculate_tx_hash(tx) for tx in self.blockchain.pending_transactions]:
            request = P2PMessage(
                message_id=f"tx_request_{self.node_id}_{time.time()}",
                message_type=MessageType.TRANSACTION_REQUEST,
                sender_id=self.node_id,
                receiver_id=message.sender_id,
                timestamp=time.time(),
                ttl=3,
                payload={
                    'transaction_hash': tx_hash
                }
            )

            self.send_message_to_peer(message.sender_id, request)

        return None

    def _handle_mining_share(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle mining share submission"""
        # Forward to team coordinator if we have one
        if self.p2p_sync and hasattr(self.p2p_sync, 'handle_team_message'):
            self.p2p_sync.handle_team_message({
                'team_id': message.payload.get('team_id'),
                'message_type': 'share_submission',
                'payload': message.payload
            })

        return None

    def _handle_team_update(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle team update message"""
        # Forward to team coordinator
        if self.p2p_sync and hasattr(self.p2p_sync, 'handle_team_message'):
            self.p2p_sync.handle_team_message(message.payload)

        return None

    def _handle_consensus_vote(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle consensus vote message"""
        vote_type = message.payload.get('type')

        if vote_type == 'vote_request':
            # Respond to vote request
            response = P2PMessage(
                message_id=f"vote_response_{self.node_id}_{time.time()}",
                message_type=MessageType.CONSENSUS_VOTE,
                sender_id=self.node_id,
                receiver_id=message.sender_id,
                timestamp=time.time(),
                ttl=1,
                payload={
                    'type': 'vote_response',
                    'term': message.payload['term'],
                    'vote_granted': True,
                    'voter_id': self.node_id
                }
            )

            return response

        elif vote_type == 'leader_heartbeat':
            # Update leader information
            self.leader_id = message.payload.get('leader_id')
            self.last_leader_heartbeat = time.time()
            self.consensus_state = ConsensusState.FOLLOWING

        return None

    def _handle_heartbeat(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle heartbeat message"""
        # Heartbeats are handled in the connection class
        # Just update our knowledge of peer state
        return None

    def _handle_disconnect(self, message: P2PMessage) -> Optional[P2PMessage]:
        """Handle disconnect message"""
        peer_id = message.sender_id
        if peer_id in self.connections:
            self.connections[peer_id].close()
            del self.connections[peer_id]
            logger.info(f"🔌 Peer {peer_id} disconnected gracefully")

        return None

    def _calculate_tx_hash(self, tx: Dict) -> str:
        """Calculate transaction hash"""
        tx_string = json.dumps(tx, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def announce_new_block(self, block_data: Dict):
        """Announce new block to network"""
        announcement = P2PMessage(
            message_id=f"block_announce_{self.node_id}_{time.time()}",
            message_type=MessageType.BLOCK_ANNOUNCE,
            sender_id=self.node_id,
            receiver_id=None,  # Broadcast
            timestamp=time.time(),
            ttl=5,  # Allow 5 hops
            payload={
                'block_hash': block_data.get('hash'),
                'block_height': block_data.get('index'),
                'transactions': len(block_data.get('transactions', [])),
                'miner': block_data.get('miner')
            }
        )

        self.broadcast_message(announcement)
        self.stats['blocks_propagated'] += 1

    def announce_transaction(self, tx_data: Dict):
        """Announce new transaction to network"""
        announcement = P2PMessage(
            message_id=f"tx_announce_{self.node_id}_{time.time()}",
            message_type=MessageType.TRANSACTION_ANNOUNCE,
            sender_id=self.node_id,
            receiver_id=None,  # Broadcast
            timestamp=time.time(),
            ttl=3,  # Allow 3 hops
            payload={
                'transaction_hash': self._calculate_tx_hash(tx_data),
                'transaction_type': tx_data.get('type'),
                'amount': tx_data.get('amount', 0)
            }
        )

        self.broadcast_message(announcement)
        self.stats['transactions_propagated'] += 1

    def get_network_stats(self) -> Dict[str, Any]:
        """Get P2P network statistics"""
        return {
            'node_id': self.node_id,
            'connections': len(self.connections),
            'consensus_state': self.consensus_state.value,
            'leader_id': self.leader_id,
            'term': self.term,
            **self.stats
        }


# Global P2P instance
p2p_protocol: Optional[PiSecureP2P] = None

def start_p2p_protocol(node_id: str, port: int = 3142,
                      blockchain: Optional[SignChain] = None,
                      p2p_sync: Optional[P2PSyncManager] = None) -> PiSecureP2P:
    """Start PiSecure P2P protocol"""
    global p2p_protocol
    p2p_protocol = PiSecureP2P(node_id, port, blockchain, p2p_sync)
    p2p_protocol.start()
    return p2p_protocol

def stop_p2p_protocol():
    """Stop PiSecure P2P protocol"""
    global p2p_protocol
    if p2p_protocol:
        p2p_protocol.stop()
        p2p_protocol = None

def get_p2p_protocol() -> Optional[PiSecureP2P]:
    """Get global P2P protocol instance"""
    return p2p_protocol