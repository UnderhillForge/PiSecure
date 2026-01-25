# PiSecure Trusted Keys

This directory contains **public cryptographic keys** used for verifying the authenticity and integrity of PiSecure components.

## Genesis Authority Public Key

**File**: `genesis_auth_pub.key`

This RSA public key is used to verify:
- Foundation trust transactions
- OTA update signatures
- Genesis block authenticity

### Key Details
- **Algorithm**: RSA-PSS
- **Key Size**: 2048 bits
- **Format**: PEM-encoded X.509 SubjectPublicKeyInfo

### Security Notes
- This public key is **safe to distribute** and include in version control
- It can only be used for **verification**, not signing
- The corresponding private key is kept completely secure and offline
- This key establishes the cryptographic identity of the PiSecure genesis authority

### Usage in Code
```python
from cryptography.hazmat.primitives import serialization

# Load the public key
with open('pisecure/trusted_keys/genesis_auth_pub.key', 'rb') as f:
    public_key = serialization.load_pem_public_key(f.read())

# Use for signature verification
# (Signature verification code would go here)
```

## Important
Never commit private keys to this repository. Private keys should always remain offline and secure.