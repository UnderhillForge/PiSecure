#!/usr/bin/env python3
"""
PiSecure - Decentralized Security Framework for Raspberry Pi
============================================================

Main entry point for PiSecure blockchain node operations.
"""

import sys
import os

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("PiSecure - Decentralized Security Framework")
        print()
        print("Usage:")
        print("  pisecure.py status          - Show blockchain status")
        print("  pisecure.py wallet          - Show wallet information")
        print("  pisecure.py mine           - Start mining")
        print("  pisecure.py mine --team NAME - Join mining team")
        print("  pisecure.py dashboard      - Start web dashboard")
        print("  pisecure.py create-wallet  - Create new wallet")
        print()
        print("Team Mining:")
        print("  --team NAME        Join existing team")
        print("  --create-team NAME Create new team")
        print()
        print("For full CLI: python -m pisecure.cli")
        return

    command = sys.argv[1]

    if command == "status":
        os.system("python -m pisecure.cli status")
    elif command == "wallet":
        os.system("python -m pisecure.cli wallet")
    elif command == "mine":
        os.system("python mining-console.py")
    elif command == "dashboard":
        os.system("python dashboard/web/minimal_dashboard.py")
    elif command == "create-wallet":
        wallet_name = input("Wallet name (default): ") or "default"
        wallet_display = input("Display name: ") or "PiSecure Wallet"
        os.system(f"python -m pisecure.cli create-wallet '{wallet_name}' --name '{wallet_display}'")
    else:
        print(f"Unknown command: {command}")
        print("Use 'pisecure.py' without arguments to see available commands")

if __name__ == "__main__":
    main()