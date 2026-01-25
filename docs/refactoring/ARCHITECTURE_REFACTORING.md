# PiSecure Architecture Refactoring: Quick Reference & Action Items

## 30-Second Summary

**Problem**: PiSecure is monolithic with tight coupling (like Bitcoin circa 2012). Code is hard to test, extend, and maintain.

**Solution**: Adopt Bitcoin Core's layered architecture with abstract interfaces as boundaries.

**Impact**: Easier to add features, test code, maintain quality, and eventually run multiprocess.

---

## Current State → Target State

### Current (Problematic)
```
cli.py (3264 lines)
  ├─ imports everything directly
  ├─ depends on core/*
  ├─ depends on api/*
  ├─ depends on dashboard/*
  └─ creates tight coupling everywhere

core/* (32 modules)
  ├─ all at same level
  ├─ circular dependencies
  ├─ hard to test independently
  └─ no clear boundaries
```

### Target (Ideal)
```
interfaces/ (abstract boundaries)
  ├─ Node
  ├─ Chain
  ├─ Wallet
  ├─ Mining
  └─ Storage

kernel/ (pure consensus, no dependencies)
  ├─ validation
  ├─ difficulty
  └─ challenges

node/ (implements interfaces)
  ├─ blockchain
  ├─ mempool
  ├─ validation_engine
  ├─ peer_manager
  └─ sync_manager

wallet/ (uses Chain interface only)
  └─ wallet_v2 (unchanged!)

api/ (implements interfaces)
  ├─ server
  └─ handlers

cli.py (thin, simple)
  ├─ creates NodeContext
  ├─ starts API
  └─ handles shutdown
```

---

## Top 10 Most Important Changes

### 1. Create interfaces/ directory
**Priority**: CRITICAL  
**Time**: 2 hours  
**Files**:
- `pisecure/interfaces/__init__.py`
- `pisecure/interfaces/node.py` - Abstract node interface
- `pisecure/interfaces/chain.py` - Wallet/API use this to query blockchain
- `pisecure/interfaces/wallet.py` - GUI/API use this to control wallet
- `pisecure/interfaces/mining.py` - Mining interface
- `pisecure/interfaces/storage.py` - Abstract storage backend

**Why**: Establishes module boundaries. Everything else depends on this.

### 2. Create NodeContext
**Priority**: CRITICAL  
**Time**: 1 hour  
**File**: `pisecure/node/context.py`

```python
@dataclass
class NodeContext:
    blockchain: 'interfaces.Chain'
    mempool: Mempool
    peer_manager: PeerManager
    scheduler: Optional[Scheduler] = None
    wallet_loader: Optional[interfaces.WalletLoader] = None
    shutdown_manager: ShutdownManager = field(default_factory=ShutdownManager)
```

**Why**: Explicit state instead of hidden globals. Pass one object instead of 10.

### 3. Split cli.py into command modules
**Priority**: HIGH  
**Time**: 4-6 hours  
**Files**:
- `pisecure/cli_commands/` (new directory)
- `cli_commands/status.py`
- `cli_commands/mine.py`
- `cli_commands/wallet.py`
- `cli_commands/network.py`
- ... one file per major command group

**Why**: 3264 lines is unmaintainable. Easier to understand with separation.

### 4. Move consensus logic to kernel/
**Priority**: HIGH  
**Time**: 3-4 hours  
**Files**:
- Move `core/validation.py` → `kernel/validation.py`
- Move `core/consensus.py` → `kernel/consensus.py`
- Move `core/challenges.py` → `kernel/challenges.py`
- Move `core/difficulty_manager.py` → `kernel/difficulty.py`

**Why**: Consensus should be independent, testable without network.

### 5. Implement interfaces in node/
**Priority**: HIGH  
**Time**: 4-5 hours  
**File**: `pisecure/node/interfaces.py`

```python
class NodeImpl(interfaces.Node):
    def __init__(self, context: NodeContext):
        self.context = context
    
    def baseInitialize(self) -> bool:
        # Setup logging, config, etc.
        pass
    
    def appInitMain(self) -> bool:
        # Load blockchain, start network, etc.
        pass

class ChainImpl(interfaces.Chain):
    def __init__(self, context: NodeContext):
        self.context = context
    
    def get_best_block_hash(self) -> str:
        return self.context.blockchain.best_block_hash
    
    def get_balance(self, address: str) -> int:
        return self.context.blockchain.get_balance(address)
```

**Why**: wallet.py and api/server.py use interfaces, not implementation.

### 6. Isolate wallet_v2 from core imports
**Priority**: HIGH  
**Time**: 2-3 hours  
**Change**: Update `wallet_v2.py` to:
- Use `interfaces.Chain` instead of importing `blockchain.py`
- Use `interfaces.Storage` for database operations
- Minimal core dependencies

**Why**: wallet_v2 becomes swappable. Independent of blockchain implementation.

### 7. Create common/ for shared utilities
**Priority**: MEDIUM  
**Time**: 2 hours  
**Files**:
- `pisecure/common/__init__.py`
- `pisecure/common/config.py` - All constants
- `pisecure/common/errors.py` - Custom exceptions
- `pisecure/common/serialization.py` - Encoding/decoding

**Why**: Single source of truth. Reduces circular imports.

### 8. Add error handling patterns
**Priority**: MEDIUM  
**Time**: 3-4 hours  
**Files**:
- `pisecure/common/result.py` - Result[T, E] type
- Update major functions to return Result instead of raising exceptions

**Why**: Better error semantics. Makes error handling explicit.

### 9. Create Init factory
**Priority**: MEDIUM  
**Time**: 2-3 hours  
**File**: `pisecure/interfaces/init.py` + implementations

```python
class Init(ABC):
    def make_node(self) -> interfaces.Node: pass
    def make_chain(self) -> interfaces.Chain: pass
    def make_wallet_loader(self) -> interfaces.WalletLoader: pass
```

**Why**: Different modes (full node, validator, cli) configure differently.

### 10. Add comprehensive logging
**Priority**: MEDIUM  
**Time**: 2-3 hours  
**Update**: Existing logging with structure

```python
# Instead of: logger.info("Block received")
# Use: logger.info("block_received", extra={"hash": block.hash, "height": height})
```

**Why**: Better debugging and monitoring. Structured logging is standard.

---

## Quick Implementation Guide

### Week 1: Foundation
- [ ] Day 1: Create interfaces/ with stubs
- [ ] Day 2: Create NodeContext
- [ ] Day 3: Move common constants
- [ ] Day 4: Add Result type
- [ ] Day 5: Create common/ directory

### Week 2: Reorganization
- [ ] Day 1-2: Move consensus logic to kernel/
- [ ] Day 3-4: Implement interfaces in node/
- [ ] Day 5: Update wallet_v2 to use interfaces

### Week 3: CLI Refactor
- [ ] Day 1-3: Split cli.py into command modules
- [ ] Day 4: Create Init factory
- [ ] Day 5: Testing and cleanup

### Week 4: Enhancement
- [ ] Day 1-2: Add Scheduler
- [ ] Day 3: Add graceful shutdown
- [ ] Day 4-5: Documentation and testing

---

## Files to Create (Priority Order)

1. `pisecure/interfaces/__init__.py`
2. `pisecure/interfaces/node.py`
3. `pisecure/interfaces/chain.py`
4. `pisecure/interfaces/wallet.py`
5. `pisecure/interfaces/mining.py`
6. `pisecure/interfaces/storage.py`
7. `pisecure/node/context.py`
8. `pisecure/common/__init__.py`
9. `pisecure/common/config.py`
10. `pisecure/common/result.py`
11. `pisecure/kernel/__init__.py`
12. `pisecure/node/interfaces.py`
13. `pisecure/cli_commands/__init__.py`
14. `pisecure/interfaces/init.py`

---

## Files to Refactor

1. `pisecure/core/validation.py` → `pisecure/kernel/validation.py`
2. `pisecure/core/consensus.py` → `pisecure/kernel/consensus.py`
3. `pisecure/core/challenges.py` → `pisecure/kernel/challenges.py`
4. `pisecure/core/difficulty_manager.py` → `pisecure/kernel/difficulty.py`
5. `pisecure/core/wallet_v2.py` - Reduce core/ imports
6. `pisecure/cli.py` - Split into cli_commands/
7. `pisecure/api/server.py` - Use interfaces

---

## Expected Metrics

### Code Quality
| Metric | Current | Target |
|--------|---------|--------|
| Cyclomatic Complexity | ~8 per function | ~3-5 per function |
| Coupling (max imports per file) | ~50 | ~10-15 |
| Lines per file | ~1000-3000 | ~200-400 |
| Test coverage | <40% | >80% |
| Circular dependencies | 5-10 | 0 |

### Maintainability
| Issue | Current | Target |
|-------|---------|--------|
| Time to understand module | 30+ min | 5-10 min |
| Time to add new feature | 1-2 days | 2-4 hours |
| Time to find bug | 30+ min | 5-10 min |
| Test run time | 2-3 min | <1 min |
| CI/CD pass rate | ~70% | >95% |

---

## Risk Mitigation

### Risk: Breaking existing code during refactoring

**Mitigation**:
1. Keep old code in parallel initially
2. Interfaces are the contract, implementations can change
3. Create feature flags for new code path vs old
4. Gradual migration (new code uses new structure, old code gradually updates)

### Risk: Migration takes too long

**Mitigation**:
1. Start with interfaces layer (small, contained)
2. Only refactor one module at a time
3. Tests verify correctness
4. Use git to track changes incrementally

### Risk: New developers confused by refactoring

**Mitigation**:
1. Document architecture decision (this file!)
2. Add architecture diagrams to code
3. Create DEVELOPMENT.md with guidelines
4. Code review ensures adherence to patterns

---

## Success Criteria

- [ ] All modules have clear responsibilities
- [ ] No circular dependencies
- [ ] Wallet can be tested without blockchain
- [ ] Blockchain can be tested without network
- [ ] API can be tested without CLI
- [ ] New contributor can add feature in <2 hours
- [ ] Test suite runs in <1 minute
- [ ] Code coverage >80%
- [ ] No "temporary" hacks (comment them as TODO)
- [ ] Documentation matches code

---

## Next Steps

### Immediate (This Week)
1. **Review** this document with team
2. **Create** interfaces/ directory stubs
3. **Document** module responsibilities
4. **Setup** migration branches

### Short Term (Next 2 weeks)
1. **Implement** NodeContext
2. **Move** constants to common/
3. **Create** first interface implementations
4. **Add** Result type to common/

### Medium Term (Next 4 weeks)
1. **Reorganize** modules by layer
2. **Update** imports to use interfaces
3. **Add** unit tests for each module
4. **Document** architecture decisions

### Long Term (Next 2-3 months)
1. **Multiprocess** design (GPU, wallet in separate process)
2. **Performance** optimization (profiling, benchmarking)
3. **Advanced** features (headers sync, compact blocks, PSBT)

---

## Resources

- Bitcoin Core Developer Reference: https://doxygen.bitcoincore.org/
- Bitcoin Core Libraries: https://github.com/bitcoin/bitcoin/tree/master/doc/design/libraries.md
- Bitcoin Interfaces: https://github.com/bitcoin/bitcoin/tree/master/src/interfaces/
- Bitcoin NodeContext: https://github.com/bitcoin/bitcoin/blob/master/src/node/context.h
- Bitcoin Multiprocess: https://github.com/bitcoin/bitcoin/blob/master/doc/design/multiprocess.md

---

## Contact & Questions

For questions about architecture decisions or implementation details:
- Review ARCHITECTURE_ANALYSIS.md (comprehensive)
- Check code comments for rationale
- Look at Bitcoin Core equivalents for reference
- Discuss in architecture review before implementing

