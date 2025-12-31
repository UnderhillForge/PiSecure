# PiSecure OTA Update System

## Overview

PiSecure implements a comprehensive Over-The-Air (OTA) update system with cryptographic verification, decentralized distribution, and automatic rollback capabilities. The system ensures updates are authentic, secure, and recoverable.

## Architecture

```
OTA Update Flow:
1. Update Registration → Blockchain
2. Update Discovery → Query blockchain
3. Package Download → IPFS/HTTP with verification
4. Cryptographic Verification → RSA/ECDSA signatures
5. Backup Creation → Automatic pre-update backup
6. Package Installation → Secure file replacement
7. Post-Install Validation → Health checks and verification
8. Rollback on Failure → Automatic recovery
```

## Creating Update Packages

### 1. Package Structure

Update packages should be tar.gz or zip archives containing:

```
update_package.tar.gz/
├── manifest.json          # Update metadata and signature
├── files/                 # Update files
│   ├── pisecure/
│   │   ├── core/
│   │   └── updates/
│   └── scripts/
└── checksums.sha256      # File integrity hashes
```

### 2. Manifest Format

```json
{
  "version": "1.0.1",
  "publisher": "PiSecure Team",
  "description": "Security updates and performance improvements",
  "target_hardware": ["raspberry_pi_4", "raspberry_pi_5"],
  "compatibility": ">=0.1.0",
  "file_hashes": {
    "sha256": "abc123..."
  },
  "file_mapping": {
    "files/pisecure/core/blockchain.py": "/usr/local/lib/pisecure/core/blockchain.py",
    "files/pisecure/updates/verifier.py": "/usr/local/lib/pisecure/updates/verifier.py"
  },
  "post_install": [
    "systemctl restart pisecure-mining",
    "pisecure status"
  ],
  "rollback_supported": true,
  "max_install_size": 10485760,
  "signing_key": "production"
}
```

### 3. Signing Updates

```bash
# Generate signing keys (RSA example)
openssl genrsa -out signing_key.pem 2048
openssl rsa -in signing_key.pem -pubout -out signing_key.pub

# Create package
tar -czf update_1.0.1.tar.gz manifest.json files/

# Sign manifest
python3 -c "
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Load manifest
with open('manifest.json', 'r') as f:
    manifest = json.load(f)

# Create canonical string
manifest_str = json.dumps(manifest, sort_keys=True)

# Load private key
with open('signing_key.pem', 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# Sign
signature = private_key.sign(
    manifest_str.encode(),
    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
    hashes.SHA256()
)

# Add signature to manifest
manifest['signature'] = signature.hex()
with open('manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
"

# Final package
tar -czf signed_update_1.0.1.tar.gz manifest.json files/
```

## CLI Usage

### Check for Updates

```bash
# Check for available updates
pisecure check-updates

# Check and automatically apply latest update
pisecure check-updates --apply
```

### Download Specific Update

```bash
# Download by IPFS hash
pisecure download-update QmABC123...

# Download and apply
pisecure download-update QmABC123 --apply
```

### Verify Update Package

```bash
# Verify downloaded package
pisecure verify-update update_1.0.1.tar.gz
```

### Update System Status

```bash
# Show comprehensive update status
pisecure update-status
```

### Rollback Operations

```bash
# List available backups
pisecure list-backups

# Rollback to latest backup
pisecure rollback

# Rollback to specific backup
pisecure rollback backup_1.0.0_1640995200

# Emergency rollback
pisecure emergency-rollback
```

## API Usage

### Basic Update Flow

```python
from pisecure.updates import OTAUpdater

# Initialize updater
updater = OTAUpdater()

# Check for updates
updates = updater.check_for_updates("1.0.0")
if updates:
    latest = updates[0]

    # Download update
    download_result = updater.download_update(latest)
    if download_result['success']:

        # Verify package
        verify_result = updater.verify_update(
            download_result['local_path'],
            latest
        )
        if verify_result['verified']:

            # Apply update
            apply_result = updater.apply_update(
                download_result['local_path'],
                verify_result['manifest']
            )

            if apply_result['success']:
                print(f"Update applied: {apply_result['version']}")
            else:
                print(f"Update failed: {apply_result['error']}")
```

### Register Update on Blockchain

```python
# Register update information
update_info = {
    'version': '1.0.1',
    'ipfs_hash': 'QmABC123...',
    'size': 10485760,
    'publisher': 'PiSecure Team',
    'description': 'Security patches',
    'target_hardware': ['raspberry_pi_4', 'raspberry_pi_5']
}

tx_hash = updater.register_update(update_info)
print(f"Update registered: {tx_hash}")
```

### Custom Verification

```python
from pisecure.updates import UpdateVerifier

verifier = UpdateVerifier()

# Add trusted key
verifier.add_trusted_key('signing_key.pub', 'production', 'rsa')

# Verify package
result = verifier.verify_package('update.tar.gz')
if result['verified']:
    print("Package authentic!")
    manifest = result['manifest']
    print(f"Version: {manifest['version']}")
```

## Security Features

### Cryptographic Verification
- **RSA-PSS/ECDSA signatures** for manifest authentication
- **SHA256 integrity checks** for all files
- **Certificate chain validation** (future enhancement)
- **Hardware-based key storage** (TPM integration)

### Decentralized Distribution
- **IPFS network** for censorship-resistant distribution
- **Multiple gateways** for redundancy
- **On-chain hash verification** for authenticity
- **HTTP fallback** for traditional distribution

### Tamper Detection
- **File integrity monitoring** with hash verification
- **Hardware binding** using device fingerprints
- **Immutable audit logs** on blockchain
- **Anomaly detection** and alerting

### Recovery Mechanisms
- **Automatic backups** before updates
- **Version rollback** to any previous state
- **Emergency recovery** with system snapshots
- **Health checks** and validation

## Advanced Configuration

### Custom IPFS Gateways

```python
from pisecure.updates import UpdateFetcher

fetcher = UpdateFetcher()

# Add custom IPFS gateway
fetcher.add_ipfs_gateway("https://your-gateway.example.com/ipfs/")

# Configure multiple sources
updater = OTAUpdater()
updater.fetcher.ipfs_gateways = [
    "https://ipfs.io/ipfs/",
    "https://your-custom-gateway.com/ipfs/",
    "https://backup-gateway.net/ipfs/"
]
```

### Trusted Key Management

```python
from pisecure.updates import UpdateVerifier

verifier = UpdateVerifier()

# Add production signing key
verifier.add_trusted_key('/path/to/prod_key.pem', 'production', 'rsa')

# Add development key
verifier.add_trusted_key('/path/to/dev_key.pem', 'development', 'ecdsa')

# List trusted keys
keys = verifier.list_trusted_keys()
print(f"Trusted keys: {keys}")
```

### Backup Configuration

```python
from pisecure.updates import RollbackManager

rollback = RollbackManager()

# Configure backup settings
rollback.max_backups = 10  # Keep 10 backups
rollback.backup_extensions = ['.py', '.json', '.yaml', '.service']

# Custom backup paths
rollback.system_paths = [
    "/usr/local/lib/pisecure",
    "/etc/pisecure/config.json",
    "/var/lib/pisecure/data"
]
```

## Integration Examples

### IoT Device Auto-Updates

```python
import time
import schedule
from pisecure.updates import OTAUpdater

def auto_update_check():
    updater = OTAUpdater()
    updates = updater.check_for_updates(current_version)

    if updates:
        print(f"Update available: {updates[0]['version']}")

        # Download and apply automatically
        download = updater.download_update(updates[0])
        if download['success']:
            verify = updater.verify_update(download['local_path'], updates[0])
            if verify['verified']:
                apply = updater.apply_update(download['local_path'], verify['manifest'])
                if apply['success']:
                    print("Auto-update successful")
                    # Restart services if needed
                    os.system("systemctl restart my-iot-service")

# Schedule daily checks
schedule.every().day.at("02:00").do(auto_update_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Enterprise Update Management

```python
from pisecure.updates import OTAUpdater

class EnterpriseUpdater:
    def __init__(self):
        self.updater = OTAUpdater()
        self.approved_versions = ['1.0.1', '1.0.2', '1.1.0']

    def approve_update(self, update_info):
        """Enterprise approval workflow"""
        if update_info['version'] in self.approved_versions:
            # Register approved update
            tx_hash = self.updater.register_update(update_info)
            return tx_hash
        return None

    def deploy_to_fleet(self, update_hash, device_list):
        """Deploy update to device fleet"""
        results = {}
        for device_id in device_list:
            # Send update command to device
            result = self._deploy_to_device(device_id, update_hash)
            results[device_id] = result
        return results
```

## Troubleshooting

### Update Verification Fails

**Problem**: `Package verification failed`

**Solutions**:
- Check if signing key is trusted: `verifier.list_trusted_keys()`
- Verify signature format (RSA-PSS vs PKCS#1)
- Ensure manifest is properly formatted
- Check file integrity with: `sha256sum -c checksums.sha256`

### Download Fails

**Problem**: `All sources failed`

**Solutions**:
- Check IPFS connectivity: `curl https://ipfs.io/ipfs/QmTest`
- Verify blockchain has update registration
- Add custom IPFS gateways
- Check network connectivity

### Rollback Issues

**Problem**: `Rollback validation failed`

**Solutions**:
- Check disk space: `df -h`
- Verify backup integrity
- Use emergency rollback if needed
- Check system health before rollback

### Permission Errors

**Problem**: `Permission denied` during installation

**Solutions**:
- Run with appropriate permissions
- Check file ownership
- Add user to required groups
- Use sudo for system files

## Future Enhancements

- **Certificate Chains**: X.509 certificate validation
- **Delta Updates**: Binary diff patches for efficiency
- **Peer-to-Peer Distribution**: Direct device-to-device updates
- **Update Channels**: Stable/Beta/Nightly release channels
- **Bandwidth Management**: Throttling and scheduling
- **Compliance Reporting**: Audit trails and compliance logs