#!/usr/bin/env python3
"""
PiSecure Consensus Mechanism
============================

Proof-of-Work consensus with ASIC resistance, hardware verification,
and decentralized mining coordination.
"""

import time
import json
import hashlib
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict

from .blockchain import SignChain, SignBlock
from .p2p_protocol import PiSecureP2P, MessageType, P2PMessage
from .p2p_sync import P2PSyncManager

logger = logging.getLogger(__name__)

class ConsensusAlgorithm(Enum):
    """Supported consensus algorithms"""
    PROOF_OF_WORK_PI_HASH = "pow_pi_hash"  # PiHash mining algorithm
    PROOF_OF_WORK_SHA256 = "pow_sha256"    # Legacy SHA256 support
    PROOF_OF_WORK_SHA3 = "pow_sha3"        # Legacy SHA3 support
    PROOF_OF_STAKE = "pos"                 # Future implementation

@dataclass
class ConsensusVote:
    """Consensus vote structure"""
    voter_id: str
    block_hash: str
    timestamp: float
    signature: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsensusVote':
        return cls(**data)

class Syndicate:
    """
    Decentralized mining syndicate for coordinated block finding

    Features:
    - Share-based reward distribution
    - ASIC-resistant algorithms
    - Hardware verification requirements
    - Geographic distribution optimization
    """

    def __init__(self, syndicate_id: str, founder_wallet: str):
        self.syndicate_id = syndicate_id
        self.founder_wallet = founder_wallet
        self.created_at = time.time()

        # Syndicate configuration
        self.min_hardware_score = 2.0  # Minimum hardware verification score
        self.max_participants = 100
        self.share_difficulty = 4  # Share submission difficulty
        self.reward_distribution = 'proportional'  # proportional, equal, founder_bonus

        # Syndicate statistics
        self.total_hashrate = 0.0
        self.active_miners = 0
        self.total_shares = 0
        self.blocks_found = 0
        self.total_rewards = 0.0

        # Participant data
        self.participants: Dict[str, Dict[str, Any]] = {}
        self.pending_shares: List[Dict[str, Any]] = []
        self.reward_history: List[Dict[str, Any]] = []

        # Current block template
        self.current_template: Optional[Dict[str, Any]] = None
        self.template_expires = 0

    def add_participant(self, miner_wallet: str, hashrate: float,
                       hardware_score: float, location: str) -> bool:
        """Add a miner to the syndicate"""

        if len(self.participants) >= self.max_participants:
            return False

        if hardware_score < self.min_hardware_score:
            return False

        if miner_wallet in self.participants:
            # Update existing participant
            self.participants[miner_wallet].update({
                'hashrate': hashrate,
                'hardware_score': hardware_score,
                'location': location,
                'last_active': time.time(),
                'status': 'active'
            })
        else:
            # Add new participant
            self.participants[miner_wallet] = {
                'hashrate': hashrate,
                'hardware_score': hardware_score,
                'location': location,
                'joined_at': time.time(),
                'last_active': time.time(),
                'shares_submitted': 0,
                'rewards_earned': 0.0,
                'status': 'active'
            }

        self._update_pool_stats()
        return True

    def remove_participant(self, miner_wallet: str) -> bool:
        """Remove a miner from the syndicate"""
        if miner_wallet in self.participants:
            del self.participants[miner_wallet]
            self._update_pool_stats()
            return True
        return False

    def submit_share(self, miner_wallet: str, share_data: Dict[str, Any]) -> bool:
        """Submit a mining share"""

        if miner_wallet not in self.participants:
            return False

        # Validate share
        if not self._validate_share(share_data):
            return False

        # Record share
        share_record = {
            'miner_wallet': miner_wallet,
            'share_data': share_data,
            'submitted_at': time.time(),
            'difficulty': self.share_difficulty
        }

        self.pending_shares.append(share_record)
        self.participants[miner_wallet]['shares_submitted'] += 1
        self.participants[miner_wallet]['last_active'] = time.time()
        self.total_shares += 1

        return True

    def _validate_share(self, share_data: Dict[str, Any]) -> bool:
        """Validate mining share"""
        required_fields = ['nonce', 'timestamp', 'block_hash']

        for field in required_fields:
            if field not in share_data:
                return False

        # Check timestamp is recent (within last 5 minutes)
        if time.time() - share_data['timestamp'] > 300:
            return False

        # Verify proof-of-work for share difficulty
        target = "0" * self.share_difficulty
        if not share_data.get('hash', '').startswith(target):
            return False

        return True

    def create_block_template(self, blockchain: SignChain) -> Dict[str, Any]:
        """Create a new block template for pool mining"""

        # Get pending transactions
        pending_txs = blockchain.pending_transactions[:50]  # Limit to 50 tx per block

        # Create block template
        template = {
            'version': 1,
            'previous_hash': blockchain.chain[-1].hash if blockchain.chain else '0',
            'timestamp': int(time.time()),
            'difficulty': blockchain.difficulty,
            'transactions': pending_txs,
            'syndicate_id': self.syndicate_id,
            'expires': int(time.time()) + 600  # 10 minute expiry
        }

        self.current_template = template
        self.template_expires = template['expires']

        return template

    def distribute_block_reward(self, block_data: Dict[str, Any], block_reward: float) -> Dict[str, float]:
        """Distribute block reward among pool participants"""

        if not self.participants:
            return {}

        total_participant_hashrate = sum(p['hashrate'] for p in self.participants.values()
                                       if p['status'] == 'active')

        if total_participant_hashrate == 0:
            return {}

        # Calculate reward distribution
        distributions = {}
        pool_reward = block_reward * 0.95  # 95% to pool participants
        founder_bonus = block_reward * 0.05  # 5% founder bonus

        if self.reward_distribution == 'proportional':
            # Distribute based on hashrate contribution
            for wallet, participant in self.participants.items():
                if participant['status'] == 'active':
                    hashrate_ratio = participant['hashrate'] / total_participant_hashrate
                    reward = pool_reward * hashrate_ratio

                    # Add founder bonus if applicable
                    if wallet == self.founder_wallet:
                        reward += founder_bonus

                    distributions[wallet] = reward
                    participant['rewards_earned'] += reward

        elif self.reward_distribution == 'equal':
            # Equal distribution
            equal_share = pool_reward / len([p for p in self.participants.values()
                                           if p['status'] == 'active'])

            for wallet, participant in self.participants.items():
                if participant['status'] == 'active':
                    reward = equal_share
                    if wallet == self.founder_wallet:
                        reward += founder_bonus

                    distributions[wallet] = reward
                    participant['rewards_earned'] += reward

        # Update pool statistics
        self.blocks_found += 1
        self.total_rewards += block_reward

        # Record reward distribution
        reward_record = {
            'block_hash': block_data.get('hash'),
            'block_height': block_data.get('index'),
            'total_reward': block_reward,
            'distributions': distributions,
            'timestamp': time.time()
        }

        self.reward_history.append(reward_record)

        return distributions

    def get_syndicate_stats(self) -> Dict[str, Any]:
        """Get comprehensive syndicate statistics"""
        return {
            'syndicate_id': self.syndicate_id,
            'founder_wallet': self.founder_wallet,
            'created_at': self.created_at,
            'participant_count': len(self.participants),
            'active_miners': self.active_miners,
            'total_hashrate': self.total_hashrate,
            'total_shares': self.total_shares,
            'blocks_found': self.blocks_found,
            'total_rewards': self.total_rewards,
            'current_template': self.current_template,
            'template_expires': self.template_expires,
            'pending_shares': len(self.pending_shares),
            'reward_distribution': self.reward_distribution
        }

    def _update_pool_stats(self):
        """Update pool statistics"""
        active_participants = [p for p in self.participants.values() if p['status'] == 'active']

        self.active_miners = len(active_participants)
        self.total_hashrate = sum(p['hashrate'] for p in active_participants)

class PiSecureConsensus:
    """
    PiSecure Consensus Engine

    Integrates:
    - Proof-of-Work validation
    - Hardware verification requirements
    - Mining pool coordination
    - P2P consensus voting
    - Fork resolution
    """

    def __init__(self, blockchain: SignChain,
                 p2p_protocol: Optional[PiSecureP2P] = None,
                 p2p_sync: Optional[P2PSyncManager] = None):
        """
        Initialize consensus engine

        Args:
            blockchain: SignChain instance
            p2p_protocol: P2P protocol instance
            p2p_sync: P2P sync manager
        """
        self.blockchain = blockchain
        self.p2p_protocol = p2p_protocol
        self.p2p_sync = p2p_sync

        # Consensus configuration
        self.consensus_algorithm = ConsensusAlgorithm.PROOF_OF_WORK_PI_HASH
        self.min_block_time = 300  # 5 minutes minimum
        self.max_block_time = 1800  # 30 minutes maximum
        self.difficulty_adjustment_interval = 10  # Blocks between adjustments

        # Mining syndicates
        self.mining_syndicates: Dict[str, Syndicate] = {}
        self.syndicate_coordination_enabled = True

        # Consensus state
        self.pending_votes: Dict[str, List[ConsensusVote]] = {}
        self.consensus_threshold = 0.67  # 67% agreement required
        self.vote_timeout = 300  # 5 minutes for consensus

        # Statistics
        self.stats = {
            'total_blocks_validated': 0,
            'forks_resolved': 0,
            'consensus_agreements': 0,
            'mining_pools_active': 0,
            'total_pool_rewards': 0.0
        }

        logger.info("⚖️ PiSecure Consensus Engine initialized")

    def validate_block_consensus(self, block_data: Dict[str, Any],
                               miner_wallet: str) -> Tuple[bool, str]:
        """
        Validate block using consensus rules

        Returns:
            Tuple of (is_valid, reason)
        """

        # Basic block validation
        if not self._validate_basic_block_structure(block_data):
            return False, "Invalid block structure"

        # Proof-of-Work validation
        if not self._validate_proof_of_work(block_data):
            return False, "Invalid proof-of-work"

        # Hardware verification (ASIC resistance)
        if not self._validate_hardware_requirements(miner_wallet):
            return False, "Hardware verification failed"

        # Mining syndicate validation (if applicable)
        if self.syndicate_coordination_enabled:
            syndicate_validation = self._validate_mining_syndicate_rules(block_data, miner_wallet)
            if not syndicate_validation[0]:
                return syndicate_validation

        # P2P consensus validation
        if self.p2p_protocol and len(self.p2p_protocol.connections) > 0:
            consensus_result = self._validate_p2p_consensus(block_data)
            if not consensus_result[0]:
                return consensus_result

        return True, "Block validated successfully"

    def _validate_basic_block_structure(self, block_data: Dict[str, Any]) -> bool:
        """Validate basic block structure"""
        required_fields = ['index', 'timestamp', 'transactions', 'previous_hash', 'nonce', 'hash']

        for field in required_fields:
            if field not in block_data:
                return False

        # Validate index is sequential
        if block_data['index'] != len(self.blockchain.chain):
            return False

        # Validate previous hash
        if self.blockchain.chain and block_data['previous_hash'] != self.blockchain.chain[-1].hash:
            return False

        # Validate timestamp is reasonable (not too far in future)
        if block_data['timestamp'] > time.time() + 300:  # 5 minutes tolerance
            return False

        return True

    def _validate_proof_of_work(self, block_data: Dict[str, Any]) -> bool:
        """Validate proof-of-work"""
        target = "0" * self.blockchain.difficulty
        block_hash = block_data.get('hash', '')

        return block_hash.startswith(target)

    def _validate_hardware_requirements(self, miner_wallet: str) -> bool:
        """Validate miner hardware requirements"""
        # This would integrate with the hardware verifier
        # For now, accept all valid wallets
        return True

    def _validate_mining_syndicate_rules(self, block_data: Dict[str, Any],
                                       miner_wallet: str) -> Tuple[bool, str]:
        """Validate mining syndicate rules"""
        syndicate_id = block_data.get('syndicate_id')

        if syndicate_id and syndicate_id in self.mining_syndicates:
            syndicate = self.mining_syndicates[syndicate_id]

            # Check if miner is in syndicate
            if miner_wallet not in syndicate.participants:
                return False, f"Miner {miner_wallet} not in syndicate {syndicate_id}"

            # Check if miner has submitted recent shares
            participant = syndicate.participants[miner_wallet]
            if time.time() - participant['last_active'] > 3600:  # 1 hour
                return False, "Miner inactive in syndicate"

        return True, "Syndicate validation passed"

    def _validate_p2p_consensus(self, block_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate block through P2P consensus"""
        if not self.p2p_protocol:
            return True, "No P2P protocol available"

        # Request consensus votes from peers
        block_hash = block_data.get('hash')
        consensus_request = P2PMessage(
            message_id=f"consensus_request_{time.time()}",
            message_type=MessageType.CONSENSUS_VOTE,
            sender_id=self.p2p_protocol.node_id,
            receiver_id=None,  # Broadcast
            timestamp=time.time(),
            ttl=3,
            payload={
                'type': 'block_validation_request',
                'block_hash': block_hash,
                'block_height': block_data.get('index'),
                'block_data': block_data
            }
        )

        self.p2p_protocol.broadcast_message(consensus_request)

        # Wait for consensus (simplified - in production would wait for quorum)
        time.sleep(2)  # Brief wait for responses

        # Check consensus votes (simplified)
        votes = self.pending_votes.get(block_hash, [])
        total_peers = len(self.p2p_protocol.connections)

        if total_peers > 0:
            approval_ratio = len([v for v in votes if v.signature]) / total_peers

            if approval_ratio >= self.consensus_threshold:
                return True, f"Consensus achieved: {approval_ratio:.1%}"
            else:
                return False, f"Consensus failed: {approval_ratio:.1%} approval"
        else:
            # Solo node - accept block
            return True, "Solo node consensus"

    def create_mining_syndicate(self, syndicate_id: str, founder_wallet: str) -> Syndicate:
        """Create a new mining syndicate"""
        if syndicate_id in self.mining_syndicates:
            raise ValueError(f"Syndicate {syndicate_id} already exists")

        syndicate = Syndicate(syndicate_id, founder_wallet)
        self.mining_syndicates[syndicate_id] = syndicate

        logger.info(f"🏢 Created mining syndicate {syndicate_id} by {founder_wallet}")
        return syndicate

    def join_mining_syndicate(self, syndicate_id: str, miner_wallet: str,
                            hashrate: float, hardware_score: float,
                            location: str) -> bool:
        """Join a mining syndicate"""
        if syndicate_id not in self.mining_syndicates:
            return False

        syndicate = self.mining_syndicates[syndicate_id]
        return syndicate.add_participant(miner_wallet, hashrate, hardware_score, location)

    def submit_syndicate_share(self, syndicate_id: str, miner_wallet: str,
                             share_data: Dict[str, Any]) -> bool:
        """Submit mining share to syndicate"""
        if syndicate_id not in self.mining_syndicates:
            return False

        syndicate = self.mining_syndicates[syndicate_id]
        return syndicate.submit_share(miner_wallet, share_data)

    def distribute_syndicate_rewards(self, syndicate_id: str, block_data: Dict[str, Any],
                                   block_reward: float) -> Dict[str, float]:
        """Distribute block reward to syndicate participants"""
        if syndicate_id not in self.mining_syndicates:
            return {}

        syndicate = self.mining_syndicates[syndicate_id]
        return syndicate.distribute_block_reward(block_data, block_reward)

    def adjust_difficulty(self) -> int:
        """Adjust mining difficulty based on network conditions"""
        if len(self.blockchain.chain) < self.difficulty_adjustment_interval:
            return self.blockchain.difficulty

        # Get last N blocks for timing analysis
        recent_blocks = self.blockchain.chain[-self.difficulty_adjustment_interval:]
        if len(recent_blocks) < 2:
            return self.blockchain.difficulty

        # Calculate average block time
        block_times = []
        for i in range(1, len(recent_blocks)):
            time_diff = recent_blocks[i].timestamp - recent_blocks[i-1].timestamp
            if self.min_block_time <= time_diff <= self.max_block_time:
                block_times.append(time_diff)

        if not block_times:
            return self.blockchain.difficulty

        avg_block_time = sum(block_times) / len(block_times)
        target_block_time = 600  # 10 minutes target

        # Adjust difficulty
        difficulty_ratio = target_block_time / avg_block_time
        new_difficulty = int(self.blockchain.difficulty * difficulty_ratio)

        # Constrain difficulty changes
        max_change = 2
        new_difficulty = max(1, min(new_difficulty,
                                  self.blockchain.difficulty + max_change,
                                  self.blockchain.difficulty - max_change))

        logger.info(f"⚖️ Difficulty adjusted: {self.blockchain.difficulty} → {new_difficulty} "
                   f"(avg block time: {avg_block_time:.1f}s)")

        return new_difficulty

    def resolve_fork(self, competing_chains: List[List[Dict]]) -> Optional[List[Dict]]:
        """
        Resolve blockchain fork using consensus

        Args:
            competing_chains: List of competing chain segments

        Returns:
            Winning chain segment, or None if no resolution
        """
        if len(competing_chains) < 2:
            return None

        # Find longest valid chain
        longest_chain = max(competing_chains, key=len)

        # Request consensus validation from network
        if self.p2p_protocol:
            fork_resolution_request = P2PMessage(
                message_id=f"fork_resolution_{time.time()}",
                message_type=MessageType.CONSENSUS_VOTE,
                sender_id=self.p2p_protocol.node_id,
                receiver_id=None,
                timestamp=time.time(),
                ttl=5,
                payload={
                    'type': 'fork_resolution',
                    'competing_chains': [{'length': len(chain), 'last_hash': chain[-1]['hash']}
                                       for chain in competing_chains],
                    'preferred_chain_hash': longest_chain[-1]['hash']
                }
            )

            self.p2p_protocol.broadcast_message(fork_resolution_request)

        # For now, use longest chain rule
        self.stats['forks_resolved'] += 1
        return longest_chain

    def get_consensus_stats(self) -> Dict[str, Any]:
        """Get consensus engine statistics"""
        return {
            'algorithm': self.consensus_algorithm.value,
            'current_difficulty': self.blockchain.difficulty,
            'mining_syndicates': len(self.mining_syndicates),
            'pending_votes': sum(len(votes) for votes in self.pending_votes.values()),
            'consensus_threshold': self.consensus_threshold,
            **self.stats
        }

    def get_syndicate_stats(self, syndicate_id: Optional[str] = None) -> Dict[str, Any]:
        """Get mining syndicate statistics"""
        if syndicate_id:
            syndicate = self.mining_syndicates.get(syndicate_id)
            return syndicate.get_syndicate_stats() if syndicate else {}
        else:
            return {
                sid: syndicate.get_syndicate_stats()
                for sid, syndicate in self.mining_syndicates.items()
            }

# Global consensus instance
consensus_engine: Optional[PiSecureConsensus] = None

def get_consensus_engine(blockchain: Optional[SignChain] = None,
                        p2p_protocol: Optional[PiSecureP2P] = None,
                        p2p_sync: Optional[P2PSyncManager] = None) -> PiSecureConsensus:
    """Get or create global consensus engine"""
    global consensus_engine
    if consensus_engine is None and blockchain:
        consensus_engine = PiSecureConsensus(blockchain, p2p_protocol, p2p_sync)
    return consensus_engine

def validate_block_with_consensus(block_data: Dict[str, Any],
                                miner_wallet: str,
                                blockchain: SignChain) -> Tuple[bool, str]:
    """Validate block using consensus engine"""
    consensus = get_consensus_engine(blockchain)
    return consensus.validate_block_consensus(block_data, miner_wallet)