# PiSecure API Documentation - Modular Architecture Supplement

**Last Updated:** Phase 3-5 Refactoring  
**Status:** Active - All endpoints functional

This document supplements the existing API documentation with updates for the new modular architecture.

## Quick Reference - Architecture Changes

### Import Path Changes

| Use Case | Old Import | New Import | Status |
|----------|-----------|-----------|--------|
| Blockchain | `from pisecure.core import SignChain` | `from pisecure.interfaces import ChainInterface` / `from pisecure.node.interfaces import ChainImpl` | ✅ Both work |
| Wallet | `from pisecure.core import SignWallet` | `from pisecure.interfaces import WalletInterface` / `from pisecure.node.interfaces import WalletImpl` | ✅ Both work |
| Mining | Direct calls | `from pisecure.interfaces import MiningInterface` / `from pisecure.node.interfaces import MiningImpl` | ✅ New recommended |
| Node State | Scattered globals | `from pisecure.node import NodeContext` | ✅ Recommended |
| CLI | `from pisecure.cli import main` | `from pisecure.cli import main` (wrapper) / `from pisecure.legacy.cli_legacy import main` (original) | ✅ All work |

## REST API - Unchanged

All existing REST endpoints continue to work without modification:

- `GET /api/v1/chain` - ✅ No changes
- `GET /api/v1/chain/blocks/{height}` - ✅ No changes
- `POST /api/v1/transactions` - ✅ No changes
- `GET /api/v1/wallet/{address}/balance` - ✅ No changes
- `GET /api/v1/wallet/{address}/transactions` - ✅ No changes
- `GET /api/v1/mining/stats` - ✅ No changes
- `POST /api/v1/mining/start` - ✅ No changes
- `GET /api/v1/network/peers` - ✅ No changes

## Python SDK - New Patterns

### Pattern 1: Using NodeContext (Recommended)

Instead of managing multiple instances, use centralized context:

```python
from pisecure.node import NodeContext
from pisecure.node.interfaces import ChainImpl, WalletImpl, NodeImpl, MiningImpl
from pisecure.core import SignChain, SignWallet
from pisecure.common import Config

# Old way - scattered state
blockchain = SignChain()
wallet = SignWallet(private_key, public_key)
# ... hard to coordinate, easy to have inconsistent state

# New way - centralized context
ctx = NodeContext(
    blockchain=ChainImpl(SignChain()),
    wallet=WalletImpl(SignWallet(private_key, public_key)),
    node=NodeImpl(...),
    miner=MiningImpl(...),
    testnet=Config.TESTNET,
    validate_only=Config.VALIDATE_ONLY,
    mock_hardware=Config.MOCK_HARDWARE
)

# Consistent, coordinated operations
ctx.blockchain.add_transaction(tx)
ctx.wallet.sign_transaction(req)
ctx.miner.mine_block(wallet_address)

# Graceful shutdown
ctx.shutdown()
```

### Pattern 2: Using Result Type for Error Handling

Explicit error handling without exceptions:

```python
from pisecure.common import Result, Ok, Err

# Old way - exceptions and try/catch
try:
    blockchain.validate_chain()
    wallet.get_balance()
except ValidationError as e:
    print(f"Error: {e}")

# New way - Result type
result = blockchain.validate_chain()
if result.is_ok():
    chain_data = result.unwrap()
    process(chain_data)
else:
    print(f"Error: {result.error()}")
    # Continue execution, no exception
```

### Pattern 3: Interface-Based Code

Write code against interfaces, not implementations:

```python
from pisecure.interfaces import ChainInterface, WalletInterface

def synchronize_wallet(chain: ChainInterface, wallet: WalletInterface):
    """Works with any ChainInterface and WalletInterface implementation"""
    
    # Get current state
    is_valid, _ = chain.validate_chain()
    balance = wallet.get_balance()
    
    if is_valid and balance > 0:
        # Do something
        pass

# Can pass any implementation
from pisecure.node.interfaces import ChainImpl, WalletImpl
from pisecure.core import SignChain, SignWallet

sync = synchronize_wallet(
    ChainImpl(SignChain()),
    WalletImpl(SignWallet(key, pubkey))
)

# Or pass mocks for testing
from unittest.mock import Mock

mock_chain = Mock(spec=ChainInterface)
mock_wallet = Mock(spec=WalletInterface)
sync = synchronize_wallet(mock_chain, mock_wallet)
```

## Configuration - New System

### Environment Variables

All configuration is now centralized:

```bash
# Testnet isolation
export PISECURE_TESTNET=1

# Validation-only (works on any platform, no Pi hardware required)
export PISECURE_VALIDATE_ONLY=1

# Mock hardware (for CI/CD testing)
export PISECURE_MOCK_HARDWARE=1

# Suppress Rich formatted output
export PISECURE_QUIET=1

# Hybrid storage (default: enabled)
export PISECURE_NO_HYBRID_STORAGE=1  # To disable
```

### Python Configuration API

```python
from pisecure.common import Config

# Read configuration
print(Config.TESTNET)                  # bool
print(Config.VALIDATE_ONLY)            # bool
print(Config.MOCK_HARDWARE)            # bool
print(Config.USE_HYBRID_STORAGE)       # bool
print(Config.DATA_DIR)                 # str
print(Config.get_blockchain_file())    # str
print(Config.get_mode_string())        # str
```

## CLI - Updated Structure

### Legacy CLI (Temporary)

Current CLI in `pisecure/cli.py` is a thin wrapper around `pisecure/legacy/cli_legacy.py` for compatibility.

**All existing CLI commands still work:**

```bash
pisecure mine
pisecure wallet
pisecure status
pisecure --testnet status
pisecure --validate-only status
pisecure --mock-hardware status
```

### New CLI Structure (In Development)

New modular CLI in `pisecure/cli/`:

```
pisecure/cli/
├── __init__.py           # Module exports
├── formatters.py         # Output formatting utilities
└── commands/             # Command implementations (growing)
```

Gradual migration path - commands will be extracted from `legacy/cli_legacy.py` incrementally.

## Interfaces - Complete Reference

### ChainInterface

```python
class ChainInterface:
    def get_latest_block(self) -> Dict:
        """Get the most recent block"""
        
    def add_block(self, block: Dict) -> Result[bool]:
        """Add a new block to the chain"""
        
    def add_transaction(self, tx: Dict) -> Result[bool]:
        """Add a transaction to pending pool"""
        
    def validate_chain(self) -> Tuple[bool, str]:
        """Validate entire blockchain"""
        
    def validate_transaction(self, tx: Dict) -> Tuple[bool, str]:
        """Validate single transaction"""
        
    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance"""
        
    def broadcast_transaction(self, tx: Dict) -> Result[bool]:
        """Broadcast transaction to network"""
```

### WalletInterface

```python
class WalletInterface:
    def get_address(self) -> str:
        """Get wallet address"""
        
    def get_balance(self) -> float:
        """Get wallet balance"""
        
    def sign_transaction(self, req: TransactionRequest) -> Result[SignedTransaction]:
        """Sign a transaction"""
        
    def get_transaction_history(self, limit: int = 50) -> List[Dict]:
        """Get transaction history"""
        
    def verify_signature(self, msg: str, sig: str, pubkey: str) -> bool:
        """Verify a signature"""
```

### MiningInterface

```python
class MiningInterface:
    def start_mining(self, wallet_address: str) -> Tuple[bool, str]:
        """Start mining process"""
        
    def stop_mining(self) -> bool:
        """Stop mining process"""
        
    def mine_block(self, wallet_address: str) -> Result[Dict]:
        """Mine single block"""
        
    def get_mining_stats(self) -> Dict:
        """Get mining statistics"""
        
    def verify_hardware(self) -> Tuple[bool, str]:
        """Verify hardware capability"""
```

### NodeInterface

```python
class NodeInterface:
    def get_peer_list(self) -> List[Dict]:
        """Get connected peers"""
        
    def sync_with_peers(self) -> Tuple[bool, str]:
        """Synchronize with network"""
        
    def is_synced(self) -> bool:
        """Check if node is synced"""
        
    def broadcast_transaction(self, tx: Dict) -> Result[bool]:
        """Broadcast transaction to network"""
        
    def broadcast_block(self, block: Dict) -> Result[bool]:
        """Broadcast block to network"""
```

### StorageInterface

```python
class StorageInterface:
    def save_block(self, block_data: Dict) -> Tuple[bool, str]:
        """Save block to storage"""
        
    def get_block(self, hash: str) -> Optional[Dict]:
        """Retrieve block from storage"""
        
    def save_transaction(self, tx_data: Dict) -> Tuple[bool, str]:
        """Save transaction to storage"""
        
    def get_wallet_transactions(self, wallet_id: str) -> List[Dict]:
        """Get wallet transaction history from storage"""
        
    def backup(self, path: str) -> Tuple[bool, str]:
        """Backup blockchain data"""
        
    def restore(self, path: str) -> Tuple[bool, str]:
        """Restore blockchain data from backup"""
```

## Testing - New Patterns

### Test with NodeContext

```python
import pytest
from pisecure.node import NodeContext
from pisecure.node.interfaces import ChainImpl, WalletImpl
from pisecure.core import SignChain, SignWallet
from pisecure.common import Config

@pytest.fixture
def test_context():
    """Create test context with mock hardware"""
    return NodeContext(
        blockchain=ChainImpl(SignChain()),
        wallet=WalletImpl(SignWallet(test_key, test_pubkey)),
        testnet=True,
        validate_only=True,
        mock_hardware=True
    )

def test_blockchain_with_context(test_context):
    ctx = test_context
    # Test operations
    result = ctx.blockchain.add_transaction(test_tx)
    assert result.is_ok()
```

### Test with Mocked Interfaces

```python
from unittest.mock import Mock
from pisecure.interfaces import ChainInterface, WalletInterface

def test_with_mocks():
    mock_chain = Mock(spec=ChainInterface)
    mock_chain.get_balance.return_value = 100.0
    
    mock_wallet = Mock(spec=WalletInterface)
    mock_wallet.get_address.return_value = "test_addr"
    
    # Your code uses the mocks
    assert mock_chain.get_balance("addr") == 100.0
    assert mock_wallet.get_address() == "test_addr"
```

## Deprecated - Migration Guide

The following have been moved to `pisecure/legacy/` and should not be used in new code:

| File | Reason | Replacement |
|------|--------|------------|
| `cli_legacy.py` | Original 3265-line CLI | `pisecure/cli/` (new modular structure) |
| `monitor.py` | Old monitoring | `pisecure/core/monitoring.py` |
| Various test files | Legacy tests | Use new test patterns in `tests/` |

**All archived files are in `pisecure/legacy/` with documentation on why they're deprecated.**

See [legacy/__init__.py](../pisecure/legacy/__init__.py) for complete list.

## Running in Different Modes

### Production Mode (Mainnet)

```bash
# Run normally - uses mainnet blockchain
pisecure mine
pisecure status
```

```python
from pisecure.core import SignChain
blockchain = SignChain()  # Uses mainnet
```

### Testnet Mode

```bash
# Isolated testnet blockchain
export PISECURE_TESTNET=1
pisecure mine

# Or in Python
from pisecure.core import SignChain
import os
os.environ['PISECURE_TESTNET'] = '1'
blockchain = SignChain()  # Uses testnet
```

### Validation-Only Mode

```bash
# Works on ANY platform (Mac, Windows, Linux, Pi)
# No hardware verification required
export PISECURE_VALIDATE_ONLY=1
pisecure status

# Perfect for network growth - all platforms can participate
```

### Mock Hardware Mode

```bash
# For CI/CD testing without Pi hardware
export PISECURE_MOCK_HARDWARE=1
pytest tests/

# All hardware calls return simulated data
```

## Troubleshooting

### Issue: "ImportError: cannot import name"

**Solution:** Use the new import paths:

```python
# ❌ Old
from pisecure.wallet_old import Wallet

# ✅ New
from pisecure.interfaces import WalletInterface
from pisecure.node.interfaces import WalletImpl
```

### Issue: Tests failing with hardware errors

**Solution:** Use mock hardware mode:

```bash
export PISECURE_MOCK_HARDWARE=1
pytest tests/
```

### Issue: "File not found" for blockchain

**Solution:** Check Config settings:

```python
from pisecure.common import Config
print(Config.DATA_DIR)  # Current data directory
print(Config.get_blockchain_file())  # Full path to blockchain file
```

## Summary of Breaking Changes

**None!** All changes are backwards compatible:

- ✅ REST API endpoints unchanged
- ✅ CLI commands unchanged
- ✅ Core Python imports still work
- ✅ New patterns available alongside old patterns
- ✅ Gradual migration path provided

**Recommendation:** New code should use:
1. `NodeContext` for centralized state management
2. `Result[T]` for explicit error handling
3. Interface-based design for testability
4. New CLI structure in `pisecure/cli/` (in development)

## Next Steps

### Phase 4 (In Development)
- Graceful shutdown coordinator in `NodeContext`
- Scheduler integration for background tasks
- Event-based architecture for decoupled components

### Phase 5 (In Development)
- Expand test coverage to >80%
- Add integration tests
- Performance benchmarks

### CLI Migration (Ongoing)
- Extract commands from `legacy/cli_legacy.py`
- Implement in `pisecure/cli/commands/`
- Full modularity while maintaining compatibility
