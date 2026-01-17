#!/usr/bin/env python3
"""
Quick Test: Hybrid Storage Default Behavior
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pisecure.core.blockchain import SignChain

def test_hybrid_storage():
    # Test with temporary directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        chain_file = os.path.join(tmpdir, "test_blockchain.json")

        # Create blockchain (should auto-detect hybrid storage)
        blockchain = SignChain(chain_file=chain_file)

        print(f"Hybrid storage enabled: {blockchain.use_hybrid_storage}")
        print(f"Blocks in chain: {len(blockchain.chain)}")

        # Test basic operations
        info = blockchain.get_chain_info()
        print(f"Chain info: {info}")

        # Check if storage files were created
        if blockchain.use_hybrid_storage:
            import glob
            blk_files = glob.glob(os.path.join(tmpdir, "blocks", "blk*.dat"))
            db_file = os.path.join(tmpdir, "pisecure.db")

            print(f"Block files created: {len(blk_files)}")
            print(f"Database created: {os.path.exists(db_file)}")

        print("✅ Test completed successfully!")

if __name__ == "__main__":
    test_hybrid_storage()