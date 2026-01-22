# PiSecure Validator Guide

## Overview

**PiSecure supports two distinct roles:**

1. **Miners** - Require genuine Raspberry Pi hardware (Pi-only)
2. **Validators** - Can run on ANY device (Pi, Mac, Windows, Linux)

This separation is fundamental to PiSecure's design and enables network growth across diverse platforms.

---

## Why Universal Validation Matters

### Network Growth Strategy
- **Mining constraints**: Only Raspberry Pi devices can mine blocks (hardware-verified PiHash)
- **Validation openness**: Anyone can validate blocks, regardless of hardware
- **Incentive alignment**: Validators earn rewards for maintaining network integrity
- **Decentralization**: More validators = stronger network consensus

### Use Cases for Non-Pi Validators
- **Data centers** validating blockchain state without Pi hardware
- **Desktop users** (Mac/Windows/Linux) running full nodes
- **Cloud validators** providing 24/7 network availability
- **Exchanges & Services** validating transactions before accepting 314ST tokens
- **Development teams** running testnets on any platform

---

## How Validation Works Without Pi Hardware

### Validation-Only Mode

PiSecure includes a special `PISECURE_VALIDATE_ONLY` mode that enables non-Pi devices to validate blocks:

```bash
# Set environment variable before starting validator
export PISECURE_VALIDATE_ONLY=1

# Run validation on any platform
pisecure status         # Check blockchain validity
pisecure validate       # Validate entire chain
```

### What Gets Validated (Platform-Agnostic)

When you run in validation-only mode, PiSecure validates:

1. **Block chain integrity** - Each block's `previous_hash` links correctly
2. **Proof-of-work validity** - Hash meets difficulty requirements (≥130 zero bits)
3. **Transaction signatures** - Cryptographic signatures verify sender authenticity
4. **Phase 1 Challenge Proofs** - Fiat-Shamir ZK proofs verify mining legitimacy
5. **UTXO consistency** - Token balances match unspent transaction outputs
6. **Consensus rules** - Block timestamps, transaction formats, etc.

**Important:** Validation does NOT require:
- Raspberry Pi hardware
- PiHash hardware verification
- GPIO access or Pi-specific features
- Mining capabilities

### Challenge Validation (Universal)

Phase 1 mining challenges use Fiat-Shamir ZK proofs that can be validated on ANY platform:

```python
from pisecure.core.challenges import get_challenge_manager

# Works on Mac, Windows, Linux, Pi - no hardware required
challenge_manager = get_challenge_manager()

# Validate any challenge response (pure SHA256 + XOR math)
is_valid, error = challenge_manager.validate_challenge_response(
    challenge_response=block.challenge_response,
    expected_prev_hash=previous_block.hash
)

print(f"Challenge valid: {is_valid}")  # True/False on any platform
```

**Why this works universally:**
- Uses only SHA256 hashing (standard cryptography)
- XOR operations (basic math)
- No hardware-specific operations
- No Pi-bound verification required

---

## Running a Validator Node

### Quick Start (Any Platform)

```bash
# 1. Install PiSecure (Mac/Windows/Linux/Pi)
pip install pisecure

# 2. Enable validation-only mode
export PISECURE_VALIDATE_ONLY=1

# 3. Start validator
pisecure validate --continuous

# 4. Join validator pool (earn rewards)
pisecure wallet register-validator --wallet-id YOUR_WALLET_ADDRESS
```

### Validation Commands

```bash
# Check blockchain status
pisecure status

# Validate entire blockchain
pisecure validate

# Continuous validation (monitor new blocks)
pisecure validate --continuous --interval 10

# Validate specific block range
pisecure validate --start-block 1000 --end-block 2000

# Get validator rewards info (0.1x block reward distributed among validators)
pisecure wallet validator-rewards --wallet-id YOUR_WALLET_ADDRESS
```

### Python API (Full Node Validator)

```python
import os
from pisecure.core import SignChain

# Enable validation-only mode (works on ANY platform)
os.environ['PISECURE_VALIDATE_ONLY'] = '1'

# Create blockchain instance
blockchain = SignChain()

# Validate entire chain
is_valid = blockchain.validate_chain()
print(f"Blockchain valid: {is_valid}")

# Get chain info
info = blockchain.get_chain_info()
print(f"Blocks: {info['blocks']}")
print(f"Network health: {info['network_health']}")

# Validate new blocks as they arrive
def on_new_block(block):
    """Callback when new block is received"""
    # Validate block against chain
    if blockchain.validate_chain():
        print(f"✅ Block {block['index']} validated")
    else:
        print(f"❌ Block {block['index']} invalid")

# Register validator callback
blockchain.register_block_callback(on_new_block)
```

---

## Validator Incentives

### Reward Structure

Validators earn 314ST tokens for maintaining network integrity:

```python
from pisecure.api.economics import TokenEconomics

economics = TokenEconomics()

# Validator reward distribution (per block)
# Total validation pool: 0.1x mining reward (~6.5 314ST per block)
validator_reward = economics.calculate_validator_reward(
    block_height=current_height,
    num_validators=active_validator_count
)

# Example rewards (distributed proportionally):
# 100 validators: ~0.065 314ST per validator per block
# 1000 validators: ~0.0065 314ST per validator per block
```

### How to Earn Validator Rewards

1. **Register as validator** - Submit wallet address to network
2. **Run full node** - Validate all blocks continuously
3. **Maintain uptime** - 95%+ uptime required for rewards
4. **Participate in consensus** - Vote on chain forks and disputes

### Validator Requirements

- **Hardware**: Any device (Pi, Mac, Windows, Linux)
- **Storage**: ~10GB for full blockchain (grows over time)
- **Network**: Stable internet connection (1 Mbps+)
- **Uptime**: 95%+ recommended for consistent rewards
- **Stake**: Optional minimum stake for higher rewards

---

## Testnet Validation

Test validation on testnet before joining mainnet:

```bash
# Enable testnet mode
export PISECURE_TESTNET=1
export PISECURE_VALIDATE_ONLY=1

# Run testnet validator
pisecure validate --continuous

# Testnet uses separate blockchain at:
# /var/lib/pisecure-testnet/
```

---

## Validation vs Mining Comparison

| Feature | Validators (Any Platform) | Miners (Pi Only) |
|---------|---------------------------|------------------|
| **Hardware Required** | Any device | Raspberry Pi |
| **PiHash Verification** | ❌ Not required | ✅ Required |
| **Block Creation** | ❌ Cannot mine | ✅ Can mine |
| **Block Validation** | ✅ Full validation | ✅ Full validation |
| **Challenge Proofs** | ✅ Validate proofs | ✅ Generate & validate |
| **Network Participation** | ✅ P2P sync | ✅ P2P sync |
| **Earn Rewards** | ✅ Validator rewards | ✅ Mining rewards |
| **Storage Requirements** | ~10GB (full chain) | ~10GB (full chain) |
| **CPU Usage** | Low (validation only) | High (mining + validation) |

---

## Technical Implementation

### How PISECURE_VALIDATE_ONLY Works

When validation-only mode is enabled, the blockchain behaves differently:

```python
# pisecure/core/blockchain.py (lines 826-831)
def calculate_hash(self) -> str:
    """Calculate hash of the block using PiHash algorithm (PiSecure standard)"""
    block_string = json.dumps(...)
    
    # In validate-only mode, allow any algorithm (we're not mining, just validating)
    if os.environ.get("PISECURE_VALIDATE_ONLY") == "1":
        # For validation, use simple hash without hardware checks
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    # Mining mode: PiHash is mandatory
    if self.algorithm != "pihash":
        raise ValueError("BLOCKCHAIN SECURITY: PiSecure requires PiHash algorithm")
    
    # Use PiHash for mining...
```

**Key insight:** Validators don't need to *compute* PiHash (requires Pi hardware), they only need to *verify* the hash meets difficulty requirements (pure math, any platform).

### Challenge Validation Implementation

```python
# pisecure/core/challenges.py (lines 136-203)
def validate_challenge_response(
    self,
    challenge_response: ChallengeResponse,
    expected_prev_hash: str
) -> Tuple[bool, str]:
    """
    Validate Fiat-Shamir ZK proof (UNIVERSAL - works on any platform)
    
    This validation uses only:
    - SHA256 hashing (standard cryptography library)
    - XOR operations (basic bitwise math)
    - Zero-bit counting (pure Python bit manipulation)
    
    No hardware-specific operations required!
    """
    # 1. Reconstruct commitment from nonce + salt
    commitment_data = f"{challenge_response.nonce_used}||{challenge_response.salt}||{challenge_response.timestamp}"
    reconstructed_commitment = hashlib.sha256(commitment_data.encode()).hexdigest()
    
    # 2. Verify commitment matches
    if reconstructed_commitment != challenge_response.commitment:
        return False, "Commitment reconstruction failed"
    
    # 3. Reconstruct Fiat-Shamir challenge
    fs_challenge_data = f"{reconstructed_commitment}||{expected_prev_hash}||{challenge_response.challenge_id.split('-')[1]}"
    reconstructed_fs_challenge = hashlib.sha256(fs_challenge_data.encode()).hexdigest()
    
    # 4. Verify XOR property: fs_response = nonce XOR fs_challenge
    # (Pure math - works everywhere)
    expected_response_int = challenge_response.nonce_used ^ int(reconstructed_fs_challenge[:16], 16)
    actual_response_int = int(challenge_response.fs_response, 16)
    
    if expected_response_int != actual_response_int:
        return False, "Fiat-Shamir response verification failed"
    
    # 5. Verify proof-of-work (count zero bits - pure Python)
    from .pihash import count_zero_bits  # Works on any platform!
    actual_zero_bits = count_zero_bits(challenge_response.hash_result)
    
    if actual_zero_bits < challenge_response.zero_bits:
        return False, f"Zero bits mismatch: claimed {challenge_response.zero_bits}, actual {actual_zero_bits}"
    
    return True, "Challenge response validated successfully"
```

**Key insight:** The `count_zero_bits` function is pure Python (no hardware dependency):

```python
# pisecure/core/pihash.py
def count_zero_bits(hash_hex: str) -> int:
    """Count leading zero bits in a hex hash (UNIVERSAL - works anywhere)"""
    if not hash_hex:
        return 0
    
    zero_bits = 0
    for char in hash_hex:
        nibble = int(char, 16)  # Convert hex char to 4-bit value
        
        if nibble == 0:
            zero_bits += 4  # All 4 bits are zero
        else:
            # Count leading zeros in this nibble
            for i in range(3, -1, -1):
                if nibble & (1 << i) == 0:
                    zero_bits += 1
                else:
                    return zero_bits  # Found first 1-bit
    
    return zero_bits  # All bits are zero
```

---

## Troubleshooting

### Common Validation Issues

**Error: "PiHash library not available"**
- **Solution**: Set `PISECURE_VALIDATE_ONLY=1` before importing blockchain
- **Cause**: Trying to mine without Pi hardware

**Error: "Hardware verification failed"**
- **Solution**: Use validation-only mode (you're validating, not mining)
- **Cause**: PiHash requires Pi hardware for mining

**Warning: "Challenge response validation failed"**
- **Expected behavior**: Some older blocks may not have challenge proofs
- **Action**: Continue validation (block itself is still valid)

### Validator Node Health Checks

```bash
# Check validator status
pisecure status --validator

# Monitor validation performance
pisecure validate --benchmark

# Check network connectivity
pisecure network peers

# Verify blockchain integrity
pisecure validate --full-check
```

---

## Best Practices

### Security
- Run validator behind firewall (only expose P2P port 3142)
- Keep validator software updated (`pip install --upgrade pisecure`)
- Backup wallet keys regularly
- Monitor validator uptime and rewards

### Performance
- Use SSD for blockchain storage (faster validation)
- Allocate sufficient RAM (4GB+ recommended)
- Monitor CPU usage during validation
- Consider running multiple validators for redundancy

### Reliability
- Set up automatic restarts on failure
- Monitor network connectivity
- Keep system clock synchronized (NTP)
- Log validation events for auditing

---

## Further Reading

- [Phase 1 Mining Challenges](phase1_mining_challenges.md) - Technical details of ZK proof system
- [Network Setup Guide](network-setup.md) - P2P networking configuration
- [Token Economics](economics.md) - Validator reward structure
- [API Documentation](api-documentation.txt) - REST API for validators

---

## Community & Support

- **Discord**: Join #validators channel for support
- **Forum**: forum.pisecure.org/validators
- **GitHub**: github.com/UnderhillForge/PiSecure/issues
- **Email**: validators@pisecure.org

**Remember:** Validators are the backbone of PiSecure's decentralized network. By running a validator on ANY platform (Mac, Windows, Linux, Pi), you earn rewards while strengthening the network!
