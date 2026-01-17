# PiHash Network Integration

## Overview

PiSecure's PiHash algorithm has been optimized for Raspberry Pi-exclusive mining with universal validation. This document explains how PiHash integrates with the blockchain network and syndicate mining pools.

## Performance Characteristics

### Hash Rates by Pi Model

| Pi Model | Hash Rate | Time per Hash | Relative Performance |
|----------|-----------|---------------|---------------------|
| Pi Zero/1 | 0.05 H/s | ~20 seconds | 0.1x |
| Pi 2 | 0.2 H/s | ~5 seconds | 0.3x |
| Pi 3 | 0.5 H/s | ~2 seconds | 0.5x |
| Pi 4 | 1.0 H/s | ~1 second | 1.0x (baseline) |
| Pi 5 | 2.0 H/s | ~0.5 seconds | 2.0x |

### Block Time Targets

- **Target**: 20 seconds per block
- **Range**: 10-30 seconds
- **Difficulty Adjustment**: Automatic based on network block times

## Network Consensus

### Difficulty Adjustment Algorithm

```python
# Target: 20 second blocks
if avg_block_time < 10 seconds:
    difficulty += 1  # Blocks too fast, increase difficulty
elif avg_block_time > 30 seconds:
    difficulty -= 1  # Blocks too slow, decrease difficulty
else:
    # Within acceptable range, maintain difficulty
```

### Mining Difficulty

Difficulty is measured in leading hex zeros:
- **Difficulty 1**: ~16 hashes required (1 hex zero)
- **Difficulty 2**: ~256 hashes required (2 hex zeros)
- **Difficulty 3**: ~4,096 hashes required (3 hex zeros)

Example hash rates for different difficulties:

| Difficulty | Avg Hashes | Pi 5 Time | Pi 4 Time | Pi 3 Time |
|-----------|------------|-----------|-----------|-----------|
| 1 | 16 | ~8s | ~16s | ~32s |
| 2 | 256 | ~128s | ~256s | ~512s |
| 3 | 4,096 | ~34m | ~68m | ~137m |

## Block Validation

### Universal Fast Validation

Any device (Pi or non-Pi) can validate blocks quickly:

```python
from pisecure.core.pihash import verify_pihash_fast

# Fast validation (< 1 second on any hardware)
is_valid = verify_pihash_fast(
    data=block_data,
    nonce=nonce,
    expected_hash=block_hash,
    rounds=1,           # Single round for fast validation
    memory_mb=32,       # Minimal memory
    parallelism=1       # Single lane
)
```

**Validation Performance:**
- Time: <1 second on any hardware
- Memory: 32MB
- Compatible with: Mobile devices, web browsers, IoT devices, exchanges

### Mining vs Validation

| Aspect | Mining | Validation |
|--------|--------|------------|
| Hardware Required | Raspberry Pi only | Any device |
| Time | ~1 second/hash (Pi 4) | <1 second total |
| Memory | 32-256MB | 32MB |
| Rounds | 1-8 | 1 |
| Parallelism | 1-4 | 1 |

## Syndicate Mining

### Overview

Mining syndicates allow multiple Pi devices to pool their hashpower for more consistent rewards.

### Reward Distribution

```python
# Block reward: 50 314ST tokens
# Syndicate fee: 5% (2.5 314ST)
# Finder bonus: 10% (5 314ST)
# Distributable: 85% (42.5 314ST)

# Distribution formula:
member_reward = (member_hashpower / total_hashpower) * distributable_amount
if member_found_block:
    member_reward += finder_bonus
```

### Example Syndicate

**Members:**
- 1x Pi 5 (2.0 H/s) - 40% hashpower
- 2x Pi 4 (1.0 H/s each) - 40% hashpower  
- 1x Pi 3 (0.5 H/s) - 10% hashpower
- 1x Pi Zero (0.05 H/s) - 1% hashpower

**Total Hashpower:** 4.55 H/s  
**Expected Block Time:** ~3.5 seconds (difficulty 1)

**Reward Distribution** (if Pi 4 finds block):
- Pi 5: 20.2 SIGN (40% of distributable)
- Pi 4 (finder): 14.2 SIGN (20% + 10% bonus)
- Pi 4 (other): 8.6 SIGN (20%)
- Pi 3: 4.1 SIGN (10%)
- Pi Zero: 0.4 SIGN (1%)
- Coordinator: 2.5 SIGN (5% fee)

### Setting Up a Syndicate

```python
from pisecure.core.syndicate import MiningSyndicate

# Create syndicate
syndicate = MiningSyndicate(
    syndicate_name="My Pi Pool",
    coordinator_wallet="your_wallet_address"
)

# Add members
syndicate.add_member(
    member_id="miner_1",
    wallet_address="member_wallet",
    pi_model="Raspberry Pi 5 Model B"
)

# Distribute work
work_packages = syndicate.distribute_work(
    block_data=block_data,
    difficulty=1,
    pihash_config={'rounds': 1, 'memory_mb': 32, 'parallelism': 1}
)

# Submit results
syndicate.submit_work_result(
    member_id="miner_1",
    found_nonce=42,
    hashes_completed=100
)

# Distribute rewards
rewards = syndicate.distribute_rewards(
    block_reward=50.0,
    finder_id="miner_1"
)
```

## Network Health Monitoring

### Hashrate Estimation

```python
from pisecure.core.blockchain import SignChain

blockchain = SignChain(mining_algorithm='pihash')
network_stats = blockchain.estimate_network_hashrate()

print(f"Network Hashrate: {network_stats['hashrate_human']}")
print(f"Unique Miners: {network_stats['unique_miners']}")
print(f"Avg Block Time: {network_stats['avg_block_time']:.1f}s")

# Estimated device distribution
for device, count in network_stats['estimated_devices'].items():
    print(f"{device}: ~{count} devices")
```

**Example Output:**
```
Network Hashrate: 45.5 H/s
Unique Miners: 23
Avg Block Time: 18.2s
Pi 5 (2 H/s): ~4 devices
Pi 4 (1 H/s): ~22 devices
Pi 3 (0.5 H/s): ~9 devices
Pi 2/Zero (0.2 H/s): ~4 devices
```

## Economic Model

### Fair Mining Rewards

Performance factors ensure fair competition:

```python
# Difficulty adjusted by Pi model
base_difficulty = 2
pi_factor = get_pi_performance_factor()  # 0.1x to 2.0x

adjusted_difficulty = base_difficulty * pi_factor

# Examples:
# Pi Zero: difficulty 2 * 0.1 = 0.2 (very easy)
# Pi 4: difficulty 2 * 1.0 = 2.0 (baseline)
# Pi 5: difficulty 2 * 2.0 = 4.0 (harder)
```

### Syndicate Economics

**Benefits for Smaller Pis:**
- Pi Zero solo mining: ~1 block per 320 seconds (difficulty 1)
- Pi Zero in syndicate: Consistent rewards every ~3.5 seconds

**Syndicate Advantages:**
- Predictable income
- Lower variance
- Shared infrastructure costs
- Professional pool management

## Implementation Examples

### Solo Mining

```python
from pisecure.core.pihash import PiHash
import json

# Initialize miner
miner = PiHash(rounds=1, memory_mb=32, parallelism=1, mining_mode=True)

# Prepare block data
block_data = json.dumps(block, sort_keys=True).encode()

# Mine block
nonce, block_hash = miner.find_nonce(block_data, difficulty=1)

print(f"Found! Nonce: {nonce}, Hash: {block_hash}")
```

### Syndicate Mining

See [`examples/syndicate_mining_demo.py`](../examples/syndicate_mining_demo.py) for complete implementation.

### Validation

```python
from pisecure.core.pihash import verify_pihash_fast

# Receive block from network
block = receive_block_from_peer()

# Validate quickly (any hardware)
is_valid = verify_pihash_fast(
    data=block.data,
    nonce=block.nonce,
    expected_hash=block.hash,
    rounds=1,
    memory_mb=32,
    parallelism=1
)

if is_valid:
    add_block_to_chain(block)
```

## Technical Details

### Algorithm Parameters

**Mining Configuration:**
- Rounds: 1-8 (more rounds = harder)
- Memory: 32-256 MB (more memory = harder)
- Parallelism: 1-4 lanes (must match for validation)
- Mining Mode: True (requires Pi hardware)

**Validation Configuration:**
- Rounds: 1 (fast path)
- Memory: 32 MB (minimal)
- Parallelism: 1 (universal)
- Mining Mode: False (no hardware requirement)

### Deterministic Hashing

PiHash hashes depend **only** on:
1. Block data
2. Nonce value

This ensures universal validation while requiring Pi hardware for efficient mining.

## Future Improvements

### Planned Features

1. **Dynamic Memory Scaling** - Adjust memory based on available RAM
2. **Parallel Validation** - Multi-threaded validation for syndicates
3. **Hardware Acceleration** - VideoCore GPU mining (Pi-specific)
4. **Quantum Resistance** - Integration with XMSS signatures
5. **Cross-Chain Bridges** - Validate PiSecure blocks on other chains

### Performance Optimizations

- ARM NEON SIMD intrinsics for 5-10x speedup
- Cache-optimized memory access patterns
- Hardware random number generator integration
- Temperature-based difficulty adjustment

## Conclusion

PiHash provides:
- ✅ Pi-exclusive mining (prevents ASIC/GPU dominance)
- ✅ Universal fast validation (any device can verify)
- ✅ Fair rewards across Pi models (performance factors)
- ✅ Efficient syndicate pooling (consistent income)
- ✅ 10-30 second block times (fast transactions)

For more information, see:
- [PiHash Mining Example](../examples/pihash_mining_example.py)
- [Syndicate Mining Demo](../examples/syndicate_mining_demo.py)
- [Core Documentation](../docs/README.md)
