# pswallet CLI Migration Summary

## Overview

Moved all wallet, transaction, and blockchain query commands from `pisecure` CLI to standalone `pswallet` CLI for better separation of concerns.

## Command Mapping

### Wallet Operations
| Old Command | New Command | Status |
|------------|-------------|--------|
| `pisecure wallet` | `pswallet list` | ✅ Migrated |
| `pisecure wallet-info` | `pswallet list` | ✅ Migrated |
| `pisecure backup-wallet` | `pswallet backup` | 🔄 Planned |
| `pisecure restore-wallet` | `pswallet restore` | 🔄 Planned |
| `pisecure export-wallet` | `pswallet export` | 🔄 Planned |
| `pisecure import-wallet` | `pswallet import` | 🔄 Planned |
| `pisecure sync-wallet` | `pswallet sync` | 🔄 Planned |

### Transaction Operations
| Old Command | New Command | Status |
|------------|-------------|--------|
| `pisecure create-tx` | `pswallet create-tx` | ✅ Migrated |
| - | `pswallet history` | ✅ New |
| - | `pswallet pending` | ✅ New |
| - | `pswallet send` | 🔄 Planned |

### Blockchain Queries
| Old Command | New Command | Status |
|------------|-------------|--------|
| `pisecure status` | `pswallet status` | ✅ Migrated |
| - | `pswallet block` | ✅ New |
| - | `pswallet validate` | ✅ New |
| `pisecure balance` | `pswallet balance` | ✅ Migrated |

### PiNS Operations
| Old Command | New Command | Status |
|------------|-------------|--------|
| - | `pswallet resolve` | ✅ New |
| - | `pswallet register` | 🔄 Planned |
| - | `pswallet names` | 🔄 Planned |
| - | `pswallet renew` | 🔄 Planned |

## Current pswallet Commands (11 total)

### Wallet (3)
1. `create` - Create new wallet
2. `list` - List all wallets
3. `balance` - Check balance from blockchain

### Transactions (3)
4. `history` - Show transaction history
5. `create-tx` - Create test transactions
6. `pending` - Show pending transactions

### Blockchain (3)
7. `block` - Show block details
8. `status` - Show blockchain status
9. `validate` - Validate blockchain

### PiNS (1)
10. `resolve` - Resolve PiNS name

### Future (1)
11. `send` - Send tokens (planned)

## Architecture

**pswallet** - Wallet & Blockchain Tool
- Wallet management
- Transaction operations
- Blockchain queries
- PiNS resolution

**pisecure** - Mining & System Tool
- Mining operations (`mine`)
- Hardware verification (`entropy`, `verify-hardware`)
- Network operations (`ws`, `peers`)
- System management (`status`, `config`)

## Testing

All commands tested on testnet:

```bash
✅ pswallet --testnet status
   → Shows 2767 blocks, difficulty 146, valid

✅ pswallet --testnet pending
   → Shows 0 pending transactions

✅ pswallet --testnet validate
   → ✅ Valid (2767 blocks)

✅ pswallet --testnet block 0
   → Shows genesis block details

✅ pswallet --testnet list
   → Shows no wallets (expected)
```

## Benefits

1. **Separation of Concerns**: Wallet operations separate from mining
2. **Cleaner UX**: `pswallet` for users, `pisecure` for miners
3. **Better Discoverability**: `pswallet --help` shows only wallet commands
4. **Future Scalability**: Can add wallet-specific features independently

## Backward Compatibility

Original `pisecure` wallet commands still work (for now). No breaking changes.

## Next Steps

1. ✅ Complete basic pswallet implementation
2. ✅ Test all blockchain query commands
3. ✅ Document new CLI
4. 🔄 Add backup/restore with encryption
5. 🔄 Add send tokens functionality
6. 🔄 Add full PiNS registration
7. 🔄 Add deprecation warnings to old `pisecure` wallet commands

## Files Modified

- ✅ `/home/pi/PiSecure/pswallet` - Complete rewrite (256 lines)
- ✅ `/home/pi/PiSecure/PSWALLET_GUIDE.md` - User documentation
- ✅ `/home/pi/PiSecure/PSWALLET_MIGRATION.md` - This file

## Implementation Details

**Language**: Python with Click framework
**Dependencies**: `pisecure.core.SignChain`, `pisecure.core.wallet.SignWallet`
**Output**: Rich tables and JSON support
**Testnet Support**: `--testnet` flag and `PISECURE_TESTNET` env var
