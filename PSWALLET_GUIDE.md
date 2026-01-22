# pswallet - PiSecure Wallet CLI Guide

Complete wallet management and blockchain interaction tool for PiSecure.

## Overview

`pswallet` is a standalone CLI tool that handles:
- **Wallet Operations**: Create, list, view balances
- **Transactions**: View history, create test transactions, check pending
- **Blockchain Queries**: Block details, status, validation
- **PiNS**: Name resolution (future: registration)

## Installation

Already available in `/home/pi/PiSecure/pswallet` (executable).

## Global Options

```bash
pswallet --testnet      # Use testnet blockchain
pswallet --json         # JSON output
pswallet --wallet-dir   # Custom wallet directory
pswallet --quiet        # Suppress network messages
```

## Wallet Commands

### Create Wallet
```bash
pswallet create my-wallet
pswallet create my-wallet --display-name "My Main Wallet"
pswallet --testnet create test-wallet
```

### List Wallets
```bash
pswallet list
pswallet --testnet list
```
Shows: Name, Address (truncated), Balance

### Check Balance
```bash
pswallet balance Pi3XXXXXXXXXXX
pswallet --testnet balance Pi3XXXXXXXXXXX
pswallet --json balance Pi3XXXXXXXXXXX
```

## Transaction Commands

### View History
```bash
pswallet history Pi3XXXXXXXXXXX
pswallet history Pi3XXXXXXXXXXX --limit 50
pswallet --json history Pi3XXXXXXXXXXX
```

### Create Test Transactions
```bash
pswallet create-tx
pswallet create-tx --count 10
```

### View Pending Transactions
```bash
pswallet pending
pswallet --json pending
```

## Blockchain Commands

### Show Block Details
```bash
pswallet block 0        # Genesis block
pswallet block 100      # Block #100
pswallet --json block 0 # JSON format
```

### Blockchain Status
```bash
pswallet status
pswallet --testnet status
```
Shows: Blocks, Pending TX, Difficulty, Valid

### Validate Blockchain
```bash
pswallet validate
pswallet --testnet validate
```

## PiNS Commands

### Resolve Name
```bash
pswallet resolve myname
pswallet resolve myname.pisecure
pswallet --json resolve myname
```

## Examples

### Check testnet status
```bash
PISECURE_QUIET=1 pswallet --testnet status
```

### View genesis block
```bash
pswallet block 0
```

### List all testnet wallets
```bash
pswallet --testnet list
```

### Check balance with JSON output
```bash
pswallet --json balance Pi3XXXXXXXXXXX
```

## Differences from `pisecure` CLI

**pswallet**: Wallet, transactions, blockchain queries
**pisecure**: Mining, hardware verification, system operations

Migration from `pisecure`:
- `pisecure wallet` → `pswallet list`
- `pisecure wallet-info` → `pswallet list` (shows balance)
- `pisecure create-tx` → `pswallet create-tx`

## File Locations

**Mainnet:**
- Wallets: `/var/lib/pisecure/wallets/` or `~/.pisecure/wallets/`
- Blockchain: `/var/lib/pisecure/`

**Testnet:**
- Wallets: `/var/lib/pisecure-testnet/wallets/` or `~/.pisecure-testnet/wallets/`
- Blockchain: `/var/lib/pisecure-testnet/`

## JSON Output

All commands support `--json` flag for programmatic access:

```bash
# Note: --json must come BEFORE the command
pswallet --json status | jq '.blocks'
pswallet --json balance Pi3XXX | jq '.balance'
pswallet --json list | jq '.[0].address'

# For cleaner JSON (suppress loading messages):
PISECURE_QUIET=1 pswallet --testnet --json status
```

## Environment Variables

- `PISECURE_TESTNET=1` - Use testnet
- `PISECURE_QUIET=1` - Suppress Rich console output
- `PISECURE_NO_WEBSOCKET=1` - Disable WebSocket auto-connect

## Future Features

- [ ] Send tokens (`pswallet send`)
- [ ] Backup/restore with encryption (`pswallet backup`, `pswallet restore`)
- [ ] Export/import wallet metadata
- [ ] PiNS registration (`pswallet register`)
- [ ] Multi-signature wallets
- [ ] Hardware wallet integration
