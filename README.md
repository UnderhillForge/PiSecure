# PiSecure

**Enterprise-Grade Security Framework for IoT & Embedded Systems**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2B%20%26%205-red.svg)](https://www.raspberrypi.org/)
[![Build Status](https://img.shields.io/badge/build-passing-green.svg)](#)
[![Coverage](https://img.shields.io/badge/coverage-85%25-yellow.svg)](#)

**PiSecure provides enterprise-grade security for IoT and embedded projects with device identity management, cryptographically secure OTA updates, and optional hardware-verified blockchain mining on Raspberry Pi.**

[Quick Start](#quick-start) • [Documentation](#documentation) • [Installation](#installation) • [Developer Guide](#developer-guide) • [Roadmap](docs/roadmap.md)

## Features

### Core Security
- **Hardware-Verified Mining**: Proof-of-work mining exclusive to Raspberry Pi hardware
- **Device Authentication**: Unique device IDs tied to hardware fingerprints
- **Mutual TLS**: Secure device-to-device and device-to-server communication
- **Revocable Certificates**: Blockchain-stored certificates and keys

### OTA Updates
- **Cryptographic Verification**: RSA/ECDSA signature verification of update packages
- **Decentralized Distribution**: IPFS-based update distribution with on-chain hashes
- **Automatic Rollback**: Failsafe rollback to previous versions on verification failure
- **Secure Boot**: Hardware-verified boot process

### Access Control & Licensing
- **Token-Gated Features**: Require token balance to unlock premium modes
- **Time-Limited Access**: Subscription-based access via on-chain records
- **Role-Based Permissions**: Hierarchical permissions (admin/operator/user)
- **Usage Metering**: Pay-per-use tracking and billing

### Micropayments & Incentives
- **Low-Fee Transfers**: Efficient token micropayments for sensor data sharing
- **Automated Rewards**: Staking tokens for running relay nodes or providing services
- **Oracle Integration**: Off-chain triggers and price feeds
- **Smart Contracts**: Automated payment processing

### Audit & Monitoring
- **Immutable Audit Logs**: All events logged on-chain with cryptographic proof
- **Tamper Detection**: Hardware-binding with TPM/serial verification
- **Integrity Monitoring**: File hash verification and anomaly detection
- **Real-time Alerts**: Automated security incident response

### Node Architectures
- **Full Node**: Complete blockchain validation and mining participation
- **Light Client**: Header-only validation with Merkle proofs
- **SPV Client**: Minimal trust assumptions, mobile/IoT optimized
- **Bootstrapping**: Easy setup from trusted peers

## Architecture

```
PiSecure/
├── core/                    # Core blockchain engine
│   ├── blockchain.py       # SignChain implementation
│   ├── hardware.py         # Hardware verification & mining
│   └── wallet.py           # SignWallet implementation
├── identity/               # Device identity management
│   ├── certificates.py     # X.509 certificate handling
│   ├── fingerprint.py      # Hardware fingerprinting
│   └── authentication.py   # Mutual auth protocols
├── updates/                # OTA update system
│   ├── verifier.py         # Cryptographic verification
│   ├── fetcher.py          # Decentralized distribution
│   └── rollback.py         # Recovery mechanisms
├── payments/               # Token economy
│   ├── wallet.py           # SignWallet implementation
│   ├── micropayments.py    # Low-fee transfers
│   └── staking.py          # Reward distribution
├── access/                 # Access control
│   ├── licensing.py        # Token-based licensing
│   ├── permissions.py      # Role-based access
│   └── metering.py         # Usage tracking
├── audit/                  # Logging & monitoring
│   ├── tamper.py           # Integrity monitoring
│   ├── logging.py          # Immutable audit logs
│   └── alerts.py           # Anomaly detection
└── nodes/                  # Client modes
    ├── full_node.py        # Complete node
    ├── light_client.py     # Header-only client
    └── spv_client.py       # Minimal client
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Install dependencies
pip3 install -r requirements.txt

# Run hardware verification
python3 -m pisecure.core.verify_hardware

# Start mining (Pi hardware only)
python3 -m pisecure.core.mine_interactive
```

### Basic Usage

```python
from pisecure import PiSecure

# Initialize PiSecure
secure = PiSecure()

# Check hardware eligibility
if secure.verify_hardware():
    print("Raspberry Pi hardware verified")

    # Start mining
    secure.start_mining()

    # Create device identity
    identity = secure.create_identity()
    print(f"Device ID: {identity.device_id}")

    # Check token balance
    balance = secure.get_balance()
    print(f"Token Balance: {balance} 314ST")
```

### CLI Usage

```bash
# Show blockchain status
pisecure status

# Start interactive mining
pisecure mine

# Create test transactions
pisecure create-tx

# Check device identity
pisecure identity

# Wallet management
pisecure create-wallet "my_wallet" --name "Personal Wallet"
pisecure show-wallet                    # List all wallets
pisecure show-wallet "my_wallet"        # Show specific wallet
pisecure transfer-tokens addr123 100 --from-wallet "my_wallet"
pisecure wallet-balance addr123
pisecure wallet-history addr123

# Verify update package
pisecure verify-update package.zip

# Export wallet
pisecure export-wallet backup.json
```

## 📋 Requirements

- **Hardware**: Any modern hardware (Raspberry Pi required for mining only)
- **OS**: Linux, macOS, Windows (Linux recommended for production)
- **Python**: 3.7 or higher
- **Dependencies**: cryptography, requests, pynacl

### Hardware Support

PiSecure works on **any modern hardware** for security features like device identity, certificate management, and OTA updates. Hardware verification using exclusive Raspberry Pi features is **only required for mining**:

- **All Platforms**: Identity management, certificates, OTA updates, blockchain validation
- **Raspberry Pi Only**: Hardware-verified proof-of-work mining using exclusive features:
  - CPU serial number verification
  - Hardware RNG access
  - VideoCore GPU detection
  - Mailbox interface validation
  - OTP register verification

This allows developers to build secure IoT applications on any platform while reserving the token mining capability for Raspberry Pi hardware.

## 🎯 Use Cases

### IoT Device Networks
Secure communication between Raspberry Pi devices in a mesh network.

### Home Automation
Token-gated smart home features with subscription-based access.

### Sensor Networks
Micropayments for environmental data sharing and analysis.

### Embedded Security
Hardware-verified boot and secure software updates.

### Community Projects
Decentralized Raspberry Pi applications with built-in monetization.

## 🛠️ Developer Guide

### Integrating PiSecure into Your Project

#### 1. Basic Setup

```python
from pisecure import PiSecure

# Initialize PiSecure
secure = PiSecure()

# Verify hardware (recommended for all deployments)
if not secure.verify_hardware():
    print("❌ Hardware verification failed")
    exit(1)

print("✅ PiSecure ready for secure operations")
```

#### 2. Device Identity Setup

```python
from pisecure.identity import DeviceIdentity

# Initialize device identity
identity = DeviceIdentity()

# Create identity (one-time setup)
result = identity.initialize_device(
    device_name="MyIoTSensor",
    organization="MyCompany"
)

if result['success']:
    print(f"Device ID: {result['device_id']}")
    print("Identity initialized successfully")
```

#### 3. Secure Communication

```python
from pisecure.identity import DeviceAuthenticator

# Set up mutual authentication
auth = DeviceAuthenticator()

# Authenticate remote device
remote_cert = "/path/to/remote/device.crt"
auth_result = auth.authenticate_device(remote_cert)

if auth_result['authenticated']:
    # Create secure channel
    channel = auth.create_secure_channel(
        auth_result['device_id'],
        auth_result['session_token']
    )

    # Now you can securely communicate
    encrypted_msg = auth.encrypt_message(channel['channel_id'], "Hello Secure World!")
    print(f"Encrypted: {encrypted_msg}")
```

#### 4. Blockchain Integration

```python
from pisecure.core import SignChain

# Initialize blockchain
blockchain = SignChain()

# Add a transaction
tx_data = {
    "type": "sensor_reading",
    "sensor_id": "temp_sensor_001",
    "value": 25.5,
    "timestamp": time.time()
}

tx_hash = blockchain.add_transaction(tx_data)
print(f"Transaction added: {tx_hash}")

# Mine pending transactions
mined_block = blockchain.mine_pending_transactions()
if mined_block:
    print(f"Block mined: #{mined_block.index}")
```

#### 5. Token Operations

```python
from pisecure.core.wallet import SignWallet

# Initialize wallet
wallet = SignWallet()

# Check balance
balance = wallet.get_balance()
print(f"Token balance: {balance}")

# Transfer tokens
success = wallet.transfer_tokens("recipient_device_id", 100)
if success:
    print("Tokens transferred successfully")
```

#### 6. Secure Updates

```python
from pisecure.updates import OTAUpdater

# Initialize update system
updater = OTAUpdater()

# Check for updates
updates = updater.check_for_updates("1.0.0")
if updates:
    # Download and apply latest update
    download = updater.download_update(updates[0])
    if download['success']:
        verify = updater.verify_update(download['local_path'], updates[0])
        if verify['verified']:
            apply = updater.apply_update(download['local_path'], verify['manifest'])
            if apply['success']:
                print("Update applied successfully")
```

### Configuration Options

#### Environment Variables

```bash
# Enable mock hardware for development
export PISECURE_MOCK_HARDWARE=1

# Set custom data directory
export PISECURE_DATA_DIR=/custom/path

# Enable debug logging
export PISECURE_DEBUG=1

# Set custom blockchain difficulty
export PISECURE_DIFFICULTY=4
```

#### Configuration File

```json
{
  "network": {
    "peers": ["192.168.1.100:3141", "10.0.0.50:3141"],
    "max_connections": 10
  },
  "mining": {
    "max_temperature": 70,
    "thermal_throttle": true,
    "daily_limit": 24
  },
  "updates": {
    "auto_check": true,
    "update_channel": "stable",
    "backup_before_update": true
  },
  "security": {
    "certificate_lifetime": 730,
    "key_size": 2048,
    "cipher_suites": ["ECDHE-RSA-AES256-GCM-SHA384"]
  }
}
```

### Example IoT Sensor Project

```python
import time
import board
import adafruit_dht
from pisecure import PiSecure

class SecureIoTSensor:
    def __init__(self):
        self.secure = PiSecure()

        # Initialize hardware
        self.dht = adafruit_dht.DHT22(board.D4)

        # Setup device identity
        self.identity = self.secure.initialize_device("WeatherSensor01")

    def read_sensor(self):
        """Read temperature and humidity"""
        try:
            temperature = self.dht.temperature
            humidity = self.dht.humidity
            return {'temp': temperature, 'humidity': humidity}
        except:
            return None

    def submit_reading(self, reading):
        """Submit sensor reading to blockchain"""
        if not reading:
            return False

        # Create transaction
        transaction = {
            'type': 'sensor_reading',
            'device_id': self.identity.device_id,
            'sensor_type': 'dht22',
            'data': reading,
            'timestamp': time.time()
        }

        # Add to blockchain
        tx_hash = self.secure.add_transaction(transaction)

        # Mine if we have enough transactions
        if self.secure.get_pending_count() >= 5:
            self.secure.mine_pending()

        return tx_hash

    def run(self):
        """Main sensor loop"""
        print(f"Secure IoT Sensor running: {self.identity.device_id}")

        while True:
            reading = self.read_sensor()
            if reading:
                tx_hash = self.submit_reading(reading)
                if tx_hash:
                    print(f"Reading submitted: {reading}")

            time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    sensor = SecureIoTSensor()
    sensor.run()
```

### Security Best Practices

#### 1. Hardware Verification
Always verify hardware before sensitive operations:

```python
if not secure.verify_hardware():
    print("Hardware verification failed - exiting")
    exit(1)
```

#### 2. Certificate Management
Rotate certificates regularly for security:

```python
# Rotate certificate every 30 days
if time.time() - identity.certificate_issued > (30 * 24 * 60 * 60):
    identity.rotate_certificate()
```

#### 3. Secure Communication
Use encrypted channels for all sensitive data:

```python
# Always encrypt sensitive sensor data
encrypted_data = secure.encrypt_for_device(remote_id, sensor_data)
```

#### 4. Update Management
Keep systems updated with latest security patches:

```python
# Check for updates weekly
if time.time() - last_update_check > (7 * 24 * 60 * 60):
    updates = secure.check_updates()
    if updates:
        secure.apply_update(updates[0])
```

#### 5. Error Handling
Implement comprehensive error handling:

```python
try:
    result = secure.mine_transaction(tx)
except HardwareVerificationError:
    print("Hardware verification failed")
except NetworkError:
    print("Network connectivity issue")
except SecurityError:
    print("Security violation detected")
```

## 🔧 API Reference

### Core Classes

#### `PiSecure()`
Main framework class providing unified access to all features.

#### `HardwareVerifier()`
Handles Raspberry Pi hardware verification and fingerprinting.

#### `SignChain()`
Blockchain implementation with proof-of-work consensus.

#### `SignWallet()`
Token wallet with transfer and backup capabilities.

#### `DeviceIdentity()`
Device identity management with certificates and fingerprints.

#### `OTAUpdater()`
Cryptographically secure over-the-air update system.

### Key Methods

```python
# Hardware & Identity
verify_hardware() -> bool
create_identity() -> DeviceIdentity
get_fingerprint() -> str
rotate_certificate() -> bool

# Blockchain & Mining
start_mining() -> bool
mine_interactive() -> None
get_chain_info() -> dict
add_transaction(tx) -> str
get_wallet_balance(address) -> float
get_wallet_transactions(address) -> list

# Wallet Management
SignWallet.create_wallet(wallet_id, name) -> dict
SignWallet.load_wallet(wallet_id) -> dict
SignWallet.sign_transaction(transaction) -> str
SignWallet.create_transfer_transaction(recipient, amount) -> dict
SignWallet.create_batch_transaction(transfers) -> dict
SignWallet.get_balance() -> float
SignWallet.get_address() -> str
SignWallet.get_transaction_history() -> list

# Token Operations
SignToken.from_dict(data) -> SignToken
SignToken.is_valid() -> bool
SignToken.has_permission(permission) -> bool

# Updates & Security
verify_update(package_path) -> bool
apply_update(package_path) -> bool
rollback_version(version) -> bool
check_updates() -> list

# Access Control
check_permission(feature) -> bool
grant_access(user, feature, duration) -> bool
revoke_access(user, feature) -> bool

# Device Communication
authenticate_device(cert_pem) -> dict
create_secure_channel(device_id, token) -> dict
encrypt_message(channel_id, message) -> str
decrypt_message(channel_id, encrypted) -> str
```

## 🤝 Contributing

We welcome contributions from the Raspberry Pi community!

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/PiSecure.git
cd PiSecure

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run linting
flake8 pisecure/
black pisecure/
```

### Testing on Different Hardware

PiSecure works on any modern hardware for security features. Use mock hardware for development:

```bash
# Test with mock hardware (recommended for development)
export PISECURE_MOCK_HARDWARE=1
python -m pytest

# Test in Docker (cross-platform development)
make docker-test

# Test mining on actual Raspberry Pi hardware
# (mining requires Pi hardware verification)
python -c "from pisecure.core.hardware import HardwareVerifier; print('Pi Hardware:', HardwareVerifier().verify_mining_eligibility())"
```

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)**: Installation and basic usage
- **[API Reference](docs/api-reference.md)**: Complete API documentation
- **[Security Model](docs/security-model.md)**: Cryptographic and hardware security details
- **[Node Types](docs/node-types.md)**: Full, light, and SPV client configurations
- **[OTA Updates](docs/ota-updates.md)**: Secure update system documentation
- **[Examples](examples/)**: Sample applications and use cases

## 🔒 Security

PiSecure implements multiple layers of security:

### Hardware Security
- Exclusive Raspberry Pi hardware verification
- Hardware fingerprinting and TPM integration
- Secure boot and trusted execution

### Cryptographic Security
- RSA/ECDSA digital signatures
- SHA256 integrity verification
- TLS 1.3 mutual authentication
- Encrypted key storage

### Network Security
- Decentralized peer discovery
- Sybil attack prevention
- Man-in-the-middle protection

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **J Stekervetz**: Original blockchain security implementation
- **Raspberry Pi Community**: Hardware and testing support
- **Open Source Contributors**: Cryptography libraries and security research

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/UnderhillForge/PiSecure/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UnderhillForge/PiSecure/discussions)
- **Documentation**: [PiSecure Docs](https://pisecure.readthedocs.io/)

---

**Built with ❤️ for the Raspberry Pi community**