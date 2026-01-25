# Bitcoin Core Patterns: Adoptable for PiSecure

## Pattern 1: Interfaces as Boundaries

**Bitcoin's Problem Solved**:
Wallet code was calling node code directly. Node changes broke wallet. Wallet changes broke node. GUI couldn't run separately.

**Bitcoin's Solution**:
- Abstract interfaces in `src/interfaces/`
- Wallet calls `interfaces::Chain`, not `CBlockIndex` directly
- Node implements `interfaces::Chain`, handles details internally
- If node implementation changes, wallet is unaffected

**For PiSecure**:
```python
# Before (tight coupling):
class Wallet:
    def get_balance(self):
        return blockchain.get_balance(address)  # Direct dependency!

# After (loose coupling):
class Wallet:
    def __init__(self, chain: interfaces.Chain):
        self.chain = chain
    
    def get_balance(self):
        return self.chain.get_balance(address)  # Through interface!
```

**Status**: NOT IN PISECURE - Create now in `pisecure/interfaces/`

---

## Pattern 2: NodeContext (Dependency Container)

**Bitcoin's Problem Solved**:
Global variables everywhere (`g_best_block`, `mempool`, `peerManager`). Hard to test. Unclear initialization order. Multiple global singletons conflicting.

**Bitcoin's Solution**:
Create one struct holding all node state:
```cpp
struct NodeContext {
    std::unique_ptr<CChainState> chainstate;
    std::unique_ptr<CTxMemPool> mempool;
    std::unique_ptr<PeerManager> peerman;
    // ... all components bundled
};
```

Pass NodeContext around instead of individual globals. One object instead of 10 globals.

**For PiSecure**:
```python
@dataclass
class NodeContext:
    blockchain: Blockchain
    mempool: Mempool
    peer_manager: PeerManager
    validation_engine: ValidationEngine
    scheduler: Scheduler
    shutdown: ShutdownManager

# Usage:
def initialize_node(context: NodeContext) -> bool:
    context.blockchain.load_from_disk()
    context.mempool.load_from_disk()
    context.scheduler.schedule_recurring(300, context.peer_manager.maintain_peers)
    return True
```

**Benefits**:
- ✅ Explicit dependencies (function signature shows what it needs)
- ✅ Easier testing (pass mock components)
- ✅ Easier initialization (one object to set up)
- ✅ No hidden globals

**Status**: NOT IN PISECURE - Create in `pisecure/node/context.py`

---

## Pattern 3: Library Layering with Clear Dependencies

**Bitcoin's Problem Solved**:
Hard to understand what dependencies what. Code mixed together at different abstraction levels. Can't use kernel logic without importing all of node logic.

**Bitcoin's Solution**:
Organize into layers with explicit dependencies:

```
libbitcoin_kernel (consensus only)
  ├─ DEPENDS ON: util, crypto, consensus
  └─ DOES NOT DEPEND ON: node, wallet, net, rpc

libbitcoin_node (node operations)
  ├─ DEPENDS ON: kernel, common, util, crypto
  └─ DOES NOT DEPEND ON: wallet, qt, rpc

libbitcoin_wallet (wallet operations)
  ├─ DEPENDS ON: common, util, crypto
  └─ DOES NOT DEPEND ON: kernel, node, qt

libbitcoin_qt (GUI)
  ├─ DEPENDS ON: common, util, crypto, qt
  └─ DOES NOT DEPEND ON: kernel, node, wallet (uses interfaces only!)
```

**Key**: Lower layers don't know about higher layers.

**For PiSecure** (Target):
```
pisecure/kernel/
  ├─ DEPENDS ON: common, util
  └─ NO DEPENDENCIES: node, wallet, api, cli
  └─ EXPORTS: Validation, Difficulty, Consensus rules

pisecure/node/
  ├─ DEPENDS ON: kernel, common, util
  └─ NO DEPENDENCIES: wallet, api, cli (uses interfaces only!)
  └─ EXPORTS: Blockchain, Mempool, NodeContext

pisecure/wallet/
  ├─ DEPENDS ON: common, util
  └─ NO DEPENDENCIES: kernel, node, api, cli (uses interfaces only!)
  └─ EXPORTS: Wallet, KeyManager, UTXOManager

pisecure/api/
  ├─ DEPENDS ON: node (implements interfaces), wallet (implements interfaces)
  └─ EXPORTS: HTTP endpoints

pisecure/cli.py
  └─ Thin entry point, imports everything as needed
```

**Current PiSecure Issue**:
- Everything in `core/` at same level
- Circular dependencies (validation depends on blockchain, blockchain depends on validation)
- Hard to extract kernel logic

**Status**: PARTIALLY EXISTS (wallet_v2 is good, but needs isolation)

---

## Pattern 4: Separated Consensus Engine (Kernel)

**Bitcoin's Problem Solved**:
Consensus rules mixed with node operations. Hard to audit. Can't use consensus validation without running full node. Difficult to implement in other languages.

**Bitcoin's Solution**:
Extract pure consensus logic to `src/kernel/`:
- No network code
- No storage code (uses abstract interface)
- No wallet code
- Pure validation algorithms

```cpp
// src/kernel/validation.h - Pure consensus
bool CheckBlockHeader(const CBlockHeader& block_header,
                      Notifications& notifications,
                      const Consensus::Params& consensus_params);

bool CheckBlock(const CBlock& block,
                const Consensus::Params& consensus_params);

// These work WITHOUT node state, network, or wallet!
```

**For PiSecure**:
```python
# pisecure/kernel/validation.py
def validate_block_header(header: BlockHeader) -> bool:
    """Pure validation - no node state needed"""
    if header.version < MIN_VERSION:
        return False
    if header.difficulty < MIN_DIFFICULTY:
        return False
    if not is_valid_pihash(header.hash):
        return False
    return True

def validate_transaction(tx: Transaction) -> bool:
    """Pure transaction validation"""
    if not tx.has_valid_signature():
        return False
    if tx.input_sum < tx.output_sum:
        return False
    return True

# pisecure/node/validation_engine.py
class ValidationEngine:
    """Uses kernel validation + node state"""
    
    def accept_block(self, block: Block, context: NodeContext) -> bool:
        # Use kernel validation
        if not kernel.validate_block(block):
            return False
        
        # Add node-specific checks
        if block.height != context.blockchain.tip().height + 1:
            return False
        
        # Update state
        context.blockchain.add_block(block)
        context.mempool.remove_transactions(block.tx_list)
        return True
```

**Benefits**:
- ✅ Kernel can be tested without network
- ✅ Kernel can be used in other projects
- ✅ Consensus changes are isolated
- ✅ Security audits can focus on kernel only

**Status**: PARTIALLY EXISTS (consensus in core/consensus.py, but mixed with node logic)

---

## Pattern 5: Abstract Storage Interface

**Bitcoin's Problem Solved**:
Blockchain storage was hardcoded to LevelDB. Wanted to use RocksDB, SQLite, or embedded. Couldn't change implementation without rewriting validation code.

**Bitcoin's Solution**:
Create abstract storage interface:
```cpp
class CCoinsView {  // Abstract interface
    virtual bool GetCoin(const COutPoint& outpoint, Coin& coin) = 0;
    virtual bool HaveCoin(const COutPoint& outpoint) = 0;
    virtual uint256 GetBestBlock() = 0;
};

class CCoinsViewDB : public CCoinsView {  // LevelDB implementation
    bool GetCoin(const COutPoint& outpoint, Coin& coin) override { ... }
};

// ValidationEngine uses CCoinsView interface, not CCoinsViewDB!
```

**For PiSecure**:
```python
# pisecure/interfaces/storage.py
class Storage(ABC):
    @abstractmethod
    def store_block(self, block: Block) -> None: pass
    
    @abstractmethod
    def get_block(self, hash: str) -> Optional[Block]: pass
    
    @abstractmethod
    def get_blocks_by_height(self, height: int) -> List[Block]: pass
    
    @abstractmethod
    def store_utxo(self, outpoint: str, coin: Coin) -> None: pass
    
    @abstractmethod
    def get_utxo(self, outpoint: str) -> Optional[Coin]: pass

# pisecure/storage/hybrid_storage.py
class HybridStorage(Storage):
    """Implementation using hybrid binary + SQLite"""
    
    def store_block(self, block: Block) -> None:
        # Store binary data in blk*.dat
        # Index in SQLite
        ...

# pisecure/storage/json_storage.py
class JsonStorage(Storage):
    """Simple JSON implementation for testing"""
    
    def store_block(self, block: Block) -> None:
        # Store as JSON for easy inspection
        ...

# Kernel validation doesn't care which storage is used!
```

**Benefits**:
- ✅ Can swap storage implementations (testing vs production)
- ✅ Can optimize storage independently
- ✅ Can implement new storage formats without touching validation

**Status**: PARTIAL (hybrid storage exists, but not abstracted via interface)

---

## Pattern 6: Init Factory Pattern

**Bitcoin's Problem Solved**:
Different executables (bitcoind, bitcoin-qt, bitcoin-wallet) need different initialization. Hard to reuse code. Duplicate initialization logic in each executable.

**Bitcoin's Solution**:
Create Init interface:
```cpp
class Init {
    virtual std::unique_ptr<Node> makeNode() = 0;
    virtual std::unique_ptr<Chain> makeChain() = 0;
    virtual std::unique_ptr<WalletLoader> makeWalletLoader() = 0;
};

class BitcoindInit : public Init {
    std::unique_ptr<Node> makeNode() override {
        return createFullNode();  // Full node with wallet
    }
};

class BitcoinQtInit : public Init {
    std::unique_ptr<Node> makeNode() override {
        return createNodeForGUI();  // GUI-compatible node
    }
};
```

**For PiSecure**:
```python
# pisecure/interfaces/init.py
class Init(ABC):
    @abstractmethod
    def make_node(self) -> interfaces.Node: pass
    
    @abstractmethod
    def make_chain(self) -> interfaces.Chain: pass
    
    @abstractmethod
    def make_mining(self) -> interfaces.Mining: pass

# pisecure/init/cli_init.py
class CLIInit(Init):
    def __init__(self, testnet=False, validate_only=False):
        self.testnet = testnet
        self.validate_only = validate_only
    
    def make_node(self) -> interfaces.Node:
        context = NodeContext(
            blockchain=HybridStorage(...),
            mempool=Mempool(),
            peer_manager=PeerManager(),
        )
        return NodeImpl(context)

# pisecure/init/api_init.py
class APIInit(Init):
    def __init__(self, config: dict):
        self.config = config
    
    def make_node(self) -> interfaces.Node:
        # Different setup for API
        ...

# pisecure/cli.py becomes simple:
init = CLIInit(testnet=args.testnet)
node = init.make_node()
chain = init.make_chain()
mining = init.make_mining()
```

**Benefits**:
- ✅ Different initialization for different modes
- ✅ Testnet vs mainnet logic centralized
- ✅ Mocking for tests is easy (MockInit with mock objects)

**Status**: NOT IN PISECURE - Create in `pisecure/interfaces/init.py`

---

## Pattern 7: Graceful Shutdown Coordination

**Bitcoin's Problem Solved**:
Shutdown was ad-hoc. Components didn't know when to stop. Data corruption from abrupt exits.

**Bitcoin's Solution**:
Centralized shutdown signaling:
```cpp
class CNodeSignals {
    boost::signals2::signal<void ()> ShutdownRequested;
};

// All components check: if (ShutdownRequested.is_connected()) { cleanup and exit }
```

**For PiSecure**:
```python
# pisecure/node/shutdown.py
class ShutdownManager:
    def __init__(self):
        self.is_shutdown = False
        self.shutdown_event = threading.Event()
    
    def request_shutdown(self):
        """Called by signal handler"""
        self.is_shutdown = True
        self.shutdown_event.set()
    
    def shutdown_requested(self) -> bool:
        return self.is_shutdown

# Usage:
def run_node(context: NodeContext):
    while not context.shutdown.shutdown_requested():
        sync_blocks()
        broadcast_transactions()
        sleep(1)
    
    # Graceful cleanup
    context.blockchain.close()
    context.mempool.flush()
    context.peer_manager.disconnect()

# Signal handlers register with shutdown manager
def handle_sigterm(sig, frame):
    context.shutdown.request_shutdown()

signal.signal(signal.SIGTERM, handle_sigterm)
```

**Benefits**:
- ✅ Coordinated shutdown (no data corruption)
- ✅ Components know when to stop
- ✅ Graceful restart capability

**Status**: NOT IN PISECURE - Create in `pisecure/node/shutdown.py`

---

## Pattern 8: Result Type for Error Handling

**Bitcoin's Problem Solved**:
Exceptions everywhere led to undefined behavior in error paths. Error handling was inconsistent.

**Bitcoin's Approach**:
Use Result types and structured error codes (not C++ style, but conceptually):

```cpp
// Instead of: throw std::exception()
// Bitcoin uses: bool, error codes, or Result<T, Error>

enum class TransactionError {
    OK,
    INPUTS_NOT_AVAILABLE,
    INSUFFICIENT_FEE,
    INVALID_SIGNATURE,
};

// Functions return clear error types
TransactionError validateTransaction(const CTransaction& tx);

// Caller decides what to do
auto error = validateTransaction(tx);
if (error == TransactionError::INVALID_SIGNATURE) {
    // Handle specifically
} else if (error != TransactionError::OK) {
    // Handle generically
}
```

**For PiSecure**:
```python
# pisecure/common/result.py
class Result(Generic[T, E]):
    @staticmethod
    def Ok(value: T) -> 'Result[T, E]':
        return Result(value=value, error=None)
    
    @staticmethod
    def Err(error: E) -> 'Result[T, E]':
        return Result(value=None, error=error)
    
    def is_ok(self) -> bool: ...
    def is_err(self) -> bool: ...
    def map(self, f): ...  # Chain operations

# Usage:
result = validate_transaction(tx)
if result.is_ok():
    add_to_mempool(result.value)
elif result.is_err():
    logger.error(f"Tx validation failed: {result.error}")
    # Handle error explicitly
```

**Benefits**:
- ✅ Errors are explicit (not hidden in exceptions)
- ✅ Caller must handle errors
- ✅ Error chains are type-safe

**Status**: NOT IN PISECURE - Create in `pisecure/common/result.py`

---

## Pattern 9: Explicit Parameter Objects (Not Scattered Arguments)

**Bitcoin's Problem Solved**:
Functions had 10+ arguments. Easy to mix up order. Hard to add new parameters.

**Bitcoin's Solution**:
Group related parameters into objects:

```cpp
// Before:
bool validateTransaction(const CTransaction& tx,
                        bool checkInputs,
                        bool allowHighFees,
                        bool checkMempoolAcceptance,
                        const CAmount& minRelayFee,
                        const size_t& maxTxSize);

// After (cleaner):
struct TransactionValidationArgs {
    bool checkInputs = true;
    bool allowHighFees = false;
    bool checkMempoolAcceptance = true;
    CAmount minRelayFee = MINIMUM_RELAY_FEE;
    size_t maxTxSize = MAX_TRANSACTION_SIZE;
};

bool validateTransaction(const CTransaction& tx,
                        const TransactionValidationArgs& args);
```

**For PiSecure**:
```python
# Instead of:
def add_transaction(tx, check_sig, check_balance, fee_limit, broadcast):
    ...

# Use:
@dataclass
class TransactionAcceptanceParams:
    check_signature: bool = True
    check_balance: bool = True
    fee_limit: Optional[float] = None
    broadcast: bool = True

def add_transaction(tx: Transaction, params: TransactionAcceptanceParams) -> Result:
    ...

# Usage is clearer:
result = add_transaction(tx, TransactionAcceptanceParams(
    check_signature=True,
    broadcast=True,
    fee_limit=0.001
))
```

**Benefits**:
- ✅ Self-documenting (parameter names are visible)
- ✅ Easy to add new parameters
- ✅ Reduces argument errors
- ✅ Enables configuration objects

**Status**: PARTIALLY EXISTS (wallet_v2 uses dataclasses well)

---

## Pattern 10: Structured Logging Categories

**Bitcoin's Problem Solved**:
Scattered logging statements. Hard to filter errors. Can't enable specific categories for debugging.

**Bitcoin's Solution**:
Categorical logging:
```cpp
// src/logging.h defines categories
BCLog::INFO    // General info
BCLog::WARNING // Warnings
BCLog::ERROR   // Errors
BCLog::NET     // Network messages
BCLog::MEMPOOL // Mempool operations
BCLog::VALIDATION // Validation operations
BCLog::MINING  // Mining operations

// Usage:
LogPrintLevel(BCLog::NET, BCLog::INFO, "Peer connected: %s", peer.addr);
LogPrintLevel(BCLog::VALIDATION, BCLog::ERROR, "Block validation failed");

// Can enable/disable per category at runtime
```

**For PiSecure**:
```python
# pisecure/common/logging.py
class LogCategory(Enum):
    CORE = "core"
    NETWORK = "network"
    VALIDATION = "validation"
    WALLET = "wallet"
    MINING = "mining"
    MEMPOOL = "mempool"
    API = "api"

def log_structured(category: LogCategory, level: str, message: str, **extra):
    logger.log(level, message, extra={
        'category': category.value,
        **extra
    })

# Usage:
log_structured(LogCategory.VALIDATION, "ERROR",
               "Block validation failed",
               block_hash=block.hash,
               height=block.height)

# Output includes metadata for analysis
```

**Benefits**:
- ✅ Can filter logs by category
- ✅ Can enable debug for specific subsystem only
- ✅ Better for production debugging

**Status**: PARTIAL (logging exists, could be more structured)

---

## Summary: What to Adopt First

| Pattern | Effort | Impact | Priority |
|---------|--------|--------|----------|
| Interfaces Layer | 2-3 hours | CRITICAL - enables everything else | 🔴 FIRST |
| NodeContext | 1-2 hours | CRITICAL - reduces globals | 🔴 FIRST |
| Library Layering | 4-6 hours | HIGH - improves modularity | 🟡 SECOND |
| Init Factory | 2-3 hours | HIGH - enables testing | 🟡 SECOND |
| Kernel Separation | 3-4 hours | HIGH - consensus isolation | 🟡 SECOND |
| Storage Interface | 2-3 hours | MEDIUM - enables swapping | 🟢 THIRD |
| Graceful Shutdown | 2 hours | MEDIUM - robustness | 🟢 THIRD |
| Result Type | 1-2 hours | MEDIUM - error handling | 🟢 THIRD |
| Parameter Objects | 2-3 hours | LOW - code clarity | 🔵 FOURTH |
| Structured Logging | 2-3 hours | LOW - debugging | 🔵 FOURTH |

---

## Recommended Implementation Order

1. **This Week**: Interfaces + NodeContext (foundation)
2. **Next Week**: Init Factory + kernel separation (enablers)
3. **Week 3**: Library reorganization (structure)
4. **Week 4**: Graceful shutdown + error handling (robustness)
5. **Week 5+**: Polish, testing, documentation

