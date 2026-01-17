#!/usr/bin/env python3
"""
PiSecure Hybrid Storage Demo
============================

Demonstrates the hybrid storage system with block files + SQLite database.
"""

import time
import os
from pisecure.core.blockchain import SignChain
from pisecure.core.storage import HybridBlockchainStorage

def demo_hybrid_storage():
    """Demonstrate hybrid storage functionality"""

    print("🔄 PiSecure Hybrid Storage Demo")
    print("=" * 50)

    # Create temporary directory for demo
    demo_dir = "/tmp/pisecure_demo"
    os.makedirs(demo_dir, exist_ok=True)

    try:
        print("\n1. Creating blockchain with hybrid storage...")
        blockchain = SignChain(
            chain_file=f"{demo_dir}/blockchain.json",
            use_hybrid_storage=True
        )

        print("\n2. Adding test transactions...")
        for i in range(3):
            tx = {
                "type": "test_transaction",
                "data": {
                    "message": f"Hybrid storage test #{i+1}",
                    "timestamp": time.time(),
                    "value": i * 10
                },
                "signature": f"test_sig_{i}",
                "timestamp": time.time()
            }
            tx_hash = blockchain.add_transaction(tx)
            print(f"   ✅ Added transaction: {tx_hash[:16]}...")

        print("\n3. Mining blocks...")
        block = blockchain.mine_pending_transactions(miner_wallet_address="demo_wallet")
        if block:
            print(f"   ✅ Mined block #{block.index} with {len(block.transactions)} transactions")

        print("\n4. Checking storage files...")
        # Check block files
        blocks_dir = f"{demo_dir}/blocks"
        if os.path.exists(blocks_dir):
            blk_files = [f for f in os.listdir(blocks_dir) if f.startswith('blk')]
            print(f"   📁 Block files: {len(blk_files)} files")

        # Check database
        db_file = f"{demo_dir}/pisecure.db"
        if os.path.exists(db_file):
            db_size = os.path.getsize(db_file)
            print(f"   🗄️ Database: {db_size} bytes")

        print("\n5. Testing balance queries...")
        balance = blockchain.get_wallet_balance("demo_wallet")
        print(f"   💰 Demo wallet balance: {balance} 314ST")

        print("\n6. Blockchain info...")
        info = blockchain.get_chain_info()
        print(f"   📊 Blocks: {info['blocks']}")
        print(f"   🔗 Chain valid: {info['is_valid']}")
        print(f"   💾 Storage type: hybrid")

        print("\n✅ Hybrid storage demo completed successfully!")
        print("   - Block data stored in binary files")
        print("   - Index and UTXO set in SQLite database")
        print("   - Fast queries with O(1) block lookups")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        import shutil
        if os.path.exists(demo_dir):
            shutil.rmtree(demo_dir)
            print(f"\n🧹 Cleaned up demo directory: {demo_dir}")

if __name__ == "__main__":
    demo_hybrid_storage()