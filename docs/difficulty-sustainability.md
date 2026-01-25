# PiSecure Difficulty & Hardware Sustainability Strategy

## Current Status (Jan 2026)

### Hardware Performance (Pi 5)
- **PiHash Settings**: 1 round, 32MB RAM
- **Hash Rate**: ~1 H/s (1 second per hash)
- **Difficulty 2**: ~4 hashes avg = ~4 seconds per block ✅ 
- **Difficulty 3**: ~8 hashes avg = ~8 seconds per block ✅
- **Difficulty 4**: ~16 hashes avg = ~16 seconds per block ⚠️
- **Difficulty 5**: ~32 hashes avg = ~32 seconds per block ❌

### Mock Hardware Removed
- ✅ `PISECURE_MOCK_HARDWARE` flag removed from production code
- ✅ PiHash works on real Pi 5 hardware (1 H/s)
- ✅ Hardware verification enforced for all mining

## Difficulty Adjustment Algorithm

### Configuration
```python
difficulty_config = {
    'min_difficulty': 2,          # Minimum for security
    'max_difficulty': 4,          # Maximum for Pi hardware
    'target_block_time': 60,      # Target 1 minute per block
    'adjustment_interval': 100,   # Adjust every 100 blocks
    'adjustment_factor_max': 2.0  # Max 2x change per adjustment
}
```

### How It Works
1. **Measures Performance**: Tracks actual block times over 100-block intervals
2. **Calculates Adjustment**: Compares actual vs target (60 seconds)
3. **Applies Caps**: 
   - Never goes below difficulty 2 (security floor)
   - Never goes above difficulty 4 (Pi hardware ceiling)
4. **Gradual Changes**: Maximum ±1 difficulty per adjustment

### Why This Works

#### For Launch Phase
- Starts at difficulty 3 (manageable for early miners)
- Allows quick block generation during network bootstrap
- Easy onboarding for new Pi miners

#### For Growth Phase
- Automatically increases to difficulty 4 if blocks too fast
- Caps prevent difficulty spiral (unlike Bitcoin's unlimited growth)
- Keeps mining accessible to all Pi models (Zero through 5)

#### For Mature Network
- Maximum difficulty 4 keeps Pi devices competitive
- ASICs deterred by memory-hard PiHash algorithm
- Network can scale via:
  - Faster Pi models (future Pi 6, 7, etc.)
  - Native PiHash acceleration (Cython extensions)
  - Parallel mining (multiple Pi devices)

## Scalability Strategy

### Short Term (0-1000 blocks)
- **Difficulty**: 2-3
- **Block Time**: 4-8 seconds
- **Strategy**: Fast bootstrap, easy onboarding

### Medium Term (1000-10000 blocks)
- **Difficulty**: 3-4
- **Block Time**: 8-16 seconds
- **Strategy**: Balanced security & accessibility

### Long Term (10000+ blocks)
- **Difficulty**: Capped at 4
- **Block Time**: ~16 seconds (1 minute target)
- **Strategy**: Sustainable Pi mining forever

## Hardware Roadmap

### Optimization Path
1. **Current**: Python PiHash (1 H/s on Pi 5)
2. **Phase 1**: Cython native extensions (5-10x = 5-10 H/s)
3. **Phase 2**: ARM NEON SIMD optimizations (20-50 H/s)
4. **Phase 3**: NPU acceleration on Pi 5 (100+ H/s potential)

### Network Growth Scenarios

#### Conservative Growth (Current Hardware)
- **Hashrate**: 1 H/s per device
- **Network**: 100 devices = 100 H/s total
- **Difficulty 4**: 16 hashes = 160ms network-wide
- **Result**: Blocks every 160ms (too fast) → difficulty increases hit cap at 4

#### Optimized Growth (Native Extensions)
- **Hashrate**: 10 H/s per device (Cython)
- **Network**: 1000 devices = 10,000 H/s total
- **Difficulty 4**: 16 hashes = 1.6ms network-wide
- **Result**: Still capped at difficulty 4, but network can scale

#### Future Growth (NPU Acceleration)
- **Hashrate**: 100 H/s per device (Pi 5 NPU)
- **Network**: 10,000 devices = 1M H/s total
- **Difficulty 4**: Still practical for individual miners
- **Result**: Massive network capacity without excluding small miners

## Key Design Principles

### 1. **Hardware Democracy**
- Any Raspberry Pi can mine (Zero to Pi 5)
- Difficulty cap prevents "arms race"
- No expensive mining rigs required

### 2. **ASIC Resistance**
- Memory-hard PiHash (32MB minimum)
- Hardware fingerprint binding
- Optimized for ARM, not x86/ASIC

### 3. **Sustainable Economics**
- Mining rewards stay accessible
- Network can grow without excluding hobbyists
- Encourages distributed network (vs centralization)

### 4. **Future-Proof Design**
- Difficulty cap allows hardware improvements
- Native acceleration path planned
- Backward compatible with older Pi models

## Testnet Usage

All development and testing should use testnet:

```bash
# Mine on testnet (separate data directory)
pisecure mine --testnet --wallet your_wallet

# Testnet data location
/var/lib/pisecure/testnet/

# Mainnet data location  
/var/lib/pisecure/
```

## Migration Notes

### Removed Features
- ❌ `PISECURE_MOCK_HARDWARE=1` environment variable (production)
- ❌ SHA256 fallback mining (security risk)
- ❌ Unlimited difficulty growth (hardware killer)

### Added Features
- ✅ `--testnet` flag for safe testing
- ✅ Hardware-capped difficulty adjustment
- ✅ Optimized PiHash settings (1 round, 32MB)
- ✅ Verbose mining progress output

### Breaking Changes
- Mining now requires real Raspberry Pi hardware
- Difficulty capped at 4 (not unlimited)
- Default difficulty reduced to 3 (was 4)

## Recommendations

### For Miners
1. Start with `--testnet` flag for testing
2. Use `--limit` to control mining sessions
3. Monitor system temperature with `--safe-mode`
4. Consider Cython extensions for 5-10x speedup

### For Developers
1. All testing on testnet (`--testnet` flag)
2. Test on real Pi hardware (mock removed)
3. Monitor block times for difficulty tuning
4. Prepare for native acceleration phase

### For Network Operators
1. Bootstrap servers should track block times
2. Adjust target block time if needed (currently 60s)
3. Monitor difficulty ceiling effectiveness
4. Plan for Cython/native rollout

## Future Considerations

### Potential Adjustments
- **Target Block Time**: Currently 60s, could adjust to 30s or 120s
- **Difficulty Cap**: Currently 4, could increase with native acceleration
- **Adjustment Interval**: Currently 100 blocks, could tune based on network size
- **PiHash Settings**: Currently 1r/32MB, could optimize per Pi model

### Network Health Metrics
- Average block time should stay near 60s
- Difficulty should stabilize at 3-4
- All Pi models should be able to mine
- No single device should dominate hashrate

## Conclusion

The capped difficulty approach ensures PiSecure remains:
- **Accessible**: Anyone with a Pi can mine
- **Secure**: Sufficient difficulty prevents attacks
- **Sustainable**: Network can grow without excluding hobbyists
- **Scalable**: Hardware improvements benefit everyone equally

This is a fundamental difference from Bitcoin's "race to the bottom" where only industrial operations can compete. PiSecure is designed for hobbyists, educators, and the maker community - forever.
