#!/bin/bash
# Quick Reference for Genesis Reset Scripts
# Run this file to see available commands and options

cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║         PiSecure Genesis Reset - Quick Reference              ║
╚════════════════════════════════════════════════════════════════╝

📦 WHAT'S INCLUDED:

  ✓ genesis-reset.sh             (Bash version - Linux/macOS)
  ✓ genesis-reset.ps1            (PowerShell version - Windows)
  ✓ GENESIS_RESET_README.md      (Full documentation)
  ✓ GENESIS_RESET_INTEGRATION.md (Testing integration guide)
  ✓ genesis-reset-reference.sh   (This file)


🚀 QUICK START:

  Linux / macOS:
  $ bash genesis-reset.sh [--force] [--backup]

  Windows (PowerShell):
  > .\genesis-reset.ps1 [-Force] [-Backup]

  Windows (Git Bash):
  $ bash genesis-reset.sh [--force] [--backup]


🎯 COMMON USE CASES:

  1. Safe interactive reset (with confirmations):
     $ bash genesis-reset.sh

  2. Fast automated reset (no prompts):
     $ bash genesis-reset.sh --force

  3. Reset with backup before deletion:
     $ bash genesis-reset.sh --backup

  4. Full automated: reset + backup + no prompts:
     $ bash genesis-reset.sh --force --backup

  5. Reset only testnet:
     $ PISECURE_TESTNET=1 bash genesis-reset.sh --force

  6. Reset for testing with mock hardware:
     $ PISECURE_MOCK_HARDWARE=1 bash genesis-reset.sh --force


📋 WHAT GETS DELETED:

  Blockchain:
  • ~/.pisecure/                (mainnet)
  • ~/.pisecure-testnet/        (testnet)
  • /var/lib/pisecure/          (mainnet alt)
  • /var/lib/pisecure-testnet/  (testnet alt)

  Wallets:
  • ~/.pisecure/wallets/        (all wallet keys)
  • /var/lib/pisecure/wallets/  (alt location)

  Data Files:
  • blockchain.json             (blockchain)
  • pending_transactions.json   (mempool)
  • *.db                        (SQLite databases)
  • blk*.dat                    (hybrid storage blocks)
  • index.db                    (block index)
  • All wallet key files


✅ WHAT STAYS INTACT:

  • /etc/pisecure/              (config files)
  • API certificates/keys       (unless in deleted dirs)
  • Plugin data                 (unless in deleted dirs)
  • CLI configuration           (unless in deleted dirs)


🔒 SAFETY FEATURES:

  ✓ Clear confirmation prompts (requires typing exact phrases)
  ✓ Shows what will be deleted before starting
  ✓ Optional backup before deletion
  ✓ Graceful handling of missing directories
  ✓ Automatic detection of OS and environment
  ✓ Colored, easy-to-read output
  ✓ Support for --force mode for CI/CD pipelines


⚙️ OPTIONS:

  --force / -Force
    • Skip confirmation prompts
    • Useful for automated testing
    • Use with caution!

  --backup / -Backup
    • Create compressed backup before deletion
    • Bash: backup-YYYYMMDD-HHMMSS.tar.gz
    • PowerShell: backup-YYYYMMDD-HHMMSS.zip
    • Stored in current directory


🧪 TESTING INTEGRATION:

  In Makefile:
    make reset              # Reset blockchain
    make hard-test          # Reset + run tests

  In pytest:
    PISECURE_HARD_TEST=1 pytest tests/

  In CI/CD:
    bash genesis-reset.sh --force --backup
    pytest tests/
    mv backup-*.tar.gz artifacts/


📚 FULL DOCUMENTATION:

  Main docs:
    • GENESIS_RESET_README.md         (Complete reference)
    • GENESIS_RESET_INTEGRATION.md    (Integration examples)

  In scripts:
    • genesis-reset.sh                (Bash - inline comments)
    • genesis-reset.ps1               (PowerShell - inline comments)


🐛 TROUBLESHOOTING:

  "Permission denied":
    $ chmod +x genesis-reset.sh

  PowerShell "cannot be loaded":
    PS> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

  "Blockchain won't recreate":
    $ python -c "from pisecure.core import SignChain; print('✓')"

  See GENESIS_RESET_README.md for more troubleshooting


✨ AFTER RESET:

  Verify fresh genesis:
    $ pisecure status
    # Should show: "✅ Chain Valid: Yes", "📦 Total Blocks: 1"

  Start mining on fresh blockchain:
    $ pisecure mine

  Testnet with validation:
    $ export PISECURE_TESTNET=1
    $ export PISECURE_VALIDATE_ONLY=1
    $ export PISECURE_MOCK_HARDWARE=1
    $ pisecure mine


📊 PERFORMANCE:

  Delete time:        <1-10 seconds (depends on blockchain size)
  Genesis creation:   ~1-2 seconds
  Total execution:    Usually <15 seconds
  Per-test overhead:  ~2-5 seconds


🔗 WORKFLOWS:

  Recommended test flow:
    1. bash genesis-reset.sh --force    (clear old state)
    2. pytest tests/                    (run tests)
    3. Review results
    4. Repeat

  Recommended backup flow:
    1. bash genesis-reset.sh --backup   (save state)
    2. Run experiments
    3. Restore from backup if needed


════════════════════════════════════════════════════════════════

For complete documentation, see:
  • GENESIS_RESET_README.md (main reference)
  • GENESIS_RESET_INTEGRATION.md (testing patterns)

For example usage, see:
  • genesis-reset.sh (inline comments in script)
  • genesis-reset.ps1 (inline comments in script)

════════════════════════════════════════════════════════════════

EOF
