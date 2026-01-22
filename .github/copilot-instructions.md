# PiSecure AI Coding Assistant Instructions

## Project Overview
PiSecure is a hardware-verified blockchain security framework for Raspberry Pi devices. It provides decentralized security primitives including proof-of-work mining, hardware-bound cryptography, and secure communication protocols. The framework enables developers to build secure, decentralized applications without implementing complex security protocols from scratch.

**CRITICAL DISTINCTION: Mining vs Validation**
- **Mining**: Requires genuine Raspberry Pi hardware (hardware-verified PiHash algorithm)
- **Validation**: Works on ANY platform (Mac, Windows, Linux, Pi) - no hardware restrictions
- **Network Growth Strategy**: Universal validation enables anyone to earn rewards and strengthen the network

## Architecture Overview
- **Core Components**: SignChain (blockchain), HardwareVerifier (Pi verification), SignWallet (token management), P2P networking
- **Service Boundaries**: CLI (`pisecure/cli.py`), REST API (`pisecure/api/server.py`), Web Dashboard (`dashboard/web/app.py`)
- **Data Flow**: Hardware verification → Blockchain operations → Network consensus → API/Web interfaces
- **Why This Structure**: 
  - Hardware-binding for mining prevents spoofing attacks and creates immutable trust anchors
  - Universal validation enables network growth across diverse platforms with validator incentives

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

### Environmental Modes & Configuration
PiSecure uses environment variables and CLI flags to control runtime behavior:

```python
# Environment-based runtime modes (set before creating SignChain)
os.environ['PISECURE_TESTNET'] = '1'        # Use testnet blockchain (separate from mainnet)
os.environ['PISECURE_VALIDATE_ONLY'] = '1'  # Validation-only mode (no hardware verification)
os.environ['PISECURE_MOCK_HARDWARE'] = '1'  # Mock hardware for testing
os.environ['PISECURE_QUIET'] = '1'          # Suppress Rich formatted output

# CLI equivalents
pisecure --testnet --validate-only --quiet status
```

**Mode Implications:**
- **Testnet**: Isolated blockchain in `/var/lib/pisecure-testnet/`, separate from production
- **Validate-Only**: **CRITICAL for network growth** - Enables validation on ANY platform (Mac/Windows/Linux/Pi) without Pi hardware
- **Mock Hardware**: Returns simulated verification data, enables CI/CD testing without Pi hardware

**Universal Validation Design:**
```python
# Validation works on ANY platform - no Pi required
os.environ['PISECURE_VALIDATE_ONLY'] = '1'
blockchain = SignChain()

# All validation operations work universally:
blockchain.validate_chain()                    # ✅ Works everywhere
blockchain.validate_block_challenges()         # ✅ Works everywhere (SHA256 + XOR only)
count_zero_bits(block.hash)                    # ✅ Pure Python, no hardware dependency

# Only mining requires Pi hardware:
blockchain.mine_pending_transactions()         # ❌ Requires Pi hardware (PiHash)
```

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
- **Block Files** (`blk*.dat`): Raw binary blockchain data (1000 blocks per file)
- **SQLite Database** (`index.db`): Block index, UTXO set, transaction metadata
- **Memory Cache**: Frequently accessed data for performance

**CLI Usage:**
```bash
# Uses hybrid storage by default
pisecure status
pisecure mine

# Explicit control
pisecure --hybrid-storage status     # Force hybrid
pisecure --no-hybrid-storage status  # Force JSON
```

### PiHash Algorithm & Hardware Verification
Mining requires PiHash algorithm exclusive to Raspberry Pi hardware:

```python
# PiHash automatically validates hardware during mining
from pisecure.core.pihash import compute_pihash, hash_meets_zero_bits

# Mining includes hardware fingerprint binding
hw_fingerprint = pihash._get_hardware_fingerprint()  # CPU serial, board revision, etc.
mining_hash = compute_pihash(block_data, nonce, hw_fingerprint)
valid_proof = hash_meets_zero_bits(mining_hash, difficulty=146)  # ~146 leading zero bits
```

**Hardware Verification:** Mining operations fail gracefully on non-Pi hardware with clear error messages. Use `PISECURE_MOCK_HARDWARE=1` for testing.

**Entropy Validation Enhancement (Phase 2):**
```python
# Local basic entropy check (existing)
from pisecure.core.hardware import HardwareVerifier
verifier = HardwareVerifier()
basic_valid = verifier._verify_rng_entropy_quality()  # Simple uniqueness check

# Enhanced NIST SP 800-90B validation via bootstrap server (recommended)
from pisecure.core.bootstrap_manager import get_bootstrap_registry
import requests
import time

registry = get_bootstrap_registry()
bootstrap_url = registry.get_active_servers()[0]

# Read 32 bytes from hardware RNG
with open('/dev/hwrng', 'rb') as hwrng:
    entropy_bytes = hwrng.read(32)

# Submit to bootstrap server for NIST validation
response = requests.post(
    f"{bootstrap_url}/api/v1/hardware/entropy",
    json={
        "node_id": verifier.get_hardware_id(),
        "entropy_hex": entropy_bytes.hex(),  # Must be exactly 64 hex chars
        "network": "mainnet",  # or "testnet"
        "timestamp": time.time()
    },
    headers={"Content-Type": "application/json"},
    timeout=10
)

if response.status_code == 200:
    result = response.json()
    # result['validation_result']: True/False
    # result['quality_score']: 0-100 (80+ excellent, 50-79 acceptable, <50 failed)
    # result['entropy_estimate_bits_per_byte']: 4.5+ required
    # result['tests']: {chi_square, runs_test, longest_run}
    # result['reputation_impact']: 0.0 (pass) or -5.0/-10.0 (fail)
elif response.status_code == 429:
    # Rate limited: 100 requests/hour per node
    retry_after = int(response.headers.get('Retry-After', 3600))
elif response.status_code == 403:
    # Node not registered with bootstrap server
    pass
```

**Submission Guidelines:**
- **Frequency**: Every 1-2 hours during mining, every 24 hours when idle
- **Rate Limits**: 100/hour per node, minimum 5 minutes between submissions
- **Endpoints**: 
  - Mainnet: `https://bootstrap.pisecure.org/api/v1/hardware/entropy`
  - Testnet: `https://bootstrap-testnet.pisecure.org/api/v1/hardware/entropy`
- **Fallback**: If bootstrap unreachable, continue mining with local validation only

### Plugin System (Hook-Based Architecture)
PiSecure provides extensible plugin framework with hooks, API endpoints, and CLI commands:

```python
# Load and manage plugins
from pisecure.plugins import PluginManager, PluginInterface, PluginContext

plugin_manager = PluginManager(plugin_dir="/opt/pisecure/plugins")
plugin_manager.register_core_service('blockchain', blockchain)
plugin_manager.load_all_plugins()

# Trigger hooks at key points
plugin_manager.trigger_hook('blockchain.new_block', block_data)
plugin_manager.trigger_hook('wallet.transaction', tx_data)

# Access plugin-provided endpoints
api_endpoints = plugin_manager.get_api_endpoints()  # {'route': handler}
cli_commands = plugin_manager.get_cli_commands()    # {'cmd': handler}
```

**Plugin Template Pattern:**
```python
class MyPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "my_plugin"
    
    def initialize(self, context: PluginContext) -> bool:
        # Register hooks
        context.register_hook('blockchain.new_block', self.on_new_block)
        return True
    
    def get_hooks(self) -> Dict[str, Callable]:
        return {'blockchain.new_block': self.on_new_block}
    
    def get_api_endpoints(self) -> Dict[str, Callable]:
        return {'/api/myplugin': self.api_handler}
```

### Token Economics (314ST)
Advanced tokenomics system controls API access and developer trust funds:

```python
# Token economics configuration
from pisecure.api.economics import TokenEconomics, TrustType, TrustVisibility

economics = TokenEconomics()

# Different trust models for API access control
trust_models = {
    'public': TrustType.PUBLIC,              # Developer pays for all access
    'subscriber_all': TrustType.SUBSCRIBER_ALL,  # All subscribers pay equally
    'subscriber_individual': TrustType.SUBSCRIBER_INDIVIDUAL,  # Per-user costs
    'hybrid': TrustType.HYBRID               # Mix of free and paid
}

# Fee distribution across stakeholders
fee_distributor.distribute_mining_reward(block_reward)
foundation_trust.allocate_governance_fund()
```

**API Access:** `/api/wallet/balance` and transaction endpoints respect 314ST token limits configured per trust fund.

### Wallet Operations
Web wallet at `/wallets` with balance checking and transaction history:

```python
# Balance checking (uses hybrid storage UTXO set)
balance = blockchain.get_wallet_balance(wallet_address)

# Transaction history (uses hybrid storage indexes)
transactions = blockchain.get_wallet_transactions(wallet_address)

# Token transfers with cryptographic signing
from pisecure.core.wallet import SignWallet
wallet = SignWallet(private_key_pem, public_key_pem)
signed_tx = wallet.create_token_transfer(recipient, amount)
blockchain.add_transaction(signed_tx)
```

**API Endpoints:**
- `GET /api/wallet/balance?wallet_id=<address>` - Get wallet balance
- `GET /api/wallet/transactions?wallet_id=<address>&limit=20` - Get transaction history
- `POST /api/wallet/transfer` - Submit signed transfer transaction

### Network Operations & P2P Synchronization
Network discovery and peer synchronization via P2PSyncManager:

```python
# Peer discovery (automatic with bootstrap peers)
from pisecure.network.discovery import PeerDiscovery
discovery = PeerDiscovery(bootstrap_peers=['peer1.example.com:3142'])
peers = discovery.discover_peers()  # Returns list of (host, port) tuples

# P2P synchronization with conflict resolution
from pisecure.core.p2p_sync import P2PSyncManager
sync_manager = P2PSyncManager(blockchain, discovery)
sync_manager.start_sync()  # Continuously syncs with peers

# Transaction broadcasting
blockchain.broadcast_transaction(tx, exclude_peers=[originating_peer])
```

**Important Constraints:**
- P2P discovery may fail in restricted networks (NAT traversal built-in)
- WebSocket connections need CORS handling (enabled in API server by default)
- Rate limiting essential for API endpoints (`flask_limiter` configured)
- Network health checks: `blockchain.get_chain_info()['network_health']`

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
# Mock hardware for testing (critical for non-Pi environments)
PISECURE_MOCK_HARDWARE=1 pytest

# Testnet testing (isolated blockchain)
PISECURE_TESTNET=1 pytest

# Unit vs integration tests
pytest tests/unit/
pytest tests/integration/

# With coverage reporting
pytest --cov=pisecure --cov-report=html
```

**Test Patterns:**
- Use `PISECURE_MOCK_HARDWARE=1` for CI/CD without physical Pi hardware
- Use `PISECURE_TESTNET=1` to avoid modifying main blockchain during tests
- Hardware verification tests require mocking unless running on actual Pi
- Transaction validation tests should cover both valid and invalid signatures

### Documentation
- Docstrings required for all public functions
- Examples in `examples/` directory showing real usage patterns
- API docs built with Sphinx
- Key architectural decisions documented in `docs/README.md`

### Security Considerations
- Hardware verification mandatory for mining (graceful failures on non-Pi)
- Cryptographic signatures on all transactions (RSA with PSS padding)
- Input validation on all API endpoints (use `ValidationError` class)
- No secrets in configuration files (read from environment variables)
- Rate limiting on API endpoints via `@limiter.limit()` decorator
- Audit logging for security events via `log_security_event()`

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

### Bootstrap Server Integration
PiSecure integrates with the separate **PiSecure-Bootstrap** repository (`https://github.com/UnderhillForge/PiSecure-Bootstrap`):

**Bootstrap Server Features (External Repository):**
- **EntropyValidator Class**: Full NIST SP 800-90B test suite for hardware RNG quality
  - Chi-Square Test: Validates uniform byte distribution
  - Runs Test: Detects non-random bit patterns
  - Longest Run Test: Identifies abnormal consecutive runs
  - Shannon Entropy: Measures randomness quality (bits/byte)
  - Quality Scoring: 0-100 score based on all test results
- **NodeTracker**: Per-node submission history and entropy quality stats
  - `entropy_quality_score` and `entropy_verified` fields
  - Methods: `update_entropy_quality()`, `get_entropy_quality()`
- **Sentinel**: Reputation system with incident tracking
  - `record_incident()` method for entropy violations
  - Automatic reputation adjustments (-10 points for low entropy)
  - Network standing updates (quarantine/blacklist)

**Client-Side Integration (This Repository):**
```python
# Bootstrap registry management
from pisecure.core.bootstrap_manager import BootstrapRegistry, get_bootstrap_registry

registry = get_bootstrap_registry()
bootstrap_servers = registry.get_active_servers()

# Entropy submission (to bootstrap server's POST /api/v1/hardware/entropy)
import secrets
entropy_sample = secrets.token_hex(32)  # 32-byte entropy as hex
response = requests.post(
    f"{bootstrap_url}/api/v1/hardware/entropy",
    json={"entropy": entropy_sample, "node_id": node_id}
)

# Response includes detailed test breakdowns and reputation impact
validation_result = response.json()
# {
#   "valid": true/false,
#   "quality_score": 0-100,
#   "tests": {
#     "chi_square": {...},
#     "runs_test": {...},
#     "longest_run": {...},
#     "shannon_entropy": {...}
#   },
#   "reputation_impact": 0 or -10
# }
```

**Important Separation:**
- Bootstrap servers run separately (centralized or distributed)
- PiSecure nodes connect to bootstrap servers for:
  - Peer discovery
  - Network health reporting
  - Entropy validation (hardware verification)
  - Reputation tracking
- Nodes can operate without bootstrap servers (P2P discovery fallback)

## Key Files for Understanding
- `pisecure/core/blockchain.py` - Core blockchain logic
- `pisecure/core/hardware.py` - Pi verification system
- `pisecure/cli.py` - Command-line interface
- `pisecure/api/server.py` - REST API implementation
- `dashboard/web/app.py` - Web dashboard
- `examples/basic_mining.py` - Usage patterns
- `install.sh` - Complete setup process