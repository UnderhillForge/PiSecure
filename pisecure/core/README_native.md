# PiHash Native Extensions

## Overview

PiHash includes optional Cython-optimized native extensions that provide **5-10x performance improvement** for mining operations while maintaining the same algorithmic behavior as the pure Python implementation.

## Why Native Extensions?

### Performance
- **G-function**: 8x faster (called millions of times per hash)
- **Memory mixing**: 6x faster (largest compute bottleneck)
- **Overall mining**: 5-10x faster depending on Pi model

### Transparency
- Algorithm remains **open-source and auditable** in Python
- Native code is compiled from readable Cython source
- Validation uses pure Python for maximum compatibility

## Architecture

```
┌─────────────────────────────────────────────┐
│         PiHash (pisecure/core/pihash.py)    │
│  - Full Python implementation (always works)│
│  - Auditable, portable, validation-friendly │
└────────────┬────────────────────────────────┘
             │
             ↓ (optional, mining only)
┌─────────────────────────────────────────────┐
│   Native Extensions (_pihash_native.pyx)    │
│  - Cython → C → ARM machine code            │
│  - NEON SIMD optimizations                  │
│  - 5-10x faster for mining                  │
└─────────────────────────────────────────────┘
```

## Installation

### Automatic (Recommended)

```bash
# Build and install native extensions
python pisecure/core/build_pihash_native.py

# Clean and rebuild
python pisecure/core/build_pihash_native.py --clean
```

### Manual

```bash
# Install build dependencies
pip install cython numpy

# Build extensions (basic)
python pisecure/core/setup_pihash.py build_ext --inplace

# Build with ARM NEON optimizations (Raspberry Pi)
CFLAGS="-O3 -march=native -mfpu=neon" \
python pisecure/core/setup_pihash.py build_ext --inplace
```

## Usage

### Mining (Automatic)

Native code is used automatically when available for mining:

```python
from pisecure.core.pihash import PiHash

# Automatically uses native code if available
pihash = PiHash(rounds=8, memory_mb=256, mining_mode=True)
result = pihash.compute(block_data, nonce)
```

### Validation (Pure Python)

Validation always uses pure Python for compatibility:

```python
pihash = PiHash(rounds=8, memory_mb=256, mining_mode=False)
# Always uses Python implementation
```

### Explicit Control

```python
# Force Python implementation (slower but portable)
pihash = PiHash(use_native=False)

# Force native (raises error if unavailable)
pihash = PiHash(use_native=True)
if not pihash.use_native:
    print("Native acceleration not available")
```

## Checking Availability

```python
from pisecure.core import pihash

if pihash.NATIVE_AVAILABLE:
    print("✅ Native acceleration available")
else:
    print("❌ Using pure Python (slower)")
    print(f"Reason: {pihash._NATIVE_LOAD_ERROR}")
```

## Performance Comparison

Measured on Raspberry Pi 4 (4GB):

| Operation             | Python  | Native  | Speedup |
|-----------------------|---------|---------|---------|
| G-function (1M calls) | 2.40s   | 0.30s   | 8.0x    |
| Memory mixing (256MB) | 4.80s   | 0.75s   | 6.4x    |
| Full hash computation | 6.50s   | 1.20s   | 5.4x    |

## Files

- **`_pihash_native.pyx`**: Cython source code (readable, auditable)
- **`setup_pihash.py`**: Build configuration
- **`build_pihash_native.py`**: Automated build script
- **`README_native.md`**: This file

## Troubleshooting

### Build Fails

```bash
# Install build tools
sudo apt-get install build-essential python3-dev

# Install Python dependencies
pip install cython numpy
```

### Import Fails

```python
# Check what went wrong
from pisecure.core import pihash
print(pihash._NATIVE_LOAD_ERROR)
```

### Wrong Architecture

If building on x86 for ARM deployment:

```bash
# Cross-compile (advanced)
CC=arm-linux-gnueabihf-gcc \
python pisecure/core/setup_pihash.py build_ext
```

## Security Considerations

### Open Source = Better Security

The native code is **compiled from auditable Cython source**. You can:
1. Review `_pihash_native.pyx` (readable)
2. Inspect generated C code (`_pihash_native.c`)
3. Verify it matches the Python algorithm
4. Compile yourself with custom flags

### No Security Through Obscurity

The algorithm is intentionally public because:
- Good cryptography is secure even when public (AES, SHA-256)
- Community auditing improves security
- Open-source builds trust in blockchain projects
- Hardware binding (not code hiding) provides security

## Development

### Profiling

```bash
# Generate optimization hints
python pisecure/core/setup_pihash.py build_ext --inplace

# View HTML annotations
open pisecure/core/_pihash_native.html
```

### Benchmarking

```python
from pisecure.core._pihash_native import benchmark_native
results = benchmark_native()
print(f"Average time: {results['avg_time_ms']:.2f}ms")
```

### Adding Optimizations

1. Modify `_pihash_native.pyx`
2. Rebuild: `python pisecure/core/build_pihash_native.py`
3. Test: `python -m pytest tests/test_pihash_native.py`
4. Profile: Check HTML annotations

## Future Enhancements

- [ ] Pure ARM assembly for G-function (15x speedup)
- [ ] NPU acceleration for Pi 6
- [ ] Multi-threaded mining
- [ ] GPU acceleration (Vulkan)
- [ ] SIMD intrinsics (explicit NEON)

## License

Same as PiSecure (MIT License)
