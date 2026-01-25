# PiSecure

**Hardware-Verified Blockchain Security for Raspberry Pi**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2B%20%26%205-red.svg)](https://www.raspberrypi.org/)

Enterprise-grade blockchain framework for IoT and embedded systems. Hardware-verified mining on Raspberry Pi + universal validation on any platform.

## 🚀 Quick Start

```bash
# One-command installation
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install-oneclick.sh | bash

# Mine on Raspberry Pi (hardware-verified)
psminer -w your_wallet_address -t 4

# Validate on any platform
export PISECURE_VALIDATE_ONLY=1
pisecure validate --continuous

# Check status
pisecure status
```

## ✨ Core Features

- **PiHash Mining** - Hardware-verified proof-of-work exclusive to Raspberry Pi
- **Universal Validation** - Run validators on Mac, Windows, Linux, or Pi
- **Validator Rewards** - Earn 314ST tokens for network participation
- **Enterprise Security** - OWASP-compliant with ML-powered DDoS defense
- **Hybrid Storage** - Block files + SQLite for 90%+ performance gains
- **Multi-Language SDKs** - Python, JavaScript, Go, Rust, C/C++, Android
- **REST API + WebSockets** - Full-featured production-ready interface
- **Real-Time Dashboard** - Monitor mining, validation, and network health

## 🏗️ Architecture Highlights

| Component | Purpose | Language |
|-----------|---------|----------|
| **pisecured** | Core blockchain validator & P2P network | C++ |
| **psminer** | High-performance mining engine | C++ |
| **pswallet** | Wallet and smart contract engine | C++ |
| **REST API** | Production-grade API server | Python |
| **Web Dashboard** | Real-time monitoring and control | Python/React |

## 📚 Documentation

For comprehensive documentation, see:

- **[Public Documentation Index](docs/PUBLIC_DOCS_INDEX.md)** - All user-facing guides organized by topic
- **[Detailed README](README_detailed.md)** - Full feature documentation
- **[Installation Guide](INSTALL.md)** - Setup instructions for all platforms
- **[Validator Guide](docs/validator-guide.md)** - Run validators and earn rewards
- **[C++ Miner Docs](cpp/psminer/README.md)** - High-performance mining
- **[API Reference](docs/api-documentation.txt)** - REST API endpoints
- **[Network Setup](docs/network-setup.md)** - Multi-node configuration

## 🎯 Use Cases

- **Secure IoT Networks** - Hardware-bound device communication
- **Edge Computing** - Decentralized data processing
- **Token-Gated Services** - Built-in micropayments and access control
- **Distributed Sensors** - Secure cross-device data sharing
- **Embedded Blockchain** - Hardware-verified security for resource-constrained devices

## 🔐 Security

- Hardware-verified cryptography bound to Raspberry Pi
- Decentralized peer-to-peer trust model
- Defense-in-depth with multiple security layers
- GDPR-compliant audit logging
- Zero-trust architecture with cryptographic verification

## 💡 Why PiSecure?

Unlike centralized cloud services or generic blockchain frameworks, PiSecure provides:
- **Hardware binding** - Cryptographic tie to physical Raspberry Pi device
- **Network incentives** - Validator rewards enable ecosystem growth
- **Production ready** - Enterprise security without complexity
- **Resource optimized** - Efficient performance on limited hardware

---

Built with ❤️ for the Raspberry Pi and blockchain communities.