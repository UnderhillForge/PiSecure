# Getting Started with PiSecure

## Installation

### Prerequisites

- **Hardware**: Raspberry Pi 4 or 5 (hardware verification required)
- **OS**: Raspberry Pi OS (64-bit recommended) or Ubuntu/Debian
- **Python**: 3.7 or higher

### Install from Source

```bash
# Clone the repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Create virtual environment (recommended)
python3 -m venv pisecure-env
source pisecure-env/bin/activate

# Install PiSecure
pip install -e .

# Verify installation
pisecure --version
```

### Install from PyPI (when available)

```bash
pip install pisecure
```

## Quick Start

### 1. Verify Hardware

First, verify your Raspberry Pi hardware:

```bash
pisecure verify-hardware
```

You should see output like:
```
🔍 Running hardware verification...

✓ cpu_serial: True (required) (weight: 0.25)
✓ videocore_gpu: True (required) (weight: 0.2)
✓ mailbox_interface: True (optional) (weight: 0.15)
✓ chip_identification: True (optional) (weight: 0.1)
✗ otp_registers: False (optional) (weight: 0.1)
    Error: OTP register verification failed
Score: 0.70/1.00 = 0.70 confidence
Required: 2/2 passed
Overall result: PASSED
Detected hardware: Raspberry Pi 5 Model B Rev 1.1

✅ Hardware verification PASSED!
📱 Device: Raspberry Pi 5 Model B Rev 1.1
🎯 Confidence: 70.0%
🔒 Anti-spoofing: ✅

🚀 This device can mine PiSecure tokens!
```

### 2. Create Test Transactions

Create some test transactions to mine:

```bash
pisecure create-tx --count 5
```

### 3. Start Mining

Start interactive mining:

```bash
pisecure mine
```

You'll see real-time mining progress and block discoveries.

### 4. Check Status

View blockchain status anytime:

```bash
pisecure status
```

## Basic Usage Examples

### Device Identity
```bash
pisecure identity
```

### Wallet Management
```bash
# Show wallet overview
pisecure wallet

# Show specific token
pisecure wallet 314ST-ABC123-1234567890
```

### Export/Import Wallet
```bash
# Export wallet
pisecure export-wallet backup.json

# Import wallet
pisecure import-wallet backup.json
```

## Development Setup

For contributors and developers:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black pisecure/
flake8 pisecure/

# Build documentation
cd docs
make html
```

## Troubleshooting

### Hardware Verification Fails

**Problem**: `Hardware verification FAILED`

**Solutions**:
- Ensure you're running on genuine Raspberry Pi hardware
- Check that `/dev/hwrng`, `/dev/gpiomem`, and `/dev/vcio` are accessible
- Try running with `sudo` if permission errors occur

### Mining Won't Start

**Problem**: `Mining blocked - hardware verification failed`

**Solutions**:
- Run `pisecure verify-hardware` first
- Ensure VideoCore GPU is accessible (`vcgencmd version`)
- Check CPU serial access in `/proc/cpuinfo`

### Permission Errors

**Problem**: `Permission denied` on device files

**Solution**: Add user to required groups:
```bash
sudo usermod -a -G gpio,video,i2c $USER
# Logout and login again for group changes to take effect
```

### Import Errors

**Problem**: `ModuleNotFoundError`

**Solutions**:
- Ensure PiSecure is installed: `pip install -e .`
- Check Python path: `python -c "import pisecure"`
- Use virtual environment if issues persist

## Next Steps

- Read the [API Reference](api-reference.md) for detailed class documentation
- Explore [Examples](../examples/) for sample applications
- Learn about [Security Model](security-model.md) for advanced features
- Check [Node Types](node-types.md) for different client configurations