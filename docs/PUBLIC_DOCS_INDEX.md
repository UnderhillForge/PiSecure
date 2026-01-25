# PiSecure Public Documentation Index

Welcome to PiSecure! This index guides you to the most relevant public documentation. Implementation details are archived in `/docs/internal/` for the development team.

## 🚀 Getting Started

New to PiSecure? Start here:

- **[Getting Started Guide](getting-started.md)** - Quick setup and first steps
- **[Installation Guide](../INSTALL.md)** - Platform-specific installation instructions
- **[Mining vs Validation](mining-vs-validation.md)** - Understand the two operational modes

## 💼 Mining

For Raspberry Pi mining operations:

- **[Mining Dashboard](mining-dashboard.md)** - Monitor mining performance
- **[C++ Miner (psminer)](../cpp/psminer/README.md)** - High-performance mining client
- **[Performance Tuning](network-setup.md)** - Optimize for your hardware

## ✅ Validation

For blockchain validation (works on any platform):

- **[Validator Guide](validator-guide.md)** - Run validators and earn rewards
- **[Validator Architecture](../cpp/psvalidator/README.md)** - Validator design and features

## 🌐 Network & P2P

Networking and distributed operations:

- **[Network Setup](network-setup.md)** - Configure multi-node networks
- **[Automatic Discovery](automatic-network-discovery.md)** - Peer discovery mechanisms
- **[No Port Forwarding Needed](no-port-forwarding-needed.md)** - Works behind NAT/firewalls
- **[WebSocket Bootstrap](websocket_bootstrap.md)** - P2P bootstrap process

## 💰 Economics & Incentives

Token economics and validator rewards:

- **[Token Economics](economics.md)** - 314ST tokenomics and incentive structures
- **[Validator Rewards](validator-guide.md)** - How validators earn tokens

## 🔐 Security

Security architecture and best practices:

- **[Security Overview](security/)** - Security architecture and design
- **[Secure Boot & Updates](ota-updates.md)** - OTA update verification
- **[Exchange Integration](exchanges.md)** - Secure external integrations

## 📊 API & Integration

For developers building on PiSecure:

- **[REST API Documentation](api-documentation.txt)** - API endpoints and usage
- **[API Integration Guide](API_INTEGRATION_REPORT.md)** - Building applications
- **[Node Registration](api-node-registration.md)** - Register nodes with the network
- **[Entropy Validation](api-entropy-validation.md)** - Hardware RNG validation

## 🛠️ Advanced

Advanced topics for operators and developers:

- **[Multi-Node Setup](multi-node-setup.md)** - Run distributed validator networks
- **[Difficulty Sustainability](difficulty-sustainability.md)** - Mining difficulty management
- **[Use Cases](use-cases.md)** - Real-world applications
- **[Roadmap](roadmap.md)** - Future development plans

## 📝 Contributing

Want to contribute?

- **[Contributing Guide](contributing.md)** - Developer guidelines

## 🏗️ Architecture

Project structure and design:

- **[Detailed README](../README_detailed.md)** - Complete feature documentation
- **[Project Structure](../README_detailed.md#architecture)** - Codebase organization

## 📚 Additional Resources

- **[Raspberry Pi Requirements](../INSTALL.md)** - Supported Pi models and versions
- **[Troubleshooting](getting-started.md#troubleshooting)** - Common issues and solutions

---

## 🔒 Internal Documentation

Implementation details, technical deep-dives, and development notes are archived in `/docs/internal/` and `/docs/internal/refactoring-archive/` for security and maintainability reasons. These documents contain:

- Hardware verification implementation specifics
- Mailbox communication protocols
- Low-level algorithm details
- Debugging and development notes

**Access to internal documentation requires developer permissions.**

---

**[← Back to README](../README.md)** | **[Main Repository](https://github.com/UnderhillForge/PiSecure)**
