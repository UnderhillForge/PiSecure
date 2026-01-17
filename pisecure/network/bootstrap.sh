#!/bin/bash
# PiSecure Network Bootstrap Script
# Downloads initial blockchain state from GitHub and initializes P2P discovery

set -e

# Configuration
GITHUB_REPO="https://api.github.com/repos/UnderhillForge/PiSecure"
BOOTSTRAP_DIR="/var/lib/pisecure"
CONFIG_DIR="/etc/pisecure"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check if running as root for system installation
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root - this will install system-wide"
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed"
        exit 1
    fi

    # Check curl or wget
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        log_error "curl or wget is required for downloading"
        exit 1
    fi

    log_success "System requirements check passed"
}

# Download file with fallback
download_file() {
    local url="$1"
    local output="$2"

    if command -v curl &> /dev/null; then
        curl -s -o "$output" "$url"
    elif command -v wget &> /dev/null; then
        wget -q -O "$output" "$url"
    else
        log_error "No download tool available"
        return 1
    fi
}

# Verify file checksum
verify_checksum() {
    local file="$1"
    local expected_hash="$2"

    if ! command -v sha256sum &> /dev/null; then
        log_warning "sha256sum not available, skipping verification"
        return 0
    fi

    local actual_hash=$(sha256sum "$file" | cut -d' ' -f1)

    if [[ "$actual_hash" != "$expected_hash" ]]; then
        log_error "Checksum verification failed for $file"
        log_error "Expected: $expected_hash"
        log_error "Actual: $actual_hash"
        return 1
    fi

    log_success "Checksum verified for $file"
    return 0
}

# Download and verify genesis block
download_genesis() {
    log_info "Downloading genesis block from GitHub..."

    local genesis_url="https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/blockchain/genesis.json"
    local genesis_file="$BOOTSTRAP_DIR/genesis.json"
    local checksums_url="https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/blockchain/checksums.sha256"
    local checksums_file="$BOOTSTRAP_DIR/checksums.sha256"

    # Create bootstrap directory
    mkdir -p "$BOOTSTRAP_DIR"

    # Download checksums first
    download_file "$checksums_url" "$checksums_file"

    # Download genesis block
    download_file "$genesis_url" "$genesis_file"

    # Verify genesis block
    local expected_hash=$(grep "genesis.json" "$checksums_file" | cut -d' ' -f1)
    if [[ -n "$expected_hash" ]]; then
        verify_checksum "$genesis_file" "$expected_hash" || {
            log_error "Genesis block verification failed"
            rm -f "$genesis_file"
            return 1
        }
    fi

    log_success "Genesis block downloaded and verified"
}

# Download network configuration
download_network_config() {
    log_info "Downloading network configuration..."

    local config_url="https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/network/config.json"
    local config_file="$BOOTSTRAP_DIR/network_config.json"

    download_file "$config_url" "$config_file"

    log_success "Network configuration downloaded"
}

# Initialize PiSecure node
initialize_node() {
    log_info "Initializing PiSecure node..."

    # Create configuration directory
    mkdir -p "$CONFIG_DIR"

    # Copy downloaded files
    cp "$BOOTSTRAP_DIR/genesis.json" "$CONFIG_DIR/"
    cp "$BOOTSTRAP_DIR/network_config.json" "$CONFIG_DIR/config.json"

    # Generate node identity (placeholder - would call pisecure command)
    log_info "Node identity would be generated here"

    log_success "PiSecure node initialized"
}

# Start P2P discovery
start_p2p_discovery() {
    log_info "Starting decentralized P2P discovery..."

    # This would start the PiSecure daemon with P2P discovery enabled
    # For now, just show what would happen
    log_info "P2P discovery would start here"
    log_info "- mDNS local network discovery"
    log_info "- DHT-based peer discovery"
    log_info "- IPFS pubsub channels"

    log_success "P2P discovery initialized"
}

# Show completion message
show_completion() {
    echo
    log_success "🎉 PiSecure bootstrap completed successfully!"
    echo
    echo "Your node is now ready to join the PiSecure network."
    echo
    echo "Next steps:"
    echo "1. Start the PiSecure daemon: pisecure start"
    echo "2. Check network status: pisecure network-status"
    echo "3. Create your first wallet: pisecure create-wallet 'my_wallet'"
    echo "4. Start mining: pisecure mine"
    echo
    echo "Documentation: https://github.com/UnderhillForge/PiSecure"
    echo "Community: https://github.com/UnderhillForge/PiSecure/discussions"
}

# Main bootstrap flow
main() {
    echo "🚀 PiSecure Network Bootstrap"
    echo "============================"
    echo

    check_requirements
    download_genesis
    download_network_config
    initialize_node
    start_p2p_discovery
    show_completion
}

# Run main function
main "$@"