#!/usr/bin/env python3
"""
Test the PiSecure mining dashboard
Run this to see the dashboard in action
"""

import sys
import time
import threading
from pathlib import Path

# Ensure pisecure is importable
sys.path.insert(0, str(Path(__file__).parent))

from pisecure.monitor import MiningDashboard
from pisecure.core.blockchain import SignChain


def simulate_mining(blockchain: SignChain, duration: int = 60):
    """Simulate mining activity to test dashboard updates"""
    print(f"🎯 Starting simulated mining for {duration} seconds...")
    
    # Initialize mining session
    with blockchain.lock:
        blockchain.mining_session['active'] = True
        blockchain.mining_session['start_time'] = time.time()
    
    start_time = time.time()
    nonce = 0
    
    while time.time() - start_time < duration:
        # Simulate mining progress
        nonce += 1
        hashes = int(time.time() - start_time)
        best_zeros = 140 + (nonce % 10)  # Simulate progress toward 146
        
        # Update session state
        with blockchain.lock:
            blockchain.mining_session['current_nonce'] = nonce
            blockchain.mining_session['hashes_tried'] = hashes
            blockchain.mining_session['best_zeros'] = best_zeros
            blockchain.mining_session['hashrate'] = hashes / (time.time() - start_time)
        
        time.sleep(0.1)
    
    # Mark mining complete
    with blockchain.lock:
        blockchain.mining_session['active'] = False
    
    print("✅ Mining simulation complete")


def main():
    """Test the dashboard"""
    print("="*60)
    print("PiSecure Mining Dashboard Test")
    print("="*60)
    
    # Initialize blockchain
    try:
        blockchain = SignChain(
            chain_file="/var/lib/pisecure/testnet/blockchain.json",
            use_hybrid_storage=False,
            mining_algorithm='pihash'
        )
        print(f"✅ Blockchain loaded: {len(blockchain.chain)} blocks")
    except Exception as e:
        print(f"⚠️  Could not load blockchain: {e}")
        print("Creating temporary blockchain...")
        blockchain = SignChain(
            chain_file="/tmp/test_blockchain.json",
            use_hybrid_storage=False,
            mining_algorithm='pihash'
        )
    
    # Option 1: Dashboard with simulated mining
    print("\nOption 1: Dashboard with simulated mining")
    print("Press Ctrl+C to stop\n")
    
    # Start simulated mining in background thread
    mining_thread = threading.Thread(
        target=simulate_mining,
        args=(blockchain, 300),  # 5 minutes
        daemon=True
    )
    mining_thread.start()
    
    # Give mining thread time to initialize
    time.sleep(1)
    
    # Create and run dashboard
    dashboard = MiningDashboard(
        blockchain=blockchain,
        mode='solo',
        refresh_rate=1.0,
        syndicate=None,
        testnet=True
    )
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\n\n✋ Dashboard stopped by user")
    except Exception as e:
        print(f"\n\n❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
