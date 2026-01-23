"""
PiHash Mining Algorithm Wrapper

This module provides access to the PiHash mining algorithm compiled in C++.
The actual hardware verification logic is sealed within the compiled binary
to prevent reverse-engineering and spoofing attacks.

Users interact with simple function signatures while the implementation details
remain protected in the optimized C++ code.
"""

import os
from typing import Optional, Dict, Tuple, Any

# Try to import C++ PiHash module
try:
    from pisecure_cpp_pihash import (
        PiHash as _PiHashCpp,
        compute_pihash as _compute_pihash_cpp,
        mine_block as _mine_block_cpp,
    )

    _CPP_PIHASH_AVAILABLE = True
except ImportError:
    _CPP_PIHASH_AVAILABLE = False
    _PiHashCpp = None


class PiHash:
    """
    PiHash mining algorithm wrapper

    Delegates to C++ implementation for hardware verification and mining.
    The actual verification algorithm is sealed in the compiled binary.

    Example:
        pihash = PiHash(rounds=8, memory_mb=256)
        nonce, hash_hex = pihash.find_nonce(block_data, difficulty=140)
    """

    def __init__(self, rounds: int = 1, memory_mb: int = 1, npu_enabled: bool = False):
        """
        Initialize PiHash instance

        Args:
            rounds: Number of computational rounds (affects difficulty)
            memory_mb: Memory buffer size in MB (1-256)
            npu_enabled: Enable NPU acceleration if available (Pi 6+)

        Raises:
            RuntimeError: If C++ module not available
        """
        if not _CPP_PIHASH_AVAILABLE:
            raise RuntimeError(
                "PiHash C++ module not available. "
                "Ensure pisecure_cpp_pihash is built and installed."
            )

        self._pihash = _PiHashCpp(
            rounds=rounds, memory_mb=memory_mb, npu_enabled=npu_enabled
        )

    def compute(
        self,
        data: bytes,
        nonce: int,
        hardware_fingerprint: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compute PiHash digest

        Hardware verification is performed internally within the C++ binary.

        Args:
            data: Block data to hash
            nonce: Mining nonce (0-2^32)
            hardware_fingerprint: Optional pre-computed hardware fingerprint

        Returns:
            Hexadecimal hash string (64 characters)

        Raises:
            RuntimeError: If hardware verification fails
        """
        # Convert bytes to list for C++ binding
        if isinstance(data, bytes):
            data = list(data)

        return self._pihash.compute(data, nonce, None)

    def find_nonce(
        self,
        block_data: bytes,
        difficulty: int,
        hardware_fingerprint: Optional[Dict[str, Any]] = None,
        max_attempts: int = 0xFFFFFFFF,
    ) -> Tuple[int, str]:
        """
        Find nonce meeting difficulty requirement

        Mining loop runs in optimized C++ for maximum performance.

        Args:
            block_data: Block data to mine
            difficulty: Target leading zero bits required
            hardware_fingerprint: Optional pre-computed hardware fingerprint
            max_attempts: Maximum nonces to try (default 2^32)

        Returns:
            Tuple of (nonce, hash_hex) meeting difficulty

        Raises:
            RuntimeError: If no valid nonce found within max_attempts
        """
        # Convert bytes to list for C++ binding
        if isinstance(block_data, bytes):
            block_data = list(block_data)

        return self._pihash.find_nonce(block_data, difficulty, None, max_attempts)

    @staticmethod
    def meets_difficulty(hash_hex: str, target_zero_bits: int) -> bool:
        """
        Check if hash meets zero-bit difficulty requirement

        Args:
            hash_hex: Hexadecimal hash string
            target_zero_bits: Required leading zero bits

        Returns:
            True if hash meets difficulty
        """
        if not _CPP_PIHASH_AVAILABLE:
            raise RuntimeError("C++ PiHash module not available")

        return _PiHashCpp.meets_difficulty(hash_hex, target_zero_bits)


# Convenience functions


def compute_pihash(
    data: bytes, nonce: int = 0, rounds: int = 8, memory_mb: int = 256
) -> str:
    """
    Convenience function to compute PiHash

    Args:
        data: Data to hash
        nonce: Mining nonce
        rounds: Computational rounds
        memory_mb: Memory buffer size in MB

    Returns:
        Hexadecimal hash string
    """
    if not _CPP_PIHASH_AVAILABLE:
        raise RuntimeError("C++ PiHash module not available")

    # Convert bytes to list if needed
    if isinstance(data, bytes):
        data = list(data)

    return _compute_pihash_cpp(data, nonce, rounds, memory_mb)


def find_nonce(
    block_data: bytes, difficulty: int, max_attempts: int = 0xFFFFFFFF
) -> Tuple[int, str]:
    """
    Find mining nonce (convenience function)

    Args:
        block_data: Block to mine
        difficulty: Target zero bits
        max_attempts: Maximum attempts

    Returns:
        Tuple of (nonce, hash) meeting difficulty
    """
    if not _CPP_PIHASH_AVAILABLE:
        raise RuntimeError("C++ PiHash module not available")

    # Convert bytes to list if needed
    if isinstance(block_data, bytes):
        block_data = list(block_data)

    return _mine_block_cpp(block_data, difficulty, max_attempts)


def is_pihash_available() -> bool:
    """Check if C++ PiHash module is available"""
    return _CPP_PIHASH_AVAILABLE


def get_implementation_info() -> Dict[str, str]:
    """Get information about PiHash implementation"""
    return {
        "backend": "C++ (compiled, hardware-sealed)",
        "available": str(_CPP_PIHASH_AVAILABLE),
        "hardware_verification": "sealed in binary",
        "mining_optimization": "optimized C++ loops (100-1000x faster than Python)",
        "security_model": "binary-only distribution with no source code exposure",
    }
