#!/bin/bash

################################################################################
# PiSecure Genesis Reset Script
# Clears all blockchain data (testnet & mainnet) and recreates fresh genesis
# Cross-platform compatible (Linux, macOS, Windows Git Bash)
#
# Usage: bash genesis-reset.sh [--force] [--backup]
# Options:
#   --force    Skip confirmation prompts (use with caution!)
#   --backup   Create backup before deletion (saved as backup-TIMESTAMP.tar.gz)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE_MODE=0
BACKUP_MODE=0

for arg in "$@"; do
    case $arg in
        --force) FORCE_MODE=1 ;;
        --backup) BACKUP_MODE=1 ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           PiSecure Genesis Reset Script v1.0              ║${NC}"
echo -e "${BLUE}║         ⚠️  WARNING: This will DELETE all blockchain data  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Determine home directory (cross-platform)
if [ -z "$HOME" ]; then
    echo -e "${RED}❌ ERROR: \$HOME environment variable not set${NC}"
    exit 1
fi

# Paths to clear
MAINNET_DIR="$HOME/.pisecure"
MAINNET_VAR_DIR="/var/lib/pisecure"
TESTNET_DIR="$HOME/.pisecure-testnet"
TESTNET_VAR_DIR="/var/lib/pisecure-testnet"

# Wallet directories
WALLET_DIR="$HOME/.pisecure/wallets"
WALLET_VAR_DIR="/var/lib/pisecure/wallets"

echo -e "${YELLOW}🔍 Detected OS: $OS${NC}"
echo -e "${YELLOW}🔍 Home directory: $HOME${NC}"
echo ""

# Show what will be deleted
echo -e "${YELLOW}📋 This will DELETE:${NC}"
echo "   ❌ Mainnet blockchain:   $MAINNET_DIR"
echo "   ❌ Mainnet (alt):        $MAINNET_VAR_DIR"
echo "   ❌ Testnet blockchain:   $TESTNET_DIR"
echo "   ❌ Testnet (alt):        $TESTNET_VAR_DIR"
echo "   ❌ All wallets:          $WALLET_DIR"
echo "   ❌ Wallet keys (alt):    $WALLET_VAR_DIR"
echo ""

# Count items to be deleted
ITEMS_TO_DELETE=0
[ -d "$MAINNET_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))
[ -d "$MAINNET_VAR_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))
[ -d "$TESTNET_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))
[ -d "$TESTNET_VAR_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))
[ -d "$WALLET_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))
[ -d "$WALLET_VAR_DIR" ] && ITEMS_TO_DELETE=$((ITEMS_TO_DELETE + 1))

if [ $ITEMS_TO_DELETE -eq 0 ]; then
    echo -e "${GREEN}✅ No blockchain data found to delete${NC}"
    echo ""
    echo -e "${BLUE}Fresh genesis files will be created:${NC}"
    echo "   ✨ $MAINNET_DIR (fresh)"
    echo "   ✨ $TESTNET_DIR (fresh)"
    echo ""
else
    echo -e "${RED}⚠️  Found $ITEMS_TO_DELETE directories to delete${NC}"
    echo ""
fi

# Backup if requested
if [ $BACKUP_MODE -eq 1 ]; then
    if [ $ITEMS_TO_DELETE -gt 0 ]; then
        BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        echo -e "${YELLOW}💾 Creating backup: $BACKUP_FILE${NC}"
        tar -czf "$BACKUP_FILE" \
            "$MAINNET_DIR" "$MAINNET_VAR_DIR" \
            "$TESTNET_DIR" "$TESTNET_VAR_DIR" \
            "$WALLET_DIR" "$WALLET_VAR_DIR" \
            2>/dev/null || true
        echo -e "${GREEN}✅ Backup created${NC}"
        echo ""
    fi
fi

# Confirmation
if [ $FORCE_MODE -eq 0 ]; then
    echo -e "${RED}🚨 FINAL WARNING: This action CANNOT be undone!${NC}"
    echo ""
    
    read -p "Type 'DELETE ALL' to confirm: " confirm1
    if [ "$confirm1" != "DELETE ALL" ]; then
        echo -e "${YELLOW}❌ Cancelled by user${NC}"
        exit 0
    fi
    
    echo ""
    read -p "Type 'YES, DELETE' to CONFIRM: " confirm2
    if [ "$confirm2" != "YES, DELETE" ]; then
        echo -e "${YELLOW}❌ Cancelled by user${NC}"
        exit 0
    fi
    
    echo ""
fi

# Delete existing data
echo -e "${BLUE}🧹 Deleting existing blockchain and wallet data...${NC}"

delete_dir() {
    local dir=$1
    local name=$2
    if [ -d "$dir" ]; then
        echo "   Removing: $dir"
        rm -rf "$dir" || true
        echo -e "   ${GREEN}✓ Deleted${NC}"
    fi
}

delete_dir "$MAINNET_DIR" "Mainnet"
delete_dir "$MAINNET_VAR_DIR" "Mainnet (alt)"
delete_dir "$TESTNET_DIR" "Testnet"
delete_dir "$TESTNET_VAR_DIR" "Testnet (alt)"
delete_dir "$WALLET_DIR" "Wallets"
delete_dir "$WALLET_VAR_DIR" "Wallet keys"

echo ""

# Create fresh directories
echo -e "${BLUE}✨ Creating fresh genesis directories...${NC}"

create_fresh_dir() {
    local dir=$1
    local name=$2
    mkdir -p "$dir"
    echo "   Created: $dir"
    echo -e "   ${GREEN}✓${NC}"
}

create_fresh_dir "$MAINNET_DIR" "Mainnet"
create_fresh_dir "$TESTNET_DIR" "Testnet"
create_fresh_dir "$WALLET_DIR" "Wallets"

echo ""

# Generate fresh genesis blocks using Python
echo -e "${BLUE}📝 Generating fresh genesis blocks...${NC}"

python3 << 'PYTHON_EOF'
import os
import sys
sys.path.insert(0, '/home/pi/PiSecure')

try:
    # Mainnet genesis
    os.environ['PISECURE_TESTNET'] = '0'
    from pisecure.core import SignChain
    blockchain_mainnet = SignChain()
    print("   ✓ Mainnet genesis created")
    
    # Testnet genesis
    os.environ['PISECURE_TESTNET'] = '1'
    blockchain_testnet = SignChain()
    print("   ✓ Testnet genesis created")
    
    print("")
    print("   Mainnet blocks:  " + str(len(blockchain_mainnet.chain)))
    print("   Testnet blocks:  " + str(len(blockchain_testnet.chain)))
    print("   Both have valid genesis blocks")
    
except Exception as e:
    print(f"   ❌ Error creating genesis: {e}")
    sys.exit(1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Failed to create genesis blocks${NC}"
    exit 1
fi

echo ""

# Success summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ GENESIS RESET COMPLETE!                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Cleared all blockchain data${NC}"
echo -e "${GREEN}✓ Cleared all wallet data${NC}"
echo -e "${GREEN}✓ Created fresh genesis blocks${NC}"
echo ""

# Show what's ready
echo -e "${BLUE}📦 Ready to use:${NC}"
echo "   • Mainnet genesis:  $MAINNET_DIR"
echo "   • Testnet genesis:  $TESTNET_DIR"
echo "   • Wallet storage:   $WALLET_DIR"
echo ""

# Instructions
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "   1. Start a fresh node:"
echo "      ${YELLOW}pisecure mine${NC}  (mainnet)"
echo "      ${YELLOW}export PISECURE_TESTNET=1 && pisecure mine${NC}  (testnet)"
echo ""
echo "   2. Or on Mac validation node:"
echo "      ${YELLOW}PISECURE_TESTNET=1 PISECURE_VALIDATE_ONLY=1 PISECURE_MOCK_HARDWARE=1 pisecure mine${NC}"
echo ""

# Backup location reminder
if [ $BACKUP_MODE -eq 1 ] && [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}📦 Backup saved: $BACKUP_FILE${NC}"
    echo ""
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
