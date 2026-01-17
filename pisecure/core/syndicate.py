"""
PiSecure Syndicate Mining
========================

Distributed mining coordination for PiHash algorithm with fair
reward distribution across different Raspberry Pi models.
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class SyndicateMember:
    """Represents a syndicate mining member"""
    member_id: str
    wallet_address: str
    pi_model: str
    hashpower: float  # Estimated H/s
    joined_at: float
    last_seen: float
    blocks_found: int = 0
    total_hashes: int = 0
    
    
class MiningWorkPackage:
    """Work package for distributed mining"""
    def __init__(self, block_data: bytes, difficulty: int, nonce_start: int, 
                 nonce_range: int, pihash_config: Dict[str, Any]):
        self.block_data = block_data
        self.difficulty = difficulty
        self.nonce_start = nonce_start
        self.nonce_range = nonce_range
        self.pihash_config = pihash_config
        self.assigned_at = time.time()
        self.completed = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission"""
        return {
            'block_data': self.block_data.hex(),
            'difficulty': self.difficulty,
            'nonce_start': self.nonce_start,
            'nonce_range': self.nonce_range,
            'pihash_config': self.pihash_config,
            'assigned_at': self.assigned_at
        }


class MiningSyndicate:
    """Coordinates distributed PiHash mining across multiple Pi devices"""
    
    def __init__(self, syndicate_name: str, coordinator_wallet: str):
        self.syndicate_name = syndicate_name
        self.coordinator_wallet = coordinator_wallet
        self.members: Dict[str, SyndicateMember] = {}
        self.active_work: Dict[str, MiningWorkPackage] = {}
        self.completed_work: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
        # Configuration
        self.syndicate_fee = 0.05  # 5% coordinator fee
        self.finder_bonus = 0.10  # 10% bonus for finding block
        self.member_timeout = 300  # 5 minutes inactivity timeout
        
        # Work distribution
        self.current_nonce_offset = 0
        self.work_chunk_size = 10000  # Nonces per work package
        
    def add_member(self, member_id: str, wallet_address: str, 
                   pi_model: str) -> bool:
        """Add a new syndicate member"""
        with self.lock:
            if member_id in self.members:
                # Update existing member
                self.members[member_id].last_seen = time.time()
                return True
            
            # Estimate hashpower based on Pi model
            hashpower = self._estimate_hashpower(pi_model)
            
            member = SyndicateMember(
                member_id=member_id,
                wallet_address=wallet_address,
                pi_model=pi_model,
                hashpower=hashpower,
                joined_at=time.time(),
                last_seen=time.time()
            )
            
            self.members[member_id] = member
            print(f"✓ Member joined: {member_id} ({pi_model}, {hashpower:.2f} H/s)")
            return True
    
    def remove_member(self, member_id: str) -> bool:
        """Remove a syndicate member"""
        with self.lock:
            if member_id in self.members:
                del self.members[member_id]
                print(f"✗ Member left: {member_id}")
                return True
            return False
    
    def _estimate_hashpower(self, pi_model: str) -> float:
        """
        Estimate member's hashpower based on Pi model
        
        Returns: hashes per second estimate for PiHash
        """
        model_lower = pi_model.lower()
        
        # PiHash hashrate estimates on different Pi models
        if 'pi zero' in model_lower or 'pi 1' in model_lower:
            return 0.05  # ~0.05 H/s (20s per hash)
        elif 'pi 2' in model_lower:
            return 0.2   # ~0.2 H/s (5s per hash)
        elif 'pi 3' in model_lower:
            return 0.5   # ~0.5 H/s (2s per hash)
        elif 'pi 4' in model_lower:
            return 1.0   # ~1 H/s (1s per hash)
        elif 'pi 5' in model_lower:
            return 2.0   # ~2 H/s (0.5s per hash)
        else:
            return 1.0   # Default to Pi 4 baseline
    
    def _get_pi_performance_factor(self, pi_model: str) -> float:
        """Get performance factor for difficulty adjustment"""
        model_lower = pi_model.lower()
        
        if 'pi zero' in model_lower or 'pi 1' in model_lower:
            return 0.1
        elif 'pi 2' in model_lower:
            return 0.3
        elif 'pi 3' in model_lower:
            return 0.5
        elif 'pi 4' in model_lower:
            return 1.0
        elif 'pi 5' in model_lower:
            return 2.0
        else:
            return 1.0
    
    def distribute_work(self, block_data: bytes, difficulty: int, 
                       pihash_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Distribute mining work to syndicate members with fair allocation
        
        Args:
            block_data: Block data to mine
            difficulty: Mining difficulty
            pihash_config: PiHash parameters (rounds, memory_mb, parallelism)
            
        Returns:
            List of work packages assigned to members
        """
        if pihash_config is None:
            pihash_config = {
                'rounds': 1,
                'memory_mb': 32,
                'parallelism': 1,
                'mining_mode': True
            }
        
        with self.lock:
            # Remove inactive members
            self._cleanup_inactive_members()
            
            if not self.members:
                return []
            
            # Calculate total hashpower
            total_hashpower = sum(m.hashpower for m in self.members.values())
            if total_hashpower == 0:
                return []
            
            work_packages = []
            
            for member_id, member in self.members.items():
                # Calculate work share based on member's hashpower
                work_share = member.hashpower / total_hashpower
                nonce_range = max(100, int(self.work_chunk_size * work_share))
                
                # Create work package
                work_package = MiningWorkPackage(
                    block_data=block_data,
                    difficulty=difficulty,
                    nonce_start=self.current_nonce_offset,
                    nonce_range=nonce_range,
                    pihash_config=pihash_config
                )
                
                self.active_work[member_id] = work_package
                work_packages.append({
                    'member_id': member_id,
                    'package': work_package.to_dict()
                })
                
                self.current_nonce_offset += nonce_range
            
            return work_packages
    
    def _cleanup_inactive_members(self):
        """Remove members that haven't been seen recently"""
        current_time = time.time()
        inactive_members = [
            member_id for member_id, member in self.members.items()
            if current_time - member.last_seen > self.member_timeout
        ]
        
        for member_id in inactive_members:
            print(f"⚠️ Removing inactive member: {member_id}")
            del self.members[member_id]
            if member_id in self.active_work:
                del self.active_work[member_id]
    
    def submit_work_result(self, member_id: str, found_nonce: Optional[int] = None,
                          hashes_completed: int = 0) -> Dict[str, Any]:
        """
        Submit work results from a member
        
        Args:
            member_id: Member who completed work
            found_nonce: Nonce if solution was found
            hashes_completed: Number of hashes computed
            
        Returns:
            Result status and any rewards
        """
        with self.lock:
            if member_id not in self.members:
                return {'status': 'error', 'message': 'Unknown member'}
            
            member = self.members[member_id]
            member.last_seen = time.time()
            member.total_hashes += hashes_completed
            
            # Record completed work
            work_result = {
                'member_id': member_id,
                'hashes_completed': hashes_completed,
                'found_nonce': found_nonce,
                'timestamp': time.time()
            }
            self.completed_work.append(work_result)
            
            # Clean up active work
            if member_id in self.active_work:
                self.active_work[member_id].completed = True
                del self.active_work[member_id]
            
            if found_nonce is not None:
                member.blocks_found += 1
                return {
                    'status': 'block_found',
                    'nonce': found_nonce,
                    'finder': member_id
                }
            
            return {'status': 'work_completed', 'hashes': hashes_completed}
    
    def distribute_rewards(self, block_reward: float, 
                          finder_id: Optional[str] = None) -> Dict[str, float]:
        """
        Distribute block rewards based on contribution and Pi model
        
        Args:
            block_reward: Total block reward (e.g., 50 314ST tokens)
            finder_id: ID of member who found the nonce (gets bonus)
        
        Returns:
            Dict mapping member_id to reward amount
        """
        with self.lock:
            if not self.members:
                return {self.coordinator_wallet: block_reward}
            
            # Calculate contribution shares
            total_contribution = 0
            contributions = {}
            
            for member_id, member in self.members.items():
                # Contribution = hashpower × time_active
                time_active = time.time() - member.joined_at
                contribution = member.hashpower * time_active
                
                contributions[member_id] = contribution
                total_contribution += contribution
            
            if total_contribution == 0:
                return {self.coordinator_wallet: block_reward}
            
            # Calculate rewards
            rewards = {}
            syndicate_fee_amount = block_reward * self.syndicate_fee
            finder_bonus_amount = block_reward * self.finder_bonus
            distributable = block_reward - syndicate_fee_amount - finder_bonus_amount
            
            for member_id, contribution in contributions.items():
                share = contribution / total_contribution
                base_reward = distributable * share
                
                # Add finder bonus if applicable
                if member_id == finder_id:
                    base_reward += finder_bonus_amount
                
                rewards[self.members[member_id].wallet_address] = base_reward
            
            # Coordinator gets syndicate fee
            rewards[self.coordinator_wallet] = syndicate_fee_amount
            
            return rewards
    
    def get_stats(self) -> Dict[str, Any]:
        """Get syndicate statistics"""
        with self.lock:
            total_hashpower = sum(m.hashpower for m in self.members.values())
            total_blocks = sum(m.blocks_found for m in self.members.values())
            total_hashes = sum(m.total_hashes for m in self.members.values())
            
            return {
                'syndicate_name': self.syndicate_name,
                'total_members': len(self.members),
                'total_hashpower': total_hashpower,
                'hashpower_human': f"{total_hashpower:.2f} H/s",
                'total_blocks_found': total_blocks,
                'total_hashes_computed': total_hashes,
                'active_work_packages': len(self.active_work),
                'completed_work_packages': len(self.completed_work),
                'members': [
                    {
                        'member_id': m.member_id,
                        'pi_model': m.pi_model,
                        'hashpower': m.hashpower,
                        'blocks_found': m.blocks_found,
                        'uptime': time.time() - m.joined_at
                    }
                    for m in self.members.values()
                ]
            }
    
    def get_member_stats(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific member"""
        with self.lock:
            if member_id not in self.members:
                return None
            
            member = self.members[member_id]
            return {
                'member_id': member.member_id,
                'wallet_address': member.wallet_address,
                'pi_model': member.pi_model,
                'hashpower': member.hashpower,
                'joined_at': member.joined_at,
                'last_seen': member.last_seen,
                'uptime': time.time() - member.joined_at,
                'blocks_found': member.blocks_found,
                'total_hashes': member.total_hashes,
                'active': time.time() - member.last_seen < self.member_timeout
            }
