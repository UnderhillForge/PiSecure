#!/usr/bin/env python3
"""
Testnet Demo - PiSecure Testing Features
=========================================

Demonstrates the --test and --validate-only flags for safe testing
without affecting your production blockchain or wallets.

Usage:
    # Run in testnet mode (separate data directory)
    python testnet_demo.py --test
    
    # Run in validate-only mode (no state changes)
    python testnet_demo.py --validate-only
    
    # Combine both flags
    python testnet_demo.py --test --validate-only
"""

import sys
import os
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pisecure.core.blockchain import SignChain
from pisecure.core.wallet import SignWallet


def print_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def get_data_dir(testnet=False):
    """Get data directory based on testnet flag"""
    return "/var/lib/pisecure-testnet" if testnet else "/var/lib/pisecure"


def get_wallet_dir(testnet=False):
    """Get wallet directory based on testnet flag"""
    return f"{get_data_dir(testnet)}/wallets"


def demo_testnet_mode():
    """Demonstrate testnet mode with separate data directory"""
    print_section("TESTNET MODE DEMONSTRATION")
    
    testnet_dir = get_data_dir(testnet=True)
    wallet_dir = get_wallet_dir(testnet=True)
    
    print("📁 Testnet Data Directories:")
    print(f"   Blockchain: {testnet_dir}/blockchain.json")
    print(f"   Wallets: {wallet_dir}/")
    print(f"   Transactions: {testnet_dir}/pending_transactions.json")
    print()
    
    # Create testnet directories
    os.makedirs(testnet_dir, exist_ok=True)
    os.makedirs(wallet_dir, exist_ok=True)
    
    # Initialize testnet blockchain
    print("🔗 Initializing testnet blockchain...")
    blockchain = SignChain(
        chain_file=f"{testnet_dir}/blockchain.json",
        difficulty=1  # Lower difficulty for testing
    )
    
    info = blockchain.get_chain_info()
    print(f"   ✅ Testnet blockchain initialized")
    print(f"   Blocks: {info['blocks']}")
    print(f"   Difficulty: {info['difficulty']}")
    print()
    
    # Create testnet wallet
    print("💰 Creating testnet wallet...")
    wallet = SignWallet(wallet_dir=wallet_dir)
    wallet_result = wallet.create_wallet("testnet_wallet_1", "Test Wallet")
    
    if 'address' in wallet_result:
        print(f"   ✅ Testnet wallet created")
        print(f"   Address: {wallet_result['address']}")
        print()
    
    # Add test transaction
    print("📦 Adding test transaction to testnet...")
    tx = {
        "type": "test_transaction",
        "data": {"message": "Testnet transaction"},
        "timestamp": time.time(),
        "signature": f"test_{int(time.time())}"
    }
    tx_hash = blockchain.add_transaction(tx)
    print(f"   ✅ Transaction added: {tx_hash[:16]}...")
    print()
    
    # Mine a block on testnet
    print("⛏️  Mining testnet block (difficulty 1)...")
    block = blockchain.mine_pending_transactions(
        miner_wallet_address=wallet_result['address'],
        verbose=False
    )
    
    if block:
        print(f"   ✅ Block mined: #{block.index}")
        print(f"   Hash: {block.hash[:32]}...")
        print()
    
    print("✨ Testnet demonstration complete!")
    print("   Your production blockchain at /var/lib/pisecure/ is unchanged.")
    print()


def demo_validate_only_mode():
    """Demonstrate validate-only mode (read-only operations)"""
    print_section("VALIDATE-ONLY MODE DEMONSTRATION")
    
    print("🔍 Validate-Only Mode: Read-only operations, no state changes")
    print()
    
    # In validate-only mode, we can read but not write
    blockchain = SignChain()
    
    # These operations are safe in validate-only mode:
    print("✅ Safe Operations (read-only):")
    print()
    
    print("   1. Get blockchain status")
    info = blockchain.get_chain_info()
    print(f"      Current blocks: {info['blocks']}")
    print(f"      Current difficulty: {info['difficulty']}")
    print()
    
    print("   2. Validate blockchain integrity")
    is_valid = blockchain.validate_chain()
    print(f"      Blockchain valid: {is_valid}")
    print()
    
    print("   3. Check wallet balance")
    # Create dummy address for demo
    test_address = "test_address_12345678"
    balance = blockchain.get_wallet_balance(test_address)
    print(f"      Test address balance: {balance} 314ST")
    print()
    
    print("   4. Estimate network hashrate")
    try:
        hashrate = blockchain.estimate_network_hashrate()
        print(f"      Network hashrate: {hashrate:.2f} H/s")
    except:
        print(f"      Network hashrate: Not enough blocks")
    print()
    
    print("❌ Blocked Operations (would modify state):")
    print("   • Mining blocks")
    print("   • Adding transactions")
    print("   • Creating wallets")
    print("   • Transferring tokens")
    print("   • Registering names")
    print()
    
    print("✨ Validate-only demonstration complete!")
    print("   No state changes were made to the blockchain.")
    print()


def demo_combined_mode():
    """Demonstrate combining --test and --validate-only"""
    print_section("COMBINED MODE: --test --validate-only")
    
    print("🔒 Combined Mode: Safe testing with no persistence")
    print()
    
    testnet_dir = get_data_dir(testnet=True)
    
    print("Benefits of combined mode:")
    print("   1. Uses testnet directory (isolated from production)")
    print("   2. No state changes (validate-only)")
    print("   3. Perfect for testing validation logic")
    print("   4. Safe for CI/CD pipelines")
    print()
    
    blockchain = SignChain(chain_file=f"{testnet_dir}/blockchain.json")
    
    print(f"📊 Testnet blockchain status:")
    info = blockchain.get_chain_info()
    print(f"   Blocks: {info['blocks']}")
    print(f"   Pending TX: {info['pending_transactions']}")
    print(f"   Valid: {info['is_valid']}")
    print()
    
    print("✨ Combined mode demonstration complete!")
    print()


def main():
    """Main demo function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PiSecure Testnet and Validation Demo"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Use testnet mode (separate data directory)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validation-only mode (no state changes)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  PiSecure Testing Features Demo")
    print("="*70)
    
    if args.test and args.validate_only:
        print("\n🔒 Running in TESTNET + VALIDATE-ONLY mode")
        demo_combined_mode()
    elif args.test:
        print("\n🧪 Running in TESTNET mode")
        demo_testnet_mode()
    elif args.validate_only:
        print("\n🔍 Running in VALIDATE-ONLY mode")
        demo_validate_only_mode()
    else:
        print("\n💡 Demo Options:")
        print("   python testnet_demo.py --test              # Testnet mode")
        print("   python testnet_demo.py --validate-only     # Validate-only mode")
        print("   python testnet_demo.py --test --validate-only  # Combined")
        print()
        
        # Run all demos
        demo_testnet_mode()
        demo_validate_only_mode()
        demo_combined_mode()
    
    print("="*70)
    print("  CLI Usage Examples:")
    print("="*70)
    print()
    print("# Testnet mining:")
    print("pisecure --test mine --wallet <address>")
    print()
    print("# Testnet blockchain status:")
    print("pisecure --test status")
    print()
    print("# Validate blockchain without changes:")
    print("pisecure --validate-only status")
    print()
    print("# Test transaction creation (testnet, no persistence):")
    print("pisecure --test --validate-only create-tx --count 10")
    print()
    print("# Show PiHash info (read-only):")
    print("pisecure --validate-only mining-info")
    print()


if __name__ == '__main__':
    main()
