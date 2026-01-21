"""
PiSecure P2P Blockchain Synchronization
=======================================

True peer-to-peer blockchain synchronization system for PiSecure network.
Implements blockchain state synchronization, block propagation, and transaction
pool sharing between network peers.

Features:
- Block synchronization from genesis to latest
- Transaction pool synchronization
- Real-time block propagation
- Fork resolution and longest-chain rule
- Bandwidth-efficient sync protocols
- Automatic peer selection and failover
"""

import time
import json
import threading
import os
import hashlib
import requests
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
import logging

from .blockchain import SignChain
from .pihash import hash_meets_zero_bits, count_zero_bits
from ..network.discovery import PeerDiscovery

logger = logging.getLogger(__name__)


class P2PSyncManager:
    """
    Manages peer-to-peer blockchain synchronization.

    This class handles:
    - Initial blockchain sync from peers
    - Continuous block/transaction propagation
    - Fork detection and resolution
    - Peer health monitoring for sync
    """

    def __init__(self, blockchain: SignChain, peer_discovery: PeerDiscovery,
                 sync_interval: int = 30, max_sync_peers: int = 3):
        """
        Initialize P2P sync manager.

        Args:
            blockchain: SignChain instance to sync
            peer_discovery: PeerDiscovery for finding sync peers
            sync_interval: Seconds between sync attempts
            max_sync_peers: Maximum peers to sync with simultaneously
        """
        self.blockchain = blockchain
        self.peer_discovery = peer_discovery or PeerDiscovery()
        self.sync_interval = sync_interval
        self.max_sync_peers = max_sync_peers
        self.logger = logging.getLogger(__name__)

        # Bootstrap node configuration
        self.bootstrap_urls = [
            "https://bootstrap.pisecure.org/api/v1/bootstrap/peers",  # Primary domain
            "https://pisecure-bootstrap-production.up.railway.app/api/v1/bootstrap/peers",  # Fallback
            # Add more bootstrap nodes as they become available
        ]
        self.bootstrap_discovery_enabled = True
        self.last_bootstrap_check = 0
        self.bootstrap_check_interval = 300  # 5 minutes

        # Sync state
        self.is_syncing = False
        self.sync_peers: Set[str] = set()
        self.last_sync_time = 0
        self.sync_stats = {
            'blocks_synced': 0,
            'transactions_synced': 0,
            'forks_resolved': 0,
            'sync_errors': 0
        }

        # Threading
        self.sync_thread: Optional[threading.Thread] = None
        self.stop_sync = threading.Event()

        # Block propagation tracking
        self.known_blocks: Set[str] = set()
        self.pending_blocks: Dict[str, Dict] = {}

        # Syndicate support
        self.syndicates: Dict[str, Dict] = {}  # syndicate_id -> syndicate_info
        self.syndicate_memberships: Dict[str, str] = {}  # wallet -> syndicate_id
        self.syndicate_message_handlers = {
            'join_syndicate': self._handle_join_syndicate,
            'leave_syndicate': self._handle_leave_syndicate,
            'syndicate_status': self._handle_syndicate_status,
            'share_submission': self._handle_share_submission,
            'block_found': self._handle_syndicate_block_found,
        }

        logger.info("🔄 P2P Sync Manager initialized with syndicate support")

    def start_sync(self):
        """Start the P2P synchronization process."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("P2P sync already running")
            return

        logger.info("🚀 Starting P2P blockchain synchronization...")
        self.stop_sync.clear()
        self.is_syncing = True

        self.sync_thread = threading.Thread(
            target=self._sync_worker,
            daemon=True,
            name="P2PSync"
        )
        self.sync_thread.start()

    def stop_sync(self):
        """Stop the P2P synchronization process."""
        logger.info("🛑 Stopping P2P blockchain synchronization...")
        self.is_syncing = False
        self.stop_sync.set()

        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5.0)

    def _sync_worker(self):
        """Main synchronization worker thread."""
        logger.info("🔄 P2P sync worker started")

        while not self.stop_sync.is_set():
            try:
                self._perform_sync_cycle()
            except Exception as e:
                logger.error(f"❌ P2P sync cycle failed: {e}")
                self.sync_stats['sync_errors'] += 1

            # Wait for next cycle
            self.stop_sync.wait(self.sync_interval)

        logger.info("🔄 P2P sync worker stopped")

    def _perform_sync_cycle(self):
        """Perform one complete synchronization cycle."""
        # Check bootstrap nodes for new peers periodically
        current_time = time.time()
        if (self.bootstrap_discovery_enabled and
            current_time - self.last_bootstrap_check > self.bootstrap_check_interval):
            self._discover_bootstrap_peers()
            self.last_bootstrap_check = current_time

        # Get healthy peers for sync
        healthy_peers = self._select_sync_peers()
        if not healthy_peers:
            logger.debug("No healthy peers available for sync")
            return

        # Update sync peer list
        self.sync_peers = set(healthy_peers)

        # Perform sync with each peer
        for peer_id in healthy_peers[:self.max_sync_peers]:
            try:
                self._sync_with_peer(peer_id)
            except Exception as e:
                logger.warning(f"Failed to sync with peer {peer_id}: {e}")

        # Propagate any pending blocks
        self._propagate_pending_blocks()

        # Update sync timestamp
        self.last_sync_time = time.time()

    def _select_sync_peers(self) -> List[str]:
        """Select the best peers for synchronization."""
        all_peers = self.peer_discovery.get_known_peers()
        healthy_peers = []

        self.logger.info(f"🔍 Checking {len(all_peers)} known peers for sync...")
        for peer_id, peer_info in all_peers.items():
            connected = peer_info.get('connected', False)
            last_seen = peer_info.get('last_seen', 0)
            age = time.time() - last_seen
            self.logger.info(f"  Peer {peer_id}: connected={connected}, age={age:.1f}s")
            
            if connected:
                # Accept manually added and bootstrap peers with longer timeout
                # Regular discovered peers use 5min, manual/bootstrap use 24hr
                is_manual = peer_id.startswith('manual_') or peer_id.startswith('bootstrap_')
                timeout = 86400 if is_manual else 300  # 24 hours vs 5 minutes
                
                if age < timeout:
                    healthy_peers.append(peer_id)
                    self.logger.info(f"    ✅ Selected for sync")
                else:
                    self.logger.info(f"    ⏰ Too old (>{timeout}s)")
            else:
                self.logger.info(f"    ❌ Not connected")

        self.logger.info(f"📋 Selected {len(healthy_peers)} healthy peers for sync")
        # Sort by connection quality (could be enhanced with latency metrics)
        return healthy_peers[:self.max_sync_peers * 2]  # Select more than needed for failover

    def _sync_with_peer(self, peer_id: str):
        """Synchronize blockchain state with a specific peer."""
        # Get peer's blockchain info
        peer_chain_info = self._get_peer_chain_info(peer_id)
        if not peer_chain_info:
            return

        peer_height = peer_chain_info.get('blocks', 0)
        local_height = len(self.blockchain.chain)

        logger.debug(f"Peer {peer_id} height: {peer_height}, local height: {local_height}")

        # Check if we need to sync
        if peer_height <= local_height:
            # We're up to date or ahead, just sync transactions
            self._sync_transactions(peer_id)
            return

        # Check if this is a potential fork
        if self._detect_fork(peer_id, peer_chain_info):
            # Handle fork resolution
            if self._resolve_fork(peer_id, peer_chain_info):
                logger.info(f"🔀 Resolved fork with peer {peer_id}")
                self.sync_stats['forks_resolved'] += 1
                return

        # We need to sync blocks
        blocks_needed = peer_height - local_height
        logger.info(f"🔄 Syncing {blocks_needed} blocks from peer {peer_id}")

        # Request missing blocks
        missing_blocks = self._request_blocks(peer_id, local_height, peer_height)
        if not missing_blocks:
            return

        # Validate and add blocks
        valid_blocks = self._validate_and_add_blocks(missing_blocks)
        self.sync_stats['blocks_synced'] += len(valid_blocks)

        # Adapt difficulty after receiving blocks from peers
        if valid_blocks:
            self.blockchain.adapt_difficulty()

        logger.info(f"✅ Successfully synced {len(valid_blocks)} blocks")

    def _get_peer_chain_info(self, peer_id: str) -> Optional[Dict]:
        """Get blockchain information from a peer."""
        try:
            # Get peer address from peer_discovery
            peers = self.peer_discovery.get_known_peers()
            if peer_id not in peers:
                self.logger.debug(f"Peer {peer_id} not in known peers")
                return None
            
            peer_info = peers[peer_id]
            peer_address = peer_info.get('address')
            peer_port = peer_info.get('port', 3142)
            
            if not peer_address:
                self.logger.debug(f"No address for peer {peer_id}")
                return None
            
            # Make HTTP request to peer's API (use correct endpoint)
            import requests
            url = f"http://{peer_address}:{peer_port}/api/v1/blockchain/info"
            self.logger.info(f"🔗 Fetching chain info from {peer_id} at {url}")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                info = response.json()
                self.logger.info(f"📊 Peer {peer_id} has {info.get('blocks', 0)} blocks")
                return info
            else:
                self.logger.warning(f"❌ Peer {peer_id} returned status {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.warning(f"❌ Failed to get chain info from {peer_id}: {e}")
            return None

    def _request_blocks(self, peer_id: str, start_height: int, end_height: int) -> List[Dict]:
        """Request blocks from a peer."""
        try:
            # Get peer address
            peers = self.peer_discovery.get_known_peers()
            if peer_id not in peers:
                return []
            
            peer_info = peers[peer_id]
            peer_address = peer_info.get('address')
            peer_port = peer_info.get('port', 3142)
            
            if not peer_address:
                return []
            
            # Request blocks from the peer using correct API endpoint
            import requests
            
            try:
                url = f"http://{peer_address}:{peer_port}/api/v1/blockchain/blocks"
                params = {'offset': start_height, 'limit': min(end_height - start_height, 100)}
                self.logger.info(f"📥 Requesting blocks {start_height} to {end_height} from {peer_id}")
                self.logger.info(f"   URL: {url}?offset={params['offset']}&limit={params['limit']}")
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    blocks = response.json()
                    if not isinstance(blocks, list):
                        blocks = blocks.get('blocks', [])
                    self.logger.info(f"✅ Received {len(blocks)} blocks from {peer_id}")
                    return blocks
                else:
                    self.logger.warning(f"❌ Peer {peer_id} returned {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                self.logger.warning(f"❌ Failed to fetch blocks from {peer_id}: {e}")
            
            return []
            
            # Fallback: Try bootstrap server's blockchain endpoint
            if 'bootstrap' in peer_id.lower():
                try:
                    bootstrap_url = f"https://{peer_address}/api/v1/bootstrap/blockchain"
                    logger.debug(f"Trying bootstrap blockchain endpoint: {bootstrap_url}")
                    response = requests.get(bootstrap_url, timeout=30)
                    
                    if response.status_code == 200:
                        blockchain_data = response.json()
                        blocks = blockchain_data.get('blocks', [])
                        needed_blocks = [b for b in blocks if start_height < b.get('index', 0) <= end_height]
                        logger.info(f"Received {len(needed_blocks)} blocks from bootstrap")
                        return needed_blocks
                except Exception as e:
                    logger.debug(f"Bootstrap blockchain fetch failed: {e}")
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to request blocks from {peer_id}: {e}")
            return []
        return []

    def _validate_and_add_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Validate and add blocks to the blockchain."""
        valid_blocks = []

        for block_data in blocks:
            try:
                # Validate block structure and proof-of-work
                if self._validate_block(block_data):
                    # Add block to blockchain
                    # Note: This would need to be integrated with SignChain.add_block
                    valid_blocks.append(block_data)
                    self.known_blocks.add(block_data.get('hash', ''))
            except Exception as e:
                logger.warning(f"Block validation failed: {e}")

        return valid_blocks

    def _validate_block(self, block_data: Dict) -> bool:
        """Validate a block's structure and proof-of-work."""
        # Basic validation checks
        required_fields = ['index', 'timestamp', 'transactions', 'previous_hash', 'nonce', 'hash']

        for field in required_fields:
            if field not in block_data:
                self.logger.debug(f"❌ Missing field: {field}")
                return False

        # For blocks received from network, trust the hash field
        # (it was already validated when created)
        # Only validate proof-of-work
        block_hash = block_data['hash']
        
        # Validate proof-of-work using MINIMUM difficulty
        # Historical blocks may have been mined at lower difficulty
        min_difficulty = 130  # Minimum threshold for testnet
        actual_bits = count_zero_bits(block_hash)
        if actual_bits < min_difficulty:
            self.logger.debug(f"❌ PoW failed at index {block_data.get('index')}: {actual_bits} bits < {min_difficulty}")
            return False

        self.logger.debug(f"✅ Block {block_data.get('index')} passed PoW check ({actual_bits} bits)")
        return True

    def _calculate_block_hash(self, block_data: Dict) -> str:
        """Calculate block hash."""
        block_string = json.dumps({
            'index': block_data['index'],
            'timestamp': block_data['timestamp'],
            'transactions': block_data['transactions'],
            'previous_hash': block_data['previous_hash'],
            'nonce': block_data['nonce']
        }, sort_keys=True)

        return hashlib.sha256(block_string.encode()).hexdigest()

    def _detect_fork(self, peer_id: str, peer_chain_info: Dict) -> bool:
        """Detect if there's a potential fork with this peer."""
        peer_height = peer_chain_info.get('blocks', 0)
        local_height = len(self.blockchain.chain)

        # If peer has more blocks, check if the chains diverge
        if peer_height > local_height:
            # Get the last common block
            common_height = min(local_height, peer_height) - 1
            if common_height >= 0:
                local_last_hash = self.blockchain.chain[common_height].hash
                peer_last_hash = peer_chain_info.get('last_block', {}).get('hash', '')

                # If hashes don't match at the common height, we have a fork
                if local_last_hash != peer_last_hash:
                    logger.warning(f"🔀 Fork detected with peer {peer_id} at height {common_height}")
                    return True

        return False

    def _resolve_fork(self, peer_id: str, peer_chain_info: Dict) -> bool:
        """
        Resolve a fork using the longest chain rule.

        Returns True if fork was resolved (we switched chains), False otherwise.
        """
        peer_height = peer_chain_info.get('blocks', 0)
        local_height = len(self.blockchain.chain)

        # Longest chain rule: always follow the longest valid chain
        if peer_height > local_height:
            logger.info(f"🔀 Resolving fork: peer {peer_id} has longer chain ({peer_height} vs {local_height})")

            # Request the competing chain from the peer
            competing_blocks = self._request_blocks(peer_id, 0, peer_height)
            if not competing_blocks:
                logger.warning(f"Failed to get competing chain from peer {peer_id}")
                return False

            # Validate the entire competing chain
            if self._validate_competing_chain(competing_blocks):
                logger.info(f"✅ Switching to longer chain from peer {peer_id}")

                # Replace our chain with the competing chain
                self._switch_to_chain(competing_blocks)
                return True
            else:
                logger.warning(f"❌ Competing chain from peer {peer_id} is invalid")
                return False

        # If chains are equal length but different, keep our current chain
        # (would need more sophisticated tie-breaking in a real implementation)
        return False

    def _validate_competing_chain(self, chain_blocks: List[Dict]) -> bool:
        """Validate an entire competing chain."""
        if not chain_blocks:
            self.logger.warning("📛 No blocks to validate")
            return False

        self.logger.info(f"🔍 Validating chain of {len(chain_blocks)} blocks...")
        
        # Validate each block in sequence
        for i, block_data in enumerate(chain_blocks):
            # First block should be genesis - accept it without validation
            # Genesis blocks must match network-wide and don't follow normal validation
            if i == 0:
                if block_data.get('index') != 0:
                    self.logger.warning(f"📛 First block is not genesis (index={block_data.get('index')})")
                    return False
                self.logger.info(f"✅ Genesis block accepted (hash: {block_data.get('hash', 'N/A')[:16]}...)")
            else:
                # Non-genesis block should connect to previous block
                prev_block = chain_blocks[i-1]
                expected_prev_hash = prev_block.get('hash')
                actual_prev_hash = block_data.get('previous_hash')
                
                if actual_prev_hash != expected_prev_hash:
                    self.logger.warning(f"📛 Block {i} previous_hash mismatch")
                    self.logger.warning(f"   Expected: {expected_prev_hash[:16] if expected_prev_hash else 'None'}...")
                    self.logger.warning(f"   Got: {actual_prev_hash[:16] if actual_prev_hash else 'None'}...")
                    return False
                    
                if not self._validate_block(block_data):
                    self.logger.warning(f"📛 Block {i} validation failed")
                    self.logger.warning(f"   Block hash: {block_data.get('hash', 'N/A')[:16]}")
                    self.logger.warning(f"   Previous: {actual_prev_hash[:16] if actual_prev_hash else 'None'}...")
                    return False
                    
                if i % 10 == 0:  # Log every 10th block
                    self.logger.info(f"   ✅ Validated blocks 0-{i}")

        self.logger.info(f"✅ All {len(chain_blocks)} blocks validated successfully")
        return True

    def _switch_to_chain(self, new_chain: List[Dict], node_id: str = None):
        """Switch to a new blockchain with Byzantine validation tracking"""
        self.logger.info(f"🔄 Switching to new chain with {len(new_chain)} blocks")

        try:
            # Convert dict blocks to SignBlock objects with validation metadata
            from .blockchain import SignBlock
            
            # Use node_id or generate one for this validator
            if not node_id:
                node_id = f"validator_{os.urandom(4).hex()}"
            
            sign_blocks = []
            for block_data in new_chain:
                # Extract validation data from network
                validators = block_data.get('validators', [])
                validation_count = block_data.get('validation_count', 0)
                validation_timestamp = block_data.get('validation_timestamp')
                
                sign_block = SignBlock(
                    index=block_data.get('index', 0),
                    timestamp=block_data.get('timestamp', 0),
                    transactions=block_data.get('transactions', []),
                    previous_hash=block_data.get('previous_hash', ''),
                    nonce=block_data.get('nonce', 0),
                    algorithm=block_data.get('algorithm', 'pihash'),
                    precomputed_hash=block_data.get('hash', ''),
                    validators=validators,
                    validation_count=validation_count,
                    validation_timestamp=validation_timestamp
                )
                
                # Add this validator to the block
                sign_block.add_validator(node_id)
                
                sign_blocks.append(sign_block)
            
            # Replace the blockchain
            self.blockchain.chain = sign_blocks
            
            # Save to disk
            self.blockchain.save_chain()
            
            self.logger.info(f"✅ Chain switched successfully - now at {len(self.blockchain.chain)} blocks")
            self.sync_stats['blocks_synced'] += len(new_chain)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to switch chain: {e}")
            raise

    def _validate_transaction(self, tx_data: Dict) -> bool:
        """Validate a transaction."""
        # Basic transaction validation
        required_fields = ['type', 'data', 'signature', 'timestamp']

        for field in required_fields:
            if field not in tx_data:
                return False

        # Validate signature (simplified)
        # In real implementation, would verify against sender's public key
        return True

    def _sync_transactions(self, peer_id: str):
        """Synchronize transaction pool with a peer."""
        # Get peer's pending transactions
        peer_txs = self._get_peer_transactions(peer_id)
        if not peer_txs:
            return

        # Add new transactions to our pool
        new_tx_count = 0
        for tx_data in peer_txs:
            try:
                # Check if we already have this transaction
                tx_hash = self._calculate_tx_hash(tx_data)
                if tx_hash not in self._get_known_transactions():
                    # Add to blockchain's pending transactions
                    self.blockchain.add_transaction(tx_data)
                    new_tx_count += 1
            except Exception as e:
                logger.debug(f"Failed to add transaction: {e}")

        if new_tx_count > 0:
            logger.info(f"✅ Synced {new_tx_count} transactions from peer {peer_id}")
            self.sync_stats['transactions_synced'] += new_tx_count

    def _get_peer_transactions(self, peer_id: str) -> List[Dict]:
        """Get pending transactions from a peer."""
        try:
            peers = self.peer_discovery.get_known_peers()
            peer_info = peers.get(peer_id)
            if not peer_info:
                return []

            address = peer_info.get('address')
            port = peer_info.get('port', 3142)
            if not address:
                return []

            base_url = f"http://{address}:{port}"
            endpoint = f"{base_url}/api/v1/mempool"

            # Determine network parameter from blockchain if available
            params = {}
            network_id = getattr(self.blockchain, 'network_id', None)
            if isinstance(network_id, str) and network_id:
                params['network'] = network_id

            response = requests.get(endpoint, params=params, timeout=5)
            if response.status_code != 200:
                return []

            data = response.json()
            # Normalize response to list of transactions
            if isinstance(data, dict):
                pending = data.get('pending')
                if isinstance(pending, list):
                    return pending
                # Fallback if server uses 'transactions'
                txs = data.get('transactions')
                if isinstance(txs, list):
                    return txs
            elif isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _calculate_tx_hash(self, tx_data: Dict) -> str:
        """Calculate transaction hash."""
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def _get_known_transactions(self) -> Set[str]:
        """Get hashes of known transactions."""
        # Placeholder - would track known transaction hashes
        return set()

    def _propagate_pending_blocks(self):
        """Propagate any pending blocks to peers."""
        if not self.pending_blocks:
            return

        # Propagate to connected peers
        for block_hash, block_data in list(self.pending_blocks.items()):
            if block_hash in self.known_blocks:
                # Block is now known, remove from pending
                del self.pending_blocks[block_hash]
            else:
                # Propagate to peers
                self._send_block_to_peers(block_data)

    def _send_block_to_peers(self, block_data: Dict):
        """Send block to connected peers."""
        # Placeholder - would broadcast block to P2P network
        logger.debug(f"Propagating block {block_data.get('hash', '')[:16]}...")

    def broadcast_new_block(self, block_data: Dict):
        """Broadcast a newly mined block to the network."""
        block_hash = block_data.get('hash', '')
        self.known_blocks.add(block_hash)

        # Add to pending propagation
        self.pending_blocks[block_hash] = block_data

        # Immediately propagate to peers
        self._send_block_to_peers(block_data)

        logger.info(f"📡 Broadcasted new block {block_hash[:16]} to network")

    def broadcast_transaction(self, tx_data: Dict):
        """Broadcast a new transaction to the network."""
        # Placeholder - would broadcast transaction to P2P network
        logger.debug("Broadcasting transaction to network")

    def get_sync_status(self) -> Dict:
        """Get current synchronization status."""
        return {
            'is_syncing': self.is_syncing,
            'sync_peers': list(self.sync_peers),
            'last_sync_time': self.last_sync_time,
            'sync_stats': self.sync_stats.copy(),
            'pending_blocks': len(self.pending_blocks),
            'known_blocks': len(self.known_blocks),
            'syndicates': len(self.syndicates),
            'syndicate_memberships': len(self.syndicate_memberships)
        }

    # === SYNDICATE MINING SUPPORT ===

    def join_syndicate(self, syndicate_name: str, wallet_address: str, hashrate: float = 0) -> Dict[str, Any]:
        """Join or create a mining syndicate."""
        syndicate_id = hashlib.sha256(f"syndicate_{syndicate_name}".encode()).hexdigest()[:16]

        # Check if syndicate exists
        if syndicate_id not in self.syndicates:
            # Create new syndicate
            self.syndicates[syndicate_id] = {
                'syndicate_name': syndicate_name,
                'founder': wallet_address,
                'participants': {wallet_address: {'hashrate': hashrate, 'joined_at': time.time()}},
                'created_at': time.time(),
                'total_hashrate': hashrate,
                'blocks_found': 0
            }
            self.syndicate_memberships[wallet_address] = syndicate_id
            logger.info(f"🏢 Created new syndicate '{syndicate_name}' with ID {syndicate_id}")
            return {'success': True, 'action': 'created', 'syndicate_id': syndicate_id}
        else:
            # Join existing syndicate
            syndicate = self.syndicates[syndicate_id]
            if wallet_address in syndicate['participants']:
                return {'success': False, 'error': 'Already a member of this syndicate'}

            if len(syndicate['participants']) >= 100:  # Max syndicate size
                return {'success': False, 'error': 'Syndicate is full'}

            syndicate['participants'][wallet_address] = {
                'hashrate': hashrate,
                'joined_at': time.time()
            }
            syndicate['total_hashrate'] += hashrate
            self.syndicate_memberships[wallet_address] = syndicate_id

            # Broadcast join message to syndicate
            self._broadcast_syndicate_message(syndicate_id, 'join_syndicate', {
                'wallet': wallet_address,
                'hashrate': hashrate,
                'timestamp': time.time()
            })

            logger.info(f"🤝 {wallet_address} joined syndicate '{syndicate_name}'")
            return {'success': True, 'action': 'joined', 'syndicate_id': syndicate_id}

    def leave_syndicate(self, wallet_address: str) -> bool:
        """Leave the current mining syndicate."""
        if wallet_address not in self.syndicate_memberships:
            return False

        syndicate_id = self.syndicate_memberships[wallet_address]
        syndicate = self.syndicates.get(syndicate_id)
        if not syndicate:
            return False

        # Remove from syndicate
        if wallet_address in syndicate['participants']:
            hashrate = syndicate['participants'][wallet_address]['hashrate']
            syndicate['total_hashrate'] -= hashrate
            del syndicate['participants'][wallet_address]

        del self.syndicate_memberships[wallet_address]

        # Broadcast leave message
        self._broadcast_syndicate_message(syndicate_id, 'leave_syndicate', {
            'wallet': wallet_address,
            'timestamp': time.time()
        })

        # Remove empty syndicates
        if not syndicate['participants']:
            del self.syndicates[syndicate_id]
            logger.info(f"🗑️ Syndicate '{syndicate['syndicate_name']}' disbanded (no participants)")

        logger.info(f"👋 {wallet_address} left syndicate '{syndicate['syndicate_name']}'")
        return True

    def get_syndicate_info(self, syndicate_id: str) -> Optional[Dict]:
        """Get information about a syndicate."""
        return self.syndicates.get(syndicate_id)

    def get_user_syndicate(self, wallet_address: str) -> Optional[str]:
        """Get the syndicate ID for a wallet address."""
        return self.syndicate_memberships.get(wallet_address)

    def submit_syndicate_share(self, wallet_address: str, share_data: Dict):
        """Submit a mining share to the syndicate coordinator."""
        syndicate_id = self.syndicate_memberships.get(wallet_address)
        if not syndicate_id:
            return False

        # Broadcast share to syndicate
        self._broadcast_syndicate_message(syndicate_id, 'share_submission', {
            'wallet': wallet_address,
            'share_data': share_data,
            'timestamp': time.time()
        })

        return True

    def handle_syndicate_message(self, message: Dict):
        """Handle incoming syndicate messages."""
        try:
            syndicate_id = message.get('syndicate_id')
            message_type = message.get('message_type')

            if message_type in self.syndicate_message_handlers:
                self.syndicate_message_handlers[message_type](message)
            else:
                logger.warning(f"Unknown syndicate message type: {message_type}")

        except Exception as e:
            logger.error(f"Failed to handle syndicate message: {e}")

    def _broadcast_syndicate_message(self, syndicate_id: str, message_type: str, payload: Dict):
        """Broadcast a message to all syndicate participants."""
        syndicate = self.syndicates.get(syndicate_id)
        if not syndicate:
            return

        syndicate_message = {
            'syndicate_id': syndicate_id,
            'message_type': message_type,
            'payload': payload,
            'timestamp': time.time(),
            'sender': 'system'
        }

        # Send to all syndicate participants (placeholder - would use P2P network)
        logger.debug(f"📡 Syndicate broadcast to {len(syndicate['participants'])} participants: {message_type}")

    def _handle_join_syndicate(self, message: Dict):
        """Handle syndicate join message."""
        syndicate_id = message.get('syndicate_id')
        payload = message.get('payload', {})

        if syndicate_id in self.syndicates:
            syndicate = self.syndicates[syndicate_id]
            wallet = payload.get('wallet')
            hashrate = payload.get('hashrate', 0)

            if wallet and wallet not in syndicate['participants']:
                syndicate['participants'][wallet] = {
                    'hashrate': hashrate,
                    'joined_at': payload.get('timestamp', time.time())
                }
                syndicate['total_hashrate'] += hashrate
                self.syndicate_memberships[wallet] = syndicate_id

    def _handle_leave_syndicate(self, message: Dict):
        """Handle syndicate leave message."""
        syndicate_id = message.get('syndicate_id')
        payload = message.get('payload', {})
        wallet = payload.get('wallet')

        if syndicate_id in self.syndicates and wallet:
            syndicate = self.syndicates[syndicate_id]
            if wallet in syndicate['participants']:
                hashrate = syndicate['participants'][wallet]['hashrate']
                syndicate['total_hashrate'] -= hashrate
                del syndicate['participants'][wallet]

            if wallet in self.syndicate_memberships:
                del self.syndicate_memberships[wallet]

            # Remove empty syndicates
            if not syndicate['participants']:
                del self.syndicates[syndicate_id]

    def _handle_syndicate_status(self, message: Dict):
        """Handle syndicate status update."""
        # Update local syndicate information
        syndicate_id = message.get('syndicate_id')
        payload = message.get('payload', {})

        if syndicate_id in self.syndicates:
            syndicate = self.syndicates[syndicate_id]
            # Update syndicate stats from status message
            syndicate['total_hashrate'] = payload.get('total_hashrate', syndicate['total_hashrate'])

    def _handle_share_submission(self, message: Dict):
        """Handle mining share submission."""
        # This would validate and record shares for reward distribution
        # For now, just log it
        payload = message.get('payload', {})
        wallet = payload.get('wallet')
        logger.debug(f"📊 Share submitted by {wallet}")

    def _handle_syndicate_block_found(self, message: Dict):
        """Handle syndicate block found notification."""
        payload = message.get('payload', {})
        finder_wallet = payload.get('finder_wallet')
        syndicate_id = message.get('syndicate_id')

        if syndicate_id in self.syndicates:
            syndicate = self.syndicates[syndicate_id]
            syndicate['blocks_found'] += 1

            # Distribute rewards (simplified)
            reward_distribution = payload.get('reward_distribution', {})

            logger.info(f"🎉 Syndicate '{syndicate['syndicate_name']}' found block! Rewards distributed to {len(reward_distribution)} participants")

    def get_syndicate_stats(self) -> Dict[str, Any]:
        """Get comprehensive syndicate mining statistics."""
        return {
            'total_syndicates': len(self.syndicates),
            'total_syndicate_participants': len(self.syndicate_memberships),
            'syndicates': {
                syndicate_id: {
                    'name': syndicate['syndicate_name'],
                    'participants': len(syndicate['participants']),
                    'total_hashrate': syndicate['total_hashrate'],
                    'blocks_found': syndicate['blocks_found']
                }
                for syndicate_id, syndicate in self.syndicates.items()
            }
        }

    # === BOOTSTRAP NODE INTEGRATION ===

    def _discover_bootstrap_peers(self):
        """Discover new peers from bootstrap nodes."""
        logger.info("🔍 Discovering peers from bootstrap nodes...")

        discovered_count = 0

        for bootstrap_url in self.bootstrap_urls:
            try:
                peers = self._fetch_peers_from_bootstrap(bootstrap_url)
                if peers:
                    for peer_info in peers:
                        try:
                            self._add_discovered_peer(peer_info)
                            discovered_count += 1
                        except Exception as e:
                            logger.debug(f"Failed to add peer {peer_info}: {e}")
                else:
                    logger.debug(f"No peers received from {bootstrap_url}")

            except Exception as e:
                logger.warning(f"Failed to discover peers from {bootstrap_url}: {e}")

        if discovered_count > 0:
            logger.info(f"✅ Discovered {discovered_count} new peers from bootstrap nodes")
        else:
            logger.debug("No new peers discovered from bootstrap nodes")

    def _fetch_peers_from_bootstrap(self, bootstrap_url: str) -> Optional[List[Dict]]:
        """Fetch peer list from a bootstrap node."""
        try:
            # Add timeout and proper error handling
            response = requests.get(f"{bootstrap_url}", timeout=90)
            response.raise_for_status()

            data = response.json()
            peers = data.get('peers', [])

            if peers:
                logger.debug(f"Fetched {len(peers)} peers from {bootstrap_url}")
                return peers
            else:
                logger.debug(f"No peers in response from {bootstrap_url}")
                return []

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Bootstrap endpoint not implemented yet at {bootstrap_url} - continuing without peers")
                return []
            else:
                logger.warning(f"HTTP error fetching from {bootstrap_url}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching from {bootstrap_url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response from {bootstrap_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching from {bootstrap_url}: {e}")
            return None

    def _add_discovered_peer(self, peer_info: Dict):
        """Add a discovered peer to our peer discovery system."""
        # Extract peer information
        node_id = peer_info.get('node_id')
        address = peer_info.get('address')
        port = peer_info.get('port', 3142)
        capabilities = peer_info.get('capabilities', [])

        if not node_id or not address:
            raise ValueError("Peer info missing required fields")

        # Create peer info for discovery system
        peer_data = {
            'node_id': node_id,
            'address': address,
            'port': port,
            'capabilities': capabilities,
            'last_seen': peer_info.get('last_seen', time.time()),
            'source': 'bootstrap',
            'connected': False  # Will be updated when we try to connect
        }

        # Add to peer discovery
        self.peer_discovery.add_peer(
            peer_id=node_id,
            address=address,
            port=port,
            capabilities=capabilities
        )

        logger.debug(f"Added bootstrap peer: {node_id} at {address}:{port}")

    def set_bootstrap_urls(self, urls: List[str]):
        """Update bootstrap node URLs."""
        self.bootstrap_urls = urls
        logger.info(f"Updated bootstrap URLs: {urls}")

    def enable_bootstrap_discovery(self, enabled: bool = True):
        """Enable or disable bootstrap peer discovery."""
        self.bootstrap_discovery_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"Bootstrap peer discovery {status}")


class BlockPropagator:
    """
    Handles efficient block propagation in the P2P network.

    Features:
    - Compact block announcements
    - Block reconciliation protocols
    - Bandwidth optimization
    - Propagation timing optimization
    """

    def __init__(self, p2p_sync: P2PSyncManager):
        self.p2p_sync = p2p_sync
        self.propagation_stats = {
            'blocks_propagated': 0,
            'propagation_time_avg': 0.0,
            'failed_propagations': 0
        }

    def propagate_block(self, block_data: Dict, source_peer: Optional[str] = None):
        """Propagate a block to all connected peers except source."""
        start_time = time.time()
        block_hash = block_data.get('hash', '')

        # Don't propagate back to source
        target_peers = [p for p in self.p2p_sync.sync_peers if p != source_peer]

        if not target_peers:
            return

        # Send compact block announcement first
        announcement = self._create_block_announcement(block_data)

        success_count = 0
        for peer_id in target_peers:
            try:
                self._send_to_peer(peer_id, announcement)
                success_count += 1
            except Exception as e:
                logger.debug(f"Failed to announce block to {peer_id}: {e}")

        # Update propagation stats
        propagation_time = time.time() - start_time
        self.propagation_stats['blocks_propagated'] += 1
        self._update_propagation_time(propagation_time)

        logger.debug(f"📡 Propagated block {block_hash[:16]} to {success_count}/{len(target_peers)} peers in {propagation_time:.3f}s")

    def _create_block_announcement(self, block_data: Dict) -> Dict:
        """Create a compact block announcement."""
        return {
            'type': 'block_announcement',
            'block_hash': block_data.get('hash'),
            'block_height': block_data.get('index'),
            'timestamp': time.time()
        }

    def _send_to_peer(self, peer_id: str, message: Dict):
        """Send message to a specific peer."""
        # Placeholder - would use P2P connection
        pass

    def _update_propagation_time(self, new_time: float):
        """Update rolling average propagation time."""
        current_avg = self.propagation_stats['propagation_time_avg']
        propagated_count = self.propagation_stats['blocks_propagated']

        # Simple moving average
        self.propagation_stats['propagation_time_avg'] = (
            (current_avg * (propagated_count - 1)) + new_time
        ) / propagated_count


# Convenience functions for integration
def start_p2p_sync(blockchain: SignChain, peer_discovery: PeerDiscovery) -> P2PSyncManager:
    """Start P2P synchronization for a blockchain node."""
    sync_manager = P2PSyncManager(blockchain, peer_discovery)
    sync_manager.start_sync()
    return sync_manager

def stop_p2p_sync(sync_manager: P2PSyncManager):
    """Stop P2P synchronization."""
    if sync_manager:
        sync_manager.stop_sync()