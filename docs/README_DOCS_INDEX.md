# PiSecure Documentation Index

Complete documentation for PiSecure blockchain framework.

## 📚 Main Documentation

### Getting Started
- [Main README](../README.md) - Quick start and overview
- [Detailed README](../README_detailed.md) - Comprehensive feature guide
- [Installation Guide](user/installation.md) - Step-by-step installation
- [Getting Started Guide](getting-started.md) - Your first PiSecure project
- [MAC Setup Guide](MAC_SETUP.md) - macOS-specific setup instructions

### API & Development
- [API Documentation](api-documentation.txt) - REST API endpoints and usage
- [API Refactoring Guide](API_REFACTORING.md) - API architecture evolution
- [API Modular Design](API_MODULAR.md) - Modular API structure
- [Entropy Validation API](api-entropy-validation.md) - Hardware entropy endpoints
- [Node Registration API](api-node-registration.md) - Network node registration

### Core Features
- [Mining vs Validation](mining-vs-validation.md) - Understanding dual-mode operation
- [Validator Rewards Guide](validator-guide.md) - Earn tokens by validating
- [Token Economics](economics.md) - 314ST token system design
- [Use Cases](use-cases.md) - Real-world applications

### Network & Infrastructure
- [Network Setup](network-setup.md) - Multi-node configuration
- [Multi-Node Setup](multi-node-setup.md) - Distributed deployment
- [Automatic Network Discovery](automatic-network-discovery.md) - Peer discovery system
- [Public IP Discovery](public-ip-discovery.md) - NAT traversal strategies
- [No Port Forwarding Needed](no-port-forwarding-needed.md) - P2P connectivity
- [Bootstrap Server](bootstrap-server.txt) - Bootstrap node configuration

### Mining & Consensus
- [Difficulty Sustainability](difficulty-sustainability.md) - Dynamic difficulty adjustment
- [Bit Counting Implementation](bit-counting-implementation.md) - Zero-bit verification
- [Mining Dashboard](mining-dashboard.md) - Visual mining monitoring

### Security & Updates
- [Security Documentation](security/) - Security best practices
- [OTA Updates](ota-updates.md) - Over-the-air update system
- [Contributing Guide](contributing.md) - Development guidelines

### Miscellaneous
- [Roadmap](roadmap.md) - Future development plans
- [Updates](updates.md) - Version history and changes
- [Exchanges](exchanges.md) - Token exchange integration

## 🏗️ Architecture & Refactoring Documentation

Technical documentation for developers working on the PiSecure core.

### Refactoring Series
- [Refactoring Index](refactoring/REFACTORING_DOCS_INDEX.md) - Complete refactoring guide
- [Refactoring Progress](refactoring/REFACTORING_PROGRESS.md) - Current status
- [Refactoring Complete](refactoring/REFACTORING_COMPLETE.md) - Summary of changes
- [Phase 3 Complete](refactoring/PHASE_3_COMPLETE.md) - Phase 3 deliverables

### Architecture Documentation
- [Architecture Analysis](refactoring/ARCHITECTURE_ANALYSIS.md) - System design patterns
- [Architecture Refactoring](refactoring/ARCHITECTURE_REFACTORING.md) - Structural improvements
- [Bitcoin Patterns](refactoring/BITCOIN_PATTERNS.md) - Bitcoin-inspired design
- [Core Conversion](core-conversion.md) - Core module evolution

### PiHash & Mining
- [PiHash Completion Summary](refactoring/PIHASH_COMPLETION_SUMMARY.md) - PiHash implementation
- [PiHash CPP Architecture](refactoring/PIHASH_CPP_ARCHITECTURE.md) - C++ acceleration design
- [VideoCore Integration](refactoring/VIDEOCORE_INTEGRATION_SUMMARY.md) - GPU integration

### Bug Fixes & Debugging
- [CPP Module Segfault Debug](refactoring/CPP_MODULE_SEGFAULT_DEBUG.md) - Memory debugging
- [SHA256 Buffer Overflow Fix](refactoring/SHA256_BUFFER_OVERFLOW_FIX.md) - Security patch
- [Segfault Fix Complete](refactoring/SEGFAULT_FIX_COMPLETE.md) - Resolution summary

## 🚀 Phase 1 Documentation

Phase 1 implementation details for mining challenges and network features.

### Implementation Summaries
- [Phase 1 Index](phase1/PHASE1_INDEX.md) - Complete Phase 1 overview
- [Phase 1 Implementation Summary](phase1/PHASE1_IMPLEMENTATION_SUMMARY.md) - Key deliverables
- [Phase 1 Mining Challenges](phase1/PHASE1_MINING_CHALLENGES.md) - Mining system design
- [Phase 1 Validation Compatibility](phase1/PHASE1_VALIDATION_COMPATIBILITY.md) - Cross-platform validation
- [Verification Report](phase1/VERIFICATION_REPORT_PHASE1.md) - Testing and validation

### WebSocket & P2P
- [WebSocket P2P Implementation](phase1/PHASE1_WEBSOCKET_P2P_IMPLEMENTATION.md) - Real-time networking
- [WebSocket P2P Complete](phase1/WEBSOCKET_P2P_PHASE1_COMPLETE.md) - Final implementation
- [WebSocket Specification](phase1/WEBSOCKET_SPECIFICATION.md) - Protocol specification
- [WebSocket Auto Connect](phase1/WEBSOCKET_AUTO_CONNECT.md) - Bootstrap integration
- [WebSocket Integration](phase1/WEBSOCKET_INTEGRATION.md) - System integration
- [WebSocket Quick Reference](phase1/WEBSOCKET_QUICK_REFERENCE.md) - API reference
- [WebSocket P2P Quick Reference](phase1/WEBSOCKET_P2P_QUICK_REFERENCE.md) - P2P guide
- [WebSocket P2P Scalability](phase1/WEBSOCKET_P2P_SCALABILITY.md) - Performance optimization
- [WebSocket Test Report](phase1/WEBSOCKET_TEST_REPORT.md) - Testing results
- [README WebSocket P2P Phase 1](phase1/README_WEBSOCKET_P2P_PHASE1.md) - Overview

## 📁 Legacy Documentation

Historical documentation and deprecated features.

Located in `/legacy/docs/`:
- Genesis reset tools
- Old wallet migration guides
- Dashboard debugging notes
- Node registration deliverables

## 🛠️ Additional Resources

### Client Libraries
- [JavaScript/TypeScript SDK](../clients/javascript/)
- [Python Client](../clients/python/)
- [Go Client](../clients/go/)
- [Rust Client](../clients/rust/)
- [C/C++ Client](../clients/c/)
- [Android Client](../clients/android/)

### Examples
- [Basic Mining Example](../examples/basic_mining.py)
- [Hybrid Storage Demo](../examples/hybrid_storage_demo.py)
- [Wallet Integration](../examples/wallet_demo.py)

### Testing
- [Test Suite](../tests/)
- [Test Documentation](../tests/compile-algorithm.md)

## 🔍 Finding Documentation

### By Topic
- **Installation**: `user/installation.md`, `getting-started.md`
- **API**: `api-documentation.txt`, `API_*.md`
- **Mining**: `mining-vs-validation.md`, `phase1/PHASE1_MINING_CHALLENGES.md`
- **Network**: `network-setup.md`, `automatic-network-discovery.md`
- **Security**: `security/`, `ota-updates.md`
- **Development**: `contributing.md`, `refactoring/`

### By Audience
- **End Users**: Main README, getting-started.md, use-cases.md
- **Validators**: validator-guide.md, mining-vs-validation.md
- **Developers**: API docs, refactoring/, phase1/
- **System Admins**: network-setup.md, multi-node-setup.md

---

**Last Updated**: January 2026  
**Version**: 0.1.1
