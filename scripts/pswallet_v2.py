#!/usr/bin/env python3
"""
PiSecure Wallet CLI v2 - Bitcoin Core Inspired
===============================================

Command-line interface for the enhanced PiSecure wallet system.
Uses wallet_v2.py with HD wallet, UTXO tracking, and advanced features.

Features:
- Create HD wallets with mnemonic phrases
- Watch-only wallet mode
- UTXO management
- Address book with labels
- Coin selection and fee estimation
- Encrypted wallet support
- Multi-wallet management
"""

import sys
import argparse
import json
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager, HDWalletDerivation


def create_parser():
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(
        description="PiSecure Wallet CLI - Enhanced wallet management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create wallet
    create_parser = subparsers.add_parser("create", help="Create new wallet")
    create_parser.add_argument("name", help="Wallet name")
    create_parser.add_argument(
        "--watch-only", action="store_true", help="Create watch-only wallet"
    )
    create_parser.add_argument("--passphrase", help="Encryption passphrase")

    # List wallets
    subparsers.add_parser("list", help="List all wallets")

    # Load wallet
    load_parser = subparsers.add_parser("load", help="Load wallet")
    load_parser.add_argument("name", help="Wallet name")

    # Get new address
    address_parser = subparsers.add_parser(
        "getnewaddress", help="Generate new receiving address"
    )
    address_parser.add_argument("wallet", help="Wallet name")
    address_parser.add_argument("--label", default="", help="Address label")

    # Get balance
    balance_parser = subparsers.add_parser("getbalance", help="Get wallet balance")
    balance_parser.add_argument("wallet", help="Wallet name")
    balance_parser.add_argument(
        "--unconfirmed", action="store_true", help="Include unconfirmed"
    )

    # List unspent
    unspent_parser = subparsers.add_parser("listunspent", help="List unspent outputs")
    unspent_parser.add_argument("wallet", help="Wallet name")
    unspent_parser.add_argument(
        "--minconf", type=int, default=1, help="Minimum confirmations"
    )

    # Send transaction
    send_parser = subparsers.add_parser("send", help="Send tokens")
    send_parser.add_argument("wallet", help="Wallet name")
    send_parser.add_argument("recipient", help="Recipient address")
    send_parser.add_argument("amount", type=float, help="Amount to send")
    send_parser.add_argument(
        "--fee-rate", type=float, default=0.0001, help="Fee rate per byte"
    )

    # Address book
    addlabel_parser = subparsers.add_parser("addlabel", help="Add address label")
    addlabel_parser.add_argument("wallet", help="Wallet name")
    addlabel_parser.add_argument("address", help="Address to label")
    addlabel_parser.add_argument("label", help="Label text")
    addlabel_parser.add_argument(
        "--purpose", default="send", help="Address purpose (send/receive)"
    )

    getlabel_parser = subparsers.add_parser("getlabel", help="Get address label")
    getlabel_parser.add_argument("wallet", help="Wallet name")
    getlabel_parser.add_argument("address", help="Address")

    # Backup
    backup_parser = subparsers.add_parser("backup", help="Backup wallet")
    backup_parser.add_argument("wallet", help="Wallet name")
    backup_parser.add_argument("path", help="Backup file path")

    # Encrypt
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt wallet")
    encrypt_parser.add_argument("wallet", help="Wallet name")
    encrypt_parser.add_argument("passphrase", help="Encryption passphrase")

    # Unlock
    unlock_parser = subparsers.add_parser("unlock", help="Unlock encrypted wallet")
    unlock_parser.add_argument("wallet", help="Wallet name")
    unlock_parser.add_argument("passphrase", help="Decryption passphrase")

    # Wallet info
    info_parser = subparsers.add_parser("info", help="Show wallet information")
    info_parser.add_argument("wallet", help="Wallet name")

    # PiNS (Pi Name System) commands
    # Check name availability
    check_parser = subparsers.add_parser(
        "checkname", help="Check PiNS name availability"
    )
    check_parser.add_argument("wallet", help="Wallet name")
    check_parser.add_argument("name", help="Name to check")

    # Register name
    register_parser = subparsers.add_parser("registername", help="Register PiNS name")
    register_parser.add_argument("wallet", help="Wallet name")
    register_parser.add_argument("name", help="Name to register")
    register_parser.add_argument(
        "--years", type=int, default=1, help="Registration years"
    )

    # Resolve name
    resolve_parser = subparsers.add_parser(
        "resolvename", help="Resolve PiNS name to address"
    )
    resolve_parser.add_argument("wallet", help="Wallet name")
    resolve_parser.add_argument("name", help="Name to resolve")

    # List wallet names
    listnames_parser = subparsers.add_parser(
        "listnames", help="List PiNS names owned by wallet"
    )
    listnames_parser.add_argument("wallet", help="Wallet name")

    return parser


def format_time(timestamp: float) -> str:
    """Format timestamp to human-readable string"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Use local wallets directory for testing (not /var/lib)
    wallet_dir = Path.home() / ".pisecure" / "wallets"
    wallet_dir.mkdir(parents=True, exist_ok=True)

    # Initialize wallet manager
    manager = WalletManager(data_dir=str(wallet_dir))

    try:
        if args.command == "create":
            print(f"Creating wallet '{args.name}'...")
            wallet = manager.create_wallet(args.name, watch_only=args.watch_only)

            if args.passphrase:
                wallet.encrypt_wallet(args.passphrase)
                print("✅ Wallet encrypted with passphrase")

            if not args.watch_only:
                address = wallet.get_new_address("Primary")
                print(f"✅ Wallet created successfully!")
                print(f"   Name: {args.name}")
                print(f"   Address: {address}")
                print(f"   Type: HD Wallet")
                print(f"   Watch-only: {args.watch_only}")
            else:
                print(f"✅ Watch-only wallet created!")
                print(f"   Name: {args.name}")

        elif args.command == "list":
            wallets = manager.list_wallets()
            if wallets:
                print(f"Available wallets ({len(wallets)}):")
                for wallet_name in wallets:
                    print(f"  • {wallet_name}")
            else:
                print("No wallets found.")

        elif args.command == "load":
            wallet = manager.load_wallet(args.name)
            if wallet:
                print(f"✅ Wallet '{args.name}' loaded successfully")
            else:
                print(f"❌ Wallet '{args.name}' not found")

        elif args.command == "getnewaddress":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            address = wallet.get_new_address(args.label)
            print(f"New address: {address}")
            if args.label:
                print(f"Label: {args.label}")

        elif args.command == "getbalance":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            balance = wallet.get_balance()
            print(f"Confirmed balance: {balance:.8f} 314ST")

            if args.unconfirmed:
                unconfirmed = wallet.get_unconfirmed_balance()
                print(f"Unconfirmed balance: {unconfirmed:.8f} 314ST")
                print(f"Total: {balance + unconfirmed:.8f} 314ST")

        elif args.command == "listunspent":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            utxos = wallet.list_unspent(min_conf=args.minconf)
            if utxos:
                print(f"Unspent outputs ({len(utxos)}):")
                total = 0.0
                for utxo in utxos:
                    print(f"  • {utxo.tx_hash[:16]}...:{utxo.output_index}")
                    print(f"    Amount: {utxo.amount:.8f} 314ST")
                    print(f"    Confirmations: {utxo.confirmations}")
                    print(f"    Spendable: {utxo.spendable}")
                    total += utxo.amount
                print(f"\nTotal: {total:.8f} 314ST")
            else:
                print("No unspent outputs.")

        elif args.command == "send":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            print(f"Creating transaction...")
            tx = wallet.create_transaction(args.recipient, args.amount, args.fee_rate)

            if tx:
                print(f"✅ Transaction created!")
                print(f"   Recipient: {args.recipient}")
                print(f"   Amount: {args.amount:.8f} 314ST")
                print(f"   Fee: {tx['fee']:.8f} 314ST")
                print(f"   Inputs: {len(tx['inputs'])}")
                print(f"   Outputs: {len(tx['outputs'])}")
                if "signature" in tx:
                    print(f"   Status: Signed")

                # In real implementation, broadcast to network here
                print(
                    "\n⚠️  Transaction created but not broadcast (needs network integration)"
                )
            else:
                print(f"❌ Failed to create transaction (insufficient funds?)")

        elif args.command == "addlabel":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            wallet.add_address_label(args.address, args.label, args.purpose)
            print(f"✅ Label added to {args.address[:16]}...")
            print(f"   Label: {args.label}")
            print(f"   Purpose: {args.purpose}")

        elif args.command == "getlabel":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            label = wallet.get_address_label(args.address)
            if label:
                print(f"Label: {label}")
            else:
                print(f"No label for address {args.address[:16]}...")

        elif args.command == "backup":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            if wallet.backup_wallet(args.path):
                print(f"✅ Wallet backed up to {args.path}")
            else:
                print(f"❌ Backup failed")

        elif args.command == "encrypt":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            if wallet.encrypt_wallet(args.passphrase):
                print(f"✅ Wallet encrypted successfully")
                print("⚠️  Keep your passphrase safe - it cannot be recovered!")
            else:
                print(f"❌ Encryption failed (already encrypted?)")

        elif args.command == "unlock":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            if wallet.unlock_wallet(args.passphrase):
                print(f"✅ Wallet unlocked successfully")
            else:
                print(f"❌ Unlock failed (wrong passphrase?)")

        elif args.command == "info":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            print(f"Wallet Information:")
            print(f"  Name: {args.wallet}")
            print(f"  Watch-only: {wallet.watch_only}")
            print(f"  Encrypted: {wallet.encrypted}")
            print(f"  Balance: {wallet.get_balance():.8f} 314ST")
            print(f"  Unconfirmed: {wallet.get_unconfirmed_balance():.8f} 314ST")

            utxos = wallet.list_unspent(min_conf=0)
            print(f"  UTXOs: {len(utxos)}")

            if wallet.spk_manager:
                print(f"  Key Manager: DescriptorScriptPubKeyMan (HD Wallet)")

        elif args.command == "checkname":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            result = wallet.check_name_availability(args.name)
            if result.get("available", False):
                print(f"✅ Name '{args.name}.pisecure' is available!")
                print(f"   Registration fee: {result['registration_fee']} tokens")
                print(
                    f"   Estimated confirmation: {result['estimated_confirmation']} seconds"
                )
            else:
                if result.get("registered", False):
                    print(f"❌ Name '{args.name}.pisecure' is already registered")
                    print(f"   Owner: {result.get('owner', 'unknown')}")
                else:
                    print(f"❌ {result.get('error', 'Name not available')}")

        elif args.command == "registername":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            result = wallet.register_pins_name(args.name, args.years)
            if result.get("success", False):
                print(f"✅ Name '{result['name']}.pisecure' registered successfully!")
                print(f"   Address: {result['address']}")
                print(f"   Registered: {time.ctime(result['registered_at'])}")
                print(f"   Expires: {time.ctime(result['expires_at'])}")
                print(f"   Fee paid: {result['fee']} tokens")
                print(f"   Status: {result['status']}")
            else:
                print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")

        elif args.command == "resolvename":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            result = wallet.resolve_pins_name(args.name)
            if result.get("resolved", False):
                print(f"✅ Name '{result['name']}.pisecure' resolves to:")
                print(f"   Address: {result['address']}")
                print(f"   Registered: {time.ctime(result['registered_at'])}")
                print(f"   Expires: {time.ctime(result['expires_at'])}")
                print(f"   Years remaining: {result['years_remaining']:.1f}")
            else:
                print(f"❌ {result.get('error', 'Resolution failed')}")

        elif args.command == "listnames":
            wallet = manager.load_wallet(args.wallet)
            if not wallet:
                print(f"❌ Wallet '{args.wallet}' not found")
                return

            names = wallet.get_wallet_pins_names()
            if names:
                print(f"PiNS names owned by this wallet:")
                for name_info in names:
                    status_icon = "✅" if name_info["status"] == "active" else "⏰"
                    print(f"  {status_icon} {name_info['name']}.pisecure")
                    print(f"     Status: {name_info['status']}")
                    print(f"     Years remaining: {name_info['years_remaining']:.1f}")
            else:
                print(f"No PiNS names registered to this wallet")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
