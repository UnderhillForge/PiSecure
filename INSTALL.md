# PiSecure Installation Guide

Complete installation guide for PiSecure on Raspberry Pi and other systems.

## Quick Install (One Line)

### Basic Installation
```bash
pip install git+https://github.com/UnderhillForge/PiSecure.git
```

### Full Production Install (Recommended for Pi)
```bash
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,native]"
```

This installs:
- ✅ Core PiSecure framework
- ✅ Native acceleration (5-10x mining speedup)
- ✅ All hardware integrations (GPIO, TPM, etc.)
- ✅ IPFS distributed storage
- ✅ MQTT IoT messaging

## Installation Options

### 1. Minimal Install (Core Only)
```bash
pip install git+https://github.com/UnderhillForge/PiSecure.git
```
- Core blockchain functionality
- CLI tools
- API server
- No hardware-specific features

### 2. With Native Acceleration (5-10x Faster Mining)
```bash
# Install build dependencies first
sudo apt-get install build-essential python3-dev

# Install with native extensions
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[native]"
```

### 3. Full Feature Set
```bash
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full]"
```
Includes: GPIO, TPM, IPFS, MQTT

### 4. Development Environment
```bash
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[dev]"
```
Includes: pytest, black, mypy, jupyter, etc.

### 5. Custom Combinations
```bash
# Native + IPFS only
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[native,ipfs]"

# Full + Development
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,dev]"
```

## Local Development Installation

### From Source
```bash
# Clone repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Create virtual environment
python3 -m venv pisecure_env
source pisecure_env/bin/activate

# Basic install (editable)
pip install -e .

# Or with all features
pip install -e ".[full,native,dev]"
```

### Building Native Extensions Separately
```bash
# After pip install
python pisecure/core/build_pihash_native.py

# Or using make
make -f Makefile.native build-native
```

## System Requirements

### Minimum
- Python 3.7+
- 1GB RAM
- 500MB disk space
- Linux (any architecture)

### Recommended (Raspberry Pi)
- Raspberry Pi 3/4/5
- Python 3.9+
- 2GB+ RAM
- 2GB+ disk space
- Raspberry Pi OS (Bullseye or newer)

### For Native Extensions
```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    make
```

## Platform-Specific Instructions

### Raspberry Pi OS

#### Full Install (Recommended)
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    build-essential \
    python3-dev \
    git

# Install PiSecure with all features
pip3 install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,native]"

# Verify installation
pisecure --version
pisecure status
```

#### Using the Install Script
```bash
# One-command install (includes everything)
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash
```

### Ubuntu/Debian (x86/ARM)
```bash
sudo apt-get update
sudo apt-get install -y python3-pip build-essential python3-dev
pip3 install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[native]"
```

### macOS (Development/Testing Only)
```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install PiSecure (hardware features won't work)
pip3 install git+https://github.com/UnderhillForge/PiSecure.git
```

### Docker
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install PiSecure
RUN pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,native]"

# Set environment
ENV PISECURE_DATA_DIR=/var/lib/pisecure

# Start API server
CMD ["python", "-m", "pisecure.api.server"]
```

## Verification

### Check Installation
```bash
# Check version
pisecure --version

# Check status
pisecure status

# Check native acceleration
python -c "from pisecure.core import pihash; print('Native:', pihash.NATIVE_AVAILABLE)"
```

### Run Tests
```bash
# Install dev dependencies
pip install ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=pisecure
```

## Troubleshooting

### Import Error: No module named 'pisecure'
```bash
# Ensure pip installed to correct Python version
python3 -m pip install git+https://github.com/UnderhillForge/PiSecure.git
```

### Native Extensions Failed to Build
```bash
# Install build tools
sudo apt-get install build-essential python3-dev

# Try rebuilding
pip install --force-reinstall --no-cache-dir ".[native]"
```

### Permission Denied (GPIO/Hardware)
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Re-login for changes to take effect
```

### Low Memory Issues (Pi Zero)
```bash
# Install without native extensions
pip install git+https://github.com/UnderhillForge/PiSecure.git

# Or reduce memory usage
export PISECURE_LOW_MEMORY=1
```

## Upgrading

### Upgrade to Latest Version
```bash
pip install --upgrade git+https://github.com/UnderhillForge/PiSecure.git
```

### Upgrade with New Features
```bash
pip install --upgrade "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,native]"
```

### Rebuild Native Extensions
```bash
python pisecure/core/build_pihash_native.py
```

## Uninstalling

```bash
# Remove package
pip uninstall pisecure

# Remove data (optional)
sudo rm -rf /var/lib/pisecure
sudo rm -rf /etc/pisecure
```

## Next Steps

After installation:

1. **Initialize blockchain**: `pisecure status`
2. **Create wallet**: `pisecure wallet`
3. **Start mining**: `pisecure mine`
4. **Start API server**: `python -m pisecure.api.server`
5. **Start dashboard**: `python dashboard/web/app.py`

For more information, see:
- [README.md](README.md) - Overview and features
- [docs/getting-started.md](docs/getting-started.md) - Usage guide
- [docs/native-acceleration.md](docs/native-acceleration.md) - Native extensions

## Support

- **Documentation**: https://github.com/UnderhillForge/PiSecure
- **Issues**: https://github.com/UnderhillForge/PiSecure/issues
- **Discussions**: https://github.com/UnderhillForge/PiSecure/discussions
