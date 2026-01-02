#!/bin/bash
#
# PiSecure Executable Wrapper
# ===========================
#
# Provides executable commands without requiring python -m syntax.
#

INSTALL_DIR="/opt/pisecure"
PYTHON_CMD="${PYTHON_CMD:-python3}"

# Check if virtual environment exists
if [[ -f "$INSTALL_DIR/venv/bin/activate" ]]; then
    source "$INSTALL_DIR/venv/bin/activate"
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
            echo "Usage: $0 transfer <recipient_wallet> <amount> [--from-wallet <source_wallet>]"
            echo "  recipient_wallet: wallet name/ID or full address"
            echo "  amount: number of tokens to transfer"
            echo "  --from-wallet: source wallet (optional, uses default if not specified)"
            exit 1
        fi

        # Resolve recipient wallet name/ID to address
        RECIPIENT="$2"
        AMOUNT="$3"

        # Check if recipient looks like a wallet name (contains letters) rather than hex address
        if [[ "$RECIPIENT" =~ [a-zA-Z] ]]; then
            # It's a wallet name/ID, resolve to address
            RECIPIENT_ADDRESS=$($PYTHON_CMD -c "
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
wallet_data = wallet.load_wallet('$RECIPIENT')
if 'error' in wallet_data:
    print('ERROR: Wallet $RECIPIENT not found')
    exit(1)
else:
    print(wallet_data.get('address', ''))
" 2>/dev/null)

            if [[ "$RECIPIENT_ADDRESS" == ERROR:* ]]; then
                echo "Error: $RECIPIENT_ADDRESS"
                exit 1
            fi
        else
            # It's already an address
            RECIPIENT_ADDRESS="$RECIPIENT"
        fi

        # Handle source wallet
        FROM_WALLET=""
        if [[ "$4" == "--from-wallet" ]]; then
            FROM_WALLET="--from-wallet $5"
        fi

        $PYTHON_CMD -m pisecure.cli transfer-tokens "$RECIPIENT_ADDRESS" "$AMOUNT" $FROM_WALLET
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
        echo "  transfer <to_wallet> <amount> [--from-wallet <wallet>] - Transfer tokens"
        echo "  mine               - Start interactive mining"
        echo "  dashboard          - Start web dashboard"
        echo "  verify-hardware    - Check Pi hardware eligibility"
        echo "  help               - Show this help"
        echo
        echo "Examples:"
        echo "  $0 status"
        echo "  $0 wallet"
        echo "  $0 create-wallet my_wallet \"My Mining Wallet\""
        echo "  $0 transfer node-406f0f 100                    # Transfer to wallet name"
        echo "  $0 transfer abc123... 100 --from-wallet my_wallet  # Transfer to address"
        echo "  $0 dashboard"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac