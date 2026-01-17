#!/usr/bin/env python3
"""
Test Wallet Functionality with Hybrid Storage
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pisecure.core.blockchain import SignChain

def test_wallet_functionality():
    # Create blockchain with hybrid storage
    blockchain = SignChain()

    print(f"Hybrid storage enabled: {blockchain.use_hybrid_storage}")

    # Test wallet balance (should be 0 for non-existent wallet)
    balance = blockchain.get_wallet_balance("test_wallet")
    print(f"Test wallet balance: {balance}")

    # Test transaction history (should be empty)
    transactions = blockchain.get_wallet_transactions("test_wallet")
    print(f"Test wallet transactions: {len(transactions)} found")

    # Add a test transaction
    tx = {
        "type": "token_transfer",
        "sender_address": "sender_wallet",
        "recipient_address": "test_wallet",
        "amount": 100.0,
        "timestamp": 1234567890,
        "signature": "test_sig"
    }

    blockchain.add_transaction(tx)
    print("Added test transaction")

    # Mine it
    block = blockchain.mine_pending_transactions()
    if block:
        print(f"Mined block #{block.index}")

    # Check balance again
    balance = blockchain.get_wallet_balance("test_wallet")
    print(f"Updated test wallet balance: {balance}")

    # Check transactions
    transactions = blockchain.get_wallet_transactions("test_wallet")
    print(f"Test wallet transactions after mining: {len(transactions)} found")

    if transactions:
        tx = transactions[0]
        print(f"Transaction details: {tx['type']}, {tx['direction']}, {tx['amount']} tokens")

    print("✅ Wallet functionality test completed!")

if __name__ == "__main__":
    test_wallet_functionality()