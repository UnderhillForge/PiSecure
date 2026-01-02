#!/bin/bash
"""
PiSecure Executable Wrapper
===========================

Provides executable commands without requiring python -m syntax.
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="${PYTHON_CMD:-python3}"

# Check if virtual environment exists
if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Main command processing
case "${1:-help}" in
    "status")
        $PYTHON_CMD -m pisecure.cli status
        ;;
    "wallet")
        $PYTHON_CMD -m pisecure.cli wallet "${2:-}"
        ;;
    "mine")
        $PYTHON_CMD -m pisecure.cli mine
        ;;
    "create-wallet")
        $PYTHON_CMD -m pisecure.cli create-wallet "${2:-default}" --name "${3:-PiSecure Wallet}"
        ;;
    "transfer")
        if [[ $# -lt 3 ]]; then
            echo "Usage: $0 transfer <recipient> <amount> [--from-wallet <wallet>]"
            exit 1
        fi
        FROM_WALLET=""
        if [[ "$4" == "--from-wallet" ]]; then
            FROM_WALLET="--from-wallet $5"
        fi
        $PYTHON_CMD -m pisecure.cli transfer-tokens "$2" "$3" $FROM_WALLET
        ;;
    "dashboard")
        $PYTHON_CMD dashboard/web/minimal_dashboard.py
        ;;
    "verify-hardware")
        $PYTHON_CMD -c "from pisecure.core.hardware import HardwareVerifier; v = HardwareVerifier(); print('Hardware check:', v.verify_mining_eligibility())"
        ;;
    "help"|"-h"|"--help")
        echo "PiSecure - Decentralized Security Framework"
        echo
        echo "Usage: $0 <command> [options]"
        echo
        echo "Commands:"
        echo "  status              - Show blockchain status"
        echo "  wallet [name]       - Show wallet info (or list all)"
        echo "  create-wallet <name> [display_name] - Create new wallet"
        echo "  transfer <to> <amount> [--from-wallet <wallet>] - Transfer tokens"
        echo "  mine               - Start interactive mining"
        echo "  dashboard          - Start web dashboard"
        echo "  verify-hardware    - Check Pi hardware eligibility"
        echo "  help               - Show this help"
        echo
        echo "Examples:"
        echo "  $0 status"
        echo "  $0 wallet"
        echo "  $0 create-wallet my_wallet \"My Mining Wallet\""
        echo "  $0 transfer abc123... 100 --from-wallet my_wallet"
        echo "  $0 dashboard"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac