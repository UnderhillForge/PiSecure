#!/usr/bin/env python3
"""Test if mining session state is being set correctly"""
import sys
import time
import threading
sys.path.insert(0, '/home/pi/PiSecure')

from pisecure.core.blockchain import SignChain

# Create blockchain
bc = SignChain('/tmp/test_mining_session.json', use_hybrid_storage=False, mining_algorithm='pihash')

print("Initial mining session state:")
print(f"  Active: {bc.mining_session['active']}")
print(f"  Start time: {bc.mining_session['start_time']}")
print()

# Simulate what the mining thread does
print("Setting mining session to active...")
with bc.lock:
    bc.mining_session['active'] = True
    bc.mining_session['start_time'] = time.time()
    bc.mining_session['target_zeros'] = bc.target_zeros

time.sleep(0.5)

# Check if it was set
stats = bc.get_live_mining_stats()
print("\nMining stats after activation:")
print(f"  mining_active: {stats['mining_active']}")
print(f"  target_zeros: {stats['target_zeros']}")
print(f"  hashrate: {stats['hashrate']}")
print()

if stats['mining_active']:
    print("✅ Mining session state is working correctly!")
else:
    print("❌ Mining session state NOT set properly!")
