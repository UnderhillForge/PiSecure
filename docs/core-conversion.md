# PiSecure Core Conversion to C++ (Inspired by Bitcoin Core)

This document outlines our migration of PiSecure’s crypto-critical paths from Python to C++, drawing architectural inspiration from Bitcoin Core’s `CSHA256`, `uint256`, `arith_uint256`, and `pow.cpp`. We will not copy code; we adopt patterns and interfaces for safety, performance, and maintainability on Raspberry Pi hardware.

## Goals
- Secure, constant-time hashing and proof-of-work checks.
- Overflow-safe 256-bit arithmetic and byte-oriented `uint256` storage.
- Pi hardware verification module that yields a hardware token for mining.
- Clean pybind11 bindings to incrementally replace Python hot paths.
- ARM/NEON-aware performance on Pi 0→5; graceful fallbacks elsewhere.

## High-Value Inspiration (from Bitcoin Core)
- **SHA-256 context (`CSHA256`)**: Incremental, no dynamic allocation, batch hashing.
- **`uint256`**: 32-byte opaque storage for hashes, hex/bytes conversions.
- **`arith_uint256`**: Limb-based 256-bit arithmetic (shifts, compact difficulty encoding).
- **`pow.cpp`**: Target comparison via `hash <= target` (avoids per-iteration hex/int conversions).

## PiSecure C++ Modules and APIs

### crypto/
- `sha256.h/.cpp`
  - `class Sha256Ctx { Sha256Ctx& write(const uint8_t*, size_t); void finalize(uint8_t out[32]); Sha256Ctx& reset(); }`
  - `void sha256(const uint8_t* in, size_t len, uint8_t out[32]);`
  - `void sha256d64(uint8_t* out, const uint8_t* in, size_t blocks);` (batch double-SHA for mining)
  - ARM/NEON/SHA2-accelerated `Transform` path with runtime feature detection.
- `pihash.h/.cpp`
  - Glue to mix Pi hardware token and memory-hard steps, producing final PoW hash.

### consensus/
- `uint256.h/.cpp`
  - `class Blob256 { static Blob256 from_bytes(span<const uint8_t>); static Blob256 from_hex(std::string_view); void to_bytes(uint8_t[32]) const; std::string to_hex() const; int compare(const Blob256&) const; };`
- `arith_uint256.h/.cpp`
  - `class Big256 { ...; Big256& set_compact(uint32_t, bool* neg=nullptr, bool* overflow=nullptr); uint32_t get_compact(bool negative=false) const; unsigned bits() const; };`
- `difficulty.h/.cpp`
  - Adapters: leading-zeros ↔ compact target.
  - `int leading_zero_bits(const Blob256&); Big256 target_from_leading_zeros(int bits);`
- `pow.h/.cpp`
  - `std::optional<Big256> derive_target(uint32_t nbits, const Blob256& pow_limit);`
  - `bool check_pow(const Blob256& hash, uint32_t nbits, const Blob256& pow_limit);`
  - `bool check_pow_target(const Blob256& hash, const Big256& target);` (constant-time compare)

### hw/
- `hw_verifier.h/.cpp`
  - `class HardwareVerifier { std::string get_hardware_id(); bool read_entropy(uint8_t* out, size_t len); VerifierReport run_self_test(); bool is_probably_virtualized(); };`
  - BCM271x register `mmap`, OTP/serial reading, `/dev/hwrng` entropy, timing heuristics.
- `mmap_region.h/.cpp`: RAII wrapper for `/dev/mem` mappings.
- `hwrng.h/.cpp`: robust entropy reads with timeouts.

### util/
- `endian.h`: explicit BE/LE helpers.
- `cpufeatures.h/.cpp`: runtime ARM feature detection.
- `ctcmp.h`: constant-time limb-wise compare helpers.

### bindings/
- `pybind_sha256.cpp`, `pybind_pow.cpp`, `pybind_hw.cpp`
  - Zero-copy buffers, GIL release in hot loops.

## Proof-of-Work Strategy
- Store difficulty as `Big256 target` (compact or derived from leading zeros).
- Compare using `hash <= target` in constant time (limb-wise, fixed-iteration).
- Keep existing leading-zeros difficulty short-term; add compact encoding for future retarget rules.
- Hash pipeline: `header || nonce || hw_token` → `Sha256Ctx` (or `sha256d64`) → `Blob256` → compare.

## SHA-256 Strategy
- Incremental context (`Sha256Ctx`) with stack fields; no heap in hot paths.
- Batch double-SHA (`sha256d64`) for mining throughput.
- Runtime ARM acceleration: SHA2 extensions where available; NEON intrinsics fallback.
- Midstate support for fixed headers.

## Hardware Verifier (Pi-only Enforcement)
- Detect SoC base (BCM2708/2709/2710/2711/2712) → `mmap` select ranges.
- Read OTP/CPU serial/board revision; build `hardware_token`.
- Read `/dev/hwrng` 32–64 bytes with timeout; rate-limit submissions.
- Timing/anti-virtualization checks: jitter profiles, monotonic drift, hypervisor hints.
- Fallbacks: device-tree and `vcgencmd` on restricted systems; CI mock mode.

## Python Bindings (Migration Bridge)
- `pisecure_cpp.crypto`: `sha256(bytes)->bytes`, `Sha256Ctx`, `sha256d64()`.
- `pisecure_cpp.consensus`: `leading_zero_bits(bytes)->int`, `check_pow(hash_bytes, nbits)->bool`.
- `pisecure_cpp.hw`: `get_hardware_id()->str`, `read_entropy(n)->bytes`, `is_probably_virtualized()->bool`.
- Release GIL in hashing/PoW loops.

## Migration Plan (Stepwise)
1. Replace Python `count_zero_bits` and `hashlib.sha256()` in validation with C++ (`leading_zero_bits`, `sha256`).
2. Introduce `check_pow()` using `Blob256`/`Big256`; compare `hash <= target` (constant-time).
3. Update nonce search loop to use `sha256d64`/midstate; keep Python orchestration initially.
4. Integrate HardwareVerifier to produce `hardware_token` mixed into mining hash; keep mock mode for non-Pi.
5. Expand to full validator path; add compact difficulty adapters.
6. Benchmarks: throughput (hashes/sec), latency (entropy read), correctness (vectors), Pi 0→5.
7. Package (CMake + scikit-build); CI with sanitizers and fuzzers.

## Testing & Security Checklist
- Constant-time big-int comparisons; branchless inner loops.
- Explicit endianness; document limb order vs wire formats.
- RAII for `mmap`/FDs; no raw `new` in hot paths.
- Error typing (compact overflow/negative targets, map failures).
- Unit tests: SHA-256 vectors, compact encode/decode, target checks.
- Fuzz: compact parsing, hash inputs; sanitizers in CI.
- Permissions: guard `/dev/mem` access; graceful fallback.
- Runtime feature gating: detect NEON/SHA2 safely; self-test on startup.

## References (for inspiration)
- Bitcoin Core: `src/crypto/sha256.*`, `src/uint256.*`, `src/arith_uint256.*`, `src/pow.cpp`.
- Raspberry Pi SoC docs (BCM2708/2709/2710/2711/2712) for base addresses.
- Linux: `/dev/mem`, `/dev/hwrng`, device-tree nodes.

---

Next actions: initialize C++ scaffold (`crypto/sha256`, `consensus/uint256/arith_uint256`, `bindings`), add pybind11 build, and wire validation paths in `pisecure/core/` to call C++ for hashing and PoW checks.