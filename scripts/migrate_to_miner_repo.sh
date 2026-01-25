#!/bin/bash
# PiSecure-Miner Repository Migration Script
# Automates copying of mining components to new private repository

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SOURCE_DIR="/home/pi/PiSecure"
AUTO_CONFIRM=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_CONFIRM=true
            shift
            ;;
        *)
            DEST_DIR="$1"
            shift
            ;;
    esac
done

DEST_DIR="${DEST_DIR:-$HOME/PiSecure-Miner}"
BACKUP_DIR="$HOME/pisecure-miner-backup-$(date +%Y%m%d-%H%M%S)"

# Helper functions
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Verify source directory
if [ ! -d "$SOURCE_DIR" ]; then
    print_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

print_header "PiSecure-Miner Migration Script"
echo "Source: $SOURCE_DIR"
echo "Destination: $DEST_DIR"
echo "Backup: $BACKUP_DIR"
echo

# Confirm before proceeding
if [ "$AUTO_CONFIRM" = false ]; then
    read -p "Continue with migration? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Migration cancelled"
        exit 0
    fi
else
    echo "Auto-confirmed: Proceeding with migration..."
fi

# Create backup directory
print_header "Creating Backup"
mkdir -p "$BACKUP_DIR"
print_success "Backup directory created: $BACKUP_DIR"

# Step 1: Create destination structure
print_header "Creating Directory Structure"
mkdir -p "$DEST_DIR"/{psminer,pihash,shared,docs,examples,tests}
mkdir -p "$DEST_DIR"/psminer/{include,src}
mkdir -p "$DEST_DIR"/pihash/{include,src,python}
mkdir -p "$DEST_DIR"/shared/{crypto,consensus,util}
print_success "Directory structure created"

# Step 2: Copy psminer files
print_header "Copying psminer Files"
if [ -d "$SOURCE_DIR/cpp/psminer" ]; then
    # Backup original
    cp -r "$SOURCE_DIR/cpp/psminer" "$BACKUP_DIR/"
    
    # Copy to new repo
    cp -r "$SOURCE_DIR"/cpp/psminer/include/* "$DEST_DIR"/psminer/include/ 2>/dev/null || true
    cp -r "$SOURCE_DIR"/cpp/psminer/src/* "$DEST_DIR"/psminer/src/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/psminer/CMakeLists.txt "$DEST_DIR"/psminer/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/psminer/Makefile "$DEST_DIR"/psminer/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/psminer/build.sh "$DEST_DIR"/psminer/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/psminer/README.md "$DEST_DIR"/psminer/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/psminer/*.md "$DEST_DIR"/psminer/ 2>/dev/null || true
    
    print_success "psminer files copied"
else
    print_warning "psminer directory not found"
fi

# Step 3: Copy PiHash C++ files
print_header "Copying PiHash C++ Files"
if [ -d "$SOURCE_DIR/cpp/hw" ]; then
    # Backup original
    cp -r "$SOURCE_DIR/cpp/hw" "$BACKUP_DIR/"
    
    # Copy headers
    cp "$SOURCE_DIR"/cpp/hw/pihash.h "$DEST_DIR"/pihash/include/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/hw/pihash.hpp "$DEST_DIR"/pihash/include/ 2>/dev/null || true
    
    # Copy source files
    cp "$SOURCE_DIR"/cpp/hw/pihash.cpp "$DEST_DIR"/pihash/src/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/hw/videocore_mailbox.* "$DEST_DIR"/pihash/src/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/hw/hw_verifier.* "$DEST_DIR"/pihash/src/ 2>/dev/null || true
    
    print_success "PiHash C++ files copied"
else
    print_warning "cpp/hw directory not found"
fi

# Step 4: Copy PiHash Python files
print_header "Copying PiHash Python Files"
if [ -d "$SOURCE_DIR/pisecure/core" ]; then
    # Backup original
    mkdir -p "$BACKUP_DIR/pisecure/core"
    cp "$SOURCE_DIR"/pisecure/core/pihash*.py "$BACKUP_DIR"/pisecure/core/ 2>/dev/null || true
    
    # Copy to new repo
    cp "$SOURCE_DIR"/pisecure/core/pihash.py "$DEST_DIR"/pihash/python/ 2>/dev/null || true
    cp "$SOURCE_DIR"/pisecure/core/pihash_cpp.py "$DEST_DIR"/pihash/python/ 2>/dev/null || true
    
    print_success "PiHash Python files copied"
else
    print_warning "pisecure/core directory not found"
fi

if [ -d "$SOURCE_DIR/pisecure/kernel" ]; then
    mkdir -p "$BACKUP_DIR/pisecure/kernel"
    cp "$SOURCE_DIR"/pisecure/kernel/pihash*.py "$BACKUP_DIR"/pisecure/kernel/ 2>/dev/null || true
    
    cp "$SOURCE_DIR"/pisecure/kernel/pihash.py "$DEST_DIR"/pihash/python/kernel_pihash.py 2>/dev/null || true
    cp "$SOURCE_DIR"/pisecure/kernel/pihash_cpp.py "$DEST_DIR"/pihash/python/kernel_pihash_cpp.py 2>/dev/null || true
    
    print_success "Kernel PiHash files copied"
fi

# Step 5: Copy hardware verification
print_header "Copying Hardware Verification"
if [ -f "$SOURCE_DIR/pisecure/core/hardware.py" ]; then
    mkdir -p "$BACKUP_DIR/pisecure/core"
    cp "$SOURCE_DIR"/pisecure/core/hardware.py "$BACKUP_DIR"/pisecure/core/
    cp "$SOURCE_DIR"/pisecure/core/hardware.py "$DEST_DIR"/pihash/python/
    print_success "Hardware verification copied"
fi

# Step 6: Copy shared dependencies
print_header "Copying Shared Dependencies"
# Crypto
if [ -d "$SOURCE_DIR/cpp/crypto" ]; then
    cp "$SOURCE_DIR"/cpp/crypto/sha256.* "$DEST_DIR"/shared/crypto/ 2>/dev/null || true
    print_success "Crypto files copied"
fi

# Consensus
if [ -d "$SOURCE_DIR/cpp/consensus" ]; then
    cp "$SOURCE_DIR"/cpp/consensus/arith_uint256.cpp "$DEST_DIR"/shared/consensus/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/consensus/uint256.cpp "$DEST_DIR"/shared/consensus/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/consensus/pow.cpp "$DEST_DIR"/shared/consensus/ 2>/dev/null || true
    cp "$SOURCE_DIR"/cpp/consensus/*.h "$DEST_DIR"/shared/consensus/ 2>/dev/null || true
    print_success "Consensus files copied"
fi

# Utilities
if [ -d "$SOURCE_DIR/cpp/util" ]; then
    cp -r "$SOURCE_DIR"/cpp/util/* "$DEST_DIR"/shared/util/ 2>/dev/null || true
    print_success "Utility files copied"
fi

# Step 7: Copy documentation
print_header "Copying Documentation"
cp "$SOURCE_DIR"/docs/phase1_mining_challenges.md "$DEST_DIR"/docs/ 2>/dev/null || true
cp "$SOURCE_DIR"/docs/PSMINER_PINS_INTEGRATION.md "$DEST_DIR"/docs/ 2>/dev/null || true
cp "$SOURCE_DIR"/docs/refactoring/PIHASH*.md "$DEST_DIR"/docs/ 2>/dev/null || true
cp "$SOURCE_DIR"/docs/refactoring/*SEGFAULT*.md "$DEST_DIR"/docs/ 2>/dev/null || true
print_success "Documentation copied"

# Step 8: Copy examples
print_header "Copying Examples"
cp "$SOURCE_DIR"/examples/basic_mining.py "$DEST_DIR"/examples/ 2>/dev/null || true
print_success "Examples copied"

# Step 9: Create top-level CMakeLists.txt
print_header "Creating Build Configuration"
cat > "$DEST_DIR/CMakeLists.txt" << 'EOF'
cmake_minimum_required(VERSION 3.12)
project(PiSecure-Miner VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Raspberry Pi platform check
if(NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "arm" AND NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "aarch64")
    message(WARNING "PiSecure-Miner is designed for Raspberry Pi (ARM) platforms")
    message(WARNING "Current processor: ${CMAKE_SYSTEM_PROCESSOR}")
    message(WARNING "Mining will fail on non-Pi hardware")
endif()

# Build options
option(BUILD_PIHASH_PYTHON "Build Python bindings for PiHash" ON)
option(BUILD_TESTS "Build test suite" OFF)
option(ENABLE_NPU "Enable NPU acceleration (Pi 6+)" OFF)
option(ENABLE_HARDWARE_VERIFICATION "Enable strict Pi hardware verification" ON)

# Global include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/pihash/include
    ${CMAKE_SOURCE_DIR}/shared/crypto
    ${CMAKE_SOURCE_DIR}/shared/consensus
    ${CMAKE_SOURCE_DIR}/shared/util
)

# Subdirectories
add_subdirectory(pihash)
add_subdirectory(psminer)

if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation
install(FILES README.md LICENSE DESTINATION share/doc/pisecure-miner)
EOF
print_success "CMakeLists.txt created"

# Step 10: Create pihash CMakeLists.txt
cat > "$DEST_DIR/pihash/CMakeLists.txt" << 'EOF'
# PiHash Algorithm Library

set(PIHASH_SOURCES
    src/pihash.cpp
    src/videocore_mailbox.cpp
    src/hw_verifier.cpp
)

add_library(pihash STATIC ${PIHASH_SOURCES})

target_include_directories(pihash PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/shared/crypto
)

# Link shared crypto
target_sources(pihash PRIVATE
    ${CMAKE_SOURCE_DIR}/shared/crypto/sha256.cpp
)

# Installation
install(TARGETS pihash
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(FILES include/pihash.h include/pihash.hpp
    DESTINATION include/pisecure-miner
)
EOF
print_success "pihash/CMakeLists.txt created"

# Step 11: Create README.md
print_header "Creating README"
cat > "$DEST_DIR/README.md" << 'EOF'
# PiSecure-Miner

**PRIVATE REPOSITORY** - Hardware-verified mining software for PiSecure blockchain

## Overview
PiSecure-Miner contains the proprietary mining software for PiSecure, including:
- **psminer**: High-performance mining application with TUI
- **PiHash**: Custom hardware-verified proof-of-work algorithm
- Hardware verification system exclusive to Raspberry Pi

## Requirements
- **Hardware**: Raspberry Pi 4/5 (4GB+ RAM recommended)
- **OS**: Raspberry Pi OS (64-bit)
- **Dependencies**: 
  - CMake 3.12+
  - GCC/Clang with C++17 support
  - ncurses library
  - Active pisecured daemon (from main PiSecure repo)

## Quick Start

### Build
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Run
```bash
# Start mining with TUI
./psminer/psminer --wallet YOUR_WALLET_ADDRESS

# CLI mode
./psminer/psminer --wallet YOUR_WALLET --cli

# Daemon mode
./psminer/psminer --wallet YOUR_WALLET --daemon
```

## Integration with PiSecure
This repository is designed to work with the main PiSecure blockchain:
- **Main Repository**: https://github.com/UnderhillForge/PiSecure (public)
- **Requires**: pisecured daemon running on port 3144
- **Protocol**: WebSocket JSON-RPC 2.0

## Architecture
```
PiSecure-Miner/
├── psminer/          # Mining application
│   ├── include/      # Headers
│   └── src/          # Implementation
├── pihash/           # PiHash algorithm
│   ├── include/      # Public API
│   ├── src/          # Implementation
│   └── python/       # Python bindings
├── shared/           # Shared dependencies
│   ├── crypto/       # SHA256, etc.
│   ├── consensus/    # PoW utilities
│   └── util/         # Common utilities
└── docs/             # Documentation
```

## PiHash Algorithm
PiHash is a custom hardware-verified proof-of-work algorithm:
- **Hardware Binding**: Incorporates Pi CPU serial, board revision
- **Memory-Hard**: 256MB default memory usage
- **ARM-Optimized**: NEON SIMD instructions
- **GPU Integration**: VideoCore mailbox communication
- **NPU Ready**: Hooks for Pi 6+ neural processor

**Target Difficulty**: ~146 leading zero bits (extremely hard)

## Documentation
- [Getting Started](docs/getting-started.md)
- [PiHash Algorithm](docs/pihash-algorithm.md)
- [Hardware Requirements](docs/hardware-requirements.md)
- [Integration Guide](docs/integration-guide.md)

## License
**Proprietary License** - All Rights Reserved

This software is private and confidential. Unauthorized copying, distribution,
or use is strictly prohibited.

## Support
- **Issues**: https://github.com/UnderhillForge/PiSecure-Miner/issues
- **Main Project**: https://github.com/UnderhillForge/PiSecure

## Migration Notes
Migrated from main PiSecure repository on 2026-01-24.
See MIGRATION_GUIDE.md for details.
EOF
print_success "README.md created"

# Step 12: Create .gitignore
cat > "$DEST_DIR/.gitignore" << 'EOF'
# Build directories
build/
cmake-build-*/
*.o
*.a
*.so
*.dylib

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
*.whl

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Binaries
psminer/psminer
psminer/build/

# Logs
*.log
mining-*.log

# Configuration (may contain wallet addresses)
config.json
mining-config.json
EOF
print_success ".gitignore created"

# Step 13: Create build script
cat > "$DEST_DIR/build.sh" << 'EOF'
#!/bin/bash
# Quick build script for PiSecure-Miner

set -e

BUILD_DIR="build"
BUILD_TYPE="${1:-Release}"

echo "Building PiSecure-Miner ($BUILD_TYPE)..."

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
cmake -DCMAKE_BUILD_TYPE="$BUILD_TYPE" ..

# Build
make -j$(nproc)

echo "Build complete!"
echo "Binary: $BUILD_DIR/psminer/psminer"
EOF
chmod +x "$DEST_DIR/build.sh"
print_success "build.sh created"

# Step 14: Initialize git repository
print_header "Initializing Git Repository"
cd "$DEST_DIR"
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial migration from PiSecure repository

Migrated components:
- psminer application (TUI, CLI, daemon modes)
- PiHash algorithm (C++ and Python)
- Hardware verification system
- Shared dependencies (crypto, consensus)
- Mining-specific documentation

Source: https://github.com/UnderhillForge/PiSecure
Migration Date: $(date +%Y-%m-%d)
"
    print_success "Git repository initialized"
else
    print_warning "Git repository already exists"
fi

# Summary
print_header "Migration Summary"
echo
echo "Source Directory:  $SOURCE_DIR"
echo "Destination:       $DEST_DIR"
echo "Backup:            $BACKUP_DIR"
echo
print_success "Migration completed successfully!"
echo
echo "Next steps:"
echo "1. cd $DEST_DIR"
echo "2. git remote add origin https://github.com/UnderhillForge/PiSecure-Miner.git"
echo "3. git push -u origin main"
echo "4. ./build.sh"
echo "5. Test: ./build/psminer/psminer --help"
echo
print_warning "Don't forget to update the main PiSecure repository:"
echo "- Remove cpp/psminer/ directory"
echo "- Add stub implementations for PiHash"
echo "- Update documentation"
echo

exit 0
