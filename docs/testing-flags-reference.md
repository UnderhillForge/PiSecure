# Testing Flags Quick Reference

## Global Flags

### `--test`
**Testnet Mode** - Uses isolated data directory for safe testing

```bash
pisecure --test <command>
```

- **Data Directory**: `/var/lib/pisecure-testnet/`
- **Wallets**: `/var/lib/pisecure-testnet/wallets/`
- **Config**: `/etc/pisecure/config-testnet.json`
- **Purpose**: Development, testing, experimentation
- **State Changes**: ✅ Allowed (but isolated)

### `--validate-only`
**Validation Mode** - Read-only operations, no state changes

```bash
pisecure --validate-only <command>
```

- **Data Directory**: Default (`/var/lib/pisecure/`)
- **Purpose**: Auditing, validation, read-only access
- **State Changes**: ❌ Blocked

### Combined: `--test --validate-only`
**Safe Testing** - Testnet + read-only

```bash
pisecure --test --validate-only <command>
```

- **Data Directory**: Testnet
- **Purpose**: CI/CD testing, validation logic testing
- **State Changes**: ❌ Blocked

## Command Reference

| Command | `--test` | `--validate-only` | Combined |
|---------|----------|-------------------|----------|
| `status` | ✅ Testnet status | ✅ Read mainnet | ✅ Read testnet |
| `mine` | ✅ Mine testnet | ❌ Blocked | ❌ Blocked |
| `create-tx` | ✅ Add to testnet | ❌ Blocked | ❌ Blocked |
| `wallet` | ✅ Testnet wallets | ✅ Read mainnet | ✅ Read testnet |
| `mining-info` | ✅ Show info | ✅ Show info | ✅ Show info |
| `verify-hardware` | ✅ Verify | ✅ Verify | ✅ Verify |
| `syndicate status` | ✅ Testnet status | ✅ Read status | ✅ Read testnet |

## Quick Examples

```bash
# Development
pisecure --test mine --wallet dev_wallet

# Testing
pisecure --test create-tx --count 10
pisecure --test status

# Validation
pisecure --validate-only status
pisecure --validate-only mining-info

# CI/CD
pisecure --test --validate-only status

# Production
pisecure mine --wallet prod_wallet  # No flags = mainnet
```

## Setup Testnet

```bash
# Create testnet directories
sudo mkdir -p /var/lib/pisecure-testnet/wallets
sudo chown -R $USER:$USER /var/lib/pisecure-testnet

# Initialize testnet blockchain
pisecure --test status
```

## Python API

```python
from pisecure.core.blockchain import SignChain
from pisecure.core.wallet import SignWallet

# Testnet
testnet_chain = SignChain(
    chain_file="/var/lib/pisecure-testnet/blockchain.json",
    difficulty=1
)

testnet_wallet = SignWallet(
    wallet_dir="/var/lib/pisecure-testnet/wallets"
)

# Mainnet
mainnet_chain = SignChain()  # Uses /var/lib/pisecure/blockchain.json
```

## Full Documentation

See [docs/testing-modes.md](testing-modes.md) for complete documentation.
