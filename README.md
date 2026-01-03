# PiSecure

**Hardware-Verified Blockchain Security for Software Developers**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2B%20%26%205-red.svg)](https://www.raspberrypi.org/)

**PiSecure gives software developers the power to build secure, decentralized applications with hardware-verified cryptography and blockchain consensus - without the complexity of implementing security protocols from scratch.**

## What Software Developers Can Build with PiSecure

PiSecure empowers software developers to create secure, decentralized applications that leverage hardware-verified cryptography and blockchain consensus without implementing complex security protocols from scratch. Whether you're building distributed systems, secure communication networks, or token-based economies, PiSecure provides production-ready components that handle the heavy lifting of cryptography, consensus, and trust management. It doesn't just stop at software either, IoT and embedded systems can benefit from PiSecure as well from the smallest tinkering projects to large enterprise systems! PiSecure gives you the tools to let your imagination work for you!

The framework gives developers access to enterprise-grade security primitives: hardware-bound digital signatures, decentralized identity management, cryptographically secure updates, and proof-of-work consensus - all backed by Raspberry Pi's unique hardware verification. This means developers can focus on their application logic while knowing their systems are secured by mathematically proven cryptography and hardware-trusted execution.

## What Makes PiSecure Powerful for Developers

PiSecure transforms complex security challenges into simple, reliable APIs that developers can integrate immediately. Instead of spending months implementing cryptographic protocols, certificate management, and consensus algorithms, developers get:

- **One-Line Security**: Simple APIs for device authentication, secure messaging, and trust establishment
- **Hardware-Verified Trust**: Cryptographic proof that security operations run on genuine hardware, eliminating spoofing attacks
- **Decentralized Architecture**: No centralized servers or certificate authorities to maintain or secure
- **Built-in Token Economy**: Ready-to-use micropayment and staking systems for monetizing applications
- **Real-time Monitoring**: Live dashboards and programmatic APIs for system health and activity tracking
- **Automatic Updates**: Secure over-the-air updates with cryptographic verification and automatic rollback

Developers can build everything from secure IoT networks and distributed sensor systems to token-gated applications and decentralized marketplaces - all with the confidence that their security is mathematically sound and hardware-verified.

## Why PiSecure Changes Everything for Software Development

Traditional security approaches force developers to choose between complex implementation (building crypto from scratch) or centralized trust (relying on cloud services and certificate authorities). PiSecure eliminates this false choice by providing **decentralized trust with developer-friendly APIs**.

What sets PiSecure apart is its **hardware-binding innovation**: security features are cryptographically linked to Raspberry Pi's unique hardware fingerprints, creating an immutable trust anchor that software alone cannot compromise. This hardware-verification enables true peer-to-peer trust - devices authenticate each other directly, creating networks resilient to attacks, censorship, and single points of failure.

For software developers, PiSecure represents a paradigm shift: instead of security being an afterthought or a complex integration, it becomes a foundational platform that enables new categories of applications. Developers can build systems that are not just secure, but provably secure - with mathematical guarantees backed by hardware verification.

PiSecure gives developers the power to build the next generation of secure, decentralized applications with confidence and simplicity.

---

**Quick Start:** `pip install pisecure && pisecure`  
**Detailed Documentation:** [README_detailed.md](README_detailed.md)  
**API Reference & Examples:** [PiSecure Docs](https://pisecure.readthedocs.io/)

Built with ❤️ for developers who demand both security and simplicity

## 🚀 Latest Features

### System Monitoring & Health Checks
PiSecure now includes comprehensive system monitoring with real-time health checks, metrics collection, and alerting:

- **Real-time Health Monitoring**: Continuous system health assessment with automatic alerts
- **Performance Metrics**: CPU, memory, disk, and network usage tracking with historical data
- **Blockchain Monitoring**: Block height, peer connectivity, and transaction queue monitoring
- **Interactive Dashboard**: Web-based monitoring interface at `/monitoring` with live charts
- **Alert Management**: Configurable thresholds with automatic notifications
- **API Endpoints**: Programmatic access to health status, metrics, and alerts

### Enhanced Security & Validation
Production-ready input validation and security utilities:

- **Input Validation**: Comprehensive validation for wallet addresses, amounts, and transactions
- **Rate Limiting**: Built-in request rate limiting to prevent abuse
- **Data Sanitization**: Safe string handling and input cleaning
- **Security Utils**: Request ID generation and sensitive data hashing
- **Transaction Validation**: Type-specific validation for all transaction types

### Improved Performance
Significant performance optimizations for production deployment:

- **Hybrid Storage**: Scalable block file + SQLite database storage (replaces JSON)
- **Lazy Loading**: On-demand component initialization reducing startup time by 90%
- **Caching**: 2-second stats caching and 30-second blockchain validation caching
- **Database Indexing**: Optimized wallet lookups with O(1) balance queries
- **Memory Management**: Efficient resource usage for resource-constrained devices

### Web Dashboard Enhancements
Enhanced web interface with wallet management and monitoring:

- **Wallet Interface**: Real-time balance checking and transaction history
- **Transaction Explorer**: Searchable transaction history with pagination
- **System Monitoring**: Live charts and health status indicators
- **Responsive Design**: Mobile-friendly interface optimized for various screen sizes

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
```

#### 3. Install System Dependencies (Optional)
```bash
# For enhanced hardware verification
sudo apt-get update
sudo apt-get install -y python3-dev build-essential

# For UPnP port forwarding
pip install miniupnpc

# For advanced networking features
pip install netifaces
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

### Configuration Options

PiSecure supports extensive configuration via `/etc/pisecure/config.json`:

```json
{
  "network": {
    "port": 3142,
    "relay_enabled": true,
    "upnp_enabled": true
  },
  "mining": {
    "enabled": true,
    "wallet_address": "your_wallet_address"
  },
  "storage": {
    "use_hybrid_storage": true,
    "block_file_size": 128
  },
  "monitoring": {
    "enabled": true,
    "alert_thresholds": {
      "cpu_percent": 80,
      "memory_percent": 85
    }
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

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with ❤️ for the Raspberry Pi and open-source communities. Special thanks to the Bitcoin Core project for inspiration on the hybrid storage architecture.