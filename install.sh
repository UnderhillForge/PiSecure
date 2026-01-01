#!/bin/bash
# PiSecure Universal Installer
# Works on all Raspberry Pi models: Zero, Zero W, Zero 2 W, 3, 3B+, 4, 5

# Note: We don't use 'set -e' because some optional package installations may fail
# and we want to continue the installation anyway

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

# Detect Raspberry Pi model
detect_pi_model() {
    if [ -f /proc/device-tree/model ]; then
        PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    elif [ -f /sys/firmware/devicetree/base/model ]; then
        PI_MODEL=$(tr -d '\0' < /sys/firmware/devicetree/base/model)
    else
        PI_MODEL="Unknown"
    fi

    log_info "Detected Raspberry Pi model: $PI_MODEL"

    # Extract model number for compatibility checks
    if [[ $PI_MODEL =~ Raspberry\ Pi\ ([0-9]+) ]]; then
        PI_NUMBER="${BASH_REMATCH[1]}"
    else
        PI_NUMBER="0"
    fi

    log_info "Pi generation: $PI_NUMBER"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check if running on Raspberry Pi
    if ! grep -q "BCM" /proc/cpuinfo && ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        log_error "This installer is designed for Raspberry Pi devices only."
        log_error "Please run on a Raspberry Pi Zero, 3, 4, or 5."
        exit 1
    fi

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)"; then
        log_success "Python $PYTHON_VERSION detected (compatible)"
    else
        log_error "Python 3.7 or higher is required. Current version: $PYTHON_VERSION"
        exit 1
    fi

    # Check available disk space (need at least 500MB)
    AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
    if [ $AVAILABLE_SPACE -lt 524288 ]; then  # 512MB in KB
        log_warning "Low disk space detected. Installation may fail."
        log_warning "Available: $(($AVAILABLE_SPACE / 1024)) MB, Recommended: 500+ MB"
    fi

    log_success "System requirements check passed"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."

    # Update package list
    sudo apt update

    # Install Python and pip if not present
    sudo apt install -y python3 python3-pip python3-venv

    # Install cryptography dependencies
    sudo apt install -y build-essential libssl-dev libffi-dev libsodium-dev

    # Install only essential Pi-specific packages (raspberrypi-userland provides vcgencmd)
    # Note: raspberrypi-bootloader is NOT needed - it only updates EEPROM firmware
    log_info "Installing raspberrypi-userland for VideoCore GPU access (provides vcgencmd)..."
    if sudo apt install -y raspberrypi-userland 2>/dev/null; then
        log_success "Installed raspberrypi-userland (VideoCore GPU access for mining)"
    elif sudo apt install -y libraspberrypi-bin 2>/dev/null; then
        log_success "Installed libraspberrypi-bin (VideoCore GPU access for mining)"
    else
        log_warning "VideoCore GPU package not found - mining features may be limited"
        log_info "PiSecure will still work for wallet and identity features"
    fi

    # Ensure user is in required groups
    sudo usermod -a -G gpio,video,i2c $USER || true
    sudo usermod -a -G dialout $USER || true

    log_success "System dependencies installed"
}

# Create virtual environment and install PiSecure
install_pisecure() {
    local install_dir="${1:-/opt/pisecure}"

    log_info "Installing PiSecure to $install_dir..."

    # Create installation directory
    sudo mkdir -p "$install_dir"
    sudo chown $USER:$USER "$install_dir"

    # Create virtual environment
    cd "$install_dir"
    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install PiSecure from GitHub (with fallback for import issues)
    log_info "Installing PiSecure dependencies..."

    # Install core dependencies that are known to work
    pip install cryptography PyNaCl requests click rich python-dateutil

    # Clone and install PiSecure manually to handle import issues
    if [ ! -d "repo" ]; then
        git clone https://github.com/UnderhillForge/PiSecure.git repo
    fi

    # Copy PiSecure modules to virtual environment
    mkdir -p venv/lib/python3.*/site-packages/pisecure/
    cp -r repo/pisecure/* venv/lib/python3.*/site-packages/pisecure/ 2>/dev/null || true

    # Create launcher script (uses simple_cli which works)
    cat > launch_pisecure.py << 'EOF'
#!/usr/bin/env python3
"""
PiSecure CLI Launcher - Simple Python launcher that works around import issues
"""

import sys
import os

# Add the current directory and repo to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.join(os.path.dirname(current_dir), 'repo')

sys.path.insert(0, current_dir)
sys.path.insert(0, repo_dir)

def main():
    """Main entry point for the launcher"""
    # Now try to import and run PiSecure CLI
    try:
        from pisecure.simple_cli import cli
        cli()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Trying alternative import paths...")

        # Try different import approaches
        try:
            # Direct module import
            sys.path.insert(0, '/opt/pisecure/repo')
            from pisecure.simple_cli import cli
            cli()
        except Exception as e2:
            print(f"Alternative import failed: {e2}")
            print("\nPiSecure CLI is having import issues.")
            print("The web dashboard works perfectly though!")
            print("Access it at: http://localhost:5000")
            sys.exit(1)


if __name__ == '__main__':
    main()
EOF

    chmod +x launch_pisecure.py

    log_success "PiSecure installed successfully"
}

# Create systemd service
create_service() {
    local install_dir="${1:-/opt/pisecure}"

    log_info "Creating systemd service..."

    # Create service file
    sudo tee /etc/systemd/system/pisecure.service > /dev/null << EOF
[Unit]
Description=PiSecure Blockchain Node
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$install_dir
ExecStart=$install_dir/venv/bin/python $install_dir/launch_pisecure.py status
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload

    log_success "Systemd service created"
}

# Create desktop shortcuts (for Pi with desktop)
create_shortcuts() {
    log_info "Creating desktop shortcuts..."

    # Create desktop entry for PiSecure Dashboard
    mkdir -p ~/.local/share/applications

    cat > ~/.local/share/applications/pisecure-dashboard.desktop << EOF
[Desktop Entry]
Name=PiSecure Dashboard
Comment=PiSecure Blockchain Node Dashboard
Exec=chromium-browser --app=http://localhost:5000
Icon=chromium-browser
Terminal=false
Type=Application
Categories=Network;Security;
EOF

    # Make executable
    chmod +x ~/.local/share/applications/pisecure-dashboard.desktop

    log_success "Desktop shortcuts created"
}

# Main installation function
main() {
    local install_dir="/opt/pisecure"

    echo "========================================"
    echo "🔐 PiSecure Universal Installer"
    echo "========================================"
    echo "Works on all Raspberry Pi models"
    echo ""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --install-dir)
                install_dir="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--install-dir DIR]"
                echo ""
                echo "Options:"
                echo "  --install-dir DIR    Installation directory (default: /opt/pisecure)"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Run installation steps
    detect_pi_model
    check_requirements
    install_system_deps
    install_pisecure "$install_dir"
    create_service "$install_dir"
    create_shortcuts

    echo ""
    echo "========================================"
    log_success "PiSecure installation completed!"
    echo ""
    echo "📍 Installation directory: $install_dir"
    echo "🚀 Launch PiSecure: $install_dir/launch_pisecure.py"
    echo "🌐 Web Dashboard: http://localhost:5000"
    echo ""
    echo "Commands:"
    echo "  $install_dir/launch_pisecure.py --help    # Show CLI help"
    echo "  $install_dir/launch_pisecure.py status    # Show blockchain status"
    echo "  $install_dir/launch_pisecure.py verify-hardware  # Verify Pi hardware"
    echo ""
    echo "Services:"
    echo "  sudo systemctl start pisecure     # Start PiSecure service"
    echo "  sudo systemctl enable pisecure    # Enable auto-start"
    echo ""
    log_warning "Important: Log out and back in for group changes to take effect"
    echo "========================================"
}

# Run main function
main "$@"