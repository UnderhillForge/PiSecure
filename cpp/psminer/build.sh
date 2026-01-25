#!/bin/bash
# Build script for psminer

set -e

echo "=== PiSecure Miner Build Script ==="
echo

# Check if running on Raspberry Pi
if [[ ! $(uname -m) =~ arm* ]] && [[ ! $(uname -m) =~ aarch64 ]]; then
    echo "⚠️  Warning: Not running on ARM architecture ($(uname -m))"
    echo "   psminer is designed for Raspberry Pi"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check dependencies
echo "Checking dependencies..."

if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found. Install: sudo apt-get install cmake"
    exit 1
fi

if ! command -v g++ &> /dev/null; then
    echo "❌ G++ not found. Install: sudo apt-get install g++"
    exit 1
fi

if ! dpkg -s libncurses-dev &> /dev/null; then
    echo "❌ libncurses-dev not found. Install: sudo apt-get install libncurses-dev"
    exit 1
fi

echo "✓ All dependencies found"
echo

# Build configuration
BUILD_TYPE=${1:-Release}
BUILD_DIR="build"
INSTALL_PREFIX=${INSTALL_PREFIX:-/usr/local}

echo "Build configuration:"
echo "  Type: $BUILD_TYPE"
echo "  Directory: $BUILD_DIR"
echo "  Install prefix: $INSTALL_PREFIX"
echo

# Create build directory
if [ -d "$BUILD_DIR" ]; then
    read -p "Build directory exists. Clean and rebuild? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$BUILD_DIR"
    fi
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
echo "Configuring..."
cmake -DCMAKE_BUILD_TYPE=$BUILD_TYPE \
      -DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX \
      ..

# Build
echo
echo "Building..."
CORES=$(nproc)
make -j$CORES

echo
echo "✓ Build complete!"
echo

# Test
if [ -f "./psminer" ]; then
    echo "Binary size: $(du -h ./psminer | cut -f1)"
    echo "Binary location: $(pwd)/psminer"
    echo
    
    # Show version
    ./psminer --version
    echo
fi

# Offer installation
read -p "Install to $INSTALL_PREFIX/bin? (requires sudo) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo make install
    echo "✓ Installed to $INSTALL_PREFIX/bin/psminer"
    echo
    echo "Run with: psminer -w YOUR_WALLET_ADDRESS"
fi

echo
echo "Build complete! 🎉"
