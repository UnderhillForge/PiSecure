#!/bin/bash
"""
PiSecure Installer - Complete Setup for Raspberry Pi Blockchain Node
====================================================================

This script installs PiSecure as a complete blockchain node with:
- Wallet creation and management
- Background mining service
- Web dashboard
- Automatic startup and peer discovery

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
INSTALL_DIR="/opt/pisecure"
DATA_DIR="/var/lib/pisecure"
CONFIG_DIR="/etc/pisecure"
SERVICE_USER="pisecure"
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. It will create a service user."
        exit 1
    fi
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

# Create service user
create_service_user() {
    log_info "Creating PiSecure service user..."

    if ! id "$SERVICE_USER" &>/dev/null; then
        sudo useradd -r -s /bin/false -m -d "$INSTALL_DIR" "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_warning "User $SERVICE_USER already exists"
    fi
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."

    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$DATA_DIR"
    sudo mkdir -p "$CONFIG_DIR"
    sudo mkdir -p "/var/log/pisecure"

    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "/var/log/pisecure"

    log_success "Directories created and permissions set"
}

# Clone and install PiSecure
install_pisecure() {
    log_info "Installing PiSecure..."

    # Clone repository
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$INSTALL_DIR"
    else
        cd "$INSTALL_DIR"
        sudo -u "$SERVICE_USER" git pull
    fi

    # Create virtual environment
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/venv"

    # Install PiSecure
    sudo -u "$SERVICE_USER" bash -c "source $INSTALL_DIR/venv/bin/activate && cd $INSTALL_DIR && pip install -e ."

    log_success "PiSecure installed"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."

    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 5000/tcp  # Dashboard
    sudo ufw allow 3141/tcp  # PiSecure P2P (placeholder)
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
        "listen_port": 3141,
        "max_connections": 10,
        "bootstrap_peers": [
            "https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/peers.json"
        ]
    },
    "mining": {
        "enabled": true,
        "max_temperature": 70,
        "thermal_throttle": true,
        "daily_limit_hours": 24
    },
    "dashboard": {
        "enabled": true,
        "port": 5000,
        "host": "0.0.0.0"
    },
    "security": {
        "auto_updates": true,
        "certificate_lifetime_days": 365,
        "key_size": 2048
    },
    "data_dir": "$DATA_DIR",
    "log_level": "INFO"
}
EOF

    sudo chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/config.json"
    sudo chmod 600 "$CONFIG_DIR/config.json"

    log_success "Configuration created"
}

# Create systemd services
create_services() {
    log_info "Creating systemd services..."

    # PiSecure mining service
    sudo tee /etc/systemd/system/pisecure-mining.service > /dev/null <<EOF
[Unit]
Description=PiSecure Blockchain Mining Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python -m pisecure.cli mine --background
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
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python dashboard/web/minimal_dashboard.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-dashboard

[Install]
WantedBy=multi-user.target
EOF

    # PiSecure main service
    sudo tee /etc/systemd/system/pisecure.service > /dev/null <<EOF
[Unit]
Description=PiSecure Blockchain Node
After=network.target pisecure-mining.service pisecure-dashboard.service
Wants=network.target
Requires=pisecure-mining.service pisecure-dashboard.service

[Service]
Type=oneshot
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python -c "print('PiSecure node started')"
RemainAfterExit=yes

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
        proxy_pass http://localhost:5000/api/;
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

# Automated wallet setup
setup_wallet() {
    log_info "Creating default mining wallet..."

    # Generate unique wallet name based on system identifier
    if [[ -f /proc/cpuinfo ]] && grep -q "Serial" /proc/cpuinfo; then
        # Raspberry Pi - use CPU serial
        SYSTEM_ID=$(grep "Serial" /proc/cpuinfo | awk '{print $3}' | tr '[:upper:]' '[:lower:]')
        WALLET_NAME="node-${SYSTEM_ID: -6}"
        WALLET_DISPLAY_NAME="PiSecure Node Wallet"
    else
        # Non-Pi system - use hostname or random identifier
        HOSTNAME_PART=$(hostname | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g' | cut -c1-6)
        if [[ -z "$HOSTNAME_PART" ]]; then
            # Fallback to random if hostname is empty
            RANDOM_ID=$(od -An -N3 -tu1 /dev/urandom | tr -d ' ')
            HOSTNAME_PART=$(printf "%06d" $((RANDOM_ID % 1000000)))
        fi
        WALLET_NAME="host-${HOSTNAME_PART}"
        WALLET_DISPLAY_NAME="PiSecure Host Wallet"
    fi

    log_info "Creating wallet: $WALLET_NAME (based on system identifier)"

    # Create wallet as service user
    WALLET_RESULT=$(sudo -u "$SERVICE_USER" bash -c "
        source $INSTALL_DIR/venv/bin/activate
        cd $INSTALL_DIR
        python -c \"
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
result = wallet.create_wallet('$WALLET_NAME', '$WALLET_DISPLAY_NAME')
if result['success']:
    print(f'SUCCESS:{result[\"address\"]}')
else:
    print(f'FAILED:{result.get(\"error\", \"Unknown error\")}')
\"
    ")

    if [[ $WALLET_RESULT == SUCCESS:* ]]; then
        WALLET_ADDRESS=$(echo "$WALLET_RESULT" | cut -d: -f2)
        log_success "Wallet created: $WALLET_NAME ($WALLET_ADDRESS)"

        # Save wallet name to config
        sudo jq --arg wallet "$WALLET_NAME" '.mining.wallet = $wallet' "$CONFIG_DIR/config.json" > /tmp/config.json
        sudo mv /tmp/config.json "$CONFIG_DIR/config.json"
    else
        ERROR_MSG=$(echo "$WALLET_RESULT" | cut -d: -f2)
        log_error "Wallet creation failed: $ERROR_MSG"
        exit 1
    fi

    log_success "Wallet setup complete"
}

# Install system-wide command
install_command() {
    log_info "Installing system-wide pisecure command..."

    # Copy pisecure.sh to /usr/local/bin/pisecure
    sudo cp "$INSTALL_DIR/pisecure.sh" /usr/local/bin/pisecure
    sudo chmod +x /usr/local/bin/pisecure

    # Test the command
    if command -v pisecure &> /dev/null; then
        log_success "System-wide command installed: pisecure"
    else
        log_warning "System-wide command installation may require logout/login"
    fi
}

# Start services
start_services() {
    log_info "Starting PiSecure services..."

    sudo systemctl enable pisecure
    sudo systemctl enable pisecure-mining
    sudo systemctl enable pisecure-dashboard

    sudo systemctl start pisecure-mining
    sudo systemctl start pisecure-dashboard
    sudo systemctl start pisecure

    log_success "Services started"
}

# Setup automatic updates
setup_updates() {
    log_info "Setting up automatic updates..."

    sudo tee /etc/cron.daily/pisecure-updates > /dev/null <<EOF
#!/bin/bash
# PiSecure automatic updates
sudo -u $SERVICE_USER bash -c "
    source $INSTALL_DIR/venv/bin/activate
    cd $INSTALL_DIR
    python -c \"
from pisecure.updates import OTAUpdater
updater = OTAUpdater()
updates = updater.check_for_updates()
if updates:
    print(f'Found {len(updates)} updates, installing latest...')
    # Auto-apply latest update
    updater.download_update(updates[0])
    updater.apply_update(updates[0]['local_path'], updates[0])
else:
    print('No updates available')
\"
"
EOF

    sudo chmod +x /etc/cron.daily/pisecure-updates
    log_success "Automatic updates configured"
}

# Print completion message
completion_message() {
    HOSTNAME=$(hostname)
    WALLET_INFO=$(sudo -u "$SERVICE_USER" bash -c "
        source $INSTALL_DIR/venv/bin/activate
        cd $INSTALL_DIR
        python -c \"
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
wallets = wallet.list_wallets()
if wallets:
    w = wallets[0]
    print(f'{w[\"name\"]} ({w[\"address\"][:16]}...)')
else:
    print('No wallet found')
\"
    ")

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
    echo "👛 Wallet: $WALLET_INFO"
    echo
    echo "📋 Useful commands:"
    echo "  Check status:  python -m pisecure.cli status"
    echo "  View wallet:   python -m pisecure.cli wallet"
    echo "  Start mining:  python -m pisecure.cli mine"
    echo "  Transfer:      python -m pisecure.cli transfer-tokens <address> <amount> --from-wallet <wallet>"
    echo
    echo "🔄 Services:"
    echo "  Mining:     sudo systemctl status pisecure-mining"
    echo "  Dashboard:  sudo systemctl status pisecure-dashboard"
    echo
    echo "📚 Documentation: https://github.com/UnderhillForge/PiSecure"
    echo
    echo "⚠️  IMPORTANT: Backup your wallet data from $DATA_DIR/wallets/"
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

    check_root
    detect_pi
    install_dependencies
    create_service_user
    setup_directories
    install_pisecure
    configure_firewall
    setup_hostname
    create_config
    create_services
    setup_nginx
    setup_wallet
    install_command
    start_services
    setup_updates

    completion_message
}

# Run main function
main "$@"