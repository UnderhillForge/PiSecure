# psminer Build Success

## Summary
Successfully built and installed the **psminer** standalone C++ mining client for PiSecure!

## Build Information
- **Binary Size**: 238KB
- **Location**: `/usr/local/bin/psminer`
- **Version**: v0.1.0
- **Build Date**: Jan 24, 2026
- **Platform**: Raspberry Pi (ARM64/aarch64)

## What Was Fixed
The main challenge was **namespace pollution** from the PiSecure C++ headers when included inside the `psminer` namespace. The solution:

1. **pihash_adapter.cpp**: Included PiHash headers BEFORE opening the psminer namespace to avoid STL header pollution
2. **Exception Handling**: Used catch-all `catch(...)` instead of specific exception types to avoid namespace conflicts
3. **CMake Configuration**: Fixed ARM64 compiler flags (removed 32-bit `-mfpu=neon`, kept vectorization)
4. **Dependencies**: Installed `libncurses-dev` for TUI support

## Architecture
```
psminer (C++ standalone binary)
├── PiHashAdapter → wraps pisecure::pihash::PiHash
├── Miner → Multi-threaded mining engine
├── MonitorTUI → ncurses 6-panel interface
├── HardwareVerifier → Pi detection & monitoring
└── CLI → Command-line argument parsing
```

## Usage Examples
```bash
# Show version
psminer --version

# Show help
psminer --help

# Start mining (requires wallet address)
psminer -w YOUR_WALLET_ADDRESS

# Multi-threaded mining with custom difficulty
psminer is a GitHub Release binary. Difficulty comes from the pisecured template (band 2–4).

# Testnet mining
psminer -w YOUR_WALLET_ADDRESS --testnet

# Hardware tuning (adjust PiHash parameters)
psminer -w YOUR_WALLET_ADDRESS --rounds 16 --memory 512 --npu
```

## Next Steps

### 1. Test Mining
```bash
# Get a wallet address from PiSecure
pisecure wallet create

# Start mining
psminer -w <wallet-address>
```

### 2. Move to Private Repository
When ready to separate psminer source code:
```bash
# psminer ships as a GitHub Release binary, not from this tree.
# 2. Move these files:
#    - cpp/psminer/
#    - cpp/hw/pihash.* (PiHash algorithm)
#    - cpp/hw/videocore_mailbox.*
#    - cpp/crypto/sha256.*
#    - cpp/consensus/*
#    
# 3. Update CMakeLists.txt to be standalone
# 4. Build releases via GitHub Actions
# 5. Distribute binaries through main PiSecure repo
```

### 3. Create GitHub Release Workflow
Add to private repo `.github/workflows/release.yml`:
```yaml
name: Build psminer Release
on:
  push:
    tags:
      - 'v*'
jobs:
  build-arm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build for ARM64
        run: |
          # Cross-compile or use ARM runner
          # Upload artifacts to release
```

## Files Modified/Created
- `cpp/psminer/src/pihash_adapter.cpp` - Fixed namespace pollution
- `cpp/psminer/include/pihash_adapter.hpp` - Added missing namespace closure
- `cpp/psminer/include/miner.hpp` - Added thread/vector includes
- `cpp/psminer/src/main.cpp` - Added thread/chrono includes
- `cpp/psminer/CMakeLists.txt` - Fixed ARM64 compiler flags
- `cpp/psminer/BUILD_SUCCESS.md` - This document

## Key Insights
1. **Namespace Hygiene**: Including large STL headers (like `<iomanip>`) inside custom namespaces causes symbol pollution
2. **Include Order Matters**: External library headers should be included BEFORE opening custom namespaces
3. **ARM Architecture**: ARM64 (aarch64) has NEON by default, doesn't need `-mfpu=neon` flag (that's for ARM32)
4. **Anonymous Exceptions**: Some compilers don't support `catch (const Type &)` without a name in certain contexts

## Testing Checklist
- [x] Binary compiles successfully
- [x] Shows version information
- [x] Shows help text
- [x] Installs to /usr/local/bin
- [ ] Detects Raspberry Pi hardware
- [ ] Starts mining with valid wallet
- [ ] TUI monitor displays correctly
- [ ] Multi-threaded mining works
- [ ] Hardware monitoring (temp/freq) works
- [ ] Block submission successful
