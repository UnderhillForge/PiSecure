#!/bin/bash
# Build script for psvalidator

set -e

echo "Building psvalidator..."
echo "======================"

cd "$(dirname "$0")"

# Create build directory
mkdir -p build
cd build

# Configure
echo "Configuring..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
echo "Building..."
make -j$(nproc)

echo ""
echo "✓ Build complete!"
echo ""
echo "Executable: $(pwd)/psvalidator"
echo ""
echo "To install system-wide:"
echo "  sudo make install"
echo ""
echo "To test:"
echo "  ./psvalidator --help"
echo "  ./psvalidator --wallet YOUR_WALLET_ADDRESS"
echo ""
