#!/bin/bash
"""
PiSecure Installer - Complete Setup for Raspberry Pi Blockchain Node
====================================================================

This script installs PiSecure as a complete blockchain node with:
- Wallet creation and management
- Background mining service
- REST API server
- Web dashboard
- Automatic startup and peer discovery

NOTE: This script uses virtual environments to avoid system Python conflicts.
Genesis keys are OPTIONAL - the system works without them for normal operations.

Usage: curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/UnderhillForge/PiSecure.git"
INSTALL_DIR="/home/pi/PiSecure"
VENV_DIR="$INSTALL_DIR/pisecure_env"
DATA_DIR="/var/lib/pisecure"
CONFIG_DIR="/etc/pisecure"
SERVICE_USER="pi"
HOSTNAME_PREFIX="pisecure-node"

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

# Detect Raspberry Pi
detect_pi() {
    if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
        log_error "This script is designed for Raspberry Pi only."
        exit 1
    fi

    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    log_info "Detected: $PI_MODEL"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."

    sudo apt update
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        jq \
        avahi-daemon \
        nginx \
        ufw \
        fail2ban \
        unattended-upgrades

    log_success "System dependencies installed"
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."

    sudo mkdir -p "$DATA_DIR"
    sudo mkdir -p "$CONFIG_DIR"
    sudo mkdir -p "/var/log/pisecure"

    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "/var/log/pisecure"

    log_success "Directories created and permissions set"
}

# Clone and install PiSecure
install_pisecure() {
    log_info "Installing PiSecure..."

    # Clone repository
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        cd "$INSTALL_DIR"
        git pull origin main
    fi

    # Create virtual environment
    python3 -m venv "$VENV_DIR"

    # Activate and install dependencies
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip

    # Install PiSecure dependencies
    pip install flask flask-cors flask-limiter cryptography requests psutil

    # Install PiSecure (must be in the correct directory)
    cd "$INSTALL_DIR"
    pip install -e .

    # Verify installation
    python -c "import pisecure; print('PiSecure import successful')" || {
        log_error "PiSecure installation failed"
        exit 1
    }

    log_success "PiSecure installed successfully"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."

    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 3142/tcp  # PiSecure API
    sudo ufw allow 5000/tcp  # Dashboard
    sudo ufw --force enable

    log_success "Firewall configured"
}

# Setup hostname
setup_hostname() {
    log_info "Setting up hostname..."

    CURRENT_HOSTNAME=$(hostname)
    if [[ "$CURRENT_HOSTNAME" != *"$HOSTNAME_PREFIX"* ]]; then
        PI_SERIAL=$(grep "Serial" /proc/cpuinfo | awk '{print $3}' | tr '[:upper:]' '[:lower:]')
        NEW_HOSTNAME="${HOSTNAME_PREFIX}-${PI_SERIAL: -6}"

        sudo hostnamectl set-hostname "$NEW_HOSTNAME"
        sudo sed -i "s/127.0.1.1.*/127.0.1.1\t$NEW_HOSTNAME/" /etc/hosts

        log_success "Hostname set to: $NEW_HOSTNAME"
        log_warning "System will use new hostname after reboot"
    else
        log_info "Hostname already configured: $CURRENT_HOSTNAME"
    fi
}

# Create configuration
create_config() {
    log_info "Creating PiSecure configuration..."

    sudo tee "$CONFIG_DIR/config.json" > /dev/null <<EOF
{
    "network": {
        "listen_port": 3142,
        "max_connections": 10,
        "bootstrap_peers": []
    },
    "mining": {
        "enabled": true,
        "wallet_address": "default_wallet",
        "threads": 4,
        "difficulty_adjustment": true
    },
    "api": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 3142,
        "rate_limit": "100 per minute"
    },
    "dashboard": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 5000
    },
    "storage": {
        "blockchain_path": "/var/lib/pisecure/blockchain.json",
        "database_path": "/var/lib/pisecure/pisecure.db"
    }
}
EOF

    sudo chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/config.json"
    sudo chmod 600 "$CONFIG_DIR/config.json"

    log_success "Configuration created"
}

# Create systemd services
create_services() {
    log_info "Creating systemd services..."

    # PiSecure API server service
    sudo tee /etc/systemd/system/pisecure.service > /dev/null <<EOF
[Unit]
Description=PiSecure Blockchain API Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python -m pisecure.api.server --host 0.0.0.0 --port 3142
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-api

[Install]
WantedBy=multi-user.target
EOF

    # PiSecure mining service
    sudo tee /etc/systemd/system/pisecure-mining.service > /dev/null <<EOF
[Unit]
Description=PiSecure Blockchain Mining Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python -m pisecure.cli mine --background
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-mining

[Install]
WantedBy=multi-user.target
EOF

    # PiSecure dashboard service
    sudo tee /etc/systemd/system/pisecure-dashboard.service > /dev/null <<EOF
[Unit]
Description=PiSecure Web Dashboard
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python dashboard/web/minimal_dashboard.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-dashboard

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    log_success "Systemd services created"
}

# Setup nginx reverse proxy
setup_nginx() {
    log_info "Setting up nginx reverse proxy..."

    sudo tee /etc/nginx/sites-available/pisecure > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # PiSecure Dashboard
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:3142/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/pisecure /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx

    log_success "Nginx configured"
}

# Setup automatic node discovery
setup_node_discovery() {
    log_info "Setting up automatic node discovery..."

    # Install NAT traversal dependencies
    sudo apt install -y miniupnpc

    # Run node discovery setup
    source "$VENV_DIR/bin/activate"

    # Test and setup node discovery
    python -c "
from pisecure.core.nat_traversal import node_discovery
import json

print('🔍 Setting up automatic node discovery...')
results = node_discovery.make_node_discoverable()

# Save discovery results
discovery_file = '/etc/pisecure/node_discovery.json'
with open(discovery_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f'✅ Node discovery configured: {results[\"success_count\"]} methods successful')
print(f'📄 Discovery results saved to: {discovery_file}')
"

    log_success "Automatic node discovery configured"
}

# Automated wallet setup
setup_wallet() {
    log_info "Creating default mining wallet..."

    # Generate unique wallet name based on system identifier
    PI_SERIAL=$(grep "Serial" /proc/cpuinfo | awk '{print $3}' | tr '[:upper:]' '[:lower:]')
    WALLET_NAME="node-${PI_SERIAL: -6}"
    WALLET_DISPLAY_NAME="PiSecure Node Wallet"

    log_info "Creating wallet: $WALLET_NAME"

    # Create wallet
    source "$VENV_DIR/bin/activate"
    WALLET_RESULT=$(python -c "
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
result = wallet.create_wallet('$WALLET_NAME', '$WALLET_DISPLAY_NAME')
if result['success']:
    print('SUCCESS:' + result['address'])
else:
    print('FAILED:' + result.get('error', 'Unknown error'))
" 2>/dev/null)

    if [[ $WALLET_RESULT == SUCCESS:* ]]; then
        WALLET_ADDRESS=$(echo "$WALLET_RESULT" | cut -d: -f2)
        log_success "Wallet created: $WALLET_NAME ($WALLET_ADDRESS)"

        # Update config with wallet address
        sudo jq --arg wallet "$WALLET_ADDRESS" '.mining.wallet_address = $wallet' "$CONFIG_DIR/config.json" > /tmp/config.json
        sudo mv /tmp/config.json "$CONFIG_DIR/config.json"
    else
        ERROR_MSG=$(echo "$WALLET_RESULT" | cut -d: -f2)
        log_error "Wallet creation failed: $ERROR_MSG"
        exit 1
    fi

    log_success "Wallet setup complete"
}

# Start services
start_services() {
    log_info "Starting PiSecure services..."

    sudo systemctl enable pisecure.service
    sudo systemctl enable pisecure-mining.service
    sudo systemctl enable pisecure-dashboard.service

    sudo systemctl start pisecure.service
    sudo systemctl start pisecure-mining.service
    sudo systemctl start pisecure-dashboard.service

    # Wait a moment for services to start
    sleep 3

    log_success "Services started"
}

# Print completion message
completion_message() {
    HOSTNAME=$(hostname)

    echo
    echo "========================================"
    echo "    🎉 PiSecure Installation Complete!"
    echo "========================================"
    echo
    echo "Your PiSecure node is now running!"
    echo
    echo "🌐 Web Dashboard: http://$HOSTNAME.local"
    echo "    or: http://$(hostname -I | awk '{print $1}')"
    echo
    echo "🔗 API Server: http://$HOSTNAME.local/api/v1/health"
    echo "    or: http://$(hostname -I | awk '{print $1}'):3142/api/v1/health"
    echo
    echo "📋 Useful commands:"
    echo "  Check status:  sudo systemctl status pisecure*"
    echo "  View logs:     sudo journalctl -u pisecure* -f"
    echo "  Stop mining:   sudo systemctl stop pisecure-mining"
    echo "  Restart API:   sudo systemctl restart pisecure"
    echo
    echo "🔑 Foundation Operations (Genesis Keys Required):"
    echo "  The API server works without genesis keys!"
    echo "  Foundation endpoints return 'not available' until keys are added"
    echo
    echo "📚 Documentation: https://github.com/UnderhillForge/PiSecure"
    echo
    log_success "Installation completed successfully!"
}

# Main installation process
main() {
    echo "========================================"
    echo "    🔐 PiSecure Node Installer"
    echo "========================================"
    echo
    log_info "Starting PiSecure installation..."
    log_warning "Genesis keys are OPTIONAL - system works without them!"

    detect_pi
    install_dependencies
    setup_directories
    install_pisecure
    configure_firewall
    setup_hostname
    create_config
    create_services
    setup_nginx
    setup_node_discovery
    setup_wallet
    start_services

    completion_message
}

# Run main function
main "$@"