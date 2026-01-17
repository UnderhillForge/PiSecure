#!/usr/bin/env python3
"""
PiSecure Syndicate Mining Demo

Demonstrates how multiple Raspberry Pi devices can pool
their mining power for more consistent block rewards.
"""

import sys
import os
import json
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pisecure.core.syndicate import MiningSyndicate
from pisecure.core.pihash import PiHash


def simulate_syndicate_mining():
    """Simulate a mining syndicate with different Pi models"""
    
    print("=" * 70)
    print("PiSecure Syndicate Mining Demonstration")
    print("=" * 70)
    print()
    
    # Create syndicate
    syndicate = MiningSyndicate(
        syndicate_name="PiPool Alpha",
        coordinator_wallet="coordinator_wallet_abc123"
    )
    
    print("📊 Syndicate Created: PiPool Alpha")
    print(f"   Coordinator: {syndicate.coordinator_wallet[:20]}...")
    print(f"   Fee: {syndicate.syndicate_fee * 100}%")
    print(f"   Finder Bonus: {syndicate.finder_bonus * 100}%")
    print()
    
    # Add members with different Pi models
    members = [
        ("miner_1", "wallet_pi5_001", "Raspberry Pi 5 Model B"),
        ("miner_2", "wallet_pi4_001", "Raspberry Pi 4 Model B"),
        ("miner_3", "wallet_pi4_002", "Raspberry Pi 4 Model B"),
        ("miner_4", "wallet_pi3_001", "Raspberry Pi 3 Model B+"),
        ("miner_5", "wallet_zero_001", "Raspberry Pi Zero 2 W"),
    ]
    
    print("👥 Adding Syndicate Members:")
    print("-" * 70)
    for member_id, wallet, pi_model in members:
        syndicate.add_member(member_id, wallet, pi_model)
        stats = syndicate.get_member_stats(member_id)
        print(f"   {member_id:12} | {pi_model:30} | {stats['hashpower']:.2f} H/s")
    print()
    
    # Show syndicate stats
    stats = syndicate.get_stats()
    print("📈 Syndicate Statistics:")
    print(f"   Total Members: {stats['total_members']}")
    print(f"   Combined Hashpower: {stats['hashpower_human']}")
    print(f"   Expected Block Time: ~{16 / stats['total_hashpower']:.1f} seconds (difficulty 1)")
    print()
    
    # Simulate block mining
    print("⛏️  Distributing Mining Work:")
    print("-" * 70)
    
    # Create block data
    block_data = json.dumps({
        'index': 12345,
        'previous_hash': '00abc123...',
        'timestamp': int(time.time()),
        'transactions': [
            {'from': 'alice', 'to': 'bob', 'amount': 10}
        ]
    }, sort_keys=True).encode()
    
    # Distribute work
    difficulty = 1
    pihash_config = {
        'rounds': 1,
        'memory_mb': 32,
        'parallelism': 1
    }
    
    work_packages = syndicate.distribute_work(block_data, difficulty, pihash_config)
    
    for package in work_packages:
        member_id = package['member_id']
        work = package['package']
        member_stats = syndicate.get_member_stats(member_id)
        
        print(f"   {member_id:12} | "
              f"Nonces: {work['nonce_start']:8,} - {work['nonce_start'] + work['nonce_range']:8,} | "
              f"Range: {work['nonce_range']:6,} | "
              f"{member_stats['pi_model']}")
    print()
    
    # Simulate mining (just find any valid hash for demo)
    print("⏱️  Simulating Mining Process...")
    print()
    
    # Simulate that miner_2 (Pi 4) finds a block
    finder_id = "miner_2"
    found_nonce = 42
    hashes_completed = 100
    
    # Submit results from all miners
    for package in work_packages:
        member_id = package['member_id']
        if member_id == finder_id:
            result = syndicate.submit_work_result(
                member_id=member_id,
                found_nonce=found_nonce,
                hashes_completed=hashes_completed
            )
            print(f"✅ {member_id} found a valid block!")
            print(f"   Nonce: {found_nonce}")
            print()
        else:
            # Other miners completed their ranges without finding a block
            syndicate.submit_work_result(
                member_id=member_id,
                hashes_completed=package['package']['nonce_range']
            )
    
    # Distribute rewards
    print("💰 Reward Distribution:")
    print("-" * 70)
    
    block_reward = 50.0  # 50 314ST tokens
    rewards = syndicate.distribute_rewards(block_reward, finder_id)
    
    total_distributed = 0
    for wallet, amount in sorted(rewards.items(), key=lambda x: x[1], reverse=True):
        # Find member name
        if wallet == syndicate.coordinator_wallet:
            member_name = "Coordinator (fee)"
        else:
            member_name = next(
                (m for m in members if m[1] == wallet),
                ("unknown", wallet, "Unknown")
            )[0]
        
        print(f"   {member_name:20} | {wallet[:20]:20} | {amount:7.3f} 314ST")
        total_distributed += amount
    
    print("-" * 70)
    print(f"   {'Total Distributed':20} | {' '*20} | {total_distributed:7.3f} 314ST")
    print()
    
    # Show updated syndicate stats
    final_stats = syndicate.get_stats()
    print("📊 Final Syndicate Statistics:")
    print(f"   Total Blocks Found: {final_stats['total_blocks_found']}")
    print(f"   Total Hashes: {final_stats['total_hashes_computed']:,}")
    print(f"   Active Work Packages: {final_stats['active_work_packages']}")
    print(f"   Completed Work: {final_stats['completed_work_packages']}")
    print()
    
    print("=" * 70)
    print("Key Benefits of Syndicate Mining:")
    print("=" * 70)
    print("  ✓ Smaller Pis (Zero/3) get consistent income")
    print("  ✓ Fair distribution based on actual hashpower")
    print("  ✓ Finder bonus incentivizes participation")
    print("  ✓ 5% coordinator fee covers infrastructure")
    print("  ✓ Work distributed proportionally to capabilities")
    print("=" * 70)


if __name__ == "__main__":
    simulate_syndicate_mining()
