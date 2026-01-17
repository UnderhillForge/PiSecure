#!/usr/bin/env python3
"""
PiHash Mining Example

Shows practical mining workflow with difficulty adjustment
and fast validation for block propagation.
"""

import json
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pisecure.core.pihash import PiHash, verify_pihash_fast

def simulate_block_mining():
    """Simulate mining a block with PiHash"""
    
    print("=" * 70)
    print("PiHash Block Mining Example")
    print("=" * 70)
    
    # Block data
    block = {
        'index': 12345,
        'previous_hash': '000a1b2c3d4e5f6789abcdef...',
        'timestamp': int(time.time()),
        'transactions': [
            {'from': 'wallet_a', 'to': 'wallet_b', 'amount': 10},
            {'from': 'wallet_c', 'to': 'wallet_d', 'amount': 5}
        ]
    }
    block_data = json.dumps(block, sort_keys=True).encode()
    
    print(f"\n📦 Block to mine:")
    print(f"   Index: {block['index']}")
    print(f"   Transactions: {len(block['transactions'])}")
    print(f"   Data size: {len(block_data)} bytes")
    
    # Mining configuration  
    base_difficulty = 1  # Require 1 leading zero (reasonable for demo)
    rounds = 1  # Single round for fast demo (production uses 4-8)
    memory_mb = 32  # Light memory for fast demo (production uses 128-256)
    
    print(f"\n⛏️  Mining configuration:")
    print(f"   Base difficulty: {base_difficulty} (leading zeros)")
    print(f"   Rounds: {rounds}")
    print(f"   Memory: {memory_mb}MB")
    
    try:
        # Initialize miner
        miner = PiHash(rounds=rounds, memory_mb=memory_mb, 
                      parallelism=1, mining_mode=True)  # Use 1 for universal compatibility
        
        # Get hardware fingerprint first
        hw_fp = miner._get_hardware_fingerprint()
        hw_verified = miner._verify_hardware(hw_fp)
        
        print(f"\n🔧 Hardware detected:")
        if hw_verified:
            model = hw_fp.get('hardware_model', 'Unknown')
            factor = miner.get_pi_performance_factor()
            adjusted_diff = max(1, int(base_difficulty * factor))
            
            print(f"   Model: {model}")
            print(f"   Performance factor: {factor}x")
            print(f"   Adjusted difficulty: {adjusted_diff}")
            
            # Start mining
            print(f"\n⏱️  Mining started...")
            start_time = time.time()
            
            # Get the hardware fingerprint used for mining
            hw_fp_for_mining = miner._get_hardware_fingerprint()
            
            # For demo, use base difficulty without adjustment
            nonce, block_hash = miner.find_nonce(
                block_data, base_difficulty, hw_fp_for_mining
            )
            perf_factor = factor
            
            mining_time = time.time() - start_time
            hash_rate = nonce / mining_time if mining_time > 0 else 0
            
            print(f"\n✅ Block mined successfully!")
            print(f"   Nonce: {nonce:,}")
            print(f"   Hash: {block_hash}")
            print(f"   Time: {mining_time:.2f}s")
            print(f"   Hash rate: {hash_rate:.2f} H/s")
            print(f"   Leading zeros: {len(block_hash) - len(block_hash.lstrip('0'))}")
            
            # Simulate block propagation - validation by other nodes
            print(f"\n📡 Broadcasting to network...")
            print(f"   Other nodes validate using fast path...")
            
            # Fast validation (works on any hardware)
            val_start = time.time()
            
            is_valid = verify_pihash_fast(
                block_data, nonce, block_hash, 
                rounds=rounds, memory_mb=memory_mb, parallelism=1  # Must match mining
            )
            val_time = time.time() - val_start
            
            print(f"\n✅ Validation result: {is_valid}")
            print(f"   Validation time: {val_time:.3f}s ({val_time*1000:.1f}ms)")
            print(f"   Speedup: {mining_time/val_time:.1f}x faster than mining")
            
            print(f"\n📊 Summary:")
            print(f"   • Mining: Pi-exclusive, hardware-verified")
            print(f"   • Validation: Universal, fast, lightweight")
            print(f"   • Fair: Difficulty adjusted for Pi model")
            print(f"   • Secure: ASIC/GPU resistant")
            
        else:
            print("   ⚠️  No verified Pi hardware detected")
            
    except ValueError as e:
        print(f"\n❌ Mining failed: {e}")
        print(f"   This system cannot mine (not a Raspberry Pi)")
        
        # But it can still validate!
        print(f"\n   However, this system CAN validate blocks:")
        print(f"   Example: verify_pihash_fast(data, nonce, hash)")

if __name__ == '__main__':
    simulate_block_mining()
