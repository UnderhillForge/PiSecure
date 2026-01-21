# PiSecure on macOS - Transaction Validation Guide

## Overview

Mac can validate transactions submitted to Pi5 mining nodes **without** running the hardware-verified mining system. This allows Mac users to:

- ✅ **Validate** transactions cryptographically  
- ✅ **Submit** transactions to Pi5 blockchain
- ✅ **Check** balances and transaction history
- ✅ **Track** blockchain state (testnet/mainnet)
- ❌ **Mine** blocks (hardware-verified Pi-only feature)

## Installation

### Step 1: Clone and Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Create Python 3.8+ virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PiSecure with all dependencies
pip install -e .
```

### Step 2: Enable Validation-Only Mode

Set environment variables to skip hardware verification and configure your network:

```bash
# Validation-only mode (skips Pi hardware checks)
export PISECURE_VALIDATE_ONLY=1

# For testnet (optional, default is mainnet)
export PISECURE_TESTNET=1

# Optional: point to specific Pi5 bootstrap node
export PISECURE_BOOTSTRAP_URL=http://pi5.local:3142
```

Add these to your shell profile (`~/.zshrc` or `~/.bash_profile`) to persist across sessions:

```bash
echo 'export PISECURE_VALIDATE_ONLY=1' >> ~/.zshrc
echo 'export PISECURE_TESTNET=1' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Create or Import Wallet

Create a new wallet with Ed25519 private key:

```python
from pisecure.core.wallet import SignWallet

# Create new wallet (keys stored in ~/.pisecure/wallets/)
wallet = SignWallet()
result = wallet.create_wallet('mac_wallet_1', 'My macOS Wallet')

if result['success']:
    print(f"✅ Wallet created!")
    print(f"   Address: {result['address']}")
    print(f"   Keys: {result['key_file']}")
else:
    print(f"❌ Error: {result['error']}")
```

**Or import existing wallet:**

```bash
# Copy wallet JSON and keys from another location
cp /path/to/existing_wallet.json ~/.pisecure/wallets/
cp /path/to/existing_wallet.pem ~/.pisecure/wallets/keys/
```

### Step 4: Connect to Pi5 Node

Three connection options (in order of preference):

**Option 1: Local mDNS (if Pi5 on same network)**
```bash
export PISECURE_BOOTSTRAP_URL=http://pi5.local:3142
```

**Option 2: IP Address**
```bash
export PISECURE_BOOTSTRAP_URL=http://192.168.1.100:3142
```

**Option 3: Remote Bootstrap** (set by bootstrap team)
```bash
export PISECURE_BOOTSTRAP_URL=https://bootstrap.pisecure.org/api/v1/bootstrap/peers
```

## Usage Examples

### Create and Sign Transaction

```python
import time
from pisecure.core.wallet import SignWallet
from pisecure.api.client import PiSecureClient

# Load wallet
wallet = SignWallet()
wallet_data = wallet.load_wallet('mac_wallet_1')

# Create transaction
tx = {
    'type': 'token_transfer',
    'sender_address': wallet_data['address'],
    'recipient_address': 'recipient_address_here',
    'amount': 100.0,
    'timestamp': time.time(),
    'network_id': 'testnet'  # CRITICAL: Must match Pi5 network
}

# Sign transaction (uses local private key)
signature = wallet.sign_transaction(tx)
if signature:
    tx['signature'] = signature
    print(f"✅ Transaction signed: {signature[:20]}...")
else:
    print("❌ Signing failed")
```

### Submit Transaction to Pi5

```python
from pisecure.api.client import PiSecureClient

# Connect to Pi5 via bootstrap discovery
client = PiSecureClient(bootstrap_url="http://pi5.local:3142")

# Submit signed transaction
response = client.submit_transaction(tx)
print(f"Response: {response}")

if response.get('success'):
    print(f"✅ Transaction submitted: {response.get('transaction_hash')}")
else:
    print(f"❌ Submission failed: {response.get('error')}")
```

### Check Wallet Balance

```python
# Query balance from Pi5
wallet_address = wallet_data['address']
balance = client.get_wallet_balance(wallet_address)
print(f"Balance: {balance} PSC")

# Or use local UTXO-based balance (faster, requires sync)
from pisecure.core.utxo import UTXOSet
utxo = UTXOSet()
local_balance = utxo.get_balance(wallet_address)
print(f"Local Balance (UTXO): {local_balance} PSC")
```

### View Transaction History

```python
# Get last 20 transactions for wallet
transactions = client.get_wallet_transactions(wallet_address, limit=20)

for tx in transactions:
    print(f"  {tx['timestamp']}: {tx['sender']} → {tx['recipient']} ({tx['amount']} PSC)")
```

### Validate Transaction Locally

```python
from pisecure.core.blockchain import SignChain

# Create lightweight blockchain instance (no mining)
blockchain = SignChain(use_hybrid_storage=False)

# Validate transaction
validation = blockchain._validate_token_transfer(tx)

if validation['valid']:
    print("✅ Transaction is valid")
else:
    print(f"❌ Validation failed: {validation['error']}")
```

### Sync UTXO Set from Pi5

```python
from pisecure.core.utxo import UTXOSet

# Sync UTXO set for fast local balance queries
utxo = UTXOSet()
utxo.sync_from_blockchain(blockchain)

stats = utxo.get_stats()
print(f"UTXO Stats:")
print(f"  Addresses: {stats['addresses']}")
print(f"  Total Outputs: {stats['total_outputs']}")
print(f"  Total Balance: {stats['total_balance']} PSC")
```

## Configuration Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `PISECURE_VALIDATE_ONLY` | unset | Enable validation-only mode (required for Mac) |
| `PISECURE_TESTNET` | unset | Use testnet (mainnet if unset) |
| `PISECURE_BOOTSTRAP_URL` | auto-detect | Bootstrap server URL |
| `PISECURE_NO_GPIO` | unset | Skip GPIO initialization (set by validation-only) |

## Key Differences: Pi5 vs Mac

| Feature | Pi5 | Mac |
|---------|-----|-----|
| **Mining** | ✅ Hardware-verified PoW | ❌ N/A |
| **Signature Verification** | ✅ RSA-PSS (2048-bit) | ✅ Full verification |
| **Transaction Validation** | ✅ Full node | ✅ Full validation |
| **Balance Tracking** | ✅ Blockchain scan | ✅ UTXO-based (fast) |
| **Network Mode** | ✅ Testnet/Mainnet | ✅ Testnet/Mainnet |
| **Key Management** | Secure local storage | Secure local storage |
| **Data Storage** | `/var/lib/pisecure` | `~/.pisecure` |

## Network Separation

**CRITICAL**: Mac and Pi5 must use the same network!

```bash
# TESTNET (for development/testing)
export PISECURE_TESTNET=1
# Files: ~/.pisecure-testnet/
# Network ID in transactions: "testnet"

# MAINNET (production, default)
unset PISECURE_TESTNET
# Files: ~/.pisecure/
# Network ID in transactions: "mainnet"
```

If networks don't match:
```
❌ Error: Network mismatch: transaction from testnet, node on mainnet
```

## Troubleshooting

### "Cannot detect Raspberry Pi hardware"

**Problem:** This error appears when running on Mac without validation-only mode.

**Solution:**
```bash
export PISECURE_VALIDATE_ONLY=1
```

The error is expected on Mac and skipped in validation-only mode.

### "Network mismatch: transaction from testnet, node on mainnet"

**Problem:** Mac and Pi5 are set to different networks.

**Solution:** Ensure both are set to same network:

```bash
# Both need testnet
export PISECURE_TESTNET=1

# Or both need mainnet (unset PISECURE_TESTNET)
unset PISECURE_TESTNET
```

**Verify current network:**
```python
from pisecure.core.blockchain import SignChain
blockchain = SignChain()
print(f"Node network: {blockchain.network_id}")
```

### "Invalid transaction signature"

**Problem:** Transaction signature verification failed.

**Causes:**
1. Wrong wallet loaded (different private key)
2. Transaction modified after signing
3. Signature corrupted

**Solution:**
```python
# Verify signature
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
result = wallet.verify_transaction_signature(tx, tx['signature'], wallet_data['public_key'])
print(f"Signature valid: {result}")

# Re-sign if needed
tx.pop('signature', None)
new_signature = wallet.sign_transaction(tx)
tx['signature'] = new_signature
```

### "Connection refused: Cannot reach Pi5"

**Problem:** Bootstrap discovery failed or Pi5 is offline.

**Solution:**

```bash
# Test connection
curl -I http://pi5.local:3142/api/v1/health

# Or use specific IP
export PISECURE_BOOTSTRAP_URL=http://192.168.1.100:3142

# Or try remote bootstrap
export PISECURE_BOOTSTRAP_URL=https://bootstrap.pisecure.org
```

### "Insufficient balance"

**Problem:** Wallet balance is too low for transaction.

**Solution:**
```python
# Check balance
balance = client.get_wallet_balance(wallet_address)
print(f"Current balance: {balance} PSC")

# Wait for mining rewards or receive tokens
# Mac clients don't mine, so ask another node to send tokens
```

### "Wallet not found"

**Problem:** Wallet file doesn't exist.

**Solution:**
```bash
# List wallets
ls ~/.pisecure/wallets/

# Create new wallet
python3 -c "
from pisecure.core.wallet import SignWallet
wallet = SignWallet()
result = wallet.create_wallet('mac_wallet_1', 'My Wallet')
print(result)
"
```

## Advanced: Custom Bootstrap URL

To use your own bootstrap server:

```bash
# Set to custom URL
export PISECURE_BOOTSTRAP_URL=https://mybootstrap.example.com

# Then use client
from pisecure.api.client import PiSecureClient
client = PiSecureClient()  # Will use env var
```

## File Locations (macOS)

```
~/.pisecure/
├── wallets/
│   ├── mac_wallet_1.json          # Wallet metadata
│   └── keys/
│       └── mac_wallet_1.pem       # Private key (600 permissions)
├── blockchain.json                # Local blockchain copy (mainnet)
├── peers.json                      # Known peers
└── utxo_set.json                  # UTXO cache for fast balance

~/.pisecure-testnet/               # Testnet directory (if PISECURE_TESTNET=1)
├── blockchain.json
├── peers.json
└── utxo_set.json
```

## Performance Tips

1. **Enable UTXO caching** for fast balance queries:
   ```python
   from pisecure.core.utxo import UTXOSet
   utxo = UTXOSet()
   utxo.sync_from_blockchain(blockchain)
   # Now balance queries are O(1) instead of O(n)
   ```

2. **Use connection pooling** for multiple transactions:
   ```python
   from pisecure.api.client import PiSecureClient
   client = PiSecureClient()  # Reuse client instance
   client.submit_transaction(tx1)
   client.submit_transaction(tx2)  # Reuses connection
   ```

3. **Batch validate transactions**:
   ```python
   for tx in transactions:
       result = blockchain._validate_token_transfer(tx)
       if not result['valid']:
           print(f"Invalid: {result['error']}")
   ```

## Security Considerations

⚠️ **Never share private keys or seed phrases**

```bash
# Private keys stored with restricted permissions (Mac default)
ls -la ~/.pisecure/wallets/keys/
# Output: -rw------- (600 = read/write owner only)

# View key (don't share!)
cat ~/.pisecure/wallets/keys/mac_wallet_1.pem
```

⚠️ **Never commit wallet files to Git**

```bash
# Add to .gitignore
echo "~/.pisecure/" >> .gitignore
echo "wallets/" >> .gitignore
```

## Support

For issues:

1. Check logs: `cat ~/.pisecure/pisecure.log`
2. Enable debug mode: `export PISECURE_DEBUG=1`
3. Run tests: `pytest tests/ -v`
4. Check documentation: `docs/` directory
