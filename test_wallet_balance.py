#!/usr/bin/env python3
"""
Test script to verify wallet balance functionality in mining console
"""

import sys
import os
sys.path.insert(0, '/Users/jws/PiSecure/PiSecure')

try:
    from pisecure.core.blockchain import SignChain
    from pisecure.core.hardware import HardwareVerifier
    print("✅ Imports successful")

    # Initialize blockchain
    blockchain = SignChain()
    print("✅ Blockchain initialized")
    print(f"✅ Hybrid storage enabled: {blockchain.use_hybrid_storage}")

    # Test wallet balance query
    test_wallet = "test_wallet_address"
    balance = blockchain.get_wallet_balance(test_wallet)
    print(f"✅ Wallet balance query successful: {balance}")

    # Test wallet transactions query
    transactions = blockchain.get_wallet_transactions(test_wallet)
    print(f"✅ Wallet transactions query successful: {len(transactions)} transactions")

    # Test with a real wallet if available
    # Try to get miner wallet from environment or config
    miner_wallet = os.environ.get('PISECURE_MINER_WALLET', 'default_miner_wallet')
    balance = blockchain.get_wallet_balance(miner_wallet)
    print(f"✅ Miner wallet balance: {balance}")

    transactions = blockchain.get_wallet_transactions(miner_wallet)
    print(f"✅ Miner wallet transactions: {len(transactions)} transactions")

    print("✅ All wallet balance and transaction tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)