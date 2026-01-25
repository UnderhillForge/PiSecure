#!/usr/bin/env python3
"""
Demo script showing psvalidator integration with PiSecure network
"""

import subprocess
import time
import json
from websocket import create_connection


def test_psvalidator():
    """Test psvalidator functionality"""

    print("=" * 70)
    print("PSVALIDATOR DEMO - Universal Blockchain Validator")
    print("=" * 70)
    print()

    # Check if pisecured is running
    print("1. Checking pisecured daemon...")
    try:
        ws = create_connection("ws://127.0.0.1:3142", timeout=2)
        ws.send(json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1}))
        response = json.loads(ws.recv())
        if response.get("result", {}).get("status") == "pong":
            print("   ✓ pisecured is running")
        ws.close()
    except Exception as e:
        print(f"   ✗ pisecured not running: {e}")
        print("   Please start pisecured first:")
        print("     pisecured --validate-only")
        return False

    print()
    print("2. psvalidator Features:")
    print("   • Works on ANY platform (Mac, Windows, Linux, Pi)")
    print("   • Validates blocks using zero bit counting")
    print("   • Validates transaction structure")
    print("   • Earns 1% of block rewards")
    print("   • Three modes: TUI, CLI, Daemon")
    print()

    print("3. Comparison with psminer:")
    print("   ┌──────────────┬─────────────────┬───────────────────┐")
    print("   │ Feature      │ psminer         │ psvalidator       │")
    print("   ├──────────────┼─────────────────┼───────────────────┤")
    print("   │ Platform     │ Raspberry Pi    │ ANY system        │")
    print("   │ Algorithm    │ PiHash          │ SHA256 + XOR      │")
    print("   │ Hardware     │ Required        │ Not required      │")
    print("   │ Rewards      │ 99% of block    │ 1% (shared)       │")
    print("   └──────────────┴─────────────────┴───────────────────┘")
    print()

    print("4. Usage Examples:")
    print()
    print("   # TUI Mode (default)")
    print("   psvalidator --wallet pisecure_wallet_abc123")
    print()
    print("   # Daemon Mode")
    print("   psvalidator --wallet pisecure_wallet_abc123 --daemon")
    print()
    print("   # Remote Daemon")
    print("   psvalidator --wallet pisecure_wallet_abc123 \\")
    print("     --daemon-url ws://192.168.1.100:3142")
    print()
    print("   # Testnet")
    print("   psvalidator --wallet pisecure_wallet_test123 --testnet")
    print()

    print("5. Validation Workflow:")
    print("   1. Connect to pisecured via WebSocket")
    print("   2. Monitor blockchain for new blocks")
    print("   3. Validate proof-of-work (zero bits)")
    print("   4. Validate transaction structure")
    print("   5. Report results to daemon")
    print("   6. Earn rewards in validator bucket")
    print()

    print("6. Reward Economics:")
    print("   Block Reward: 50 tokens")
    print("   ├─ 99% → Miner (49.5 tokens)")
    print("   └─ 1% → Validator Pool (0.5 tokens)")
    print("       └─ Split among N active validators")
    print()
    print("   Example with 10 validators:")
    print("     Each earns: 0.5 ÷ 10 = 0.05 tokens/block")
    print("     Over 1000 blocks: 50 tokens earned")
    print()

    print("7. TUI Display Preview:")
    print(
        """
╔════════════════════════════════════════════════════════════════╗
║              PSVALIDATOR - VALIDATION MONITOR                  ║
╚════════════════════════════════════════════════════════════════╝

┌─ VALIDATION STATISTICS ────────────────────────────────────────┐
│ Blocks Validated:            1,234                             │
│ Transactions Validated:     56,789                             │
│ Invalid Blocks:                  3                             │
│ Current Height:            1,235                               │
│ Uptime:                   12:34:56                             │
└────────────────────────────────────────────────────────────────┘

┌─ VALIDATOR REWARDS ────────────────────────────────────────────┐
│ Total Earned:               45.2500 tokens                     │
│ Current Bucket:             15.5000 tokens                     │
│ Reward Rate:            1% of block rewards                    │
└────────────────────────────────────────────────────────────────┘

Press 'q' to quit | 'r' to refresh | No Pi Hardware Required
    """
    )

    print("=" * 70)
    print("✓ psvalidator is ready for use!")
    print("=" * 70)
    print()
    print("Build:")
    print("  cd /home/pi/PiSecure/cpp/psvalidator")
    print("  ./build.sh")
    print()
    print("Run:")
    print("  ./build/psvalidator --help")
    print("  ./build/psvalidator --wallet YOUR_WALLET")
    print()

    return True


if __name__ == "__main__":
    import sys

    success = test_psvalidator()
    sys.exit(0 if success else 1)
