#!/usr/bin/env python3
"""
Basic PiSecure Mining Example
==============================

This example demonstrates basic blockchain mining with PiSecure.
It creates test transactions and mines them into blocks.
"""

import time
from pisecure.core import SignChain, HardwareVerifier, SignTokenMiner

def main():
    print("🔒 PiSecure Basic Mining Example")
    print("=" * 40)

    # 1. Verify hardware
    print("\n1. 🔍 Verifying hardware...")
    verifier = HardwareVerifier()
    result = verifier.verify_mining_eligibility()

    if not result['eligible']:
        print("❌ Hardware verification failed - cannot mine on this device")
        return

    print(f"✅ Hardware verified: {result['hardware_model']}")

    # 2. Initialize blockchain
    print("\n2. ⛓️ Initializing blockchain...")
    blockchain = SignChain()
    print(f"   Chain loaded with {blockchain.get_chain_info()['blocks']} blocks")

    # 3. Create test transactions
    print("\n3. 📦 Creating test transactions...")
    for i in range(3):
        tx = {
            "type": "test_transaction",
            "data": {
                "message": f"Example transaction #{i+1}",
                "timestamp": time.time(),
                "sensor_reading": 25.5 + i  # Fake sensor data
            },
            "signature": f"example_sig_{i}",
            "timestamp": time.time()
        }
        tx_hash = blockchain.add_transaction(tx)
        print(f"   ✅ Added transaction: {tx_hash[:16]}...")

    # 4. Mine the transactions
    print(f"\n4. ⛏️ Mining {blockchain.get_chain_info()['pending_transactions']} transactions...")

    miner = SignTokenMiner(blockchain)
    success = miner.start_interactive_mining()

    if success:
        print("\n✅ Mining completed successfully!")
        print(f"   Final chain length: {blockchain.get_chain_info()['blocks']} blocks")
    else:
        print("\n❌ Mining failed or was interrupted")

    # 5. Show final status
    print("\n5. 📊 Final blockchain status:")
    info = blockchain.get_chain_info()
    print(f"   Blocks: {info['blocks']}")
    print(f"   Difficulty: {info['difficulty']}")
    print(f"   Chain valid: {'✅' if info['is_valid'] else '❌'}")

if __name__ == "__main__":
    main()