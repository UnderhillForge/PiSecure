#!/usr/bin/env python3
"""
PiSecure Wallet Demo
====================

Demonstrates wallet creation, token transfers, and balance management
using the PiSecure hybrid wallet system.
"""

import time
import sys
import os

# Add PiSecure to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pisecure.core.wallet import SignWallet
from pisecure.core.blockchain import SignChain


def demo_wallet_operations():
    """Demonstrate basic wallet operations"""

    print("🔐 PiSecure Wallet Demo")
    print("=" * 50)

    # Initialize wallet system
    wallet_system = SignWallet()
    blockchain = SignChain()

    # Create two test wallets
    print("\n1. Creating test wallets...")

    wallet1_result = wallet_system.create_wallet("demo_wallet_1", "Demo Wallet 1")
    if wallet1_result['success']:
        wallet1_id = wallet1_result['wallet_id']
        wallet1_address = wallet1_result['address']
        print(f"   ✓ Created wallet: {wallet1_id}")
        print(f"     Address: {wallet1_address}")
    else:
        print(f"   ✗ Failed to create wallet 1: {wallet1_result.get('error')}")
        return

    wallet2_result = wallet_system.create_wallet("demo_wallet_2", "Demo Wallet 2")
    if wallet2_result['success']:
        wallet2_id = wallet2_result['wallet_id']
        wallet2_address = wallet2_result['address']
        print(f"   ✓ Created wallet: {wallet2_id}")
        print(f"     Address: {wallet2_address}")
    else:
        print(f"   ✗ Failed to create wallet 2: {wallet2_result.get('error')}")
        return

    # Load wallets for operations
    print("\n2. Loading wallets for operations...")

    wallet1 = SignWallet(f"/var/lib/pisecure/wallets/{wallet1_id}.json")
    wallet2 = SignWallet(f"/var/lib/pisecure/wallets/{wallet2_id}.json")

    # Check initial balances
    print("\n3. Checking initial balances...")
    balance1 = wallet1.get_balance()
    balance2 = wallet2.get_balance()

    print(f"   Wallet 1 ({wallet1_id}): {balance1:.2f} tokens")
    print(f"   Wallet 2 ({wallet2_id}): {balance2:.2f} tokens")

    # Create a transfer transaction
    print("\n4. Creating token transfer...")
    transfer_amount = 50.0

    transaction = wallet1.create_transfer_transaction(wallet2_address, transfer_amount, "Demo transfer")

    if 'error' in transaction:
        print(f"   ✗ Failed to create transfer: {transaction['error']}")
        return

    print(f"   ✓ Created transfer: {transfer_amount} tokens")
    print(f"     From: {wallet1_address[:20]}...")
    print(f"     To: {wallet2_address[:20]}...")
    print(f"     Signature: {transaction['signature'][:20]}...")

    # Submit transaction to blockchain
    print("\n5. Submitting transaction to blockchain...")

    try:
        tx_hash = blockchain.add_transaction(transaction)
        print(f"   ✓ Transaction submitted: {tx_hash}")

        # Mine the transaction
        print("   Mining transaction...")
        mined_block = blockchain.mine_pending_transactions(verbose=False)

        if mined_block:
            print(f"   ✓ Transaction mined in block #{mined_block.index}")

            # Update wallet balances
            wallet1.add_transaction_record(transaction, tx_hash)
            # Note: In real implementation, wallet2 would also be updated
            # when it receives confirmation from the network

        else:
            print("   ✗ Failed to mine transaction")
            return

    except Exception as e:
        print(f"   ✗ Transaction failed: {e}")
        return

    # Check final balances
    print("\n6. Checking final balances...")
    final_balance1 = wallet1.get_balance()
    final_balance2 = blockchain.get_wallet_balance(wallet2_address)  # Get from blockchain

    print(f"   Wallet 1 ({wallet1_id}): {final_balance1:.2f} tokens")
    print(f"   Wallet 2 ({wallet2_id}): {final_balance2:.2f} tokens")

    # Show transaction history
    print("\n7. Wallet 1 transaction history:")
    history = wallet1.get_transaction_history()

    if history:
        for tx in history[-3:]:  # Show last 3 transactions
            direction = "→ OUT" if tx['direction'] == 'outgoing' else "← IN"
            print(f"   {direction} {tx['amount']:.2f} tokens (Block #{tx['block_index']})")
    else:
        print("   No transactions found")

    print("\n8. Creating batch transfer...")

    # Create batch transfer
    batch_transfers = [
        {'recipient': wallet2_address, 'amount': 10.0},
        {'recipient': wallet2_address, 'amount': 15.0},
        {'recipient': wallet2_address, 'amount': 25.0}
    ]

    batch_tx = wallet1.create_batch_transaction(batch_transfers, "Batch demo transfer")

    if 'error' in batch_tx:
        print(f"   ✗ Failed to create batch transfer: {batch_tx['error']}")
        return

    print(f"   ✓ Created batch transfer: {batch_tx['transfer_count']} transfers, {batch_tx['total_amount']} total tokens")

    # Submit batch transaction
    try:
        batch_hash = blockchain.add_transaction(batch_tx)
        print(f"   ✓ Batch transaction submitted: {batch_hash}")

        # Mine batch transaction
        batch_block = blockchain.mine_pending_transactions(verbose=False)
        if batch_block:
            print(f"   ✓ Batch transaction mined in block #{batch_block.index}")

    except Exception as e:
        print(f"   ✗ Batch transaction failed: {e}")

    print("\n✅ Wallet demo completed successfully!")
    print("\nKey takeaways:")
    print("- Wallets use RSA cryptography for secure signing")
    print("- Transactions are validated before blockchain inclusion")
    print("- Batch transfers group multiple operations efficiently")
    print("- Balances are tracked locally and verified on-chain")


def demo_wallet_cli():
    """Show equivalent CLI commands"""
    print("\n" + "=" * 50)
    print("Equivalent CLI Commands:")
    print("=" * 50)

    cli_commands = [
        "# Create wallets",
        "pisecure create-wallet 'demo_wallet_1' --name 'Demo Wallet 1'",
        "pisecure create-wallet 'demo_wallet_2' --name 'Demo Wallet 2'",
        "",
        "# Check balances",
        "pisecure show-wallet",
        "",
        "# Transfer tokens",
        "pisecure transfer-tokens <wallet2_address> 50 --from-wallet 'demo_wallet_1'",
        "",
        "# View history",
        "pisecure wallet-history <wallet1_address>",
        "",
        "# Check blockchain status",
        "pisecure status"
    ]

    for cmd in cli_commands:
        if cmd.startswith("#"):
            print(f"\033[92m{cmd}\033[0m")  # Green for comments
        elif cmd.strip():
            print(f"\033[94m{cmd}\033[0m")  # Blue for commands
        else:
            print()


if __name__ == "__main__":
    try:
        demo_wallet_operations()
        demo_wallet_cli()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()