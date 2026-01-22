# Genesis Reset Scripts

Hard-testing toolkit for PiSecure blockchain. Completely resets blockchain state and recreates fresh genesis blocks for both mainnet and testnet.

## Overview

The genesis reset scripts are essential for hard testing phases:
- **Clears all blockchain data** (mainnet & testnet)
- **Removes all wallet keys and balances**
- **Deletes database indexes** (SQLite)
- **Recreates fresh genesis blocks** from scratch
- **Cross-platform compatible** (Linux, macOS, Windows)

## Files

- **`genesis-reset.sh`** - Bash script for Linux/macOS/Windows (Git Bash)
- **`genesis-reset.ps1`** - PowerShell script for Windows native
- **`GENESIS_RESET_README.md`** - This file

## Quick Start

### Linux / macOS

```bash
# Reset with confirmation prompts (safe default)
bash genesis-reset.sh

# Reset without prompts (for CI/CD or automated testing)
bash genesis-reset.sh --force

# Reset with backup of previous state
bash genesis-reset.sh --backup
```

### Windows (PowerShell)

```powershell
# Reset with confirmation prompts (safe default)
.\genesis-reset.ps1

# Reset without prompts (for CI/CD or automated testing)
.\genesis-reset.ps1 -Force

# Reset with backup of previous state
.\genesis-reset.ps1 -Backup
```

### Windows (Git Bash)

If you have Git Bash installed, you can use the bash script:

```bash
bash genesis-reset.sh [options]
```

## What Gets Deleted

### Directories Cleared
- `~/.pisecure/` - Mainnet blockchain data
- `/var/lib/pisecure/` - Mainnet blockchain (alternate location)
- `~/.pisecure-testnet/` - Testnet blockchain data
- `/var/lib/pisecure-testnet/` - Testnet blockchain (alternate location)
- `~/.pisecure/wallets/` - All wallet keys and data
- `/var/lib/pisecure/wallets/` - Wallet storage (alternate location)

### Files Deleted Within Directories
- `blockchain.json` - JSON blockchain file
- `pending_transactions.json` - Pending transaction queue
- `*.db` - SQLite database files
- `blk*.dat` - Hybrid storage block files
- `index.db` - Block index database
- `wallet_*` - All wallet key files
- `*.key` - Private key files

### What's NOT Deleted
- Configuration files in `/etc/pisecure/`
- API server keys/certificates
- CLI configuration
- Plugin data (unless explicitly in `~/.pisecure/`)

## Options

### `--force` / `-Force`
Skip all confirmation prompts. Useful for:
- Automated testing pipelines
- CI/CD environments
- Scripted test scenarios

**⚠️ Use with caution** - no second chance!

```bash
# Bash version
bash genesis-reset.sh --force

# PowerShell version
.\genesis-reset.ps1 -Force
```

### `--backup` / `-Backup`
Create compressed backup of all data before deletion:
- Bash: `backup-YYYYMMDD-HHMMSS.tar.gz`
- PowerShell: `backup-YYYYMMDD-HHMMSS.zip`

Backup stored in current directory.

```bash
# Bash version
bash genesis-reset.sh --backup

# PowerShell version
.\genesis-reset.ps1 -Backup
```

Combine options:
```bash
bash genesis-reset.sh --force --backup
```

## Safety Features

### Bash Version
1. **Clear confirmation prompts** - Requires typing exact phrases
   - First: `DELETE ALL`
   - Second: `YES, DELETE`
2. **Automatic detection** - Shows what exists before deletion
3. **Graceful failures** - Non-existent directories don't cause errors
4. **Optional backup** - Pre-deletion backup available
5. **Cross-platform detection** - Identifies Linux, macOS, Windows

### PowerShell Version
1. **Clear confirmation prompts** - Same two-step confirmation
2. **Directory validation** - Checks before deletion
3. **Automatic backup** - Optional pre-deletion zip archive
4. **Error handling** - Continues even if some items don't exist
5. **Colored output** - Clear visual feedback

## Usage Scenarios

### Scenario 1: Hard Testing Reset (No Backup)
```bash
bash genesis-reset.sh --force
```
Best for:
- Repeated testing cycles
- Quick blockchain state reset
- Test suite runs

### Scenario 2: Safe Manual Reset (With Backup)
```bash
bash genesis-reset.sh --backup
```
Best for:
- First time running
- Want to save current state
- Troubleshooting before fresh start

### Scenario 3: CI/CD Pipeline
```bash
#!/bin/bash
# Pre-test setup
bash genesis-reset.sh --force --backup

# Run test suite
pytest tests/

# Archive backup for debugging
mv backup-*.tar.gz test-artifacts/
```

### Scenario 4: Testnet Hard Reset on Mac
```bash
# Test environment
export PISECURE_TESTNET=1
export PISECURE_MOCK_HARDWARE=1

# Reset testnet only
bash genesis-reset.sh --force

# Fresh testnet ready
PISECURE_VALIDATE_ONLY=1 pisecure mine
```

## Verification After Reset

### Check Fresh Genesis Created
```bash
# Bash check
ls -la ~/.pisecure/
ls -la ~/.pisecure-testnet/

# Should show:
# - blockchain.json (fresh genesis)
# - index.db (fresh database)
# - blk0000.dat (fresh block file if hybrid storage)
```

### Verify Blockchain State
```bash
pisecure status

# Should show:
# ✅ Chain Valid: Yes
# 📦 Total Blocks: 1 (just genesis)
# ⛓️ Genesis Block: [valid hash]
```

### Test Mining on Fresh Genesis
```bash
# Mainnet mining
pisecure mine

# Or testnet with mock hardware
export PISECURE_TESTNET=1
export PISECURE_MOCK_HARDWARE=1
pisecure mine
```

## Troubleshooting

### "Permission denied" on Linux/macOS
```bash
# Make script executable
chmod +x genesis-reset.sh

# Or run with explicit bash
bash genesis-reset.sh
```

### PowerShell "cannot be loaded" on Windows
```powershell
# Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run
.\genesis-reset.ps1
```

### Blockchain won't recreate
```bash
# Ensure Python environment is activated
source pisecure_env/bin/activate  # Linux/macOS

# Check PiSecure is importable
python -c "from pisecure.core import SignChain; print('✓ OK')"

# Try reset again
bash genesis-reset.sh --force
```

### Backup file too large
- Default: Creates tar.gz (bash) or zip (PowerShell)
- Consider removing old backups
- Or use `--force` without `--backup` for fresh resets

### Multiple data locations detected
Script handles both common locations:
- `~/.pisecure/` (user home)
- `/var/lib/pisecure/` (system directory)

Script will delete from both if they exist. This is intentional to ensure clean reset.

## Cross-Platform Notes

### Linux / macOS
- Uses standard bash (`#!/bin/bash`)
- Compatible with zsh on macOS
- Tested on Ubuntu 20.04+, macOS 11+

### Windows (PowerShell)
- Requires PowerShell 5.0+ (included in Windows 10+)
- Run as Administrator for best results
- Uses `$USERPROFILE` for home directory

### Windows (Git Bash)
- Use bash script: `bash genesis-reset.sh`
- Requires Git for Windows installed
- Same behavior as Linux/macOS version

## Performance Impact

- **Delete time**: Depends on data size
  - Empty/small: <1 second
  - Large blockchain (1000+ blocks): 2-10 seconds
- **Genesis creation**: ~1-2 seconds
- **Total execution**: Usually <10 seconds

## Recovery

**⚠️ WARNING:** Once deleted, data cannot be recovered (unless backup was created).

To recover from backup:
```bash
# Extract tar.gz backup (bash)
tar -xzf backup-YYYYMMDD-HHMMSS.tar.gz

# Or extract zip backup (PowerShell)
Expand-Archive -Path backup-YYYYMMDD-HHMMSS.zip
```

## Contributing

To improve these scripts:
1. Test on target OS (Linux/macOS/Windows)
2. Test with various data sizes
3. Verify backup functionality
4. Update this README with changes

## License

These scripts are part of PiSecure and follow the same license as the main project.

---

**Last Updated:** January 21, 2026
**Version:** 1.0
**Tested Platforms:** Linux (Ubuntu 20.04+), macOS 11+, Windows 10/11
