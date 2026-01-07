#!/usr/bin/env python3
"""
PiSecure - Decentralized Security Framework for Raspberry Pi
============================================================

Main entry point for PiSecure blockchain node operations.
"""

import sys
import os
import time
import json
import threading
import psutil
import socket
from datetime import datetime
from collections import deque

try:
    # Try relative imports first (for package installation)
    from pisecure.core.blockchain import SignChain
    from pisecure.core.hardware import HardwareVerifier
    from pisecure.core.nat_traversal import node_discovery
    from pisecure.core.p2p_sync import P2PSyncManager
    from pisecure.core.consensus import get_consensus_engine
    from pisecure.network.discovery import PeerDiscovery
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core.blockchain import SignChain
    from core.hardware import HardwareVerifier
    from core.nat_traversal import node_discovery
    from core.p2p_sync import P2PSyncManager
    from core.consensus import get_consensus_engine
    from network.discovery import PeerDiscovery


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
        # Parse mining arguments
        team_name = None
        create_team = None
        wallet = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--team" and i + 1 < len(sys.argv):
                team_name = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--create-team" and i + 1 < len(sys.argv):
                create_team = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--wallet" and i + 1 < len(sys.argv):
                wallet = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        # Use CLI mining interface instead
        os.system(f"python -m pisecure.cli mine --wallet '{wallet}'" if wallet else "python -m pisecure.cli mine")
    elif command == "dashboard":
        os.system("python dashboard/web/minimal_dashboard.py")
    elif command == "create-wallet":
        wallet_name = input("Wallet name (default): ") or "default"
        wallet_display = input("Display name: ") or "PiSecure Wallet"
        os.system(f"python -m pisecure.cli create-wallet '{wallet_name}' --display-name '{wallet_display}'")
    else:
        print(f"Unknown command: {command}")
        print("Use 'pisecure.py' without arguments to see available commands")

if __name__ == "__main__":
    main()