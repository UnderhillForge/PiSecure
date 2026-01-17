# PiSecure Layer-to-File Mapping

Quick reference showing which files implement each architectural layer.

## Layer 0: Hardware Foundation

```
pisecure/core/
├── hardware.py          - Raspberry Pi hardware detection & verification
├── pihash.py           - PiHash mining algorithm (Argon2id-inspired)
└── monitoring.py       - System health, temperature, CPU monitoring
```

**Key Classes:**
- `PiHardwareVerifier` - Hardware capability verification
- `PiHash` - Hardware-verified mining algorithm
- `SystemMonitor` - Hardware health monitoring

## Layer 1: Consensus & Blockchain Core

```
pisecure/core/
├── blockchain.py       - Core blockchain, blocks, transactions
├── consensus.py        - PoW consensus, mining syndicates
├── difficulty_manager.py - Dynamic difficulty adjustment
├── syndicate.py        - Mining pool coordination
├── storage.py          - Hybrid storage (blocks + SQLite)
└── validation.py       - Block and transaction validation
```

**Key Classes:**
- `SignChain` - Main blockchain class
- `SignBlock` - Block structure
- `ConsensusEngine` - PoW coordination
- `MiningSyndicate` - Pool mining
- `HybridBlockchainStorage` - Scalable storage

## Layer 2: Token Economy & DeFi

```
pisecure/core/
├── tokens.py           - 314ST token implementation
├── token_economics.py  - Supply model, rewards, halving
├── dex.py             - Decentralized exchange, AMM
├── market_data.py     - Price feeds, trading data
└── validator_rewards.py - Mining reward calculations
```

**Key Classes:**
- `SignToken` - 314ST token
- `PiSecureDEX` - Trading platform
- `LiquidityPool` - AMM pools
- `MarketDataEngine` - Price tracking

## Layer 3: Smart Contract Primitives

```
pisecure/core/
├── custody.py          - Multi-sig, escrow, time-locks
├── compliance.py       - KYC/AML, regulations
└── iot_security.py     - Oracle contracts, device trust
```

**Key Classes:**
- `CustodyService` - Custody contracts
- `ComplianceEngine` - Regulatory compliance
- `DeviceOracle` - IoT oracles
- `IoTEnhancedSecurity` - Risk-based security

## Layer 4: Application Services

```
pisecure/api/
├── server.py           - REST API server (Flask)
├── client.py           - Python SDK
├── async_client.py     - Async Python client
├── validation.py       - Input validation
└── economics.py        - Economic calculations

pisecure/
└── cli.py             - Command-line interface

clients/
├── javascript/        - JS/TS SDK
├── go/               - Go client
├── rust/             - Rust client
├── c/                - C library
├── cpp/              - C++ client
└── android/          - Android SDK
```

**Key Classes:**
- `BlockchainAPI` - REST API
- `PiSecureClient` - Python client
- `cli` - CLI commands

## Layer 5: IoT Integration

```
pisecure/core/
├── iot_security.py     - Device integration
└── network.py          - IoT networking

pisecure/plugins/
└── iot_integration.py  - IoT device plugins
```

**Key Classes:**
- `IoTEnhancedSecurity` - IoT security layer
- `DeviceNetwork` - Device coordination
- `DeviceOracle` - Sensor data aggregation

## Layer 6: Network & P2P

```
pisecure/core/
├── p2p_protocol.py     - P2P messaging protocol
├── p2p_sync.py         - Blockchain synchronization
├── bootstrap_manager.py - Bootstrap server discovery
└── nat_traversal.py    - NAT/firewall traversal

pisecure/network/
└── discovery.py        - Peer discovery
```

**Key Classes:**
- `PiSecureP2P` - P2P protocol
- `P2PSyncManager` - Chain sync
- `BootstrapRegistry` - Server discovery
- `PeerDiscovery` - Peer finding

## Layer 7: Security & Monitoring

```
pisecure/api/
├── ddos_protection.py  - DDoS mitigation
└── audit_logger.py     - HMAC-verified logging

pisecure/core/
└── monitoring.py       - System monitoring

pisecure/updates/
├── ota_updater.py      - Secure updates
└── signature_verification.py - Update verification
```

**Key Classes:**
- `DDoSProtection` - Attack prevention
- `AuditLogger` - Tamper-proof logs
- `SystemMonitor` - Health checks
- `OTAUpdater` - Secure updates

## Supporting Components

### Identity & Authentication
```
pisecure/identity/
├── device_identity.py  - Device fingerprinting
└── device_authenticator.py - Authentication
```

### Access Control
```
pisecure/access/
└── access_control.py   - Authorization
```

### Payments
```
pisecure/payments/
└── payment_processor.py - Payment handling
```

### Web Dashboard
```
dashboard/web/
├── app.py             - Full web dashboard
├── minimal_dashboard.py - Lightweight UI
├── templates/         - HTML templates
└── static/           - CSS, JS, images
```

## File Count by Category

| Category | Files | Lines of Code* |
|----------|-------|----------------|
| Core Blockchain | 15 | ~8,000 |
| API & Services | 10 | ~5,000 |
| Networking | 8 | ~3,000 |
| Security | 6 | ~2,000 |
| Client SDKs | 7 | ~4,000 |
| Testing | 12 | ~2,500 |
| Documentation | 20+ | N/A |
| **Total** | **78+** | **~24,500** |

*Approximate

## Module Dependencies

```
Layer 7 (Security)
    ↓
Layer 6 (Network) ──→ Layer 4 (API)
    ↓                      ↓
Layer 5 (IoT) ────────────┘
    ↓
Layer 3 (Contracts)
    ↓
Layer 2 (DeFi)
    ↓
Layer 1 (Blockchain)
    ↓
Layer 0 (Hardware)
```

## Import Hierarchy

```python
# Layer 0 - No dependencies
from pisecure.core.hardware import PiHardwareVerifier
from pisecure.core.pihash import PiHash

# Layer 1 - Depends on Layer 0
from pisecure.core.blockchain import SignChain, SignBlock
from pisecure.core.storage import HybridBlockchainStorage

# Layer 2 - Depends on Layer 1
from pisecure.core.dex import PiSecureDEX
from pisecure.core.tokens import SignToken

# Layer 3 - Depends on Layers 1-2
from pisecure.core.custody import CustodyService
from pisecure.core.iot_security import DeviceOracle

# Layer 4 - Depends on Layers 1-3
from pisecure.api.server import BlockchainAPI
from pisecure.api.client import PiSecureClient

# Layer 5 - Depends on Layers 1, 3-4
from pisecure.core.iot_security import IoTEnhancedSecurity

# Layer 6 - Depends on Layer 1
from pisecure.core.p2p_protocol import PiSecureP2P
from pisecure.network.discovery import PeerDiscovery

# Layer 7 - Depends on Layer 4
from pisecure.api.ddos_protection import DDoSProtection
from pisecure.api.audit_logger import AuditLogger
```

## Entry Points

### Command Line Interface
```bash
pisecure <command>
```
Entry: `pisecure/cli.py`

### API Server
```bash
pisecure server
python -m pisecure.api.server
```
Entry: `pisecure/api/server.py`

### Web Dashboard
```bash
python dashboard/web/app.py
```
Entry: `dashboard/web/app.py`

### Python Library
```python
from pisecure.core import SignChain
blockchain = SignChain()
```
Entry: `pisecure/__init__.py`

## Configuration Files

```
/etc/pisecure/
├── config.json          - Main configuration
├── config-testnet.json  - Testnet configuration
└── peers.json          - Known peer list

/var/lib/pisecure/
├── blockchain.json      - JSON blockchain (legacy)
├── pending_transactions.json - Mempool
├── name_registry.json   - Name registry
├── blk*.dat            - Block files (hybrid storage)
├── pisecure.db         - SQLite index (hybrid storage)
└── wallets/            - Wallet storage
    └── *.json          - Individual wallets

/var/lib/pisecure-testnet/
└── (same structure)     - Testnet data
```

## See Also

- [Blockchain Architecture](blockchain-architecture.md) - Detailed layer descriptions
- [Architecture Diagrams](architecture-diagrams.md) - Visual representations
- [API Documentation](api-documentation.txt) - REST API reference
- [Getting Started](getting-started.md) - Setup guide
