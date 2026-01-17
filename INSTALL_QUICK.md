# PiSecure Installation Quick Reference

## One-Line Install Commands

### Production (Recommended)
```bash
pip install "git+https://github.com/UnderhillForge/PiSecure.git#egg=pisecure[full,native]"
```
**Includes:** Everything + 5-10x mining speedup

### Basic
```bash
pip install git+https://github.com/UnderhillForge/PiSecure.git
```
**Includes:** Core functionality only

### From Local Source
```bash
# Clone and install
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure
pip install ".[full,native]"
```

### Development
```bash
pip install -e ".[dev,native]"  # Editable install with dev tools
```

## Feature Sets

| Extra | Includes | Use Case |
|-------|----------|----------|
| `[native]` | Cython extensions | 5-10x faster mining |
| `[hardware]` | GPIO, Pi-specific | Raspberry Pi deployment |
| `[ipfs]` | IPFS client | Distributed storage |
| `[tpm]` | TPM support | Hardware security |
| `[mqtt]` | MQTT client | IoT integration |
| `[full]` | All above (except dev) | Production deployment |
| `[dev]` | Testing, linting tools | Development |

## Combining Features

```bash
# Custom combinations
pip install ".[native,ipfs]"           # Native + IPFS
pip install ".[full,dev]"              # Everything + dev tools
pip install ".[hardware,mqtt,native]"  # IoT + performance
```

## Quick Start After Install

```bash
pisecure --version        # Check installation
pisecure status           # Initialize blockchain
pisecure wallet          # Create wallet
pisecure mine            # Start mining
```

## Verification

```bash
# Check native extensions
python -c "from pisecure.core import pihash; print('Native:', pihash.NATIVE_AVAILABLE)"

# Run tests
pip install ".[dev]"
pytest tests/
```

## Troubleshooting

### Build tools missing
```bash
sudo apt-get install build-essential python3-dev
```

### Import errors
```bash
python3 -m pip install --upgrade pip setuptools wheel
```

### Native build failed
Installation will work but mining will be slower. To fix:
```bash
pip install --force-reinstall ".[native]"
```

## Support

- Full docs: [INSTALL.md](INSTALL.md)
- Issues: https://github.com/UnderhillForge/PiSecure/issues
