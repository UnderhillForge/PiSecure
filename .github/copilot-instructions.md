# PiSecure AI Coding Assistant Instructions

## Project Overview
PiSecure is a hardware-verified blockchain security framework for Raspberry Pi devices. It provides decentralized security primitives including proof-of-work mining, hardware-bound cryptography, and secure communication protocols. The framework enables developers to build secure, decentralized applications without implementing complex security protocols from scratch.

## Architecture Overview
- **Core Components**: SignChain (blockchain), HardwareVerifier (Pi verification), SignWallet (token management), P2P networking
- **Service Boundaries**: CLI (`pisecure/cli.py`), REST API (`pisecure/api/server.py`), Web Dashboard (`dashboard/web/app.py`)
- **Data Flow**: Hardware verification → Blockchain operations → Network consensus → API/Web interfaces
- **Why This Structure**: Hardware-binding ensures cryptographic operations run on genuine Raspberry Pi hardware, preventing spoofing attacks and creating immutable trust anchors

## Critical Developer Workflows

### Installation & Setup
```bash
# Full node installation (includes wallet, mining, API, dashboard)
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash

# Development setup
make install-dev  # Installs with dev dependencies
pip install -e ".[full]"  # All optional dependencies
```

### Development Commands
```bash
make test          # Run all tests
make test-cov      # Tests with coverage
make lint          # Code quality checks
make format        # Auto-format code
make docs          # Build documentation
```

### Runtime Operations
```bash
pisecure status           # Blockchain/network status
pisecure mine             # Start mining (hardware verified)
pisecure wallet           # Wallet operations
python mining-console.py  # Interactive mining
python dashboard/web/app.py  # Start web dashboard
```

## Project-Specific Patterns

### Hybrid Storage System
PiSecure uses a scalable hybrid storage architecture by default (inspired by Bitcoin Core):

```python
# Hybrid storage is enabled by default
from pisecure.core import SignChain
blockchain = SignChain()  # Uses hybrid storage automatically

# Explicit control if needed
blockchain = SignChain(use_hybrid_storage=True)   # Force hybrid
blockchain = SignChain(use_hybrid_storage=False)  # Force JSON only
```

**Storage Components:**
- **Block Files** (`blk*.dat`): Raw binary blockchain data
- **SQLite Database** (`index.db`): Block index, UTXO set, metadata
- **Memory Cache**: Frequently accessed data

**CLI Usage:**
```bash
# Uses hybrid storage by default
pisecure status
pisecure mine

# Explicit control
pisecure --hybrid-storage status     # Force hybrid
pisecure --no-hybrid-storage status  # Force JSON
```

### Wallet Operations
Web wallet at `/wallets` with balance checking and transaction history:

```python
# Balance checking (uses hybrid storage UTXO set)
balance = blockchain.get_wallet_balance(wallet_address)

# Transaction history (uses hybrid storage indexes)
transactions = blockchain.get_wallet_transactions(wallet_address)
```

**API Endpoints:**
- `GET /api/wallet/balance?wallet_id=<address>` - Get wallet balance
- `GET /api/wallet/transactions?wallet_id=<address>&limit=20` - Get transaction history

### File System Conventions
- **Blockchain data**: `/var/lib/pisecure/blockchain.json`
- **Pending transactions**: `/var/lib/pisecure/pending_transactions.json`
- **Configuration**: `/etc/pisecure/config.json`
- **Logs**: Standard logging to console/files

### Import Patterns
```python
# Core functionality
from pisecure.core import SignChain, HardwareVerifier, SignWallet

# Relative imports within package
from .core.blockchain import SignChain
from ..api.server import BlockchainAPI
```

### Error Handling
```python
try:
    blockchain = SignChain()
    # Operations that may fail
except FileNotFoundError:
    # Handle missing blockchain file
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
```

## Integration Points

### REST API Endpoints
- `GET /api/v1/chain` - Blockchain status
- `POST /api/v1/transactions` - Submit transactions
- `GET /api/v1/wallet/{address}/balance` - Wallet balance
- `WebSocket /api/v1/stream` - Real-time updates

### Client Libraries
Multi-language support in `clients/` directory:
- `clients/python/` - Python SDK
- `clients/c/`, `clients/go/`, `clients/rust/` - System languages
- `clients/javascript/` - Web integration

### External Dependencies
- **IPFS**: Optional distributed storage (`ipfshttpclient`)
- **MQTT**: IoT messaging (`paho-mqtt`)
- **TPM**: Hardware security modules (`tpm2-pytss`)
- **GPIO**: Hardware control (`RPi.GPIO`, `gpiozero`)

## Code Quality Standards

### Testing
```bash
# Mock hardware for testing
PISECURE_MOCK_HARDWARE=1 pytest

# Unit vs integration tests
pytest tests/unit/
pytest tests/integration/
```

### Documentation
- Docstrings required for all public functions
- Examples in `examples/` directory
- API docs built with Sphinx

### Security Considerations
- Hardware verification mandatory for mining
- Cryptographic signatures on all transactions
- Input validation on all API endpoints
- No secrets in configuration files

## Common Pitfalls

### Hardware Assumptions
- Code must work on all Pi models (Zero to 5)
- Hardware verification failures should be graceful
- GPIO access requires proper permissions

### File Permissions
- Blockchain files need write access for mining
- Configuration in `/etc/pisecure/` requires sudo
- Virtual environment isolation critical

### Network Operations
- P2P discovery may fail in restricted networks
- WebSocket connections need CORS handling
- Rate limiting essential for API endpoints

## Key Files for Understanding
- `pisecure/core/blockchain.py` - Core blockchain logic
- `pisecure/core/hardware.py` - Pi verification system
- `pisecure/cli.py` - Command-line interface
- `pisecure/api/server.py` - REST API implementation
- `dashboard/web/app.py` - Web dashboard
- `examples/basic_mining.py` - Usage patterns
- `install.sh` - Complete setup process