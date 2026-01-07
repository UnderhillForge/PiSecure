#!/bin/bash
#
# PiSecure Genesis Reset Script
# =============================
#
# DANGER: This script completely resets PiSecure to genesis state
#         ALL BLOCKCHAIN DATA, WALLETS, AND TRANSACTIONS WILL BE LOST
#
# This script will:
# - Stop all PiSecure services
# - Remove all blockchain data files
# - Clear all wallet data and keys
# - Reset economic data (trust funds, subscriptions)
# - Clear P2P network state and peer data
# - Remove identity and certificate data
# - Reset configuration to defaults
# - Clear all caches and temporary files
#
# Use with extreme caution - this is irreversible!

set -e  # Exit on any error
set -o pipefail  # Catch errors in pipelines
set -o pipefail  # Catch errors in pipelines

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/genesis_backup_$(date +%Y%m%d_%H%M%S)"

# Track which stage we're in for error reporting
CURRENT_STAGE=""

# Error handling function
error_handler() {
    local line_number=$1
    local error_code=$2
    print_error "Script failed at line ${line_number} with exit code ${error_code}"
    
    if [ -n "$CURRENT_STAGE" ]; then
        print_error "Failed during: ${CURRENT_STAGE}"
    fi
    
    echo ""
    echo -e "${RED}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   ❌ GENESIS RESET FAILED ❌                 ║"
    echo "║                                                              ║"
    echo "║  The genesis reset was interrupted due to an error          ║"
    echo "║                                                              ║"
    echo "║  Error Details:                                              ║"
    echo "║  • Line: ${line_number}"
    echo "║  • Exit Code: ${error_code}"
    echo "║  • Stage: ${CURRENT_STAGE}"
    echo "║                                                              ║"
    echo "║  System may be in an inconsistent state!                    ║"
    echo "║                                                              ║"
    echo "║  Recommendations:                                            ║"
    echo "║  1. Check the error message above                           ║"
    echo "║  2. Review system logs for more details                     ║"
    echo "║  3. Restore from backup if available:                       ║"
    if [ -d "$BACKUP_DIR" ]; then
        echo "║     ${BACKUP_DIR}"
    else
        echo "║     (No backup was created yet)"
    fi
    echo "║  4. Contact support if the issue persists                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    exit $error_code
}

# Set up error trap
trap 'error_handler ${LINENO} $?' ERR

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to confirm dangerous operation
confirm_reset() {
    echo -e "${RED}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    ⚠️  DANGER ZONE ⚠️                        ║"
    echo "║                                                              ║"
    echo "║  This will COMPLETELY RESET PiSecure to genesis state!       ║"
    echo "║                                                              ║"
    echo "║  ALL DATA WILL BE LOST:                                      ║"
    echo "║  • Blockchain (10,000+ blocks)                               ║"
    echo "║  • All wallets and private keys                              ║"
    echo "║  • Transaction history                                       ║"
    echo "║  • Trust funds and subscriptions                             ║"
    echo "║  • Mining rewards and balances                               ║"
    echo "║  • P2P network connections                                   ║"
    echo "║  • Device identities and certificates                        ║"
    echo "║  • Economic data and market history                          ║"
    echo "║                                                              ║"
    echo "║  This action is IRREVERSIBLE!                                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo ""
    echo -e "${YELLOW}Type 'YES' (in all caps) to confirm genesis reset:${NC}"
    read -r confirmation

    if [ "$confirmation" != "YES" ]; then
        echo -e "${RED}Genesis reset cancelled.${NC}"
        CURRENT_STAGE="User cancelled operation"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}Are you absolutely sure? Type 'CONFIRM' to proceed:${NC}"
    read -r final_confirmation

    if [ "$final_confirmation" != "CONFIRM" ]; then
        echo -e "${RED}Genesis reset cancelled.${NC}"
        CURRENT_STAGE="User cancelled operation"
        exit 1
    fi
}

# Function to create backup (optional)
create_backup() {
    CURRENT_STAGE="Creating backup"
    print_warning "Creating backup before reset..."

    mkdir -p "$BACKUP_DIR"

    # Backup important configuration files (but not data)
    if [ -f "/etc/pisecure/config.json" ]; then
        cp "/etc/pisecure/config.json" "$BACKUP_DIR/config.json.backup" 2>/dev/null || true
        print_status "Backed up /etc/pisecure/config.json"
    fi

    if [ -f "${PROJECT_ROOT}/pisecure_env/config.json" ]; then
        cp "${PROJECT_ROOT}/pisecure_env/config.json" "$BACKUP_DIR/env_config.json.backup" 2>/dev/null || true
        print_status "Backed up pisecure_env/config.json"
    fi

    print_success "Backup created in: $BACKUP_DIR"
}

# Function to stop all PiSecure services
stop_services() {
    CURRENT_STAGE="Stopping PiSecure services"
    print_status "Stopping all PiSecure services..."

    # Stop systemd services
    systemctl stop pisecure.service 2>/dev/null || true
    systemctl stop pisecure-mining.service 2>/dev/null || true
    systemctl stop pisecure-dashboard.service 2>/dev/null || true
    systemctl stop pisecure-relay.service 2>/dev/null || true
    systemctl stop pisecure-api.service 2>/dev/null || true

    # Kill any running Python processes
    pkill -f "pisecure" 2>/dev/null || true
    pkill -f "python.*pisecure" 2>/dev/null || true

    # Wait a moment for processes to stop
    sleep 2

    print_success "All PiSecure services stopped"
}

# Function to remove blockchain data
clear_blockchain_data() {
    CURRENT_STAGE="Clearing blockchain data"
    print_status "Clearing blockchain data..."

    # Remove blockchain storage files from project directory
    rm -rf "${PROJECT_ROOT}/pisecure_env/blockchain/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/blocks/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/transactions/"* 2>/dev/null || true

    # Remove hybrid storage data from project directory
    rm -rf "${PROJECT_ROOT}/pisecure_env/hybrid_storage/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/storage/"* 2>/dev/null || true

    # Remove system blockchain data (hybrid storage location)
    rm -rf "/var/lib/pisecure/blocks/"* 2>/dev/null || true
    rm -f "/var/lib/pisecure/index.db" 2>/dev/null || true
    rm -f "/var/lib/pisecure/index.db-wal" 2>/dev/null || true
    rm -f "/var/lib/pisecure/index.db-shm" 2>/dev/null || true
    rm -f "/var/lib/pisecure/.migration_complete" 2>/dev/null || true
    rm -f "/var/lib/pisecure/blockchain.json" 2>/dev/null || true
    rm -f "/var/lib/pisecure/pending_transactions.json" 2>/dev/null || true

    # Remove blockchain database files
    find "${PROJECT_ROOT}" -name "*.blockchain" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*blockchain*.db" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*blockchain*.json" -delete 2>/dev/null || true

    # Remove chain state files
    rm -f "${PROJECT_ROOT}/pisecure_env/chain_state.json" 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/pisecure_env/blockchain_state.json" 2>/dev/null || true

    print_success "Blockchain data cleared"
}

# Function to fix data directory permissions
fix_data_permissions() {
    CURRENT_STAGE="Fixing data directory permissions"
    print_status "Fixing data directory permissions..."

    # Check current permissions
    print_status "Checking current permissions on /var/lib/pisecure"
    ls -la /var/lib/pisecure 2>/dev/null || print_warning "Directory may not exist yet"

    # Fix ownership if needed
    print_status "Setting ownership to pi:pi"
    sudo chown -R pi:pi /var/lib/pisecure 2>/dev/null || print_warning "Failed to change ownership"

    # Verify pi user can write to the directory
    print_status "Testing write permissions for pi user"
    if sudo -u pi touch /var/lib/pisecure/test_write 2>/dev/null; then
        rm /var/lib/pisecure/test_write 2>/dev/null || true
        print_success "Permissions test passed - pi user can write to /var/lib/pisecure"
    else
        print_error "Permissions test failed - pi user cannot write to /var/lib/pisecure"
        return 1
    fi

    print_success "Data directory permissions fixed"
}

# Function to remove wallet data
clear_wallet_data() {
    CURRENT_STAGE="Clearing wallet data"
    print_status "Clearing wallet data..."

    # Remove wallet directories
    rm -rf "/var/lib/pisecure/wallets/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/wallets/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/wallets/"* 2>/dev/null || true

    # Remove wallet files
    find "${PROJECT_ROOT}" -name "*.wallet" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*wallet*.json" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*wallet*.db" -delete 2>/dev/null || true

    # Remove key files (be very careful - only remove generated ones)
    rm -rf "/var/lib/pisecure/wallets/keys/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/keys/"* 2>/dev/null || true

    print_success "Wallet data cleared"
}

# Function to clear economic data
clear_economic_data() {
    CURRENT_STAGE="Clearing economic data"
    print_status "Clearing economic data..."

    # Remove trust fund data
    rm -rf "${PROJECT_ROOT}/pisecure_env/trust_funds/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/economics/"* 2>/dev/null || true

    # Remove subscription data
    rm -rf "${PROJECT_ROOT}/pisecure_env/subscriptions/"* 2>/dev/null || true

    # Remove foundation data
    rm -rf "${PROJECT_ROOT}/pisecure_env/foundation/"* 2>/dev/null || true

    # Remove market data
    rm -rf "${PROJECT_ROOT}/pisecure_env/market_data/"* 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/pisecure_env/economic_metrics.json" 2>/dev/null || true

    print_success "Economic data cleared"
}

# Function to clear P2P and network data
clear_network_data() {
    CURRENT_STAGE="Clearing P2P and network data"
    print_status "Clearing P2P and network data..."

    # Remove peer data
    rm -rf "${PROJECT_ROOT}/pisecure_env/peers/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/p2p/"* 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/peers.json" 2>/dev/null || true

    # Remove network state
    rm -f "${PROJECT_ROOT}/pisecure_env/network_state.json" 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/pisecure_env/p2p_state.json" 2>/dev/null || true

    # Clear consensus data
    rm -rf "${PROJECT_ROOT}/pisecure_env/consensus/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/mining_pools/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/syndicates/"* 2>/dev/null || true

    print_success "Network data cleared"
}

# Function to clear identity and security data
clear_identity_data() {
    CURRENT_STAGE="Clearing identity and security data"
    print_status "Clearing identity and security data..."

    # Remove device identities
    rm -f "${PROJECT_ROOT}/device_identity.json" 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/device_fingerprint.json" 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/identity/"* 2>/dev/null || true

    # Remove certificates (be careful - don't remove trusted keys)
    rm -rf "${PROJECT_ROOT}/pisecure_env/certificates/"* 2>/dev/null || true
    rm -rf "/var/lib/pisecure/certificates/"* 2>/dev/null || true

    # Remove authentication data
    rm -rf "${PROJECT_ROOT}/pisecure_env/auth/"* 2>/dev/null || true

    # Keep trusted keys directory but clear generated content
    find "${PROJECT_ROOT}/pisecure/trusted_keys/" -name "*.key" -not -name "genesis_auth_pub.key" -delete 2>/dev/null || true

    print_success "Identity data cleared"
}

# Function to clear cache and temporary data
clear_cache_data() {
    CURRENT_STAGE="Clearing cache and temporary data"
    print_status "Clearing cache and temporary data..."

    # Remove cache directories
    rm -rf "${PROJECT_ROOT}/pisecure_env/cache/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/pisecure_env/tmp/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/cache/"* 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/tmp/"* 2>/dev/null || true

    # Remove log files
    rm -f "${PROJECT_ROOT}/*.log" 2>/dev/null || true
    rm -rf "${PROJECT_ROOT}/logs/"* 2>/dev/null || true

    # Remove update cache
    rm -rf "${PROJECT_ROOT}/pisecure_env/updates/"* 2>/dev/null || true

    # Clear Python cache
    find "${PROJECT_ROOT}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*.pyc" -delete 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*.pyo" -delete 2>/dev/null || true

    print_success "Cache data cleared"
}

# Function to reset configuration
reset_configuration() {
    CURRENT_STAGE="Resetting configuration to defaults"
    print_status "Resetting configuration to defaults..."

    # Reset environment config
    cat > "${PROJECT_ROOT}/pisecure_env/config.json" << 'EOF'
{
  "network": {
    "port": 443,
    "bootstrap_nodes": ["https://pisecure-bootstrap-production.up.railway.app"],
    "max_peers": 50,
    "enable_nat_traversal": true,
    "relay_enabled": false
  },
  "mining": {
    "enabled": true,
    "wallet_address": null,
    "threads": 4,
    "max_temperature": 70
  },
  "blockchain": {
    "storage_type": "hybrid",
    "max_cache_size": 1000,
    "sync_interval": 30,
    "difficulty": 4
  },
  "security": {
    "require_hardware_verification": true,
    "enable_device_identity": true,
    "key_rotation_interval": 86400
  },
  "updates": {
    "auto_update": true,
    "update_channel": "stable",
    "backup_before_update": true
  }
}
EOF

    print_success "Configuration reset to defaults"
}

# Function to restart services
restart_services() {
    CURRENT_STAGE="Restarting PiSecure services"
    print_status "Restarting PiSecure services..."

    # Start basic services
    systemctl start pisecure.service 2>/dev/null || true
    systemctl start pisecure-api.service 2>/dev/null || true

    print_success "Services restarted"
}

# Function to verify reset
verify_reset() {
    CURRENT_STAGE="Verifying genesis reset"
    print_status "Verifying genesis reset..."

    # Check that blockchain starts from genesis
    if python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}')
try:
    from pisecure.core.blockchain import SignChain
    chain = SignChain()
    block_count = len(chain.chain)
    print(f'Blocks after reset: {block_count}')
    if chain.chain:
        print(f'Genesis block hash: {chain.chain[0].hash[:16]}...')
        print(f'Genesis block index: {chain.chain[0].index}')
    else:
        print('No blocks found!')
        exit(1)

    # Verify this is actually a genesis reset (should have exactly 1 block)
    if block_count == 1 and chain.chain[0].index == 0:
        print('Genesis reset verified successfully')
        exit(0)
    else:
        print(f'Genesis reset verification failed: {block_count} blocks, genesis index {chain.chain[0].index if chain.chain else \"None\"}')
        exit(1)
except Exception as e:
    print(f'Error during verification: {e}')
    exit(1)
" 2>/dev/null; then
        print_success "Genesis reset verification successful"
    else
        print_error "Genesis reset verification failed"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${RED}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                PiSecure Genesis Reset Script                ║"
    echo "║                      Version 1.0.0                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Confirm the dangerous operation
    confirm_reset

    echo ""
    print_warning "Beginning genesis reset process..."
    echo ""

    # Create backup (optional safety measure)
    create_backup

    # Stop all services
    stop_services

    # Clear all data in order
    clear_blockchain_data

    # Fix data directory permissions
    fix_data_permissions

    clear_wallet_data
    clear_economic_data
    clear_network_data
    clear_identity_data
    clear_cache_data

    # Reset configuration
    reset_configuration

    # Verify the reset worked
    verify_reset

    # Restart services
    restart_services

    echo ""
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   🎉 GENESIS RESET COMPLETE 🎉              ║"
    echo "║                                                              ║"
    echo "║  PiSecure has been reset to genesis state (block 0)         ║"
    echo "║                                                              ║"
    echo "║  • All blockchain data cleared                               ║"
    echo "║  • All wallets and keys removed                              ║"
    echo "║  • Economic data reset                                       ║"
    echo "║  • Network state cleared                                     ║"
    echo "║  • Identity data reset                                       ║"
    echo "║  • Configuration restored to defaults                       ║"
    echo "║                                                              ║"
    echo "║  Backup created: ${BACKUP_DIR}                               ║"
    echo "║                                                              ║"
    echo "║  Services have been restarted                                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo ""
    print_success "Genesis reset completed successfully!"
    print_warning "Remember to restore any important configuration from backup if needed"
}

# Run main function
main "$@"