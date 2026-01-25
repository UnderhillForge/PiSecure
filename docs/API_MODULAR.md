# PiSecure API Documentation (Updated - Modular Architecture)

## Overview

PiSecure provides both REST API and Python SDK interfaces. The architecture has been refactored to be modular with clear abstraction boundaries.

## Architecture Changes

### New Modular Structure

```
pisecure/
├── interfaces/         # Abstract API boundaries
├── kernel/            # Pure consensus logic
├── node/              # Node services + context
├── common/            # Shared utilities (Result type, Config)
├── core/              # Core implementations
├── api/               # REST API endpoints
└── cli/               # Modular CLI commands
```

### Key Components

#### 1. **Interfaces Layer** (`pisecure/interfaces/`)

Abstract contracts for all major components:

- **ChainInterface** - Blockchain operations
  ```python
  interface ChainInterface:
    - get_latest_block() -> Block
    - add_block(block: Block) -> bool
    - add_transaction(tx: Transaction) -> bool
    - validate_chain() -> (bool, str)
    - validate_transaction(tx: Transaction) -> (bool, str)
    - get_balance(wallet_id: str) -> float
    - broadcast_transaction(tx: Transaction)
  ```

- **WalletInterface** - Wallet operations
  ```python
  interface WalletInterface:
    - get_address() -> str
    - get_balance() -> float
    - sign_transaction(req: TransactionRequest) -> SignedTransaction
    - get_transaction_history(limit: int) -> List[Dict]
    - verify_signature(msg, sig, pubkey) -> bool
  ```

- **NodeInterface** - Network operations
  ```python
  interface NodeInterface:
    - get_peer_list() -> List[PeerInfo]
    - sync_with_peers() -> (bool, str)
    - is_synced() -> bool
    - broadcast_transaction(tx: Dict)
    - broadcast_block(block: Dict)
  ```

- **MiningInterface** - Mining operations
  ```python
  interface MiningInterface:
    - start_mining(wallet_address: str) -> (bool, str)
    - stop_mining() -> bool
    - mine_block(wallet_address: str) -> MiningResult
    - get_mining_stats() -> MiningStats
    - verify_hardware() -> (bool, str)
  ```

- **StorageInterface** - Data persistence
  ```python
  interface StorageInterface:
    - save_block(block_data: Dict) -> (bool, str)
    - get_block(hash: str) -> Optional[Dict]
    - save_transaction(tx_data: Dict) -> (bool, str)
    - get_wallet_transactions(wallet_id: str) -> List[Dict]
    - backup(path: str) -> (bool, str)
    - restore(path: str) -> (bool, str)
  ```

#### 2. **Kernel Layer** (`pisecure/kernel/`)

Pure consensus logic with zero network dependencies:

- `consensus.py` - Consensus rules
- `validation.py` - Block/transaction validation
- `pihash.py` - PiHash proof-of-work algorithm
- `pihash_cpp.py` - C++ optimizations

#### 3. **Node Context** (`pisecure/node/context.py`)

Centralized state container replacing scattered globals:

```python
class NodeContext:
  - blockchain: ChainInterface
  - wallet: WalletInterface
  - miner: MiningInterface
  - node: NodeInterface
  - storage: StorageInterface
  - hooks: Dict[str, List[Callable]]  # Event system
  - metrics: Dict[str, Any]
  - register_hook(event, callback)
  - trigger_hook(event, *args, **kwargs)
```

#### 4. **Result Type** (`pisecure/common/result.py`)

Explicit error handling without exceptions:

```python
class Result[T]:
  - is_ok() -> bool
  - is_err() -> bool
  - unwrap() -> T
  - unwrap_or(default: T) -> T
  - error() -> str
  - map(fn) -> Result
  - map_err(fn) -> Result

# Usage:
result = operation()
if result.is_ok():
    value = result.unwrap()
else:
    error = result.error()
```

#### 5. **Centralized Config** (`pisecure/common/config.py`)

```python
class Config:
  - DATA_DIR: str
  - CONFIG_DIR: str
  - TESTNET: bool
  - VALIDATE_ONLY: bool
  - MOCK_HARDWARE: bool
  - USE_HYBRID_STORAGE: bool
  - get_blockchain_file() -> str
  - get_mode_string() -> str
```

## REST API Endpoints

### Chain Operations

#### GET /api/v1/chain
Get blockchain status

**Response:**
```json
{
  "chain_length": 1234,
  "difficulty": 146,
  "latest_block_hash": "0000abc...",
  "is_valid": true,
  "network_health": "healthy"
}
```

#### GET /api/v1/chain/blocks/{height}
Get block by height

**Response:**
```json
{
  "index": 42,
  "timestamp": 1234567890.5,
  "transactions": [...],
  "previous_hash": "...",
  "hash": "...",
  "nonce": 1234,
  "difficulty": 146
}
```

#### POST /api/v1/transactions
Submit new transaction

**Request:**
```json
{
  "sender": "address",
  "recipient": "address",
  "amount": 10.5,
  "signature": "sig_data"
}
```

**Response:**
```json
{
  "success": true,
  "tx_id": "abc123",
  "message": "Transaction accepted"
}
```

### Wallet Operations

#### GET /api/v1/wallet/{address}/balance
Get wallet balance

**Response:**
```json
{
  "address": "wallet_address",
  "balance": 50.25,
  "pending": 10.0
}
```

#### GET /api/v1/wallet/{address}/transactions
Get wallet transaction history

**Response:**
```json
{
  "address": "wallet_address",
  "transactions": [
    {
      "tx_id": "abc123",
      "from": "...",
      "to": "...",
      "amount": 5.0,
      "timestamp": 1234567890.5
    }
  ]
}
```

### Mining Operations

#### GET /api/v1/mining/stats
Get mining statistics

**Response:**
```json
{
  "is_mining": true,
  "blocks_found": 42,
  "hash_rate": 1000000.5,
  "difficulty": 146,
  "average_block_time": 60.2
}
```

#### POST /api/v1/mining/start
Start mining

**Request:**
```json
{
  "wallet_address": "address",
  "difficulty": 146
}
```

### Network Operations

#### GET /api/v1/network/peers
Get connected peers

**Response:**
```json
{
  "peers": [
    {
      "host": "peer.example.com",
      "port": 3142,
      "node_id": "...",
      "latency_ms": 45.2
    }
  ]
}
```

#### GET /api/v1/network/stats
Get network statistics

**Response:**
```json
{
  "connected_peers": 12,
  "pending_transactions": 45,
  "sync_status": "synced",
  "network_difficulty": 146
}
```

## Python SDK Usage

### Import from Interfaces

```python
from pisecure.node.interfaces import ChainImpl, WalletImpl, NodeImpl, MiningImpl
from pisecure.core import SignChain, SignWallet
from pisecure.core.p2p_sync import P2PSyncManager

# Create implementations
blockchain = ChainImpl(SignChain())
wallet = WalletImpl(SignWallet(...))
node = NodeImpl(P2PSyncManager(...))

# Use interfaces
is_valid, msg = blockchain.validate_chain()
balance = wallet.get_balance()
peers = node.get_peer_list()
```

### Using NodeContext

```python
from pisecure.node import NodeContext
from pisecure.common import Config

# Create context
ctx = NodeContext(
    blockchain=blockchain,
    wallet=wallet,
    node=node,
    miner=miner,
    testnet=Config.TESTNET,
    validate_only=Config.VALIDATE_ONLY
)

# Register event handlers
ctx.register_hook('blockchain.new_block', on_new_block)

# Access services through context
ctx.blockchain.add_transaction(tx)
ctx.wallet.sign_transaction(req)
ctx.node.sync_with_peers()

# Graceful shutdown
ctx.shutdown()
```

### Using Result Type

```python
from pisecure.common import Result, Ok, Err

def create_transaction(tx_req) -> Result:
    try:
        if not validate(tx_req):
            return Err("Invalid transaction")
        tx = sign(tx_req)
        return Ok(tx)
    except Exception as e:
        return Err(str(e))

# Usage
result = create_transaction(req)
if result.is_ok():
    tx = result.unwrap()
    submit_to_network(tx)
else:
    print(f"Error: {result.error()}")
```

## Migration Guide

### For New Code

Always use the new modular architecture:

```python
# ✅ GOOD: Use interfaces
from pisecure.interfaces import ChainInterface
from pisecure.node.interfaces import ChainImpl
from pisecure.core import SignChain

chain_impl = ChainImpl(SignChain())
# Now chain_impl implements ChainInterface

# ❌ BAD: Don't import from legacy
# from pisecure.legacy.cli_legacy import ...
```

### For Existing Code

Gradually migrate using the bridge pattern:

```python
# 1. Create implementation wrapper
old_blockchain = SignChain()
new_chain = ChainImpl(old_blockchain)

# 2. Use new interface in new code
new_chain.validate_chain()

# 3. Gradually replace old direct calls
# OLD: old_blockchain.validate()
# NEW: new_chain.validate_chain()

# 4. Once everything is updated, remove old code
```

## Configuration

### Environment Variables

```bash
# Testnet mode
export PISECURE_TESTNET=1

# Validation-only mode (no mining, works on any platform)
export PISECURE_VALIDATE_ONLY=1

# Mock hardware (for testing)
export PISECURE_MOCK_HARDWARE=1

# Quiet mode (no Rich formatting)
export PISECURE_QUIET=1

# Use hybrid storage
export PISECURE_NO_HYBRID_STORAGE=0  # Default is ON
```

### Python Config

```python
from pisecure.common import Config

# Check current settings
print(Config.TESTNET)  # bool
print(Config.VALIDATE_ONLY)  # bool
print(Config.DATA_DIR)  # str
print(Config.get_mode_string())  # str like "testnet,mock-hardware"
```

## Error Handling

New modular architecture uses `Result[T]` instead of exceptions for better error handling:

```python
# Interface methods return (success: bool, error_message: str) tuples
is_valid, msg = blockchain.validate_transaction(tx)

# Or Result types
result = blockchain.add_block(block)
if result.is_ok():
    block = result.unwrap()
else:
    error_msg = result.error()
```

## Deprecated APIs

The following are now in `pisecure/legacy/`:

- `cli_legacy.py` - Use `pisecure/cli.py` instead
- `monitor.py` - Use `pisecure/core/monitoring.py`
- Old wallet implementation - Use `SignWallet` or `WalletInterface`

See `pisecure/legacy/__init__.py` for full list.

## Testing

### Test New Components

```python
from pisecure.node.context import NodeContext
from pisecure.common import Result, Ok, Err

def test_with_context():
    ctx = NodeContext(
        blockchain=mock_blockchain,
        wallet=mock_wallet,
        validate_only=True,  # Mock mode
        mock_hardware=True
    )
    # Test with mocked context
    ctx.blockchain.add_transaction(test_tx)
```

### Mock Interfaces

```python
from unittest.mock import Mock
from pisecure.interfaces import ChainInterface

mock_chain = Mock(spec=ChainInterface)
mock_chain.get_balance.return_value = 100.0
mock_chain.validate_chain.return_value = (True, "")

# Use mock in tests
assert mock_chain.get_balance("addr") == 100.0
```

## Backwards Compatibility

- All existing REST endpoints continue to work
- Python SDK imports from `pisecure.core` still work
- CLI commands unchanged (temporarily using legacy CLI)
- New code should use `pisecure.interfaces` and `pisecure.node`

## Support

For questions about the new architecture:
- See [ARCHITECTURE_ANALYSIS.md](../ARCHITECTURE_ANALYSIS.md)
- See [BITCOIN_PATTERNS.md](../BITCOIN_PATTERNS.md)
- See [REFACTORING_COMPLETE.md](../REFACTORING_COMPLETE.md)
