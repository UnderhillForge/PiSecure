# Initial Security Setup

**CONFIDENTIAL - AUTHORIZED PERSONNEL ONLY**

This document contains critical security procedures for initializing PiSecure update authorization. These steps ensure that **only you** can push OTA updates to your PiSecure network.

## ⚠️ CRITICAL SECURITY WARNING

- **DO NOT** share your private signing keys with anyone
- **DO NOT** commit private keys to version control
- **DO NOT** run these commands on untrusted systems
- **KEEP PRIVATE KEYS SECURE** - they control your entire network

## Prerequisites

- PiSecure installed and running on at least one node
- Secure system for key generation (preferably air-gapped)
- Strong password for key encryption
- Backup storage for private keys

## Step 1: Generate Update Signing Keys

**Location**: Secure system (not connected to any network)

```bash
# Generate your cryptographic signing keypair
# This creates RSA-2048 keys for update authorization
pisecure generate-signing-key

# Expected output:
# 🔐 Generating update signing keypair...
# Enter private key password: [enter strong password]
# Repeat password: [repeat password]
# ✅ Signing keypair generated successfully!
#    Public Key: -----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
#    Key Size: 2048 bits
#    Algorithm: RSA-PSS
# ⚠️ Secure the private key file - it contains your signing credentials
```

**IMPORTANT**: The private key is saved to `/etc/pisecure/update_signing_key.pem`

## Step 2: Extract Public Key

```bash
# Extract your public key for registration
PUBLIC_KEY_FILE="/tmp/my_public_key.pem"
pisecure generate-signing-key 2>/dev/null | grep -A 20 "Public Key:" | tail -n +2 > "$PUBLIC_KEY_FILE"

# Verify the public key file
cat "$PUBLIC_KEY_FILE"
```

**SECURITY NOTE**: The public key is safe to share - it cannot be used to sign updates.

## Step 3: Register Your Public Key

**Location**: PiSecure node on your network

```bash
# Register your public key as authorized for updates
# This creates a blockchain transaction authorizing your key
pisecure register-update-key developer_key /tmp/my_public_key.pem

# Expected output:
# 📝 Registering update key: developer_key
# ✅ Update key registered successfully!
#    Blockchain TX: abc123...
```

## Step 4: Set Signature Threshold

```bash
# Set minimum signatures required for updates
# For solo development: 1 signature required
# For team development: 2+ signatures recommended
pisecure set-update-threshold 1

# Expected output:
# ⚙️ Setting update threshold to: 1
# ✅ Update threshold set successfully!
#    Blockchain TX: def456...
```

## Step 5: Verify Setup

```bash
# List all authorized update keys
pisecure list-update-keys

# Expected output:
# 🔑 Authorized Update Keys (Threshold: 1)
#
# ✅ Active Keys:
#    developer_key:
#      Added: [timestamp]
#      Permissions: sign_updates

# Verify update system status
pisecure update-status

# Should show your key in the authorized list
```

## Step 6: Secure Key Storage

### Private Key Backup
```bash
# Create encrypted backup of private key
sudo cp /etc/pisecure/update_signing_key.pem /secure/backup/update_key_backup.pem

# Verify backup integrity
openssl rsa -in /etc/pisecure/update_signing_key.pem -check
openssl rsa -in /secure/backup/update_key_backup.pem -check
```

### Public Key Distribution
```bash
# Extract public key for distribution (safe to share)
pisecure generate-signing-key 2>/dev/null | sed -n '/Public Key:/,/Algorithm:/p' > public_key_info.txt

# This file can be safely shared with team members
```

## Step 7: Test Update Signing

### Create Test Update
```bash
# Create a test update manifest
cat > test_update.json << 'EOF'
{
  "version": "1.0.1-test",
  "description": "Test update for verification",
  "publisher": "developer",
  "target_hardware": ["raspberry-pi"],
  "file_mapping": {
    "test_file.py": "/tmp/test_file.py"
  },
  "post_install": ["echo 'Test update installed'"]
}
EOF
```

### Sign the Update
```bash
# Sign the update with your private key
pisecure sign-update test_update.json

# Expected output:
# ✍️ Signing update data...
# ✅ Update signed successfully!
#    Signature: a1b2c3d4...
#    Signed file: test_update_signed.json
```

### Verify Signature
```bash
# Verify the signed update
pisecure verify-update test_update_signed.json

# Should show successful verification with your key
```

## Step 8: Emergency Key Recovery

### If Private Key is Lost
```bash
# Generate new keypair
pisecure generate-signing-key

# Extract new public key
# Register new public key
pisecure register-update-key developer_key_v2 /path/to/new_public_key.pem

# Revoke old key
pisecure revoke-update-key developer_key

# Update threshold if needed
pisecure set-update-threshold 1
```

### Key Compromise Response
```bash
# Immediately revoke compromised key
pisecure revoke-update-key compromised_key_id

# Generate and register replacement key
pisecure generate-signing-key
pisecure register-update-key replacement_key /path/to/new_public_key.pem

# Increase threshold for additional security
pisecure set-update-threshold 2  # Require 2 signatures
```

## Security Best Practices

### Key Management
- **Store private keys offline** when not in use
- **Use strong passwords** for key encryption
- **Regularly rotate keys** (revoke old, register new)
- **Never share private keys** via email or chat
- **Use hardware security modules** for production

### Network Security
- **Run key generation on air-gapped systems**
- **Use encrypted backups** for key storage
- **Monitor blockchain** for unauthorized key registrations
- **Enable firewall** and security services

### Operational Security
- **Limit access** to systems with private keys
- **Audit regularly** using `pisecure list-update-keys`
- **Test updates** on development nodes first
- **Have backup keys** ready for emergencies

## Verification Checklist

- [ ] Private key generated and secured
- [ ] Public key registered on blockchain
- [ ] Signature threshold set appropriately
- [ ] Key listing shows your authorized key
- [ ] Test update signing works
- [ ] Private key backed up securely
- [ ] Emergency recovery procedure documented

## Troubleshooting

### Key Registration Fails
```bash
# Check blockchain connection
pisecure status

# Verify public key format
openssl rsa -pubin -in public_key.pem -text -noout
```

### Signature Verification Fails
```bash
# Check key permissions
pisecure list-update-keys

# Verify threshold settings
pisecure update-status

# Test with known good update
pisecure sign-update test_update.json
pisecure verify-update test_update_signed.json
```

---

**Document Version**: 1.0.0
**Last Updated**: January 2, 2026
**Classification**: CONFIDENTIAL - PRIVATE KEYS NEVER INCLUDED