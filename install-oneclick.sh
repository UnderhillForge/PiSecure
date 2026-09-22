#!/bin/bash
#
# PiSecure One-Click Installer
# =============================
# Complete installation of PiSecure blockchain system
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install-oneclick.sh | bash
#   OR
#   wget -qO- https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install-oneclick.sh | bash
#   OR (if already cloned):
#   bash install-oneclick.sh
#
# What this installs:
# - Python 3.x with all dependencies
# - C++ build tools (cmake, gcc, g++)
# - PiSecure blockchain daemon (pisecured)
# - Mining client (psminer) - provided separately via private repo (not installed here)
# - Wallet client (pswallet) with smart contracts
# - Validator client (psvalidator) - works on ANY platform
# - Web dashboard on port 5000
# - API server on port 3142
# - RPC daemon on port 3144
#

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/UnderhillForge/PiSecure.git"
INSTALL_DIR="${HOME}/PiSecure"
VENV_DIR="${INSTALL_DIR}/pisecure_env"
DATA_DIR="/var/lib/pisecure"
CONFIG_DIR="/etc/pisecure"

# Logging functions
log_header() {
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC} ${CYAN}$1${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "${CYAN}==>${NC} $1"
}

# Detect system
detect_system() {
    log_header "Detecting System"
    
    OS=$(uname -s)
    ARCH=$(uname -m)
    
    log_info "Operating System: $OS"
    log_info "Architecture: $ARCH"
    
    # Detect if Raspberry Pi
    IS_PI=false
    if [ -f /proc/device-tree/model ]; then
        PI_MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "Unknown")
        if [[ "$PI_MODEL" == *"Raspberry Pi"* ]]; then
            IS_PI=true
            log_success "Raspberry Pi detected: $PI_MODEL"
            log_info "Mining (psminer) will be available"
        fi
    fi
    
    if [ "$IS_PI" = false ]; then
        log_warning "Not running on Raspberry Pi"
        log_info "Mining requires Raspberry Pi hardware"
        log_info "Validation (psvalidator) works on ANY platform"
    fi
    
    # Check for required commands
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python detected: $PYTHON_VERSION"
    
    # Check for git
    if ! command -v git &> /dev/null; then
        log_warning "Git not found, will attempt to install"
        INSTALL_GIT=true
    else
        log_success "Git detected: $(git --version | cut -d' ' -f3)"
        INSTALL_GIT=false
    fi
}

# Install system dependencies
install_system_deps() {
    log_header "Installing System Dependencies"
    
    if [ "$OS" = "Linux" ]; then
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt-get"
            UPDATE_CMD="sudo apt-get update"
            INSTALL_CMD="sudo apt-get install -y"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            UPDATE_CMD="sudo yum check-update || true"
            INSTALL_CMD="sudo yum install -y"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
            UPDATE_CMD="sudo dnf check-update || true"
            INSTALL_CMD="sudo dnf install -y"
        elif command -v pacman &> /dev/null; then
            PKG_MANAGER="pacman"
            UPDATE_CMD="sudo pacman -Sy"
            INSTALL_CMD="sudo pacman -S --noconfirm"
        else
            log_error "No supported package manager found (apt, yum, dnf, pacman)"
            exit 1
        fi
        
        log_step "Using package manager: $PKG_MANAGER"
        log_step "Updating package lists..."
        $UPDATE_CMD
        
        log_step "Installing build tools and dependencies..."
        
        if [ "$PKG_MANAGER" = "apt-get" ]; then
            $INSTALL_CMD \
                python3 \
                python3-pip \
                python3-venv \
                python3-dev \
                build-essential \
                cmake \
                git \
                curl \
                wget \
                libssl-dev \
                libffi-dev \
                sqlite3 \
                libsqlite3-dev \
                pkg-config
        elif [ "$PKG_MANAGER" = "yum" ] || [ "$PKG_MANAGER" = "dnf" ]; then
            $INSTALL_CMD \
                python3 \
                python3-pip \
                python3-devel \
                gcc \
                gcc-c++ \
                make \
                cmake \
                git \
                curl \
                wget \
                openssl-devel \
                libffi-devel \
                sqlite-devel
        elif [ "$PKG_MANAGER" = "pacman" ]; then
            $INSTALL_CMD \
                python \
                python-pip \
                base-devel \
                cmake \
                git \
                curl \
                wget \
                openssl \
                libffi \
                sqlite
        fi
        
        log_success "System dependencies installed"
        
    elif [ "$OS" = "Darwin" ]; then
        # macOS
        log_step "Detected macOS"
        
        if ! command -v brew &> /dev/null; then
            log_error "Homebrew not found. Please install from https://brew.sh/"
            exit 1
        fi
        
        log_step "Installing dependencies via Homebrew..."
        brew update
        brew install python3 cmake git wget openssl libffi sqlite3
        
        log_success "System dependencies installed"
    else
        log_warning "Unsupported OS: $OS"
        log_info "Attempting to continue with existing tools..."
    fi
}

# Clone or update repository
setup_repository() {
    log_header "Setting Up Repository"
    
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Directory $INSTALL_DIR already exists"
        log_step "Updating existing repository..."
        cd "$INSTALL_DIR"
        
        # Check if it's a git repo
        if [ -d ".git" ]; then
            git fetch --all
            git pull origin main || git pull origin master || log_warning "Could not pull latest changes"
            log_success "Repository updated"
        else
            log_warning "Not a git repository, using existing files"
        fi
    else
        log_step "Cloning PiSecure repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
        log_success "Repository cloned"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    log_header "Setting Up Python Environment"
    
    cd "$INSTALL_DIR"
    
    if [ -d "$VENV_DIR" ]; then
        log_warning "Virtual environment already exists"
        log_step "Using existing environment at: $VENV_DIR"
    else
        log_step "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    fi
    
    log_step "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    log_step "Upgrading pip, setuptools, wheel..."
    pip install --upgrade pip setuptools wheel
    
    log_success "Python environment ready"
}

# Install Python dependencies
install_python_deps() {
    log_header "Installing Python Dependencies"
    
    cd "$INSTALL_DIR"
    source "$VENV_DIR/bin/activate"
    
    log_step "Installing core requirements..."
    pip install -r requirements.txt
    log_success "Core dependencies installed"
    
    log_step "Installing PiSecure package..."
    pip install -e .
    log_success "PiSecure package installed"
    
    # Show installed packages
    log_info "Key packages installed:"
    pip list | grep -E "cryptography|Flask|PyNaCl|rich|textual|aiohttp|websocket" || true
}

# Build C++ components
build_cpp_components() {
    log_header "Building C++ Components"
    
    cd "$INSTALL_DIR"
    
    # Check for CMake
    if ! command -v cmake &> /dev/null; then
        log_error "CMake not found. Please install CMake first."
        return 1
    fi
    
    # Build pisecured (RPC daemon)
    if [ -d "cpp/pisecured" ]; then
        log_step "Building pisecured (RPC daemon)..."
        mkdir -p cpp/pisecured/build
        cd cpp/pisecured/build
        
        cmake -DCMAKE_BUILD_TYPE=Release .. && \
        make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2) && \
        log_success "pisecured built successfully" || \
        log_warning "pisecured build failed (optional component)"
        
        cd "$INSTALL_DIR"
    fi
    
    # Build pswallet (wallet + smart contracts)
    if [ -d "cpp/pswallet" ]; then
        log_step "Building pswallet (wallet client)..."
        mkdir -p cpp/pswallet/build
        cd cpp/pswallet/build
        
        cmake -DCMAKE_BUILD_TYPE=Release .. && \
        make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2) && \
        log_success "pswallet built successfully" || \
        log_warning "pswallet build failed"
        
        cd "$INSTALL_DIR"
    fi
    
    # Build psvalidator (universal validator)
    if [ -d "cpp/psvalidator" ]; then
        log_step "Building psvalidator (universal validator)..."
        mkdir -p cpp/psvalidator/build
        cd cpp/psvalidator/build
        
        cmake -DCMAKE_BUILD_TYPE=Release .. && \
        make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2) && \
        log_success "psvalidator built successfully" || \
        log_warning "psvalidator build failed"
        
        cd "$INSTALL_DIR"
    fi
}

# Setup directories
setup_directories() {
    log_header "Setting Up Data Directories"
    
    # Create data directory
    if [ ! -d "$DATA_DIR" ]; then
        log_step "Creating data directory: $DATA_DIR"
        sudo mkdir -p "$DATA_DIR"
        sudo chown "$USER:$USER" "$DATA_DIR" 2>/dev/null || sudo chown "$USER" "$DATA_DIR"
        log_success "Data directory created"
    else
        log_info "Data directory already exists: $DATA_DIR"
    fi
    
    # Create config directory
    if [ ! -d "$CONFIG_DIR" ]; then
        log_step "Creating config directory: $CONFIG_DIR"
        sudo mkdir -p "$CONFIG_DIR"
        sudo chown "$USER:$USER" "$CONFIG_DIR" 2>/dev/null || sudo chown "$USER" "$CONFIG_DIR"
        log_success "Config directory created"
    else
        log_info "Config directory already exists: $CONFIG_DIR"
    fi
}

# Create wrapper scripts
create_wrappers() {
    log_header "Creating Command Wrappers"
    
    cd "$INSTALL_DIR"
    
    # Create pisecure wrapper
    log_step "Creating pisecure command wrapper..."
    cat > pisecure << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/pisecure_env/bin/activate"
python -m pisecure.cli "$@"
EOF
    chmod +x pisecure
    
    # Create links to C++ binaries
    if [ -f "cpp/pisecured/build/pisecured" ]; then
        ln -sf "$INSTALL_DIR/cpp/pisecured/build/pisecured" "$INSTALL_DIR/pisecured" 2>/dev/null || true
    fi
    
    if [ -f "cpp/pswallet/build/pswallet" ]; then
        # Prefer symlink (auto-updates on rebuild)
        ln -sf "$INSTALL_DIR/cpp/pswallet/build/pswallet" "$INSTALL_DIR/pswallet" 2>/dev/null || true
        # Fallback copy if symlink fails for any reason
        if [ ! -x "$INSTALL_DIR/pswallet" ]; then
            cp "$INSTALL_DIR/cpp/pswallet/build/pswallet" "$INSTALL_DIR/pswallet" 2>/dev/null || true
            chmod +x "$INSTALL_DIR/pswallet" 2>/dev/null || true
        fi
    fi

    if [ -f "cpp/psvalidator/build/psvalidator" ]; then
        ln -sf "$INSTALL_DIR/cpp/psvalidator/build/psvalidator" "$INSTALL_DIR/psvalidator" 2>/dev/null || true
    fi
    
    log_success "Command wrappers created"
}

# Setup systemd service for auto-start
setup_systemd_service() {
    log_header "Configuring Auto-Start Services"
    
    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        log_warning "systemd not found, skipping auto-start setup"
        return 0
    fi
    
    # Check if pisecured was built
    if [ ! -f "$INSTALL_DIR/cpp/pisecured/build/pisecured" ] && [ ! -f "$INSTALL_DIR/pisecured" ]; then
        log_warning "pisecured not found, skipping auto-start setup"
        return 0
    fi
    
    echo ""
    echo -e "${YELLOW}Would you like pisecured to start automatically at boot?${NC}"
    echo "This is recommended for dedicated blockchain nodes."
    echo ""
    read -p "Enable auto-start? (Y/n): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        log_step "Creating systemd service file..."
        
        # Determine pisecured binary path
        if [ -f "$INSTALL_DIR/pisecured" ]; then
            PISECURED_BIN="$INSTALL_DIR/pisecured"
        else
            PISECURED_BIN="$INSTALL_DIR/cpp/pisecured/build/pisecured"
        fi
        
        # Create systemd service file
        sudo tee /etc/systemd/system/pisecured.service > /dev/null << EOF
[Unit]
Description=PiSecure Blockchain Daemon
Documentation=https://github.com/UnderhillForge/PiSecure
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$PISECURED_BIN --host 0.0.0.0 --port 3144
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecured

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$DATA_DIR

# Resource limits
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF
        
        log_success "Systemd service created: /etc/systemd/system/pisecured.service"
        
        # Reload systemd
        log_step "Reloading systemd daemon..."
        sudo systemctl daemon-reload
        
        # Enable service
        log_step "Enabling pisecured service..."
        sudo systemctl enable pisecured.service
        
        # Ask if user wants to start now
        echo ""
        read -p "Start pisecured now? (Y/n): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            log_step "Starting pisecured service..."
            sudo systemctl start pisecured.service
            sleep 2
            
            # Check status
            if sudo systemctl is-active --quiet pisecured.service; then
                log_success "pisecured is running!"
                log_info "Check status: sudo systemctl status pisecured"
                log_info "View logs: sudo journalctl -u pisecured -f"
            else
                log_warning "pisecured failed to start"
                log_info "Check logs: sudo journalctl -u pisecured -n 50"
            fi
        else
            log_info "Start later with: sudo systemctl start pisecured"
        fi
        
        log_success "Auto-start configured"
        
        echo ""
        echo -e "${CYAN}Service Management Commands:${NC}"
        echo "  sudo systemctl start pisecured      - Start daemon"
        echo "  sudo systemctl stop pisecured       - Stop daemon"
        echo "  sudo systemctl restart pisecured    - Restart daemon"
        echo "  sudo systemctl status pisecured     - Check status"
        echo "  sudo systemctl disable pisecured    - Disable auto-start"
        echo "  sudo journalctl -u pisecured -f     - View live logs"
    else
        log_info "Auto-start skipped (you can run pisecured manually)"
    fi
}

# Display completion message
show_completion() {
    log_header "Installation Complete!"
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}              PiSecure Successfully Installed!                   ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${CYAN}Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${CYAN}Python Environment:${NC} $VENV_DIR"
    echo -e "${CYAN}Data Directory:${NC} $DATA_DIR"
    echo ""
    
    echo -e "${YELLOW}Available Commands:${NC}"
    echo ""
    
    # Check which components were built
    if [ -f "$INSTALL_DIR/pisecure" ]; then
        echo -e "  ${GREEN}✓${NC} ./pisecure            - Main CLI (wallet, blockchain, status)"
    fi
    
    if [ -f "$INSTALL_DIR/pisecured" ] || [ -f "cpp/pisecured/build/pisecured" ]; then
        echo -e "  ${GREEN}✓${NC} ./pisecured           - RPC daemon (WebSocket JSON-RPC)"
    fi
    
    if [ -f "$INSTALL_DIR/pswallet" ] || [ -f "cpp/pswallet/build/pswallet" ]; then
        echo -e "  ${GREEN}✓${NC} ./pswallet            - Wallet + smart contracts"
    fi
    
    if [ -f "$INSTALL_DIR/psvalidator" ] || [ -f "cpp/psvalidator/build/psvalidator" ]; then
        echo -e "  ${GREEN}✓${NC} ./psvalidator         - Universal validator (any platform)"
    fi
    
    echo ""
    echo -e "${YELLOW}Quick Start:${NC}"
    echo ""
    echo "  # Activate environment"
    echo "  cd $INSTALL_DIR"
    echo "  source pisecure_env/bin/activate"
    echo ""
    echo "  # Check status"
    echo "  ./pisecure status"
    echo ""
    echo "  # Start RPC daemon"
    echo "  ./pisecured"
    echo ""
    
    if [ "$IS_PI" = true ]; then
        echo "  # psminer is a GitHub Release binary for Raspberry Pi 2-5"
        echo ""
    fi
    
    echo "  # Start validator (earn rewards)"
    echo "  ./psvalidator --rpc ws://127.0.0.1:3144"
    echo ""
    echo "  # Wallet operations"
    echo "  ./pswallet balance"
    echo "  ./pswallet send <recipient> <amount>"
    echo ""
    echo -e "${CYAN}Documentation:${NC} $INSTALL_DIR/docs/"
    echo -e "${CYAN}Support:${NC} https://github.com/UnderhillForge/PiSecure/issues"
    echo ""
    
    # Show service status if enabled
    if systemctl is-enabled pisecured.service &>/dev/null; then
        echo -e "${GREEN}✓${NC} pisecured auto-start: ${GREEN}ENABLED${NC}"
        if systemctl is-active pisecured.service &>/dev/null; then
            echo -e "${GREEN}✓${NC} pisecured status: ${GREEN}RUNNING${NC}"
        fi
        echo ""
    fi
    
    if [ "$IS_PI" = false ]; then
        echo -e "${YELLOW}Note:${NC} You're running on a non-Pi system."
        echo "      Mining requires Raspberry Pi hardware."
        echo "      Validation works on ALL platforms and earns rewards!"
        echo ""
    fi
}

# Main installation flow
main() {
    clear
    
    log_header "PiSecure One-Click Installer"
    
    echo -e "${CYAN}This will install:${NC}"
    echo "  • PiSecure blockchain node"
    echo "  • Python environment with dependencies"
    echo "  • C++ components (pisecured, psminer*, pswallet, psvalidator)"
    echo "  • Development tools and utilities"
    echo ""
    echo -e "${YELLOW}*${NC} psminer requires Raspberry Pi hardware"
    echo ""
    
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
    
    # Run installation steps
    detect_system
    install_system_deps
    setup_repository
    setup_python_env
    install_python_deps
    build_cpp_components
    setup_directories
    create_wrappers
    setup_systemd_service
    show_completion
}

# Run main installation
main "$@"
