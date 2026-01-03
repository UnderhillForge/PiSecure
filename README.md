# PiSecure

**Hardware-Verified Blockchain Security for IoT & Embedded Systems**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Version 0.1.1](https://img.shields.io/badge/version-0.1.1-green.svg)](https://github.com/UnderhillForge/PiSecure/releases)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2B%20%26%205-red.svg)](https://www.raspberrypi.org/)

**PiSecure gives developers the power to build secure, decentralized IoT networks and embedded applications with hardware-verified cryptography and blockchain consensus - without implementing complex security protocols from scratch.**

## What Makes PiSecure Revolutionary

Traditional IoT security relies on centralized cloud services and certificate authorities that create single points of failure. PiSecure eliminates this by **cryptographically binding security to your Raspberry Pi's unique hardware fingerprint**, creating an immutable trust anchor that software alone cannot compromise.

This hardware-verification enables true peer-to-peer trust - devices authenticate each other directly, creating networks resilient to attacks, censorship, and infrastructure failures. Whether you're building distributed sensor networks, secure communication systems, or token-gated applications, PiSecure provides production-ready security primitives that scale.

## ⚡ Quick Start

```bash
# Install everything automatically
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash

# Access your secure node at http://localhost:5000
```

## 🚀 Key Features

- **Hardware-Verified Mining**: Earn tokens while securing the network through Raspberry Pi-exclusive proof-of-work
- **Enterprise Security**: Input validation, rate limiting, comprehensive monitoring
- **Multi-Language SDKs**: Python, JavaScript/TypeScript, Go, Rust, C/C++, Android
- **Hybrid Storage**: Bitcoin Core-inspired architecture with 90%+ performance gains
- **Real-Time Monitoring**: Live dashboards with health checks and performance metrics
- **Secure OTA Updates**: Cryptographically verified over-the-air updates with rollback
- **Token Economy**: Built-in micropayments and developer incentives
- **REST API**: Full-featured API with WebSocket streaming

## 💡 Perfect For

- **IoT Device Networks**: Secure sensor data sharing with hardware-verified trust
- **Embedded Applications**: Hardware-bound security for resource-constrained devices
- **Distributed Systems**: Decentralized applications without centralized infrastructure
- **Secure Communication**: End-to-end encrypted messaging between devices
- **Token-Gated Services**: Monetize applications with built-in payment systems
- **Edge Computing**: Secure data processing at the network edge

## 🔧 Built For Developers

PiSecure transforms complex security challenges into simple APIs. Instead of spending months implementing cryptography, consensus algorithms, and certificate management, developers get:

- **One-Line Security**: Simple APIs for device authentication and secure communication
- **Hardware-Bound Trust**: Mathematical guarantees backed by Raspberry Pi hardware
- **Production Ready**: Enterprise-grade security with comprehensive monitoring
- **Multi-Platform**: Client libraries for every major programming language

## 📚 Documentation

- **[Detailed Documentation](README_detailed.md)** - Complete installation, API reference, and examples
- **[API Reference](https://pisecure.readthedocs.io/)** - Full API documentation
- **[Examples](examples/)** - Code samples and use cases
- **[Contributing](CONTRIBUTING.md)** - Development guidelines

---

**Ready to build the next generation of secure IoT applications?** [Get started with PiSecure today!](README_detailed.md)

Built with ❤️ for the Raspberry Pi and open-source communities.

## 🚀 Latest Features

### Hybrid Storage Architecture
PiSecure now uses a production-ready hybrid storage system inspired by Bitcoin Core:

- **Block Files + SQLite**: Raw blockchain data in binary `.dat` files with SQLite indexing
- **O(1) Balance Queries**: Instant wallet balance lookups via UTXO set indexing
- **90%+ Performance Gains**: Massive improvements over JSON-based storage
- **Concurrent Access**: Multi-threaded read/write operations
- **Automatic Migration**: Seamless upgrade from JSON to hybrid storage

### Enterprise Security & Validation
Production-grade security features for enterprise deployment:

- **Comprehensive Input Validation**: Type-specific validation for all data types
- **Rate Limiting**: Built-in request rate limiting to prevent abuse
- **Data Sanitization**: Safe string handling and input cleaning
- **Request Authentication**: Optional authentication for API endpoints
- **Security Utils**: Request ID generation and sensitive data hashing

### System Monitoring & Health Checks
Real-time system monitoring with comprehensive health assessment:

- **Real-time Health Monitoring**: Continuous system health assessment with automatic alerts
- **Performance Metrics**: CPU, memory, disk, and network usage tracking with historical data
- **Blockchain Monitoring**: Block height, peer connectivity, and transaction queue monitoring
- **Interactive Dashboard**: Web-based monitoring interface at `/monitoring` with live charts
- **Alert Management**: Configurable thresholds with automatic notifications
- **API Endpoints**: Programmatic access to health status, metrics, and alerts

### Enhanced Web Dashboard
Modern web interface with comprehensive wallet and blockchain management:

- **Wallet Interface**: Real-time balance checking and transaction history with pagination
- **Transaction Explorer**: Searchable transaction history with advanced filtering
- **Blockchain Browser**: Block exploration with transaction details and Merkle proofs
- **System Monitoring**: Live charts and health status indicators
- **Responsive Design**: Mobile-friendly interface optimized for various screen sizes
- **RESTful API**: Complete programmatic access to all dashboard features

### Advanced Mining Console (Textual TUI)
Interactive terminal user interface for mining operations:

- **Real-time Statistics**: Live mining hashrate, accepted/rejected blocks, and earnings
- **System Monitoring**: CPU, memory, temperature, and hardware status
- **Mining Controls**: Start/stop mining with configurable parameters
- **Network Status**: Peer connections, relay server coordination, and network health
- **Activity Log**: Color-coded activity feed with mining events and system notifications
- **Progress Bars**: Visual progress indicators for mining operations and block validation

### Multi-Language Client SDKs
Production-ready client libraries for seamless integration:

- **Python SDK**: Async client with batch operations and WebSocket streaming
- **JavaScript/TypeScript**: NPM package with promise-based API and browser support
- **Go SDK**: High-performance client with goroutine-based operations
- **Rust SDK**: Memory-safe client with zero-cost abstractions
- **C/C++ Libraries**: System-level integration for embedded applications
- **Android SDK**: Mobile client for Android applications

### Comprehensive REST API
Full-featured REST API for blockchain operations:

- **Blockchain Queries**: Block exploration, transaction lookup, and chain statistics
- **Wallet Operations**: Balance checking, transaction history, and fund transfers
- **Network Management**: Peer discovery, network status, and relay coordination
- **Token Economics**: Trust funds, developer incentives, and micropayment systems
- **Update Management**: Secure OTA updates with cryptographic verification
- **WebSocket Streaming**: Real-time blockchain and network event streaming

### Advanced CLI Tools
Command-line interface with comprehensive blockchain management:

- **Blockchain Operations**: Status checking, mining control, and transaction management
- **Wallet Management**: Create wallets, check balances, and transfer funds
- **Network Tools**: Peer discovery, relay configuration, and network diagnostics
- **Update System**: Download, verify, and apply secure updates
- **Plugin System**: Install and manage community plugins
- **Hardware Verification**: Validate Raspberry Pi hardware authenticity

---

## 📦 Installation

### System Requirements

**Hardware:**
- Raspberry Pi 4 or 5 (recommended) or Raspberry Pi Zero 2 W (minimum)
- 8GB microSD card (16GB+ recommended for full node)
- Internet connection for peer discovery and updates

**Software:**
- Raspberry Pi OS (64-bit recommended) or Ubuntu/Debian
- Python 3.7 or higher
- 2GB RAM minimum (4GB+ recommended)
- SQLite 3.0+ (included with Python)

### Dependencies

**Core Dependencies:**
- `cryptography>=41.0.0` - Cryptographic operations
- `PyNaCl>=1.5.0` - Digital signatures and encryption
- `requests>=2.31.0` - HTTP client for API calls
- `click>=8.1.0` - Command-line interface framework
- `rich>=13.0.0` - Rich terminal output
- `textual>=0.41.0` - Terminal user interface framework
- `python-dateutil>=2.8.2` - Date/time utilities

**Optional Dependencies:**
- `RPi.GPIO>=0.7.0` & `gpiozero>=2.0` - Hardware GPIO access
- `ipfshttpclient>=0.8.0` - IPFS distributed storage
- `tpm2-pytss>=1.2.0` - TPM hardware security modules
- `paho-mqtt>=1.6.1` - IoT messaging protocol
- `fastapi>=0.100.0` & `uvicorn>=0.23.0` - Alternative web framework

### Quick Install (Recommended)

For a complete PiSecure node with all features:

```bash
# Download and run the installation script
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash
```

This will install PiSecure with:
- Full blockchain node
- Web dashboard
- Mining console
- All optional dependencies
- Systemd services for auto-startup

### Manual Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure
```

#### 2. Install Python Dependencies
```bash
# Install with all optional dependencies
pip install -e ".[full]"

# Or install minimal version
pip install -e "."

# For development
pip install -e ".[dev]"
```

#### 3. Install System Dependencies (Optional)
```bash
# For enhanced hardware verification
sudo apt-get update
sudo apt-get install -y python3-dev build-essential

# For GPIO hardware control
sudo apt-get install -y python3-rpi.gpio

# For advanced networking features
pip install netifaces
```

### Client SDK Installation

PiSecure provides client libraries for multiple programming languages:

#### Python SDK
```bash
pip install pisecure-client
```

#### JavaScript/TypeScript SDK
```bash
npm install @pisecure/client
# or
yarn add @pisecure/client
```

#### Go SDK
```bash
go get github.com/UnderhillForge/PiSecure/clients/go
```

#### Rust SDK
```bash
cargo add pisecure-client
```

#### C/C++ Libraries
Download from [releases](https://github.com/UnderhillForge/PiSecure/releases) and follow platform-specific instructions.

#### Android SDK
Add to your `build.gradle`:
```gradle
dependencies {
    implementation 'com.underhillforge:pisecure-android:0.1.1'
}
```

### Development Setup

For developers who want to contribute or modify PiSecure:

```bash
# Clone repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Install development dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Build documentation
make docs
```

### Docker Installation

```bash
# Build Docker image
docker build -t pisecure .

# Run PiSecure node
docker run -p 3142:3142 -p 5000:5000 -v pisecure-data:/data pisecure
```

### Post-Installation Setup

#### 1. Initialize Configuration
```bash
# Generate default configuration
pisecure init

# Edit configuration if needed
sudo nano /etc/pisecure/config.json
```

#### 2. Start Services
```bash
# Start blockchain node
sudo systemctl start pisecure-node

# Start web dashboard
sudo systemctl start pisecure-dashboard

# Enable auto-startup
sudo systemctl enable pisecure-node pisecure-dashboard
```

#### 3. Access Interfaces
- **Web Dashboard**: http://localhost:5000
- **Mining Console**: `python mining-console.py`
- **CLI Tools**: `pisecure --help`
- **REST API**: http://localhost:3142/api/v1/

### CLI Commands

PiSecure provides a comprehensive command-line interface:

```bash
# Blockchain operations
pisecure status                    # Show blockchain and system status
pisecure mine --wallet <address>   # Start mining with specific wallet
pisecure create-tx --count 5       # Create test transactions

# Wallet management
pisecure wallet create <name>      # Create a new wallet
pisecure wallet balance <address>  # Check wallet balance
pisecure wallet transfer <from> <to> <amount>  # Transfer funds

# Network operations
pisecure network peers             # List connected peers
pisecure network status            # Show network health

# Update management
pisecure update check              # Check for updates
pisecure update apply <version>    # Apply specific update

# Hardware verification
pisecure verify-hardware           # Verify Raspberry Pi authenticity

# Plugin system
pisecure plugin list               # List installed plugins
pisecure plugin install <file>     # Install plugin from file
```

### REST API Endpoints

PiSecure exposes a comprehensive REST API for integration:

#### Blockchain Operations
```
GET  /api/v1/blockchain/info              # Chain statistics
GET  /api/v1/blockchain/block/<index>     # Get specific block
GET  /api/v1/blockchain/blocks            # List recent blocks
GET  /api/v1/blockchain/transaction/<hash> # Get transaction details
```

#### Wallet Operations
```
GET  /api/v1/wallet/<address>/balance     # Get wallet balance
GET  /api/v1/wallet/<address>/transactions # Get transaction history
POST /api/v1/wallet                       # Create new wallet
POST /api/v1/transaction                  # Submit transaction
```

#### Network Management
```
GET  /api/v1/network/peers                # List network peers
GET  /api/v1/network/status               # Network health status
```

#### System Monitoring
```
GET  /api/v1/health                       # System health check
GET  /api/v1/monitoring/metrics           # Performance metrics
```

#### Token Economics
```
POST /api/v1/trust                        # Create developer trust fund
GET  /api/v1/trust/<id>                   # Get trust fund details
POST /api/v1/trust/<id>/fund              # Fund trust
```

### Configuration Options

PiSecure supports extensive configuration via `/etc/pisecure/config.json`:

```json
{
  "network": {
    "port": 3142,
    "relay_enabled": true,
    "upnp_enabled": true,
    "max_peers": 50
  },
  "mining": {
    "enabled": true,
    "wallet_address": "your_wallet_address",
    "threads": 4
  },
  "storage": {
    "use_hybrid_storage": true,
    "block_file_size": 128,
    "cache_size_mb": 100
  },
  "monitoring": {
    "enabled": true,
    "alert_thresholds": {
      "cpu_percent": 80,
      "memory_percent": 85,
      "disk_percent": 90
    },
    "metrics_retention_days": 30
  },
  "api": {
    "rate_limit": "100 per minute",
    "cors_origins": ["*"],
    "auth_required": false
  }
}
```

### Troubleshooting

#### Common Issues

**Import Errors:**
```bash
# Reinstall dependencies
pip install -e ".[full]" --force-reinstall
```

**Permission Errors:**
```bash
# Fix permissions for blockchain data
sudo chown -R $USER:$USER /var/lib/pisecure
```

**Port Conflicts:**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :3142
sudo netstat -tulpn | grep :5000
```

**Storage Issues:**
```bash
# Check disk space
df -h

# Clean old logs
sudo find /var/log/pisecure -name "*.log" -mtime +7 -delete
```

### Updating PiSecure

```bash
# Update from repository
cd PiSecure
git pull
pip install -e ".[full]"

# Restart services
sudo systemctl restart pisecure-node pisecure-dashboard
```

### Getting Help

- **Documentation**: [README_detailed.md](README_detailed.md)
- **API Reference**: [PiSecure Docs](https://pisecure.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/UnderhillForge/PiSecure/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UnderhillForge/PiSecure/discussions)

---

## 🔧 Client SDKs & Integration

PiSecure provides production-ready client libraries for seamless integration into your applications.

### Python SDK

```python
from pisecure import PiSecureClient

# Initialize client
client = PiSecureClient(base_url="http://localhost:3142")

# Get blockchain info
info = await client.get_blockchain_info()
print(f"Current block height: {info['blocks']}")

# Check wallet balance
balance = await client.get_wallet_balance("wallet_address")
print(f"Balance: {balance} PSC")

# Submit transaction
tx = await client.submit_transaction({
    "recipient": "recipient_address",
    "amount": 10.0,
    "data": {"message": "Payment for services"}
})
print(f"Transaction hash: {tx['hash']}")
```

### JavaScript/TypeScript SDK

```javascript
import { PiSecureClient } from '@pisecure/client';

const client = new PiSecureClient('http://localhost:3142');

// Get blockchain info
const info = await client.getBlockchainInfo();
console.log(`Current block height: ${info.blocks}`);

// Real-time updates
client.on('newBlock', (block) => {
    console.log('New block mined:', block.index);
});

// Wallet operations
const balance = await client.getWalletBalance('wallet_address');
const tx = await client.submitTransaction({
    recipient: 'recipient_address',
    amount: 10.0
});
```

### Go SDK

```go
package main

import (
    "fmt"
    "log"
    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    client := pisecure.NewClient("http://localhost:3142")

    // Get blockchain info
    info, err := client.GetBlockchainInfo()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Blocks: %d\n", info.Blocks)

    // Wallet operations
    balance, err := client.GetWalletBalance("wallet_address")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Balance: %.2f PSC\n", balance)
}
```

### Rust SDK

```rust
use pisecure_client::PiSecureClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = PiSecureClient::new("http://localhost:3142")?;

    // Get blockchain info
    let info = client.get_blockchain_info().await?;
    println!("Blocks: {}", info.blocks);

    // Wallet operations
    let balance = client.get_wallet_balance("wallet_address").await?;
    println!("Balance: {} PSC", balance);

    Ok(())
}
```

### C/C++ Integration

```c
#include <pisecure/client.h>

int main() {
    pisecure_client_t* client = pisecure_client_new("http://localhost:3142");

    // Get blockchain info
    pisecure_blockchain_info_t info;
    pisecure_get_blockchain_info(client, &info);
    printf("Blocks: %d\n", info.blocks);

    // Wallet operations
    double balance = pisecure_get_wallet_balance(client, "wallet_address");
    printf("Balance: %.2f PSC\n", balance);

    pisecure_client_free(client);
    return 0;
}
```

### Android SDK

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var client: PiSecureClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        client = PiSecureClient("http://your-pi-node:3142")

        // Get blockchain info
        lifecycleScope.launch {
            try {
                val info = client.getBlockchainInfo()
                Log.d("PiSecure", "Blocks: ${info.blocks}")

                val balance = client.getWalletBalance("wallet_address")
                Log.d("PiSecure", "Balance: $balance PSC")
            } catch (e: Exception) {
                Log.e("PiSecure", "Error", e)
            }
        }
    }
}
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with ❤️ for the Raspberry Pi and open-source communities. Special thanks to the Bitcoin Core project for inspiration on the hybrid storage architecture, the Textual framework for the amazing TUI capabilities, and the cryptography community for the robust security foundations.

---

## 📋 Changelog

### Version 0.1.1 (Current)
- **Hybrid Storage System**: Complete overhaul with block files + SQLite indexing
- **Enterprise Security**: Comprehensive input validation and rate limiting
- **Multi-Language SDKs**: Production-ready clients for Python, JS/TS, Go, Rust, C/C++, Android
- **Advanced Mining Console**: Textual TUI with real-time monitoring and controls
- **REST API**: Full-featured API with WebSocket streaming
- **System Monitoring**: Real-time health checks and performance metrics
- **Web Dashboard**: Enhanced interface with wallet management and blockchain explorer

### Version 0.1.0
- Initial release with core blockchain functionality
- Basic mining and wallet operations
- Simple web dashboard
- JSON-based storage system
- Basic CLI tools

---

## 🗺️ Roadmap

### Version 0.2.0 (Q1 2026)
- **Smart Contracts**: Basic smart contract functionality
- **Advanced Token Economics**: Enhanced developer incentives and trust funds
- **Mobile Apps**: Native iOS and Android applications
- **Hardware Acceleration**: GPU mining support for compatible devices
- **Advanced Networking**: Improved P2P protocols and relay coordination

### Version 0.3.0 (Q2 2026)
- **Decentralized Exchange**: Built-in DEX for token trading
- **Cross-Chain Bridges**: Interoperability with other blockchains
- **Advanced Analytics**: Comprehensive blockchain analytics and reporting
- **Enterprise Features**: Multi-node clustering and load balancing

### Future Versions
- **Layer 2 Solutions**: Scaling solutions for high-throughput applications
- **Privacy Features**: Zero-knowledge proofs and privacy-preserving transactions
- **IoT Integration**: Enhanced support for IoT device networks
- **AI/ML Integration**: Machine learning capabilities for network optimization