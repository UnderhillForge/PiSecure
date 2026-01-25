"""
PiHash C++ Bindings Stub - Mining Moved to Private Repository

This module attempted to wrap C++ PiHash implementation.
Mining functionality has been moved to the private PiSecure-Miner repository.

VALIDATION: Available through pihash module
MINING: Moved to https://github.com/UnderhillForge/PiSecure-Miner
"""


def count_zero_bits(hash_hex: str) -> int:
    """
    Count LEADING zero bits in hash (universal validation).

    Works on ANY platform - no hardware requirements.
    Import from pisecure.core.pihash instead.
    """
    try:
        value = int(hash_hex, 16)
    except ValueError:
        return 0

    if value == 0:
        return 256

    return 256 - value.bit_length()


def hash_meets_zero_bits(hash_hex: str, target_zero_bits: int) -> bool:
    """
    Check if hash meets difficulty (universal validation).

    Works on ANY platform - no hardware requirements.
    Import from pisecure.core.pihash instead.
    """
    return count_zero_bits(hash_hex) >= target_zero_bits


class PiHash:
    """
    PiHash C++ Wrapper - MOVED TO PRIVATE REPOSITORY

    C++ mining implementation moved to PiSecure-Miner.
    This is now a stub that raises helpful errors.

    Install from: https://github.com/UnderhillForge/PiSecure-Miner
    """

    def __init__(self, rounds: int = 8, memory_mb: int = 256):
        raise NotImplementedError(
            "PiHash C++ mining has been moved to PiSecure-Miner.\n"
            "https://github.com/UnderhillForge/PiSecure-Miner"
        )

    def compute(self, data: bytes, nonce: int, hw_fingerprint=None) -> str:
        raise NotImplementedError("Mining moved to PiSecure-Miner private repository")

    def find_nonce(self, block_data: bytes, difficulty: int, hw_fingerprint=None,
                   max_attempts: int = None):
        raise NotImplementedError("Mining moved to PiSecure-Miner private repository")


def compute_pihash(data: bytes, nonce: int, rounds: int = 8, memory_mb: int = 256) -> str:
    """Compute PiHash via C++ - Mining moved to PiSecure-Miner"""
    raise NotImplementedError(
        "PiHash C++ mining has been moved to PiSecure-Miner.\n"
        "https://github.com/UnderhillForge/PiSecure-Miner"
    )


def find_nonce(block_data: bytes, difficulty: int, max_attempts: int = None) -> tuple:
    """Find nonce via C++ - Mining moved to PiSecure-Miner"""
    raise NotImplementedError(
        "PiHash C++ mining has been moved to PiSecure-Miner.\n"
        "https://github.com/UnderhillForge/PiSecure-Miner"
    )
