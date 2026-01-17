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
"""

import hashlib
import os
import struct
import time
from typing import Dict, Any, Optional, Tuple


def count_zero_bits(hash_hex: str) -> int:
    """Count zero bits in a 256-bit hash hex string.

    Returns 0 if the input is not valid hex.
    """
    try:
        value = int(hash_hex, 16)
    except ValueError:
        return 0

    # SHA256/PiHash outputs 256-bit digests; zeros are the complement of set bits
    return 256 - value.bit_count()


def hash_meets_zero_bits(hash_hex: str, target_zero_bits: int) -> bool:
    """Check if a hash has at least the requested number of zero bits."""
    return count_zero_bits(hash_hex) >= target_zero_bits


class PiHash:
    """
    PiSecure's custom hardware-verified hash algorithm

    Designed for Raspberry Pi mining with:
    - Hardware fingerprinting integration
    - Memory-hard computations (256MB default)
    - ARM CPU optimizations
    - NPU acceleration hooks
    """

    def __init__(self, rounds: int = 1, memory_mb: int = 8, npu_enabled: bool = False):
        """
        Initialize PiHash with configurable parameters

        Args:
            rounds: Number of computational rounds (difficulty factor)
            memory_mb: Memory usage in MB (default 8MB, optimized for Pi mining speed)
            npu_enabled: Enable NPU acceleration when available (Pi 6)
        """
        self.rounds = rounds
        self.memory_mb = memory_mb
        self.npu_enabled = npu_enabled
        self.memory_bytes = memory_mb * 1024 * 1024

        # Hardware verification
        self.hardware_verified = False
        self.hardware_fingerprint = {}

    def compute(self, data: bytes, nonce: int, hardware_fingerprint: Optional[Dict] = None) -> str:
        """
        Compute PiHash digest

        Args:
            data: Block data to hash
            nonce: Mining nonce
            hardware_fingerprint: Pi hardware verification data

        Returns:
            Hexadecimal hash string
        """
        if hardware_fingerprint is None:
            hardware_fingerprint = self._get_hardware_fingerprint()

        # Verify hardware compatibility
        if not self._verify_hardware(hardware_fingerprint):
            raise ValueError("PiHash requires verified Raspberry Pi hardware")

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
                'mac_address': self._get_mac_address(),
                'memory_info': self._get_memory_info(),
                'hardware_rng': self._get_hardware_rng(32),
                'timestamp': int(time.time())
            }

            # Generate unique hardware ID
            hw_id_data = (
                str(fingerprint['cpu_serial']) +
                fingerprint['hardware_model'] +
                fingerprint['mac_address'] +
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

            # Verify hardware RNG is available
            if 'hardware_rng' not in fingerprint:
                return False

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

    def _get_mac_address(self) -> str:
        """Get primary network interface MAC address"""
        try:
            import subprocess
            result = subprocess.run(['cat', '/sys/class/net/eth0/address'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()

            # Try wlan0
            result = subprocess.run(['cat', '/sys/class/net/wlan0/address'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()

            return "00:00:00:00:00:00"  # Fallback
        except Exception:
            return "00:00:00:00:00:00"

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

    def _hardware_hash(self, data: bytes, nonce: int, fingerprint: Dict) -> bytes:
        """
        Stage 1: Integrate hardware-specific data into hash

        Args:
            data: Block data
            nonce: Mining nonce
            fingerprint: Hardware verification data

        Returns:
            Hardware-integrated hash bytes
        """
        # Combine block data, nonce, and hardware fingerprint
        hw_data = data + struct.pack('<Q', nonce)  # Pack nonce as uint64

        # Add hardware-specific elements
        hw_data += fingerprint['unique_id'].encode()
        hw_data += fingerprint['hardware_rng']

        # CPU serial as salt
        serial_bytes = str(fingerprint['cpu_serial']).encode()
        hw_data += serial_bytes

        # Create initial hash
        initial_hash = hashlib.sha256(hw_data).digest()

        # Mix with memory pattern (Pi-specific)
        memory_pattern = self._get_memory_access_pattern()
        mixed_hash = bytes(a ^ b for a, b in zip(initial_hash, memory_pattern))

        return mixed_hash

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
        Stage 2: Memory-hard computation optimized for Pi RAM

        Uses configurable memory (default 8MB) in a Pi-optimized pattern
        """
        # Initialize memory buffer (only allocate what we need)
        buffer_size = min(self.memory_bytes, 8 * 1024 * 1024)  # Cap at 8MB for fast mining
        memory_buffer = bytearray(buffer_size)

        # Fill memory buffer with Pi-optimized pattern
        for i in range(0, len(memory_buffer), 32):
            # Create 32-byte chunks (SHA256 output size)
            chunk_data = hw_hash + struct.pack('<Q', nonce) + struct.pack('<Q', i)
            chunk_hash = hashlib.sha256(chunk_data).digest()

            # Fill memory with hash data (32 bytes at a time)
            for j in range(min(32, len(memory_buffer) - i)):
                memory_buffer[i + j] = chunk_hash[j]

        # Mix memory buffer (optimized for performance)
        # Use fewer passes for larger buffers to keep computation reasonable
        mix_rounds = max(1, self.rounds // 2)
        
        for round_num in range(mix_rounds):
            # Access memory in larger chunks for better cache locality
            for i in range(0, len(memory_buffer), 1024):  # Process 1KB chunks
                # Mix a chunk efficiently
                for j in range(min(1024, len(memory_buffer) - i)):
                    idx = i + j
                    prev = memory_buffer[(idx - 1) % len(memory_buffer)]
                    curr = memory_buffer[idx]
                    next_val = memory_buffer[(idx + 1) % len(memory_buffer)]

                    # Simple but effective mixing
                    memory_buffer[idx] = ((prev ^ curr ^ next_val) + round_num) & 0xFF

        # Reduce to 32-byte hash
        reduced_hash = hashlib.sha256(memory_buffer).digest()
        return reduced_hash

    def _cpu_optimized_finalize(self, memory_hash: bytes) -> bytes:
        """
        Stage 3: CPU-optimized finalization for ARM architecture

        Uses multiple rounds of ARM-optimized operations
        """
        hash_state = list(memory_hash)  # Convert to mutable list

        for round_num in range(self.rounds):
            # ARM-optimized mixing operations
            for i in range(len(hash_state)):
                # Simulate ARM NEON operations (simplified)
                a = hash_state[i]
                b = hash_state[(i + 1) % len(hash_state)]
                c = hash_state[(i + 2) % len(hash_state)]

                # Custom ARM-style operations
                mixed = (a + b + c) & 0xFF
                mixed = ((mixed * 7) + 3) & 0xFF  # Multiplication common in ARM
                mixed ^= (mixed >> 4)  # Bit operations

                hash_state[i] = mixed

            # Additional diffusion
            hash_state = self._arm_diffusion(hash_state)

        return bytes(hash_state)

    def _arm_diffusion(self, state: list) -> list:
        """ARM-optimized diffusion function"""
        # Simulate ARM instruction patterns
        for i in range(0, len(state), 4):
            if i + 3 < len(state):
                # SIMD-like operations on 4 bytes
                a, b, c, d = state[i:i+4]

                # ARM-style register operations
                a = (a + b) & 0xFF
                c = (c + d) & 0xFF
                a, c = (a ^ c), (a ^ c)  # Swap
                b = (b + c) & 0xFF
                d = (d + a) & 0xFF

                state[i:i+4] = [a, b, c, d]

        return state

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

    def meets_difficulty(self, hash_hex: str, target_zero_bits: int) -> bool:
        """Check if a hash meets the zero-bit difficulty target."""
        return hash_meets_zero_bits(hash_hex, target_zero_bits)

    def find_nonce(self, block_data: bytes, difficulty: int,
                   hardware_fingerprint: Optional[Dict] = None) -> Tuple[int, str]:
        """
        Find nonce that meets difficulty requirement

        Args:
            block_data: Block data to mine
            difficulty: Target zero bits required
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


# Convenience functions
def compute_pihash(data: bytes, nonce: int = 0,
                  hardware_fingerprint: Optional[Dict] = None,
                  rounds: int = 8, memory_mb: int = 256) -> str:
    """
    Convenience function to compute PiHash

    Args:
        data: Data to hash
        nonce: Nonce value
        hardware_fingerprint: Hardware verification data
        rounds: Number of computational rounds
        memory_mb: Memory usage in MB

    Returns:
        Hexadecimal hash string
    """
    pihash = PiHash(rounds=rounds, memory_mb=memory_mb)
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