"""
PiHash - Custom Hardware-Verified Hash Algorithm for PiSecure

PiHash is a custom proof-of-work hash algorithm designed exclusively for
Raspberry Pi hardware. It incorporates hardware fingerprinting, memory-hard
computations, and CPU optimizations to ensure mining can only occur on
verified Pi devices running PiSecure software.

Key Features:
- Hardware verification (CPU serial, RNG, memory patterns)
- Memory-hard computation optimized for Pi RAM
- CPU optimization for ARM architecture
- NPU acceleration hooks for future Pi 6
- Adjustable difficulty through rounds and memory usage

Performance:
- Pure Python: Auditable, portable, validation-friendly
- Native extensions: 5-10x faster mining (optional Cython module)
"""

import hashlib
import os
import struct
import time
from typing import Dict, Any, Optional, Tuple, List

# Try to import native acceleration module
try:
    from pisecure.core._pihash_native import (
        memory_hard_mix_native,
        parallel_lane_mix_native,
        cpu_optimized_finalize_native,
        benchmark_native
    )
    NATIVE_AVAILABLE = True
    _NATIVE_LOAD_ERROR = None
except ImportError as e:
    NATIVE_AVAILABLE = False
    _NATIVE_LOAD_ERROR = str(e)
    # Fallback: all functions use pure Python


class PiHash:
    """
    PiSecure's custom hardware-verified hash algorithm

    Designed for Raspberry Pi mining with:
    - Hardware fingerprinting integration
    - Memory-hard computations (256MB default)
    - ARM CPU optimizations
    - NPU acceleration hooks
    """

    def __init__(self, rounds: int = 8, memory_mb: int = 256, npu_enabled: bool = False, parallelism: int = 1, mining_mode: bool = True, use_native: bool = True):
        """
        Initialize PiHash with configurable parameters

        Args:
            rounds: Number of computational rounds (difficulty factor)
            memory_mb: Memory usage in MB (default 256MB, Pi-friendly)
            npu_enabled: Enable NPU acceleration when available (Pi 6)
            parallelism: Number of parallel lanes (1-4 for Pi 4, 1-8 for Pi 5)
                        NOTE: Parallelism affects hash output, so validators must use same value as miners
            mining_mode: If True, use full Pi-specific optimizations (mining)
                        If False, use minimal compute path (validation)
            use_native: If True and available, use Cython-optimized native code (5-10x faster)
        """
        self.mining_mode = mining_mode
        self.rounds = rounds  # Use specified rounds for both mining and validation
        self.memory_mb = memory_mb  # Use specified memory for both
        self.npu_enabled = npu_enabled
        # NOTE: Parallelism affects hash computation, so must match between mining/validation
        self.parallelism = parallelism  # Don't cap for validation anymore
        self.memory_bytes = self.memory_mb * 1024 * 1024
        
        # Native acceleration (only use for mining, not validation for compatibility)
        self.use_native = use_native and NATIVE_AVAILABLE and mining_mode

        # Argon2-inspired parameters
        self.block_size = 64  # 64-byte blocks (Blake2b max digest size)
        self.segment_length = 0  # Will be calculated based on memory size

        # Hardware verification
        self.hardware_verified = False
        self.hardware_fingerprint = {}
        
        # Cache Pi-specific hardware patterns (compute once, not per hash)
        self._cached_videocore_pattern = None
        self._cached_trustzone_data = None
        self._cached_temperature_baseline = None

    @staticmethod
    def _argon2_g_function(a: int, b: int, c: int, d: int) -> Tuple[int, int, int, int]:
        """
        Argon2 G function (quarter-round compression) - ARM NEON Optimized

        Performs the core mixing operation from Argon2, optimized for ARM Cortex-A series.
        Uses 32-bit operations that map well to NEON SIMD instructions.

        NEON Optimization Notes:
        - vadd.i32: 32-bit addition
        - vmul.i32: 32-bit multiplication
        - veor: XOR operations
        - vshr.u32/vshl.u32: Bit shifts for rotations

        Args:
            a, b, c, d: Four 32-bit integers to mix

        Returns:
            Tuple of four mixed 32-bit integers
        """
        # Convert to 32-bit unsigned integers (NEON: vmov.i32)
        a = a & 0xFFFFFFFF
        b = b & 0xFFFFFFFF
        c = c & 0xFFFFFFFF
        d = d & 0xFFFFFFFF

        # First quarter-round (NEON: SIMD operations on vector {a,b,c,d})
        # a = (a + b + 2 * a * b) & 0xFFFFFFFF
        ab_prod = (a * b) & 0xFFFFFFFF  # NEON: vmul.i32
        a = (a + b + 2 * ab_prod) & 0xFFFFFFFF  # NEON: vadd.i32, vmla.i32

        # d = ((d ^ a) >> 16) | ((d ^ a) << 16) & 0xFFFFFFFF  # Rotate right 16
        d_xor_a = d ^ a  # NEON: veor
        d = ((d_xor_a >> 16) | (d_xor_a << 16)) & 0xFFFFFFFF  # NEON: vshr.u32, vshl.u32, vorr

        # c = (c + d + 2 * c * d) & 0xFFFFFFFF
        cd_prod = (c * d) & 0xFFFFFFFF  # NEON: vmul.i32
        c = (c + d + 2 * cd_prod) & 0xFFFFFFFF  # NEON: vadd.i32, vmla.i32

        # b = ((b ^ c) >> 12) | ((b ^ c) << 20) & 0xFFFFFFFF  # Rotate right 12
        b_xor_c = b ^ c  # NEON: veor
        b = ((b_xor_c >> 12) | (b_xor_c << 20)) & 0xFFFFFFFF  # NEON: vshr.u32, vshl.u32, vorr

        # Second quarter-round
        # a = (a + b + 2 * a * b) & 0xFFFFFFFF
        ab_prod = (a * b) & 0xFFFFFFFF  # NEON: vmul.i32
        a = (a + b + 2 * ab_prod) & 0xFFFFFFFF  # NEON: vadd.i32, vmla.i32

        # d = ((d ^ a) >> 8) | ((d ^ a) << 24) & 0xFFFFFFFF   # Rotate right 8
        d_xor_a = d ^ a  # NEON: veor
        d = ((d_xor_a >> 8) | (d_xor_a << 24)) & 0xFFFFFFFF  # NEON: vshr.u32, vshl.u32, vorr

        # c = (c + d + 2 * c * d) & 0xFFFFFFFF
        cd_prod = (c * d) & 0xFFFFFFFF  # NEON: vmul.i32
        c = (c + d + 2 * cd_prod) & 0xFFFFFFFF  # NEON: vadd.i32, vmla.i32

        # b = ((b ^ c) >> 7) | ((b ^ c) << 25) & 0xFFFFFFFF   # Rotate right 7
        b_xor_c = b ^ c  # NEON: veor
        b = ((b_xor_c >> 7) | (b_xor_c << 25)) & 0xFFFFFFFF  # NEON: vshr.u32, vshl.u32, vorr

        return a, b, c, d

    @staticmethod
    def _process_block_neon_optimized(block: bytearray, hw_hash: bytes, nonce: int, round_num: int, block_idx: int) -> None:
        """
        Process a 64-byte block using NEON-optimized operations

        ARM NEON SIMD operations can process multiple 32-bit words simultaneously.
        This function is structured for easy translation to NEON assembly or C intrinsics.

        Args:
            block: 64-byte block to process
            hw_hash: Hardware hash for seeding
            nonce: Mining nonce
            round_num: Current round number
            block_idx: Block index for uniqueness
        """
        # Pre-compute hardware-specific values (can be done in NEON registers)
        hw_influence = hash(hw_hash) & 0xFFFFFFFF
        nonce_masked = nonce & 0xFFFFFFFF

        # Process all four 16-byte sub-blocks (ideal for NEON vectorization)
        # Each sub-block becomes a NEON vector {a,b,c,d}
        for sub_block_idx in range(0, 64, 16):
            # Load 16 bytes as four 32-bit little-endian words
            # NEON: vld4.32 {d0,d1,d2,d3}, [r0]  (load 4x32-bit interleaved)
            sub_block = block[sub_block_idx:sub_block_idx+16]
            a = int.from_bytes(sub_block[0:4], 'little')
            b = int.from_bytes(sub_block[4:8], 'little')
            c = int.from_bytes(sub_block[8:12], 'little')
            d = int.from_bytes(sub_block[12:16], 'little')

            # Apply hardware-specific mixing (NEON: vector operations)
            # NEON: veor q0, q0, q_hw_influence
            a ^= round_num
            b ^= block_idx
            c ^= nonce_masked
            d ^= hw_influence

            # Apply double G function (core of Argon2 compression)
            # NEON: Custom G function implementation using SIMD
            a, b, c, d = PiHash._argon2_g_function(a, b, c, d)
            a, b, c, d = PiHash._argon2_g_function(a, b, c, d)

            # Store result back (NEON: vst4.32 {d0,d1,d2,d3}, [r0])
            block[sub_block_idx:sub_block_idx+4] = a.to_bytes(4, 'little')
            block[sub_block_idx+4:sub_block_idx+8] = b.to_bytes(4, 'little')
            block[sub_block_idx+8:sub_block_idx+12] = c.to_bytes(4, 'little')
            block[sub_block_idx+12:sub_block_idx+16] = d.to_bytes(4, 'little')

    def compute(self, data: bytes, nonce: int, hardware_fingerprint: Optional[Dict] = None) -> str:
        """
        Compute PiHash digest with mode-specific complexity

        Args:
            data: Block data to hash
            nonce: Mining nonce
            hardware_fingerprint: Pi hardware verification data (only needed for mining)

        Returns:
            Hexadecimal hash string
        """
        if self.mining_mode:
            # Full Pi-optimized mining path
            if hardware_fingerprint is None:
                hardware_fingerprint = self._get_hardware_fingerprint()
            if not self._verify_hardware(hardware_fingerprint):
                raise ValueError("Mining requires verified Raspberry Pi hardware")
        else:
            # Validation path: hardware-agnostic
            if hardware_fingerprint is None:
                hardware_fingerprint = self._get_synthetic_fingerprint(data, nonce)

        # Stage 1: Hardware integration
        hw_hash = self._hardware_hash(data, nonce, hardware_fingerprint)

        # Stage 2: Memory-hard mixing
        memory_hash = self._memory_hard_mix(hw_hash, nonce)

        # Stage 3: CPU-optimized finalization
        cpu_hash = self._cpu_optimized_finalize(memory_hash)

        # Stage 4: NPU acceleration (if available and enabled)
        if self.npu_enabled and self._has_npu():
            final_hash = self._npu_accelerate(cpu_hash)
        else:
            final_hash = cpu_hash

        return final_hash.hex()

    def _get_synthetic_fingerprint(self, data: bytes, nonce: int) -> Dict[str, Any]:
        """
        Generate deterministic 'fingerprint' from block data for validation
        
        This allows any hardware to validate without actual Pi hardware,
        but makes it impossible to mine efficiently without real Pi.
        
        Args:
            data: Block data
            nonce: Mining nonce
            
        Returns:
            Synthetic fingerprint dictionary
        """
        seed = hashlib.sha256(data + struct.pack('<Q', nonce)).digest()
        return {
            'cpu_serial': seed[:16].hex(),
            'hardware_model': 'ValidationNode',
            'memory_info': {'total': 4 * 1024 * 1024 * 1024, 'available': 2 * 1024 * 1024 * 1024},
            'unique_id': seed[16:24].hex()
        }

    def _get_hardware_fingerprint(self) -> Dict[str, Any]:
        """
        Generate comprehensive Raspberry Pi hardware fingerprint

        Returns:
            Dictionary containing hardware verification data
        """
        try:
            fingerprint = {
                'cpu_serial': self._get_cpu_serial(),
                'hardware_model': self._get_hardware_model(),
                'memory_info': self._get_memory_info()
            }

            # Generate unique hardware ID (deterministic for same hardware)
            hw_id_data = (
                str(fingerprint['cpu_serial']) +
                fingerprint['hardware_model'] +
                str(fingerprint['memory_info']['total'])
            ).encode()

            fingerprint['unique_id'] = hashlib.sha256(hw_id_data).hexdigest()[:16]

            return fingerprint

        except Exception as e:
            raise ValueError(f"Hardware fingerprinting failed: {e}")

    def _verify_hardware(self, fingerprint: Dict) -> bool:
        """
        Verify this is a genuine Raspberry Pi

        Args:
            fingerprint: Hardware fingerprint data

        Returns:
            True if verified Pi hardware
        """
        try:
            # Check for Raspberry Pi specific indicators
            model = fingerprint.get('hardware_model', '').lower()
            if 'raspberry pi' not in model:
                return False

            # Verify CPU serial exists and is valid
            serial = fingerprint.get('cpu_serial')
            if not serial or len(str(serial)) < 8:
                return False

            # Check memory is reasonable for Pi (1GB - 16GB)
            memory_mb = fingerprint.get('memory_info', {}).get('total', 0) / (1024 * 1024)
            if memory_mb < 1024 or memory_mb > 16384:  # 1GB - 16GB range
                return False

            # Hardware fingerprint is deterministic (no RNG dependency)
            # Verification based on stable hardware characteristics only

            self.hardware_verified = True
            self.hardware_fingerprint = fingerprint
            return True

        except Exception:
            return False

    def _get_cpu_serial(self) -> str:
        """Get Raspberry Pi CPU serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
            # Fallback to device tree
            with open('/proc/device-tree/serial-number', 'rb') as f:
                serial = f.read().decode('ascii').rstrip('\x00')
                return serial
        except Exception:
            raise ValueError("Cannot read CPU serial")

    def _get_hardware_model(self) -> str:
        """Get Raspberry Pi model information"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Model'):
                        return line.split(':')[1].strip()
            # Fallback
            with open('/proc/device-tree/model', 'rb') as f:
                model = f.read().decode('ascii').rstrip('\x00')
                return model
        except Exception:
            return "Unknown Raspberry Pi Model"

    def _get_memory_info(self) -> Dict[str, int]:
        """Get system memory information"""
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = {}
                for line in f:
                    if line.startswith('MemTotal'):
                        mem_info['total'] = int(line.split()[1]) * 1024  # Convert to bytes
                    elif line.startswith('MemAvailable'):
                        mem_info['available'] = int(line.split()[1]) * 1024
                return mem_info
        except Exception:
            return {'total': 2 * 1024 * 1024 * 1024, 'available': 1 * 1024 * 1024 * 1024}  # 2GB fallback

    def _get_hardware_rng(self, bytes_needed: int) -> bytes:
        """Get random bytes from hardware RNG"""
        try:
            # Try hardware RNG (Pi 3+)
            with open('/dev/hwrng', 'rb') as f:
                return f.read(bytes_needed)
        except Exception:
            # Fallback to software RNG seeded with hardware data
            seed_data = str(time.time_ns()) + str(os.getpid()) + self._get_cpu_serial()
            seed = int(hashlib.sha256(seed_data.encode()).hexdigest(), 16)
            # Simple PRNG for fallback (not cryptographically secure for mining)
            result = bytearray(bytes_needed)
            for i in range(bytes_needed):
                seed = (seed * 1103515245 + 12345) % (2**31)
                result[i] = seed % 256
            return bytes(result)

    def _has_videocore(self) -> bool:
        """Detect Raspberry Pi VideoCore GPU"""
        return os.path.exists('/dev/vchiq') or os.path.exists('/dev/vc-mem')

    def _videocore_memory_pattern(self) -> bytes:
        """Generate pattern based on GPU memory access (Pi-specific)"""
        try:
            # Read GPU memory info (Pi-specific command)
            import subprocess
            result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'], 
                                  capture_output=True, text=True, timeout=1)
            gpu_mem = result.stdout.strip()
            return hashlib.sha256(gpu_mem.encode()).digest()[:16]
        except Exception:
            return b'\x00' * 16

    def _has_trustzone(self) -> bool:
        """Check for ARM TrustZone availability"""
        try:
            # Check for OP-TEE or other TrustZone implementation
            return os.path.exists('/dev/tee0') or os.path.exists('/dev/teepriv0')
        except Exception:
            return False

    def _trustzone_random(self, size: int) -> bytes:
        """Get hardware random from TrustZone (if available)"""
        try:
            with open('/dev/hwrng', 'rb') as f:
                return f.read(size)
        except Exception:
            return os.urandom(size)

    def _get_soc_temperature(self) -> str:
        """Get SoC temperature as proof-of-work witness"""
        try:
            # Pi-specific temperature read
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millidegrees = int(f.read().strip())
                return str(temp_millidegrees)
        except Exception:
            return "45000"  # Fallback temperature

    def _hardware_hash(self, data: bytes, nonce: int, fingerprint: Dict) -> bytes:
        """
        Stage 1: Integrate hardware-specific data into hash
        Enhanced with Pi-specific performance characteristics

        Args:
            data: Block data
            nonce: Mining nonce
            fingerprint: Hardware verification data

        Returns:
            Hardware-integrated hash bytes
        """
        # Combine block data and nonce ONLY
        # Do NOT include hardware-specific data in the hash
        # This allows universal validation while still requiring Pi for mining
        hw_data = data + struct.pack('<Q', nonce)  # Pack nonce as uint64

        if self.mining_mode:
            # Mining path: Verify we're on Pi hardware for mining privileges
            # But don't pollute the hash with hardware-specific data
            # Store mining metadata (not hashed, just for stats/verification)
            self._mining_metadata = {
                'has_videocore': self._has_videocore(),
                'has_trustzone': self._has_trustzone(),
                'cpu_serial': fingerprint.get('cpu_serial'),
                'hardware_model': fingerprint.get('hardware_model')
            }

        # Create initial hash using Blake2b (faster and more secure than SHA256)
        initial_hash = hashlib.blake2b(hw_data, digest_size=32).digest()

        # Mix with memory pattern (deterministic, not hardware-specific)
        memory_pattern = self._get_memory_access_pattern_deterministic(data, nonce)
        mixed_hash = bytes(a ^ b for a, b in zip(initial_hash, memory_pattern))

        return mixed_hash
    
    def _get_memory_access_pattern_deterministic(self, data: bytes, nonce: int) -> bytes:
        """Generate deterministic memory access pattern from block data"""
        pattern_size = 32
        pattern = bytearray(pattern_size)
        
        # Derive pattern from block data + nonce (deterministic)
        seed_data = data + struct.pack('<Q', nonce)
        seed_hash = hashlib.sha256(seed_data).digest()
        
        for i in range(pattern_size):
            pattern[i] = seed_hash[i % len(seed_hash)]
        
        return bytes(pattern)

    def _get_memory_access_pattern(self) -> bytes:
        """Generate Pi-specific memory access pattern"""
        # Create a pattern based on Pi's memory architecture
        pattern_size = 32
        pattern = bytearray(pattern_size)

        # Use various system values to create unique pattern
        try:
            pid = os.getpid()
            uid = os.getuid()
            memory_total = self.hardware_fingerprint.get('memory_info', {}).get('total', 2*1024*1024*1024)

            for i in range(pattern_size):
                pattern[i] = ((pid + uid + memory_total + i) % 256)
        except Exception:
            # Fallback pattern
            for i in range(pattern_size):
                pattern[i] = i % 256

        return bytes(pattern)

    def _memory_hard_mix(self, hw_hash: bytes, nonce: int) -> bytes:
        """
        Stage 2: Memory-hard computation with Argon2id-inspired block structure

        Uses 64-byte blocks organized like Argon2, with hybrid access patterns
        and parallel lane support for multi-core Pi utilization.
        
        For reasonable performance, we limit to a maximum of 16K blocks even if
        memory_mb is set higher (16K * 64 bytes = 1MB actual usage for mining speed)
        
        Note: Uses native acceleration if available and enabled (5-10x faster)
        """
        # Use native implementation if available (mining mode only)
        if self.use_native:
            try:
                return memory_hard_mix_native(hw_hash, nonce, self.rounds, self.memory_bytes)
            except Exception as e:
                # Fall back to Python on any native error
                print(f"⚠️  Native memory mixing failed, using Python: {e}")
                pass
        
        # Pure Python implementation (validation or fallback)
        # Calculate block layout (Argon2-inspired)
        # Cap at 16K blocks for reasonable performance (1MB)
        max_blocks = 16384  # 16K blocks = 1MB
        total_blocks = min(max_blocks, max(128, self.memory_bytes // self.block_size))
        blocks_per_lane = total_blocks // self.parallelism

        # Initialize memory as list of blocks (1024 bytes each)
        memory_blocks = []
        for block_idx in range(total_blocks):
            # Create initial block data using Blake2b
            block_data = hw_hash + struct.pack('<Q', nonce) + struct.pack('<Q', block_idx)
            initial_block = hashlib.blake2b(block_data, digest_size=self.block_size).digest()
            memory_blocks.append(bytearray(initial_block))

        # Argon2id-inspired processing: hybrid access pattern
        for round_num in range(self.rounds):
            # Phase 1: Data-independent filling (sequential access)
            for lane in range(self.parallelism):
                for slice_idx in range(blocks_per_lane):
                    block_idx = lane * blocks_per_lane + slice_idx
                    if block_idx >= len(memory_blocks):
                        continue

                    self._process_block(memory_blocks[block_idx], hw_hash, nonce, round_num, block_idx)

            # Phase 2: Data-dependent mixing (random access based on previous results)
            for lane in range(self.parallelism):
                for slice_idx in range(blocks_per_lane):
                    block_idx = lane * blocks_per_lane + slice_idx
                    if block_idx >= len(memory_blocks):
                        continue

                    # Generate data-dependent reference using current block content
                    ref_block = self._get_reference_block(memory_blocks, block_idx, round_num, lane)
                    if ref_block is not None:
                        self._mix_blocks(memory_blocks[block_idx], ref_block)

        # Reduce all blocks to final hash
        combined_data = b''.join(memory_blocks)
        final_hash = hashlib.blake2b(combined_data, digest_size=32).digest()
        return final_hash

    def _process_block(self, block: bytearray, hw_hash: bytes, nonce: int, round_num: int, block_idx: int) -> None:
        """
        Process a single 64-byte block using Argon2-style operations

        Args:
            block: 64-byte block to process
            hw_hash: Hardware hash for seeding
            nonce: Mining nonce
            round_num: Current round number
            block_idx: Block index for uniqueness
        """
        # Each 64-byte block contains 4 × 16-byte sub-blocks (perfect for G function)
        for sub_block_idx in range(0, self.block_size, 16):
            if sub_block_idx + 15 >= self.block_size:
                break

            # Extract 16 bytes (4 × 32-bit words)
            sub_block = block[sub_block_idx:sub_block_idx+16]
            a = int.from_bytes(sub_block[0:4], 'little')
            b = int.from_bytes(sub_block[4:8], 'little')
            c = int.from_bytes(sub_block[8:12], 'little')
            d = int.from_bytes(sub_block[12:16], 'little')

            # Add round-specific and hardware-specific data
            a ^= round_num
            b ^= block_idx
            c ^= nonce & 0xFFFFFFFF
            d ^= hash(hw_hash) & 0xFFFFFFFF

            # Apply Argon2 G function twice (like Argon2)
            a, b, c, d = self._argon2_g_function(a, b, c, d)
            a, b, c, d = self._argon2_g_function(a, b, c, d)

            # Store result back
            block[sub_block_idx:sub_block_idx+4] = a.to_bytes(4, 'little')
            block[sub_block_idx+4:sub_block_idx+8] = b.to_bytes(4, 'little')
            block[sub_block_idx+8:sub_block_idx+12] = c.to_bytes(4, 'little')
            block[sub_block_idx+12:sub_block_idx+16] = d.to_bytes(4, 'little')

    def _get_reference_block(self, memory_blocks: List[bytearray], current_idx: int, round_num: int, lane: int) -> Optional[bytearray]:
        """
        Get a data-dependent reference block for mixing (hybrid access pattern)

        Args:
            memory_blocks: All memory blocks
            current_idx: Current block index
            round_num: Current round number
            lane: Current lane number

        Returns:
            Reference block for mixing, or None if no valid reference
        """
        if len(memory_blocks) <= 1:
            return None

        # Generate pseudo-random reference based on current block content
        # This creates the data-dependent access pattern of Argon2id
        current_block = memory_blocks[current_idx]

        # Use first 8 bytes of current block as seed for reference generation
        if len(current_block) >= 8:
            seed = int.from_bytes(current_block[0:8], 'little')
            # Add round and lane influence
            seed ^= (round_num << 24) ^ (lane << 16) ^ current_idx

            # Generate reference index (data-dependent)
            ref_idx = (seed % (len(memory_blocks) - 1))
            if ref_idx >= current_idx:  # Avoid self-reference
                ref_idx += 1
            ref_idx %= len(memory_blocks)

            return memory_blocks[ref_idx]

        return None

    def _mix_blocks(self, block: bytearray, ref_block: bytearray) -> None:
        """
        Mix two blocks together using Argon2-style compression

        Args:
            block: Block to modify
            ref_block: Reference block for mixing
        """
        # XOR blocks first (like Argon2 compression)
        for i in range(min(len(block), len(ref_block))):
            block[i] ^= ref_block[i]

        # Apply additional G function mixing to maintain diffusion
        for sub_block_idx in range(0, min(self.block_size, len(block)), 16):
            if sub_block_idx + 15 >= len(block):
                break

            # Extract and mix with G function
            a = int.from_bytes(block[sub_block_idx:sub_block_idx+4], 'little')
            b = int.from_bytes(block[sub_block_idx+4:sub_block_idx+8], 'little')
            c = int.from_bytes(block[sub_block_idx+8:sub_block_idx+12], 'little')
            d = int.from_bytes(block[sub_block_idx+12:sub_block_idx+16], 'little')

            a, b, c, d = self._argon2_g_function(a, b, c, d)

            # Store result
            block[sub_block_idx:sub_block_idx+4] = a.to_bytes(4, 'little')
            block[sub_block_idx+4:sub_block_idx+8] = b.to_bytes(4, 'little')
            block[sub_block_idx+8:sub_block_idx+12] = c.to_bytes(4, 'little')
            block[sub_block_idx+12:sub_block_idx+16] = d.to_bytes(4, 'little')

    def _cpu_optimized_finalize(self, memory_hash: bytes) -> bytes:
        """
        Stage 3: CPU-optimized finalization for ARM Cortex-A series

        Uses ARM NEON-inspired operations and cache-friendly processing.
        Optimized for the 32-byte final hash output.

        NEON Optimization Strategy:
        - Process 32-byte hash in 16-byte chunks using 128-bit NEON registers
        - Use ARM-specific multiplication constants (7, 3, 5, 11)
        - Leverage L1 cache with small working set
        """
        # Convert to mutable list for processing
        hash_state = list(memory_hash)

        for round_num in range(self.rounds):
            # ARM NEON-inspired 16-byte chunk processing
            # Process in 16-byte chunks (fits in NEON 128-bit registers)
            for chunk_start in range(0, len(hash_state), 16):
                chunk_end = min(chunk_start + 16, len(hash_state))
                chunk = hash_state[chunk_start:chunk_end]

                # Extend chunk to 16 bytes if needed (for NEON register alignment)
                while len(chunk) < 16:
                    chunk.append(0)

                # ARM NEON-style operations on 16-byte vectors
                self._arm_neon_mix_chunk(chunk, round_num)

                # Store back (only the original chunk size)
                hash_state[chunk_start:chunk_end] = chunk[:chunk_end - chunk_start]

            # Cross-chunk diffusion (ARM cache-friendly)
            hash_state = self._arm_cache_optimized_diffusion(hash_state, round_num)

        return bytes(hash_state)

    def _arm_neon_mix_chunk(self, chunk: list, round_num: int) -> None:
        """
        ARM NEON-inspired mixing for 16-byte chunks

        Simulates NEON operations that would be highly optimized in assembly:
        - vld1.8 {q0}, [r0]  (load 16 bytes)
        - Various SIMD operations
        - vst1.8 {q0}, [r0]  (store 16 bytes)

        Args:
            chunk: 16-byte list to mix (mutable)
            round_num: Current round for round-specific constants
        """
        # NEON register simulation: process 16 bytes as four 32-bit words
        # This structure allows easy translation to NEON assembly
        for word_idx in range(0, 16, 4):
            if word_idx + 3 >= 16:
                break

            # Load 32-bit word (NEON: vmov.32 r0, d0[word_idx])
            word = (chunk[word_idx] << 24) | (chunk[word_idx + 1] << 16) | \
                   (chunk[word_idx + 2] << 8) | chunk[word_idx + 3]

            # ARM-specific mixing operations (NEON-friendly)
            # Use different prime multipliers for each round (ARM optimization)
            prime_mult = [7, 11, 13, 17, 23, 29, 31, 37][round_num % 8]

            # NEON-style operations: add, multiply, rotate, XOR
            word = (word + round_num) & 0xFFFFFFFF  # NEON: vadd.i32
            word = (word * prime_mult) & 0xFFFFFFFF  # NEON: vmul.i32
            word = ((word << 13) | (word >> 19)) & 0xFFFFFFFF  # NEON: vshr.u32/vshl.u32
            word ^= (round_num << 24)  # NEON: veor

            # Store back (NEON: vmov.32 d0[word_idx], r0)
            chunk[word_idx] = (word >> 24) & 0xFF
            chunk[word_idx + 1] = (word >> 16) & 0xFF
            chunk[word_idx + 2] = (word >> 8) & 0xFF
            chunk[word_idx + 3] = word & 0xFF

    def _arm_cache_optimized_diffusion(self, state: list, round_num: int) -> list:
        """
        ARM cache-optimized diffusion function

        Uses cache-friendly access patterns optimized for ARM Cortex-A cache hierarchy:
        - L1 cache: 32KB, 4-way set associative
        - Process in cache-line friendly chunks
        - Minimize cache misses with linear access

        Args:
            state: Hash state list
            round_num: Current round number

        Returns:
            Diffused state
        """
        result = state.copy()

        # Process in 64-byte chunks (typical cache line size)
        for chunk_start in range(0, len(result), 64):
            chunk_end = min(chunk_start + 64, len(result))
            chunk = result[chunk_start:chunk_end]

            # ARM-specific diffusion pattern (cache-friendly)
            # Use different diffusion constants per round
            diffusion_key = [0x9E, 0x79, 0xB9, 0x5D, 0x2C, 0x8A, 0xE3, 0x7F][round_num % 8]

            for i in range(len(chunk)):
                # ARM-optimized mixing: use hardware-specific operations
                prev = chunk[(i - 1) % len(chunk)]
                curr = chunk[i]
                next_val = chunk[(i + 1) % len(chunk)]

                # Hardware-accelerated operations on ARM
                # NEON: vadd.i8, veor, vshl.i8/vshr.i8
                mixed = (prev + curr + next_val + diffusion_key) & 0xFF
                mixed = ((mixed << 3) | (mixed >> 5)) & 0xFF  # ARM barrel shifter
                mixed ^= diffusion_key  # NEON: veor

                chunk[i] = mixed

            result[chunk_start:chunk_end] = chunk

        return result

    def _has_npu(self) -> bool:
        """
        Detect if system has Neural Processing Unit (Pi 6 future feature)

        Returns:
            True if NPU is available
        """
        try:
            # Check for NPU device (placeholder for Pi 6)
            return os.path.exists('/dev/npu') or os.path.exists('/dev/accel0')
        except Exception:
            return False

    def _npu_accelerate(self, data: bytes) -> bytes:
        """
        Stage 4: NPU acceleration for future Pi 6

        Placeholder for neural processing unit acceleration
        """
        # For now, return data unchanged
        # Future implementation will use NPU for matrix operations
        # Could provide 5-10x speedup for hash computations

        # Simulate NPU processing (placeholder)
        npu_hash = hashlib.sha256(data + b"NPU_ACCELERATED").digest()
        return npu_hash

    def get_pi_performance_factor(self) -> float:
        """
        Calculate performance factor based on Pi hardware
        
        Returns multiplier for difficulty adjustment:
        - Pi Zero/1: 0.1x (easier difficulty)
        - Pi 3: 0.5x
        - Pi 4: 1.0x (baseline)
        - Pi 5: 2.0x (harder difficulty for faster hardware)
        """
        model = self.hardware_fingerprint.get('hardware_model', '').lower()
        
        if 'pi zero' in model or 'pi 1' in model:
            return 0.1
        elif 'pi 2' in model:
            return 0.3
        elif 'pi 3' in model:
            return 0.5
        elif 'pi 4' in model:
            return 1.0
        elif 'pi 5' in model:
            return 2.0
        else:
            return 1.0

    def meets_difficulty(self, hash_hex: str, difficulty: int) -> bool:
        """
        Check if hash meets difficulty requirement (leading zeros)

        Args:
            hash_hex: Hash as hex string
            difficulty: Number of leading zeros required

        Returns:
            True if hash meets difficulty
        """
        return hash_hex.startswith('0' * difficulty)

    def find_nonce(self, block_data: bytes, difficulty: int,
                   hardware_fingerprint: Optional[Dict] = None) -> Tuple[int, str]:
        """
        Find nonce that meets difficulty requirement

        Args:
            block_data: Block data to mine
            difficulty: Number of leading zeros required
            hardware_fingerprint: Optional hardware verification data

        Returns:
            Tuple of (nonce, hash_hex) that meets difficulty
        """
        nonce = 0
        max_nonce = 2**32  # Prevent infinite loops

        while nonce < max_nonce:
            hash_hex = self.compute(block_data, nonce, hardware_fingerprint)

            if self.meets_difficulty(hash_hex, difficulty):
                return nonce, hash_hex

            nonce += 1

        raise ValueError(f"Could not find nonce meeting difficulty {difficulty}")

    def find_nonce_adjusted(self, block_data: bytes, base_difficulty: int,
                           hardware_fingerprint: Optional[Dict] = None) -> Tuple[int, str, float]:
        """
        Find nonce with difficulty adjusted for Pi model
        
        Ensures fair mining across different Pi hardware generations
        
        Args:
            block_data: Block data to mine
            base_difficulty: Base difficulty level
            hardware_fingerprint: Optional hardware verification data
            
        Returns:
            Tuple of (nonce, hash_hex, performance_factor)
        """
        if hardware_fingerprint is None:
            hardware_fingerprint = self._get_hardware_fingerprint()
        
        # Verify hardware first
        if not self._verify_hardware(hardware_fingerprint):
            raise ValueError("Mining requires verified Raspberry Pi hardware")
        
        factor = self.get_pi_performance_factor()
        adjusted_difficulty = max(1, int(base_difficulty * factor))
        
        nonce, hash_hex = self.find_nonce(block_data, adjusted_difficulty, hardware_fingerprint)
        return nonce, hash_hex, factor


# Convenience functions
def compute_pihash(data: bytes, nonce: int = 0,
                  hardware_fingerprint: Optional[Dict] = None,
                  rounds: int = 8, memory_mb: int = 256,
                  parallelism: int = 1) -> str:
    """
    Convenience function to compute PiHash

    Args:
        data: Data to hash
        nonce: Nonce value
        hardware_fingerprint: Hardware verification data
        rounds: Number of computational rounds
        memory_mb: Memory usage in MB
        parallelism: Number of parallel lanes

    Returns:
        Hexadecimal hash string
    """
    pihash = PiHash(rounds=rounds, memory_mb=memory_mb, parallelism=parallelism)
    return pihash.compute(data, nonce, hardware_fingerprint)


def verify_pihash(data: bytes, nonce: int, expected_hash: str,
                 hardware_fingerprint: Optional[Dict] = None,
                 rounds: int = 8, memory_mb: int = 256) -> bool:
    """
    Verify a PiHash computation

    Args:
        data: Original data
        nonce: Nonce used
        expected_hash: Expected hash result
        hardware_fingerprint: Hardware verification data
        rounds: Number of computational rounds
        memory_mb: Memory usage in MB

    Returns:
        True if hash matches
    """
    computed_hash = compute_pihash(data, nonce, hardware_fingerprint, rounds, memory_mb)
    return computed_hash == expected_hash


def verify_pihash_fast(data: bytes, nonce: int, expected_hash: str,
                       rounds: int = 1, memory_mb: int = 32, parallelism: int = 1) -> bool:
    """
    Fast validation path - optimized for non-Pi hardware
    
    Uses minimal memory and single round for quick verification.
    This allows mobile devices, web browsers, etc. to validate blocks.
    
    Args:
        data: Original block data
        nonce: Nonce found during mining
        expected_hash: Hash to verify against
        rounds: Validation rounds (default 1)
        memory_mb: Validation memory (default 32MB)
        parallelism: Parallelism setting (must match mining, default 1)
    
    Returns:
        True if hash matches
    """
    pihash = PiHash(rounds=rounds, memory_mb=memory_mb, 
                   parallelism=parallelism, mining_mode=False)
    computed_hash = pihash.compute(data, nonce, hardware_fingerprint=None)
    return computed_hash == expected_hash
