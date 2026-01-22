# Genesis Reset Integration Guide

Quick reference for using genesis reset in testing workflows.

## Installation

Both scripts are included in the repository root:

```
/home/pi/PiSecure/
├── genesis-reset.sh         # Bash version (Linux/macOS/Git Bash)
├── genesis-reset.ps1        # PowerShell version (Windows native)
└── GENESIS_RESET_README.md  # Full documentation
```

Scripts are ready to use immediately - no additional installation needed.

## In Test Suite

### Using in pytest

```python
# tests/conftest.py
import subprocess
import os

def pytest_configure(config):
    """Reset blockchain before running tests"""
    if os.environ.get('PISECURE_HARD_TEST'):
        subprocess.run(
            ['bash', 'genesis-reset.sh', '--force'],
            cwd='/home/pi/PiSecure',
            check=True
        )

def pytest_unconfigure(config):
    """Optional: Backup blockchain after tests"""
    if os.environ.get('PISECURE_BACKUP_TESTS'):
        subprocess.run(
            ['bash', 'genesis-reset.sh', '--backup'],
            cwd='/home/pi/PiSecure',
            check=True
        )
```

Usage:
```bash
# Run tests with hard reset
PISECURE_HARD_TEST=1 pytest tests/

# Run and backup after
PISECURE_HARD_TEST=1 PISECURE_BACKUP_TESTS=1 pytest tests/
```

## In Makefile

Add to `Makefile`:

```makefile
.PHONY: hard-test
hard-test: reset
	pytest tests/ -v --tb=short

.PHONY: reset
reset:
	@echo "🧹 Resetting blockchain for hard testing..."
	bash genesis-reset.sh --force --backup

.PHONY: reset-testnet
reset-testnet:
	@PISECURE_TESTNET=1 bash genesis-reset.sh --force
```

Usage:
```bash
make reset                # Reset both mainnet & testnet
make reset-testnet        # Reset only testnet
make hard-test            # Reset then run tests
```

## In CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/hard-test.yml
name: Hard Testing

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Reset blockchain
        run: bash genesis-reset.sh --force
      
      - name: Run hard tests
        run: pytest tests/ -v
      
      - name: Save backups
        if: failure()
        uses: actions/upload-artifact@v2
        with:
          name: blockchain-backup
          path: backup-*.tar.gz
```

### Jenkins

```groovy
pipeline {
    stages {
        stage('Reset') {
            steps {
                sh 'bash genesis-reset.sh --force'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest tests/ -v'
            }
        }
        stage('Archive Backups') {
            when {
                unsuccessful()
            }
            steps {
                archiveArtifacts artifacts: 'backup-*.tar.gz'
            }
        }
    }
}
```

## Testing Different Scenarios

### Scenario: Complete Hard Reset

```bash
#!/bin/bash
set -e

echo "🔄 Complete Hard Testing Cycle"

# Reset mainnet
echo "1️⃣ Resetting mainnet..."
bash genesis-reset.sh --force

# Run mainnet tests
echo "2️⃣ Testing mainnet..."
pytest tests/blockchain/ -v

# Reset testnet
echo "3️⃣ Resetting testnet..."
PISECURE_TESTNET=1 bash genesis-reset.sh --force

# Run testnet tests
echo "4️⃣ Testing testnet..."
PISECURE_TESTNET=1 pytest tests/blockchain/ -v

echo "✅ All hard tests passed!"
```

### Scenario: Mac Validation Testing

```bash
#!/bin/bash

export PISECURE_TESTNET=1
export PISECURE_MOCK_HARDWARE=1
export PISECURE_VALIDATE_ONLY=1

echo "🍎 Mac Validation Testing"

# Fresh testnet
bash genesis-reset.sh --force

# Start validator
echo "Starting validation node..."
pisecure mine &
MINER_PID=$!

# Wait for blocks
sleep 30

# Test validation
echo "Testing validation..."
pisecure status

# Cleanup
kill $MINER_PID

echo "✅ Mac validation test complete!"
```

### Scenario: Mining Performance Testing

```bash
#!/bin/bash

echo "⚙️ Mining Performance Test"

# Fresh blockchain
bash genesis-reset.sh --force

# Start mining with timing
echo "Mining 10 blocks..."
time {
    for i in {1..10}; do
        pisecure mine --blocks=1
        echo "✓ Block $i"
    done
}

# Report statistics
pisecure status | grep -E "(Total Blocks|Hashrate|Block)"

echo "✅ Performance test complete!"
```

## Environment Variables

When using genesis reset scripts, these environment variables affect behavior:

### PiSecure Configuration
- `PISECURE_TESTNET=1` - Use testnet blockchain
- `PISECURE_VALIDATE_ONLY=1` - Validation-only mode (no mining)
- `PISECURE_MOCK_HARDWARE=1` - Mock hardware for testing (Linux/Mac)
- `PISECURE_QUIET=1` - Suppress Rich formatted output

### Script Behavior
- `HOME` / `USERPROFILE` - Home directory (set by OS)
- Standard shell variables work as expected

Example combined:
```bash
# Reset testnet, then run validation tests
PISECURE_TESTNET=1 bash genesis-reset.sh --force
PISECURE_TESTNET=1 PISECURE_VALIDATE_ONLY=1 PISECURE_MOCK_HARDWARE=1 pytest tests/validation/
```

## Monitoring Reset Progress

### Bash Version
Script outputs colored progress:
```
🔍 Detected OS: linux
📋 This will DELETE: ...
🧹 Deleting existing blockchain and wallet data...
✨ Creating fresh genesis directories...
📝 Generating fresh genesis blocks...
✅ GENESIS RESET COMPLETE!
```

### PowerShell Version
Same colored output with PowerShell formatting:
```
🔍 Detected OS: Windows (PowerShell)
📋 This will DELETE: ...
🧹 Deleting existing blockchain and wallet data...
✨ Creating fresh genesis directories...
📝 Generating fresh genesis blocks...
✅ GENESIS RESET COMPLETE!
```

## Common Test Patterns

### Pattern 1: Reset Before Each Test Class

```python
import pytest
import subprocess

class TestBlockchainHard:
    @classmethod
    def setup_class(cls):
        """Reset before running class tests"""
        subprocess.run(['bash', 'genesis-reset.sh', '--force'], check=True)
    
    def test_mining_produces_valid_blocks(self):
        # Tests with fresh genesis
        pass
    
    def test_chain_validation(self):
        # Tests with fresh genesis
        pass
```

### Pattern 2: Reset Per-Test Method

```python
class TestBlockchainHardPerMethod:
    def setup_method(self):
        """Reset before each test"""
        subprocess.run(['bash', 'genesis-reset.sh', '--force'], check=True)
    
    def test_clean_genesis_exists(self):
        from pisecure.core import SignChain
        chain = SignChain()
        assert len(chain.chain) == 1  # Only genesis
```

### Pattern 3: Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("scenario", [
    "clean_genesis",
    "after_blocks",
    "corrupted_state"
])
def test_validation_scenarios(scenario):
    # Reset for each scenario
    subprocess.run(['bash', 'genesis-reset.sh', '--force'], check=True)
    
    # Setup scenario-specific state
    if scenario == "after_blocks":
        mine_test_blocks(10)
    elif scenario == "corrupted_state":
        corrupt_blockchain()
    
    # Run validation test
    assert validate_blockchain() == True
```

## Troubleshooting

### Scripts Not Found
```bash
# Ensure you're in the repository root
cd /home/pi/PiSecure

# Verify scripts exist
ls -la genesis-reset.sh genesis-reset.ps1

# Make executable (if needed)
chmod +x genesis-reset.sh
```

### Permission Issues
```bash
# Linux/macOS - sudo may be needed for /var/lib/pisecure access
sudo bash genesis-reset.sh --force

# Windows - run PowerShell as Administrator
# Then: .\genesis-reset.ps1
```

### Blockchain Doesn't Recreate
```bash
# Verify Python environment
source pisecure_env/bin/activate
python -c "from pisecure.core import SignChain; print('OK')"

# Check directories were created
ls -la ~/.pisecure ~/.pisecure-testnet

# Try reset with debug output
bash -x genesis-reset.sh --force
```

## Performance Tips

1. **Disable backups during repeated testing**
   - Use `--force` without `--backup` for fastest resets
   - Save time: ~1-2 seconds per test cycle

2. **Use testnet for quick iteration**
   ```bash
   PISECURE_TESTNET=1 bash genesis-reset.sh --force
   ```

3. **Run tests in parallel**
   ```bash
   pytest tests/ -n auto  # Requires pytest-xdist
   ```

4. **Cache Python imports**
   - Tests run faster if environment stays active
   - Only reset blockchain, not Python environment

---

**See Also:**
- [GENESIS_RESET_README.md](GENESIS_RESET_README.md) - Full documentation
- [Testing Guide](docs/contributing.md) - General testing practices
