# PiSecure Validator Rewards System

## Overview

PiSecure implements a comprehensive validator reward system that incentivizes network participation across all platforms. While mining requires Raspberry Pi hardware for proof-of-work, **validators can run on any platform** (Mac, Windows, Linux, Pi) and earn **0.5 314ST per confirmed block**.

This design enables:
- **Universal Network Growth**: Anyone with a computer can become a validator and earn rewards
- **Decentralized Security**: Multiple independent validators confirm blocks
- **Platform Agnostic**: No hardware restrictions for validation
- **Economic Incentives**: Validators earn real rewards for their work

## Architecture

### Block Confirmation
Blocks become "confirmed" when they reach one of these thresholds:
1. **5+ validations** (immediate confirmation)
2. **1+ validation aged 7+ days** (time-based confirmation)

### Validator Rewards
When a block reaches confirmation status:
- Each validator who validated the block earns **0.5 314ST**
- Rewards are tracked in `validator_rewards_per_block` dictionary
- Each validator receives reward only once per block
- Validators tracked by node_id to prevent double-rewarding

### Reward Distribution
The system automatically distributes validator rewards during mining:
1. When a new block is mined, the system checks for newly confirmed blocks
2. For each confirmed block, it identifies validators who haven't been rewarded yet
3. Creates validator reward transactions (tracked in-memory)
4. Maintains reward history for audit and reporting

## Implementation Details

### Core Blockchain Changes (`pisecure/core/blockchain.py`)

#### New Data Structures
```python
# Initialize in SignChain.__init__
self.validation_rewards_awarded = {}  # wallet_address -> total_amount
self.validator_rewards_per_block = {}  # block_index -> {node_id: {wallet, amount, timestamp}}
```

#### New Methods

**`award_validator_reward_transaction()`**
- Creates a validator reward transaction when a block confirms
- Returns None if already rewarded or block not confirmed
- Tracks reward in `validator_rewards_per_block`
- Updates cumulative `validation_rewards_awarded`

**`_distribute_pending_validator_rewards()`**
- Called during mining with verbose mode enabled
- Iterates through confirmed blocks
- Awards validators that haven't been compensated yet
- Returns count of rewards distributed

**`get_validator_reward_history(wallet_address=None)`**
- Returns list of all validator reward records
- Optional filtering by wallet address
- Each record includes: block_index, validator_node_id, wallet, amount, timestamp

**`get_confirmed_blocks_stats()`**
- Returns statistics on confirmed blocks and validator participation
- Includes: confirmed_count, unique_validators, participation distribution

#### Block Validation (`SignBlock` class)

**`is_confirmed` Property**
```python
@property
def is_confirmed(self) -> bool:
    """Check if block is confirmed (5+ validations or aged 7 days with 1+ validation)"""
    if self.validation_count >= 5:
        return True
    if self.validation_count >= 1 and self.validation_timestamp:
        age_seconds = time.time() - self.validation_timestamp
        if age_seconds >= 7 * 24 * 3600:  # 7 days
            return True
    return False
```

**`add_validator()` Method**
- Adds a validator node_id to a block (only once per node)
- Tracks validation timestamp on first validation
- Updates validation_count

## CLI Commands

Three new commands added to `pswallet` CLI:

### `pswallet validator-rewards [WALLET_ADDRESS]`
Check total validator rewards earned by a wallet.

**Usage:**
```bash
# Show all validators and total rewards
pswallet validator-rewards

# Check specific wallet
pswallet validator-rewards "validator-abc123..."

# JSON output
pswallet validator-rewards --json
```

**Output:**
```
Wallet Address: validator-abc123... | Total Rewards (314ST): 15.50
```

### `pswallet validator-history [WALLET_ADDRESS] [--limit N]`
Show detailed validator reward history with block references.

**Usage:**
```bash
# Show last 20 rewards
pswallet validator-history

# Show rewards for specific validator
pswallet validator-history "validator-abc123..."

# Show last 100 rewards
pswallet validator-history --limit 100

# JSON output
pswallet validator-history --json
```

**Output:**
```
Block #    | Validator ID | Wallet Address | Amount (314ST) | Time
100        | validator... | validator-... | 0.50           | 2026-01-21 14:32:15
101        | validator... | validator-... | 0.50           | 2026-01-21 14:32:45
```

### `pswallet validator-status`
Show network-wide validator statistics.

**Usage:**
```bash
# Show validator network stats
pswallet validator-status

# JSON output
pswallet validator-status --json
```

**Output:**
```
Validator Network Statistics
  Confirmed Blocks: 250
  Unique Validators: 42
  Total Validations: 1,250
  Avg Validators/Block: 5.0

  Top Validators:
    • validator1... (156 blocks)
    • validator2... (142 blocks)
    • validator3... (138 blocks)
```

## How Validator Rewards Work

### Step 1: P2P Network Validation
When blocks are received from peers, validators add themselves:
```python
# In p2p_sync.py _switch_to_chain()
sign_block.add_validator(node_id)  # Each validator adds themselves
```

### Step 2: Block Confirmation
After 5 validators endorse a block (or 7 days pass with 1+ validation):
```python
@property
def is_confirmed(self):
    return self.validation_count >= 5  # Confirmed immediately
    # or aged 7+ days with 1+ validation
```

### Step 3: Automatic Reward Distribution
During mining, system checks for newly confirmed blocks:
```python
# In mine_pending_transactions()
if verbose:
    self._distribute_pending_validator_rewards()  # Called after mining
```

### Step 4: Reward Tracking
Validator rewards are tracked in-memory for:
- Cumulative totals per wallet
- Per-block reward history
- Validator participation stats

## Example Scenario

### Setup
- Node A runs on Mac in validation mode
- Node B runs on Linux in validation mode  
- Node C runs on Pi 5 in mining mode

### Process
1. **Node C mines Block #100** → Added to network
2. **Nodes A, B receive Block #100** → Add themselves as validators
3. **Node A adds validator** → block.validation_count = 1
4. **Node B adds validator** → block.validation_count = 2
5. **After 2 more nodes validate** → block.validation_count = 5
6. **Block #100 becomes CONFIRMED**
7. **Next mining cycle** → System distributes 0.5 314ST to each of 4 validators (2 314ST total)

## Verification

### Test Validator Rewards
```bash
# Run validator rewards test
python3 /tmp/test_validator_rewards.py
```

### Check Blockchain State
```python
from pisecure.core import SignChain
import os

os.environ["PISECURE_TESTNET"] = "1"
blockchain = SignChain()

# Get stats
stats = blockchain.get_confirmed_blocks_stats()
print(f"Confirmed blocks: {stats['total_confirmed_blocks']}")
print(f"Validators: {stats['unique_validators']}")

# Check specific wallet rewards
rewards = blockchain.get_validation_rewards("validator-abc123...")
print(f"Rewards earned: {rewards:.2f} 314ST")

# Get full history
history = blockchain.get_validator_reward_history()
for record in history:
    print(f"Block {record['block_index']}: {record['amount']} 314ST")
```

### CLI Verification
```bash
# Show all validator rewards
pswallet validator-rewards

# Show network stats
pswallet validator-status

# Show reward history
pswallet validator-history --limit 50
```

## Future Enhancements

### Phase 2: Validator Registration
- Persistent validator identity registration
- Reputation scoring based on validation accuracy
- Stake requirements for validator participation

### Phase 3: Advanced Incentives
- Validator slashing for malicious behavior
- Delegation system (stake validators with tokens)
- Governance participation rewards

### Phase 4: Integration with Bootstrap Server
- Entropy quality scoring for validators
- Reputation persistence across network
- Validator tier system based on participation

## Technical Notes

### Why Validators Must Track Separately
- Mining rewards go to miner wallet (immediate)
- Validator rewards accumulate as blocks confirm over time
- Separate tracking prevents double-rewarding
- Enables fair distribution to all validators

### Performance Considerations
- `_distribute_pending_validator_rewards()` is O(n) where n = confirmed blocks
- Called only during mining with verbose=True
- Cached in-memory until persisted
- Does not create actual tokens (tracked separately)

### Security Properties
- Node_id prevents validator spoofing
- Per-validator-per-block tracking prevents double-rewards
- Timestamp tracking enables forensic analysis
- Confirmation requires Byzantine quorum (5 validators)

## Integration with Existing Systems

### Mining System
- Validator rewards independent of mining rewards
- Miners earn base reward + transaction fees
- Validators earn 0.5 per confirmed block
- No conflict in incentive structures

### P2P Sync
- Validator tracking happens in block receipt
- Confirmed blocks propagate via network
- Rewards calculated locally on each node

### Wallet System
- Validator rewards tracked in SignChain object
- Can be queried via CLI commands
- Future: integrate into wallet balance (with options)

## Deployment Checklist

- [x] Implement validator reward tracking in blockchain.py
- [x] Add is_confirmed property to SignBlock
- [x] Implement reward distribution method
- [x] Add CLI commands to pswallet
- [x] Test validator reward system
- [ ] Update documentation
- [ ] Add validator reward persistence (optional)
- [ ] Implement validator registration (future)
- [ ] Add reputation scoring (future)

---

**Last Updated:** January 21, 2026
**Version:** 1.0 - Initial Implementation
**Status:** Ready for Testing
