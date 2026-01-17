# Testing and Validation Modes

PiSecure provides two important flags for safe testing and validation: `--test` and `--validate-only`.

## Overview

| Flag | Purpose | Data Directory | State Changes |
|------|---------|----------------|---------------|
| `--test` | Testnet mode | `/var/lib/pisecure-testnet/` | ✅ Allowed |
| `--validate-only` | Validation mode | Default | ❌ Blocked |
| `--test --validate-only` | Safe testing | Testnet | ❌ Blocked |

## Testnet Mode (`--test`)

Use testnet mode for development and testing without affecting your production blockchain.

### Features

- **Isolated Data Directory**: Uses `/var/lib/pisecure-testnet/` instead of `/var/lib/pisecure/`
- **Separate Wallets**: Wallet directory at `/var/lib/pisecure-testnet/wallets/`
- **Separate Config**: Uses `/etc/pisecure/config-testnet.json`
- **Full Functionality**: All operations work normally (mining, transfers, etc.)

### Usage

```bash
# Check testnet blockchain status
pisecure --test status

# Mine on testnet
pisecure --test mine --wallet <test_address>

# Create testnet wallet
pisecure --test wallet

# Add test transactions to testnet
pisecure --test create-tx --count 10

# Show syndicate status on testnet
pisecure --test syndicate status
```

### Benefits

✅ Safe experimentation without risking production data  
✅ Test network upgrades before mainnet deployment  
✅ Development and debugging with real blockchain operations  
✅ CI/CD pipeline integration for automated testing  
✅ Lower difficulty for faster block mining  

### Testnet Setup

```bash
# Create testnet directories
sudo mkdir -p /var/lib/pisecure-testnet/wallets
sudo chown -R $USER:$USER /var/lib/pisecure-testnet

# Optional: Create testnet config
sudo cp /etc/pisecure/config.json /etc/pisecure/config-testnet.json
```

## Validate-Only Mode (`--validate-only`)

Use validate-only mode for read-only operations and validation without modifying blockchain state.

### Features

- **Read-Only Operations**: All queries work, state changes are blocked
- **Safe Inspection**: Check blockchain integrity without risk
- **Validation Testing**: Test validation logic without side effects
- **Production Safe**: Can run against mainnet without concerns

### Usage

```bash
# Check blockchain status (read-only)
pisecure --validate-only status

# Validate blockchain integrity
pisecure --validate-only status

# Show PiHash mining information
pisecure --validate-only mining-info

# Check wallet balance (read-only)
pisecure --validate-only wallet <wallet_name>

# View syndicate status (read-only)
pisecure --validate-only syndicate status
```

### Allowed Operations (Read-Only)

✅ `pisecure --validate-only status` - Blockchain status  
✅ `pisecure --validate-only mining-info` - PiHash information  
✅ `pisecure --validate-only wallet` - View wallet balances  
✅ `pisecure --validate-only syndicate status` - View syndicate info  
✅ `pisecure --validate-only verify-hardware` - Hardware verification  

### Blocked Operations (State-Changing)

❌ `pisecure --validate-only mine` - Mining blocks  
❌ `pisecure --validate-only create-tx` - Creating transactions  
❌ Wallet creation  
❌ Token transfers  
❌ Name registration  
❌ Trust/loan operations  

When a blocked operation is attempted, you'll see:
```
⚠️ WARNING: Skipping mining - VALIDATE-ONLY mode active
```

## Combined Mode (`--test --validate-only`)

Combine both flags for the safest testing environment.

### Features

- **Isolated + Read-Only**: Uses testnet directory with no state changes
- **Perfect for CI/CD**: Automated testing without side effects
- **Validation Testing**: Test validation logic on testnet data
- **Zero Risk**: Cannot affect production or persist changes

### Usage

```bash
# Test blockchain validation on testnet
pisecure --test --validate-only status

# Test PiHash validation logic
pisecure --test --validate-only mining-info

# Test wallet balance calculations
pisecure --test --validate-only wallet

# Verify testnet blockchain integrity
pisecure --test --validate-only status
```

### Use Cases

🔬 **Testing Validation Logic**
```bash
# Test blockchain validation algorithm
pisecure --test --validate-only status
```

🚀 **CI/CD Pipelines**
```bash
# Run in GitHub Actions / Jenkins
pisecure --test --validate-only status
pisecure --test --validate-only mining-info
```

🐛 **Debugging**
```bash
# Inspect testnet state without changes
pisecure --test --validate-only wallet <test_wallet>
```

📊 **Auditing**
```bash
# Audit blockchain integrity on testnet
pisecure --test --validate-only status
```

## Examples

### Example 1: Testing Mining Setup

```bash
# Setup testnet for mining tests
pisecure --test status
pisecure --test create-tx --count 5
pisecure --test mine --wallet test_miner_address

# Verify results (read-only)
pisecure --test --validate-only status
```

### Example 2: Validating Production Blockchain

```bash
# Check mainnet status without changes
pisecure --validate-only status

# Verify blockchain integrity
pisecure --validate-only status

# View wallet balances (read-only)
pisecure --validate-only wallet
```

### Example 3: Development Workflow

```bash
# Develop on testnet
pisecure --test mine --wallet dev_wallet
pisecure --test create-tx --count 10
pisecure --test mine --wallet dev_wallet

# Test validation logic
pisecure --test --validate-only status

# Deploy to mainnet when ready
pisecure mine --wallet production_wallet
```

### Example 4: Automated Testing

```bash
#!/bin/bash
# test-blockchain.sh

set -e

echo "Testing PiSecure Blockchain..."

# Test blockchain initialization
pisecure --test --validate-only status

# Test PiHash algorithm
pisecure --test --validate-only mining-info

# Test hardware verification
pisecure --test --validate-only verify-hardware

echo "All tests passed!"
```

## Python API

You can also use these modes in Python code:

```python
from pisecure.core.blockchain import SignChain
from pisecure.core.wallet import SignWallet

# Testnet blockchain
testnet_chain = SignChain(
    chain_file="/var/lib/pisecure-testnet/blockchain.json",
    difficulty=1  # Lower difficulty for testing
)

# Testnet wallet
testnet_wallet = SignWallet(
    wallet_dir="/var/lib/pisecure-testnet/wallets"
)

# Validate-only operations (just don't call state-changing methods)
info = testnet_chain.get_chain_info()  # ✅ Read-only
is_valid = testnet_chain.validate_chain()  # ✅ Read-only
# testnet_chain.mine_pending_transactions()  # ❌ Don't call in validate-only
```

## Environment Variables

You can also use environment variables:

```bash
# Set testnet mode
export PISECURE_TESTNET=1
pisecure status  # Uses testnet

# Set validate-only mode
export PISECURE_VALIDATE_ONLY=1
pisecure status  # Read-only mode
```

## Best Practices

### Development

1. **Always use `--test` for development**
   ```bash
   pisecure --test mine --wallet dev_address
   ```

2. **Test validation with `--validate-only`**
   ```bash
   pisecure --test --validate-only status
   ```

3. **Keep testnet difficulty low (1-2)**
   ```python
   SignChain(chain_file="testnet.json", difficulty=1)
   ```

### Production

1. **Use `--validate-only` for audits**
   ```bash
   pisecure --validate-only status
   ```

2. **Never use `--test` on production servers**
   - Testnet flag is for development only
   - Production should use default paths

3. **Backup before major changes**
   ```bash
   # Backup mainnet
   cp -r /var/lib/pisecure /var/lib/pisecure-backup-$(date +%Y%m%d)
   
   # Test on testnet first
   pisecure --test <operation>
   
   # Then apply to mainnet
   pisecure <operation>
   ```

### CI/CD

1. **Use combined mode for tests**
   ```yaml
   # .github/workflows/test.yml
   - name: Test Blockchain
     run: |
       pisecure --test --validate-only status
       pisecure --test --validate-only mining-info
   ```

2. **Clean up testnet after tests**
   ```bash
   rm -rf /var/lib/pisecure-testnet/*
   ```

## Troubleshooting

### Issue: "Permission denied" on testnet directory

```bash
# Fix permissions
sudo mkdir -p /var/lib/pisecure-testnet
sudo chown -R $USER:$USER /var/lib/pisecure-testnet
```

### Issue: Testnet blockchain not found

```bash
# Initialize testnet
pisecure --test status
# This will create the genesis block
```

### Issue: Validate-only mode blocks needed operation

```bash
# Remove --validate-only flag
pisecure mine --wallet <address>

# Or use testnet for testing
pisecure --test mine --wallet <address>
```

## See Also

- [Getting Started](getting-started.md) - Basic PiSecure setup
- [Mining Guide](pihash-network-integration.md) - PiHash mining details
- [API Documentation](api-documentation.txt) - REST API reference
- [Examples](../examples/) - Code examples
