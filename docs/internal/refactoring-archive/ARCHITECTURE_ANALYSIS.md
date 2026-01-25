# PiSecure vs Bitcoin Core Architecture Analysis

## Executive Summary

Bitcoin Core's architecture is **highly modular with strict separation of concerns** through:
1. **Layered libraries** (kernel, node, wallet, gui)
2. **Abstract interfaces** (src/interfaces/) as communication boundaries
3. **Process isolation** (multiprocess capability)
4. **Dependency inversion** (higher-level code never depends on lower-level implementation details)

PiSecure currently has **monolithic modules with tight coupling**. This document identifies gaps and provides a roadmap for architectural improvements.

---

## Part 1: Bitcoin Core Architecture Model

### 1.1 Layer Structure

```
Bitcoin Core Layers (Bottom-Up):
┌─────────────────────────────────────┐
│ GUI (src/qt/) & CLI (src/bitcoin/)  │  ← User Interfaces
├─────────────────────────────────────┤
│ Interfaces (src/interfaces/)         │  ← Communication Boundaries (CRITICAL)
├─────────────────────────────────────┤
│ Node (src/node/)                    │  ← Node Operations & State Management
│ Wallet (src/wallet/)                │  ← Wallet Operations
│ RPC (src/rpc/)                      │  ← RPC Server
├─────────────────────────────────────┤
│ Kernel (src/kernel/)                │  ← Consensus Engine (Pure consensus logic)
│ Validation (src/validation.*)       │  ← Validation Logic
├─────────────────────────────────────┤
│ Common (src/common/)                │  ← Common Utilities (Shared by all)
│ Util (src/util/)                    │  ← Basic Utilities
│ Crypto (src/crypto/)                │  ← Cryptography (No dependencies)
└─────────────────────────────────────┘
```

### 1.2 Key Bitcoin Core Modules

| Module | Purpose | Dependencies | Notes |
|--------|---------|--------------|-------|
| **kernel/** | Pure consensus engine | util, crypto | Planned for external library (libbitcoinkernel) |
| **node/** | Node state & operations | kernel, common, util | chainstate, mempool management, peer coordination |
| **wallet/** | Wallet management | common, crypto, util | Uses interfaces::Chain only (not direct node access) |
| **interfaces/** | Abstract boundaries | none | Pure virtual methods for cross-module communication |
| **validation.cpp** | Block/tx validation | kernel, common | Orchestrates consensus rules |
| **net.cpp, net_processing.cpp** | P2P protocol | common, util | Message handling, peer management |
| **txmempool.cpp** | Transaction pool | common | Mempool validation, eviction policies |
| **rpc/** | RPC endpoints | node, wallet, common | HTTP/JSON-RPC interface |
| **policy/** | Relay/acceptance policies | common, crypto | Mempool policies, transaction relay rules |

### 1.3 Critical Pattern: Abstract Interfaces (src/interfaces/)

**Purpose**: Enable wallet, node, and GUI to be completely independent modules that communicate only through abstract virtual methods.

**Key Interfaces**:

```cpp
// src/interfaces/chain.h - Wallet uses this to access node
class Chain {
    virtual BlockMeta getBlockMetadata(const uint256& block_hash) = 0;
    virtual int getHeight() = 0;
    virtual uint256 getBestBlock() = 0;
    // ... wallet queries node through this interface only
};

// src/interfaces/wallet.h - GUI uses this to access wallet
class Wallet {
    virtual CAmount getBalance() = 0;
    virtual std::vector<WalletTx> getTransactions() = 0;
    // ... GUI queries wallet through this interface only
};

// src/interfaces/node.h - GUI uses this to control node
class Node {
    virtual bool baseInitialize() = 0;
    virtual bool appInitMain() = 0;
    virtual void appShutdown() = 0;
    // ... GUI controls node through this interface only
};

// src/interfaces/mining.h - RPC uses this for mining
class Mining {
    virtual std::unique_ptr<BlockTemplate> getBlockTemplate() = 0;
};
```

**Why This Matters**:
- ✅ Wallet code cannot directly call node code → modularity
- ✅ Node code cannot directly call wallet code → independence
- ✅ Changes to wallet implementation don't affect node
- ✅ Enables multiprocess (wallet in different process than node)
- ✅ Makes unit testing easier (mock implementations possible)

### 1.4 NodeContext: The Hub

```cpp
// src/node/context.h
namespace node {
struct NodeContext {
    // Core services
    std::unique_ptr<kernel::Context> kernel;
    std::unique_ptr<CChainState> chainstate;
    std::unique_ptr<CTxMemPool> mempool;
    
    // Connection state
    std::unique_ptr<CConnman> connman;
    std::unique_ptr<PeerManager> peerman;
    
    // Signaling
    std::unique_ptr<ValidationSignals> validation_signals;
    std::unique_ptr<KernelNotifications> notifications;
    
    // Scheduler
    std::unique_ptr<CScheduler> scheduler;
    
    // Wallet integration (indirect only)
    std::vector<std::unique_ptr<interfaces::ChainClient>> chain_clients;
    interfaces::WalletLoader* wallet_loader;
};
```

**Key Insight**: All node components are referenced through NodeContext, passed around as a bundle rather than as individual global variables. This makes initialization, testing, and shutdown deterministic.

### 1.5 Dependency Model

```
Bitcoin's Dependency Graph:

kernel/
  ├─ DEPENDS ON: util, crypto, consensus
  └─ NO DEPENDENCIES: node, wallet, qt, net, rpc

node/
  ├─ DEPENDS ON: kernel, common, util, crypto
  └─ NO DEPENDENCIES: wallet, qt, rpc (uses interfaces only)

wallet/
  ├─ DEPENDS ON: common, util, crypto
  └─ NO DEPENDENCIES: kernel, node, qt (uses interfaces::Chain only)

gui (qt/)/
  ├─ DEPENDS ON: common, util, crypto
  └─ NO DEPENDENCIES: kernel, node, wallet (uses interfaces only)

rpc/
  ├─ DEPENDS ON: node, wallet (indirectly through interfaces)
  └─ chains through: node -> wallet

Key Rule: wallet/ ≠depends on= node/
```

**Why**: Allows wallet and node to run in separate processes independently.

### 1.6 Multiprocess Architecture

```
Old Bitcoin (Monolithic):
┌───────────────────────────────┐
│  bitcoind (single process)     │
│  ├─ node logic                │
│  ├─ wallet logic              │
│  └─ RPC/HTTP server           │
└───────────────────────────────┘

New Bitcoin (Multiprocess):
┌──────────────────────┐    ┌──────────────────────┐
│  bitcoin-node        │    │  bitcoin-wallet      │
│  ├─ P2P networking   │    │  ├─ Key management   │
│  ├─ Blockchain sync  │◄───►  ├─ UTXO tracking    │
│  ├─ Validation       │ IPC │  ├─ Transaction     │
│  └─ Mempool          │    │  └─ Signing          │
└──────────────────────┘    └──────────────────────┘

Benefits:
- Wallet crash doesn't crash node
- Wallet can be updated without stopping node
- Better security (wallet isolated from network)
- Scalability (multiple wallets on one node)
```

### 1.7 Initialization Pattern

```cpp
// Bitcoin's init flow uses the Init interface:
class Init {
    virtual std::unique_ptr<Node> makeNode() = 0;
    virtual std::unique_ptr<Chain> makeChain() = 0;
    virtual std::unique_ptr<WalletLoader> makeWalletLoader() = 0;
};

// Different executables implement Init differently:
// bitcoind: NodeInit -> starts node, loads wallets
// bitcoin-gui: GuiInit -> starts GUI, connects to node via IPC
// bitcoin-wallet: WalletInit -> wallet-only operations
```

---

## Part 2: PiSecure Current Architecture

### 2.1 Current Directory Structure

```
pisecure/
├── core/                    # 32 Python modules (monolithic!)
│   ├── blockchain.py        # Core blockchain logic
│   ├── hardware.py          # Hardware verification
│   ├── validation.py        # Validation logic
│   ├── consensus.py         # Consensus rules
│   ├── wallet_v2.py         # Wallet (NEW - good!)
│   ├── tokens.py            # Token logic
│   ├── pihash.py            # Mining algorithm
│   ├── p2p_sync.py          # P2P synchronization
│   ├── network.py           # Network logic
│   ├── storage.py           # Storage abstraction
│   ├── entropy_client.py    # Entropy handling
│   ├── bootstrap_manager.py # Bootstrap coordination
│   ├── market_data.py       # Market data
│   ├── dex.py               # DEX functionality
│   └── ... 18 more modules
├── api/                     # 9 modules
│   ├── server.py            # Flask REST API
│   ├── economics.py         # Token economics
│   ├── validation.py        # Request validation
│   ├── audit_logger.py      # Audit logging
│   └── ... 5 more
├── cli.py                   # 3264 lines (MONOLITHIC!)
├── access/                  # Access control
├── audit/                   # Audit trails
├── blockchain/              # Duplicate blockchain code?
├── identity/                # Identity management
├── network/                 # Network management
├── nodes/                   # Empty!
├── payments/                # Payment processing
├── plugins/                 # Plugin system
├── trusted_keys/            # Key management
└── updates/                 # Update management
```

### 2.2 Current Coupling Issues

| Issue | Bitcoin Core | PiSecure | Impact |
|-------|--------------|----------|--------|
| **Direct Imports** | Interfaces only | Direct imports everywhere | Tight coupling |
| **Node State** | NodeContext (explicit) | Implicit globals & singletons | Hard to test |
| **Wallet Access** | interfaces::Chain | Direct blockchain calls | Wallet can't be separate |
| **Process Separation** | Planned & documented | Not possible today | Single-process only |
| **Module Independence** | Clear boundaries | Everything depends on everything | Maintenance nightmare |
| **Testing** | Easy (mock interfaces) | Hard (need full stack) | Low test coverage |
| **Initialization** | Explicit (Init factory) | Implicit (module imports) | Unclear startup order |

### 2.3 PiSecure's Specific Tight Couplings

**Example 1: wallet_v2 depending on core modules**
```python
# wallet_v2.py (should be independent!)
from pisecure.core.blockchain import SignChain  # ❌ Direct dependency!
from pisecure.core.tokens import SignToken      # ❌ Direct dependency!

# Bitcoin Core equivalent (wallet should use interfaces only):
from pisecure.interfaces.chain import Chain     # ✅ Abstract interface
```

**Example 2: cli.py depending on everything**
```python
# cli.py (3264 lines!) imports:
from pisecure.core.blockchain import SignChain
from pisecure.core.pihash import compute_pihash
from pisecure.core.wallet_v2 import PiSecureWallet
from pisecure.core.entropy_client import EntropyClient
from pisecure.core.bootstrap_manager import get_bootstrap_registry
from pisecure.api.server import BlockchainAPI
from dashboard.web.app import create_app
# ... and ~50 more direct imports

# This creates a "God Object" pattern - cli.py knows about everything!
```

**Example 3: api/server.py depending on core**
```python
# api/server.py imports:
from pisecure.core.blockchain import SignChain  # Direct!
from pisecure.core.wallet_v2 import PiSecureWallet  # Direct!

# Bitcoin Core:
# RPC code uses interfaces::Wallet & interfaces::Node instead
```

### 2.4 Missing Key Patterns

| Pattern | Bitcoin Core | PiSecure | Issue |
|---------|--------------|----------|-------|
| **Interfaces Layer** | ✅ src/interfaces/ | ❌ Missing | No abstraction boundaries |
| **Context Object** | ✅ NodeContext | ❌ Missing | Implicit state |
| **Explicit Init** | ✅ Init interface | ❌ Missing | Import-based initialization |
| **Library Layers** | ✅ kernel, node, wallet | ❌ All in core/ | No separation |
| **IPC Framework** | ✅ Multiprocess ready | ❌ Not possible | Single process only |
| **Policy Module** | ✅ src/policy/ | ❌ Scattered | No centralized rules |
| **Scheduler** | ✅ CScheduler | ❌ Manual threading | Ad-hoc async |

---

## Part 3: Recommended PiSecure Refactoring

### Phase 1: Create Interfaces Layer (Foundation)

**Goal**: Establish abstraction boundaries before major changes.

```
pisecure/interfaces/
├── __init__.py
├── node.py           # Abstract node interface
├── chain.py          # Abstract chain interface (for wallet/API)
├── wallet.py         # Abstract wallet interface
├── mining.py         # Abstract mining interface
├── storage.py        # Abstract storage interface
├── network.py        # Abstract P2P interface
└── hardware.py       # Abstract hardware verification interface
```

**Example: interfaces/chain.py**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class Chain(ABC):
    """Abstract interface that wallet & API use to access blockchain state"""
    
    @abstractmethod
    def get_best_block_hash(self) -> str:
        """Get the hash of the current best block"""
        pass
    
    @abstractmethod
    def get_block_height(self) -> int:
        """Get current blockchain height"""
        pass
    
    @abstractmethod
    def get_balance(self, address: str) -> int:
        """Get balance for address"""
        pass
    
    @abstractmethod
    def send_transaction(self, tx_hex: str) -> str:
        """Submit a transaction"""
        pass
    
    # ... more abstract methods
```

**Key Benefit**: Wallet and API now depend on abstract interface, not concrete blockchain implementation. Blockchain implementation can change without affecting wallet/API.

### Phase 2: Create Node Context

**Goal**: Explicit state management instead of implicit globals.

```python
# pisecure/node/context.py
@dataclass
class NodeContext:
    """Central hub for all node services - passed around instead of using globals"""
    
    # Core services
    blockchain: Chain
    mempool: Mempool
    validation_engine: ValidationEngine
    
    # Network
    peer_manager: PeerManager
    network_coordinator: NetworkCoordinator
    
    # Hardware
    hardware_verifier: HardwareVerifier
    entropy_client: EntropyClient
    
    # Wallet integration (indirect only via interface)
    wallet_loader: Optional['interfaces.WalletLoader'] = None
    
    # Scheduling
    scheduler: Optional[Scheduler] = None
    
    # State
    is_syncing: bool = False
    exit_code: int = 0
```

**Key Benefit**: All components explicitly passed around; no hidden dependencies on globals.

### Phase 3: Reorganize Modules into Layers

**Current (Monolithic)**:
```
pisecure/core/  # 32 modules all at same level
```

**Target (Layered)**:
```
pisecure/
├── interfaces/            # Layer 0: Abstract boundaries
│   ├── node.py
│   ├── chain.py
│   ├── wallet.py
│   ├── mining.py
│   └── storage.py
├── kernel/                # Layer 1: Pure consensus (NO network, NO wallet deps)
│   ├── consensus.py
│   ├── validation.py
│   ├── difficulty.py
│   └── challenges.py
├── common/                # Layer 2: Utilities used by all
│   ├── serialization.py
│   ├── encoding.py
│   ├── errors.py
│   └── config.py
├── node/                  # Layer 3: Node operations
│   ├── context.py
│   ├── blockchain.py
│   ├── mempool.py
│   ├── validation_engine.py
│   ├── peer_manager.py
│   ├── sync_manager.py
│   └── interfaces.py      # Implements interfaces::Node, interfaces::Chain
├── wallet/                # Layer 4: Wallet (independent of node impl!)
│   ├── wallet_v2.py
│   └── interfaces.py      # Implements interfaces::Wallet
├── api/                   # Layer 5: HTTP/RPC interfaces
│   ├── server.py
│   ├── rpc_handlers.py
│   └── interfaces.py      # Implements interfaces::RPC
├── cli.py                 # Entry point (thin!)
└── main.py                # Application init
```

**Dependency Flow**:
```
cli.py
  → interfaces/Init (factory)
  → main.py (AppInit)
    → node/context.py (create NodeContext)
    → api/server.py (implements interfaces::Node, interfaces::Chain)
    → wallet/ (connects via interfaces::Wallet only)
```

### Phase 4: Create Init Factory Pattern

**Goal**: Explicit, configurable initialization.

```python
# pisecure/interfaces/init.py
class Init(ABC):
    """Factory for creating node/wallet/API components"""
    
    @abstractmethod
    def make_node(self) -> 'interfaces.Node':
        """Create and initialize node"""
        pass
    
    @abstractmethod
    def make_chain(self) -> 'interfaces.Chain':
        """Create chain interface"""
        pass
    
    @abstractmethod
    def make_wallet_loader(self) -> 'interfaces.WalletLoader':
        """Create wallet loader"""
        pass
    
    @abstractmethod
    def make_mining(self) -> 'interfaces.Mining':
        """Create mining interface"""
        pass

# Different implementations for different modes
class FullNodeInit(Init):
    """Full node with wallet support"""
    def make_node(self) -> interfaces.Node:
        # Create full node context
        pass

class ValidatorInit(Init):
    """Validation-only node (no mining)"""
    def make_node(self) -> interfaces.Node:
        # Create validator-only context
        pass

class CLIInit(Init):
    """CLI application"""
    def __init__(self, testnet=False, validate_only=False):
        self.testnet = testnet
        self.validate_only = validate_only
```

**Usage**:
```python
# cli.py becomes simple
def main():
    init = CLIInit(testnet=args.testnet, validate_only=args.validate_only)
    node = init.make_node()
    node.baseInitialize()
    node.appInitMain()
```

### Phase 5: Move Business Logic to Proper Layers

**Current Problem**: core/blockchain.py has ~2000 lines mixing everything.

**Target Reorganization**:

```python
# kernel/consensus.py - Pure consensus rules (no network, no I/O)
def validate_transaction(tx: Transaction) -> bool:
    """Pure validation logic"""
    pass

def validate_block_header(header: BlockHeader) -> bool:
    """Pure header validation"""
    pass

# node/validation_engine.py - Orchestrates validation with state
class ValidationEngine:
    def __init__(self, context: NodeContext):
        self.context = context
        self.consensus = kernel.Consensus()
    
    def accept_block(self, block: Block) -> bool:
        """Accept block with full node state"""
        if not kernel.validate_block(block):
            return False
        # Store in blockchain, update UTXO set, etc.
        pass

# node/blockchain.py - Blockchain state management
class Blockchain:
    def __init__(self, storage: interfaces.Storage):
        self.storage = storage
        self.chain = []
    
    def add_block(self, block: Block):
        self.storage.store_block(block)

# interfaces/storage.py - Abstract storage
class Storage(ABC):
    @abstractmethod
    def store_block(self, block: Block) -> None: pass
    
    @abstractmethod
    def get_block(self, hash: str) -> Optional[Block]: pass
```

**Benefit**: kernel/ is testable without network, blockchain can swap storage implementations.

---

## Part 4: Gap Analysis & Missing Functionality

### 4.1 Missing Patterns Bitcoin Has That PiSecure Needs

| Feature | Bitcoin | PiSecure | Priority | Complexity |
|---------|---------|----------|----------|-----------|
| **Interfaces Layer** | ✅ src/interfaces/ | ❌ | CRITICAL | Medium |
| **Context Object** | ✅ NodeContext | ❌ | CRITICAL | Low |
| **Init Factory** | ✅ Init interface | ❌ | CRITICAL | Medium |
| **Policy Module** | ✅ src/policy/ | ❌ | High | Medium |
| **Scheduler** | ✅ CScheduler | ❌ Threads | High | Medium |
| **Error Handling** | ✅ Result<T,E> | ❌ Exceptions | High | Medium |
| **Logging** | ✅ BCLog categories | ✅ Exists | Medium | Low |
| **Configuration** | ✅ Args system | ✅ Partial | Medium | Low |
| **RPC Framework** | ✅ Structured | ❌ Flask ad-hoc | Medium | High |
| **Multiprocess** | ✅ IPC design | ❌ Single process | Low | High |
| **Banman** | ✅ Peer banning | ❌ Manual | Low | Low |
| **Addrman** | ✅ Address management | ❌ Manual | Low | Medium |
| **Headers Sync** | ✅ Efficient sync | ❌ Full block sync | Medium | High |
| **CompactBlocks** | ✅ BIP 152 | ❌ | Low | Medium |
| **Coin Selection** | ✅ Multiple algorithms | ✅ wallet_v2 has it | Low | Low |
| **PSBT** | ✅ BIP 174 | ❌ | Low | Medium |

### 4.2 Security Gaps

| Gap | Bitcoin Approach | PiSecure Issue | Impact |
|-----|------------------|----------------|--------|
| **Wallet isolated** | Separate process possible | Direct imports | Wallet compromise = node compromise |
| **Consensus engine** | Standalone (kernel/) | Mixed with node | Hard to audit consensus |
| **Parameter validation** | Centralized args system | Ad-hoc validation | Inconsistent validation |
| **Error handling** | Result types (no exceptions) | Exceptions everywhere | Undefined behavior in error paths |
| **Logging** | Structured categories | String-based | Hard to debug, security blindspots |
| **Rate limiting** | Built-in | Per-endpoint in Flask | Inconsistent protection |
| **Peer eviction** | Sophisticated algorithm | Manual | Vulnerability to attacks |
| **Network isolation** | Clear protocol messages | Mixed protocols | Protocol confusion possible |

### 4.3 Operational Gaps

| Gap | Bitcoin Feature | PiSecure Status | Impact |
|-----|-----------------|-----------------|--------|
| **Graceful Shutdown** | Signal handling, cleanup | Not robust | Data corruption risk |
| **Health Checks** | Multiple endpoints | Scattered | Hard to diagnose issues |
| **Metrics** | Prometheus-ready | Custom format | Hard to monitor |
| **Config Validation** | Startup validation | No | Misconfiguration at runtime |
| **Upgrade Path** | Clear (--version checking) | Manual | Risk of version mismatch |
| **Replay Detection** | Network replay proof | None | Vulnerable to old tx replay |
| **Bandwidth Management** | Per-peer rate limiting | Global only | Single peer can saturate network |
| **Memory Management** | Limits and eviction | None | OOM crashes possible |

### 4.4 Testability Gaps

| Issue | Bitcoin | PiSecure | Affects |
|-------|---------|----------|---------|
| **Unit Testing** | Easy (mocks interfaces) | Hard (needs full stack) | Coverage <30% likely |
| **Fixture Setup** | TestingSetup class | Ad-hoc | Test maintenance burden |
| **Determinism** | Seed-based RNG | System RNG | Tests flaky |
| **Fuzzing** | Comprehensive | None | Undiscovered bugs |
| **Performance Testing** | Integrated | Manual | Regressions missed |

---

## Part 5: Implementation Roadmap

### Priority 1 (Months 1-2): Lay Foundation

✅ **Create interfaces/ layer**
- interfaces/node.py - Abstract node operations
- interfaces/chain.py - Abstract blockchain access  
- interfaces/wallet.py - Abstract wallet access
- interfaces/mining.py - Abstract mining
- interfaces/storage.py - Abstract storage

✅ **Create node/context.py**
- NodeContext dataclass with all services
- Dependency injection via constructor

✅ **Move constants to common/**
- Difficulty constants
- Network parameters
- Blockchain constants

### Priority 2 (Months 2-3): Reorganize Code

✅ **Separate kernel/** from node/**
- kernel/consensus.py - Pure validation logic
- kernel/difficulty.py - Difficulty calculations
- kernel/challenges.py - PiHash challenges

✅ **Create node/ layer**
- node/blockchain.py - Chain state
- node/mempool.py - Tx pool  
- node/validation_engine.py - Validation orchestration
- node/peer_manager.py - Peer management
- node/sync_manager.py - Synchronization

✅ **Implement interfaces**
- node/interfaces.py - Implements interfaces::Node, interfaces::Chain
- wallet/interfaces.py - Implements interfaces::Wallet
- api/interfaces.py - Implements interfaces::RPC

### Priority 3 (Months 3-4): Enhance Features

✅ **Add missing Bitcoin patterns**
- Error handling (Result type or custom exceptions with proper handling)
- Scheduler/thread pool (CScheduler pattern)
- Policy module (relay policies, mempool policies)
- Peer banning (BanMan pattern)
- Address management (AddrMan pattern)

✅ **Improve init flow**
- Create Init factory
- Implement different modes (full node, validator, cli)
- Configuration validation at startup

✅ **Better RPC framework**
- Structured RPC command definitions
- Unified parameter validation
- Rate limiting per command
- Better error responses

### Priority 4 (Months 4-5): Testing & Validation

✅ **Unit test framework**
- TestingSetup fixtures
- Mock implementations of interfaces
- Unit tests for each layer

✅ **Integration tests**
- Full workflow tests
- P2P network simulation
- Mining/validation scenarios

✅ **Performance testing**
- Benchmark key operations
- Memory profiling
- Network throughput

### Priority 5 (Months 5-6): Documentation & Polish

✅ **Architecture documentation**
- Module dependency graphs
- Design decisions document
- API documentation

✅ **Developer guides**
- How to add new functionality
- Testing guide
- Debugging guide

---

## Part 6: Detailed Recommendations

### 6.1 Interfaces Layer Design

```python
# pisecure/interfaces/chain.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class BlockHeader:
    hash: str
    height: int
    timestamp: int
    difficulty: int
    
@dataclass  
class BlockMetadata:
    hash: str
    height: int
    in_active_chain: bool
    timestamp: int

class Chain(ABC):
    """Interface used by wallet and API to access chain state"""
    
    # Query methods (wallet needs these)
    @abstractmethod
    def get_best_block_hash(self) -> str: pass
    
    @abstractmethod
    def get_block_height(self) -> int: pass
    
    @abstractmethod
    def get_block(self, hash_or_height) -> Optional[BlockMetadata]: pass
    
    @abstractmethod
    def get_balance(self, address: str) -> int: pass
    
    @abstractmethod
    def get_utxos(self, address: str) -> List[Dict]: pass
    
    # Transaction submission
    @abstractmethod
    def send_transaction(self, tx_hex: str) -> str: pass
    
    @abstractmethod
    def get_transaction_status(self, tx_hash: str) -> Dict: pass
    
    # Notification registration (wallet subscribes to updates)
    @abstractmethod
    def register_balance_change_handler(self, callback) -> None: pass
    
    @abstractmethod
    def register_block_connected_handler(self, callback) -> None: pass
    
    @abstractmethod
    def register_transaction_added_handler(self, callback) -> None: pass
```

### 6.2 Error Handling Pattern

```python
# Instead of: Exception -> catch, log, return error
# Use: Result type with proper semantics

from typing import Union, TypeVar, Generic, Callable
from enum import Enum

T = TypeVar('T')
E = TypeVar('E')

class Result(Generic[T, E]):
    """Result type for error handling"""
    
    def __init__(self, value: Optional[T] = None, error: Optional[E] = None):
        if value is None and error is None:
            raise ValueError("Result must have value or error")
        if value is not None and error is not None:
            raise ValueError("Result cannot have both value and error")
        self.value = value
        self.error = error
    
    def is_ok(self) -> bool:
        return self.value is not None
    
    def is_err(self) -> bool:
        return self.error is not None
    
    def map(self, f: Callable[[T], 'Result']) -> 'Result':
        if self.is_ok():
            return f(self.value)
        return self
    
    @staticmethod
    def Ok(value: T) -> 'Result[T, E]':
        return Result(value=value)
    
    @staticmethod
    def Err(error: E) -> 'Result[T, E]':
        return Result(error=error)

# Usage:
def validate_transaction(tx: Transaction) -> Result[Transaction, ValidationError]:
    if not tx.has_valid_signature():
        return Result.Err(ValidationError("Invalid signature"))
    return Result.Ok(tx)

# Chain operations:
result = validate_transaction(tx).map(lambda tx: add_to_mempool(tx))
if result.is_ok():
    print(f"Added: {result.value}")
else:
    print(f"Error: {result.error}")
```

### 6.3 Scheduler Pattern

```python
# Similar to Bitcoin's CScheduler

class Scheduler:
    """Thread-pool based task scheduler"""
    
    def __init__(self, num_threads: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        self.tasks: Dict[str, asyncio.Task] = {}
    
    def schedule_at(self, when: float, fn: Callable, *args):
        """Schedule function to run at specific time"""
        pass
    
    def schedule_recurring(self, interval: float, fn: Callable, *args):
        """Schedule function to run every interval seconds"""
        pass
    
    def schedule_once(self, fn: Callable, *args):
        """Schedule function to run once ASAP"""
        pass
    
    def stop(self):
        """Gracefully shutdown scheduler"""
        pass

# Usage:
scheduler = Scheduler()
scheduler.schedule_recurring(60, sync_blocks)  # Every 60 seconds
scheduler.schedule_recurring(300, broadcast_peers)  # Every 5 minutes
scheduler.schedule_once(initial_peer_discovery)
```

### 6.4 Policy Module

```python
# pisecure/policy/policies.py

@dataclass
class MempoolPolicy:
    """Mempool acceptance policies"""
    max_size_bytes: int = 300 * 1024 * 1024  # 300MB
    min_relay_fee: float = 0.00001
    max_tx_size: int = 4 * 1024 * 1024  # 4MB
    min_confirmations_for_relay: int = 0
    enable_rbf: bool = True
    min_fee_for_rbf: float = 0.00001

class MempoolAcceptance:
    """Centralized mempool acceptance logic"""
    
    def __init__(self, policy: MempoolPolicy):
        self.policy = policy
    
    def accept_transaction(self, tx: Transaction) -> Result[None, str]:
        """Check if transaction should be accepted to mempool"""
        
        # Check size
        if len(tx.to_bytes()) > self.policy.max_tx_size:
            return Result.Err(f"Transaction too large: {len(tx)}")
        
        # Check fees
        if tx.fee < self.policy.min_relay_fee:
            return Result.Err("Insufficient fees")
        
        # ... more checks
        return Result.Ok(None)

# Usage:
policy = MempoolPolicy(max_size_bytes=500*1024*1024)
acceptance = MempoolAcceptance(policy)
result = acceptance.accept_transaction(tx)
```

### 6.5 Graceful Shutdown Pattern

```python
# Instead of: sys.exit() scattered around
# Use: Coordinated shutdown

class ShutdownManager:
    def __init__(self):
        self.is_shutdown = False
        self.shutdown_event = threading.Event()
    
    def request_shutdown(self):
        self.is_shutdown = True
        self.shutdown_event.set()
    
    def shutdown_requested(self) -> bool:
        return self.is_shutdown
    
    def wait_shutdown(self):
        self.shutdown_event.wait()

# Usage in main:
shutdown = ShutdownManager()

# Register signal handlers
def signal_handler(sig, frame):
    shutdown.request_shutdown()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# In main loop:
while not shutdown.shutdown_requested():
    do_work()
    time.sleep(0.1)

# Cleanup
blockchain.close()
mempool.flush()
network.disconnect()
```

---

## Part 7: Quick Wins (Can Do Now)

### 7.1 Create pisecure/interfaces/ with stubs
- ✅ 1-2 hours
- ✅ Establishes boundaries
- ✅ Wallet doesn't import core directly yet, but interface exists

### 7.2 Move constants to common/
- ✅ 1 hour
- ✅ Reduces circular imports
- ✅ Single source of truth for network params

### 7.3 Create NodeContext for explicit state
- ✅ 2-3 hours
- ✅ Easier to understand what services exist
- ✅ Makes testing easier

### 7.4 Split cli.py into smaller files
- ✅ 2-3 hours per command group
- ✅ 3264 lines → 20-30 files of ~100 lines each
- ✅ Easier to maintain

### 7.5 Add Result type for error handling
- ✅ 1 hour implementation
- ✅ Gradual adoption (new code uses it)
- ✅ Better than exception chains

---

## Part 8: Expected Benefits

### After Phase 1 (Interfaces):
- ✅ Clarity on module boundaries
- ✅ Easier to add new features
- ✅ Foundation for testing
- ✅ Documentation of expectations

### After Phase 2 (Context):
- ✅ Explicit dependency injection
- ✅ No hidden global state
- ✅ Better initialization control
- ✅ Easier unit testing

### After Phase 3 (Reorganization):
- ✅ Kernel can be tested independently
- ✅ Node can be tested independently
- ✅ Wallet/API can be swapped
- ✅ Code is ~30-40% shorter (less duplication)

### After Phase 4 (Features):
- ✅ Multiprocess possible
- ✅ Better performance (scheduler)
- ✅ Better security (policies centralized)
- ✅ More robust (better error handling)

### After Phase 5 (Testing):
- ✅ >80% code coverage
- ✅ Caught bugs earlier
- ✅ Easier debugging
- ✅ Confident deployments

---

## Conclusion

Bitcoin Core's architecture is a **masterclass in modularity through abstraction boundaries**. PiSecure can adopt these patterns incrementally:

1. **Start small**: Interfaces layer + NodeContext
2. **Prove it works**: Add unit tests, see coverage improve
3. **Expand gradually**: Reorganize module by module
4. **Finish strong**: Add missing features, enable multiprocess

The goal isn't to copy Bitcoin exactly, but to **adopt the principles that make Bitcoin maintainable at scale**: clear boundaries, explicit dependencies, testable components, and separation of concerns.

This refactoring would make PiSecure:
- ✅ **Easier to maintain** (clear module responsibilities)
- ✅ **Easier to extend** (add features without touching core)
- ✅ **Easier to test** (mock interfaces, not implementations)
- ✅ **More secure** (isolated concerns, easier to audit)
- ✅ **More scalable** (multiprocess ready)
- ✅ **Better documented** (architecture is code)

