#!/bin/bash
# PiSecure Dashboard Installation Script for Raspberry Pi Zero 2 W
# Optimized for limited hardware (512MB RAM, 1GHz CPU)

set -e

# Configuration
PISECURE_DIR="/opt/pisecure"
DASHBOARD_DIR="$PISECURE_DIR/dashboard"
VENV_DIR="$PISECURE_DIR/venv"
CONFIG_DIR="/etc/pisecure"
DATA_DIR="/var/lib/pisecure"
LOG_DIR="/var/log/pisecure"
USER="pi"
GROUP="pi"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_DIR/install.log" 2>/dev/null || true
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" >> "$LOG_DIR/install.log" 2>/dev/null || true
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1" >> "$LOG_DIR/install.log" 2>/dev/null || true
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_DIR/install.log" 2>/dev/null || true
}

# Check if running on Raspberry Pi
check_hardware() {
    log_info "Checking hardware compatibility..."

    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        log_error "This script is designed for Raspberry Pi systems"
        exit 1
    fi

    # Check RAM (should be at least 512MB)
    total_ram=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
    if [ "$total_ram" -lt 400 ]; then
        log_warning "Low memory detected: ${total_ram}MB. Performance may be limited."
    fi

    log_success "Hardware check passed"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check OS version
    if ! grep -q "Raspberry Pi OS" /etc/os-release 2>/dev/null; then
        log_warning "Not running Raspberry Pi OS - some features may not work"
    fi

    # Check Python 3.7+
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required"
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)"; then
        log_success "Python $python_version detected"
    else
        log_error "Python 3.7 or higher is required"
        exit 1
    fi

    # Check internet connectivity
    if ! ping -c 1 -W 5 8.8.8.8 &> /dev/null; then
        log_error "Internet connectivity is required"
        exit 1
    fi

    log_success "System requirements check passed"
}

# Create directories
create_directories() {
    log_info "Creating directories..."

    # Create main directories
    sudo mkdir -p "$PISECURE_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

    # Set ownership
    sudo chown -R "$USER:$GROUP" "$PISECURE_DIR" "$DATA_DIR" "$LOG_DIR"
    sudo chown "$USER:$GROUP" "$CONFIG_DIR"

    # Create subdirectories
    mkdir -p "$DASHBOARD_DIR"/{web/{static/{css,js,img},templates,api},scripts,docs}
    mkdir -p "$DATA_DIR"/{wallets,peers,backups}
    mkdir -p "$LOG_DIR"/{dashboard,blockchain,mining}

    log_success "Directories created"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."

    # Update package list
    sudo apt-get update

    # Install Python and development tools
    sudo apt-get install -y python3-dev python3-pip python3-venv

    # Install web server dependencies
    sudo apt-get install -y nginx

    # Install monitoring dependencies
    sudo apt-get install -y lm-sensors

    # Install security-related packages
    sudo apt-get install -y haveged rng-tools

    # Clean up
    sudo apt-get autoremove -y
    sudo apt-get clean

    log_success "System dependencies installed"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."

    # Create virtual environment
    python3 -m venv "$VENV_DIR"

    # Activate and upgrade pip
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel

    log_success "Virtual environment created"
}

# Install PiSecure and dashboard
install_pisecure() {
    log_info "Installing PiSecure and dashboard..."

    source "$VENV_DIR/bin/activate"

    # Install PiSecure from source (assumes we're running from PiSecure directory)
    if [ -f "setup.py" ]; then
        pip install -e .
        log_success "PiSecure installed from source"
    else
        # Install from GitHub
        pip install git+https://github.com/UnderhillForge/PiSecure.git
        log_success "PiSecure installed from GitHub"
    fi

    # Install dashboard dependencies
    pip install flask flask-socketio python-socketio psutil requests aiohttp

    # Optional: Install Chart.js and other frontend dependencies
    # These are loaded from CDN in the template

    log_success "PiSecure and dashboard dependencies installed"
}

# Configure system
configure_system() {
    log_info "Configuring system..."

    # Create PiSecure configuration
    cat > "$CONFIG_DIR/config.json" << EOF
{
  "network": {
    "name": "PiSecure Mainnet",
    "version": "0.1.0",
    "default_port": 3141
  },
  "dashboard": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "mining": {
    "hardware_verification_required": true,
    "thermal_limits": {
      "max_temperature": 70,
      "throttle_threshold": 65
    }
  },
  "system": {
    "data_dir": "$DATA_DIR",
    "log_dir": "$LOG_DIR",
    "user": "$USER"
  }
}
EOF

    # Configure log rotation
    sudo tee /etc/logrotate.d/pisecure > /dev/null << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 0644 $USER $GROUP
    postrotate
        systemctl reload pisecure-dashboard.service || true
    endscript
}
EOF

    log_success "System configuration completed"
}

# Setup systemd services
setup_services() {
    log_info "Setting up systemd services..."

    # PiSecure Dashboard service
    sudo tee /etc/systemd/system/pisecure-dashboard.service > /dev/null << EOF
[Unit]
Description=PiSecure Dashboard Web Interface
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$DASHBOARD_DIR/web
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-dashboard

# Memory and CPU limits for Pi Zero
MemoryLimit=256M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

    # PiSecure Mining service (optional)
    sudo tee /etc/systemd/system/pisecure-mining.service > /dev/null << EOF
[Unit]
Description=PiSecure Mining Service
After=network.target pisecure-dashboard.service
Wants=pisecure-dashboard.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$PISECURE_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/pisecure mine --background
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-mining

# Resource limits
MemoryLimit=128M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable services
    sudo systemctl daemon-reload
    sudo systemctl enable pisecure-dashboard.service

    log_success "Systemd services configured"
}

# Setup web server (Nginx)
setup_web_server() {
    log_info "Setting up Nginx reverse proxy..."

    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/pisecure > /dev/null << EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Proxy to dashboard
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeout settings for Pi Zero
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Static files with caching
    location /static/ {
        alias $DASHBOARD_DIR/web/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Enable site and disable default
    sudo ln -sf /etc/nginx/sites-available/pisecure /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default

    # Test configuration
    if sudo nginx -t; then
        sudo systemctl reload nginx
        log_success "Nginx configured and reloaded"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

# Setup auto-updates (GitHub webhooks)
setup_auto_updates() {
    log_info "Setting up auto-update system..."

    # Install webhook dependencies
    source "$VENV_DIR/bin/activate"
    pip install flask gunicorn

    # Create webhook handler
    cat > "$DASHBOARD_DIR/web/webhook.py" << 'EOF'
#!/usr/bin/env python3
"""
GitHub Webhook Handler for Auto-Updates
"""

import hmac
import hashlib
import subprocess
import sys
from flask import Flask, request, jsonify

app = Flask(__name__)

# GitHub webhook secret (should be set securely)
WEBHOOK_SECRET = "your-webhook-secret-here"  # TODO: Set this securely

@app.route('/webhook/github', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook for auto-updates"""

    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return jsonify({'error': 'No signature'}), 400

    # Get payload
    payload = request.get_data()
    expected_signature = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({'error': 'Invalid signature'}), 403

    # Process webhook
    data = request.get_json()

    if data.get('action') == 'push' and data.get('ref') == 'refs/heads/main':
        # Trigger update
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pisecure.update',
                '--auto', '--restart-services'
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return jsonify({'status': 'update_started', 'output': result.stdout})
            else:
                return jsonify({'error': 'update_failed', 'output': result.stderr}), 500

        except subprocess.TimeoutExpired:
            return jsonify({'error': 'update_timeout'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'ignored'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
EOF

    # Make executable
    chmod +x "$DASHBOARD_DIR/web/webhook.py"

    # Create systemd service for webhook
    sudo tee /etc/systemd/system/pisecure-webhook.service > /dev/null << EOF
[Unit]
Description=PiSecure GitHub Webhook Handler
After=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$DASHBOARD_DIR/web
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/python webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    log_success "Auto-update system configured"
}

# Optimize for Pi Zero 2 W
optimize_for_pi_zero() {
    log_info "Applying Pi Zero 2 W optimizations..."

    # Disable unnecessary services
    sudo systemctl disable bluetooth.service 2>/dev/null || true
    sudo systemctl disable hciuart.service 2>/dev/null || true

    # Configure memory management
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
    echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.conf

    # Configure CPU governor for performance
    echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

    # Setup log rotation for small storage
    sudo sed -i 's/rotate 4/rotate 2/' /etc/logrotate.conf
    sudo sed -i 's/weekly/daily/' /etc/logrotate.conf

    log_success "Pi Zero optimizations applied"
}

# Final setup and startup
final_setup() {
    log_info "Performing final setup..."

    # Copy dashboard files (if running from source)
    if [ -d "dashboard" ]; then
        cp -r dashboard/* "$DASHBOARD_DIR/"
    fi

    # Set proper permissions
    find "$DASHBOARD_DIR" -type f -name "*.py" -exec chmod +x {} \;
    find "$DASHBOARD_DIR" -type f -name "*.sh" -exec chmod +x {} \;

    # Create initial data directories
    mkdir -p "$DATA_DIR"/{blockchain,wallets,peers,backups}

    # Generate self-signed certificate for HTTPS (optional)
    if command -v openssl &> /dev/null; then
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/ssl/private/pisecure.key \
            -out /etc/ssl/certs/pisecure.crt \
            -subj "/C=US/ST=State/L=City/O=PiSecure/CN=localhost"
    fi

    log_success "Final setup completed"
}

# Show completion message
show_completion() {
    echo
    log_success "🎉 PiSecure Dashboard Installation Complete!"
    echo
    echo "Dashboard will be available at:"
    echo "  Local:   http://localhost"
    echo "  Network: http://$(hostname -I | awk '{print $1}')"
    echo
    echo "Services:"
    echo "  Dashboard: sudo systemctl status pisecure-dashboard"
    echo "  Mining:    sudo systemctl status pisecure-mining (optional)"
    echo "  Webhook:   sudo systemctl status pisecure-webhook (optional)"
    echo
    echo "Management:"
    echo "  Start:    sudo systemctl start pisecure-dashboard"
    echo "  Stop:     sudo systemctl stop pisecure-dashboard"
    echo "  Logs:     journalctl -u pisecure-dashboard -f"
    echo
    echo "Configuration: $CONFIG_DIR/config.json"
    echo "Data:          $DATA_DIR"
    echo "Logs:          $LOG_DIR"
    echo
    log_success "Installation completed successfully!"
}

# Main installation flow
main() {
    echo "🚀 PiSecure Dashboard Installation for Raspberry Pi Zero 2 W"
    echo "=============================================================="
    echo

    # Run installation steps
    check_hardware
    check_requirements
    create_directories
    install_system_deps
    setup_venv
    install_pisecure
    configure_system
    setup_services
    setup_web_server
    setup_auto_updates
    optimize_for_pi_zero
    final_setup

    show_completion
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    log_error "This script should not be run as root. It will use sudo when needed."
    exit 1
fi

# Run main installation
main "$@"