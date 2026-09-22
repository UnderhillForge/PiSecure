"""
PiHash Validation Module - Mining Moved to Private Repository

This module provides validation-only functions that work on ANY platform.

VALIDATION FUNCTIONS (kept here):
- count_zero_bits(hash_hex) - Count leading zero bits in hash
- hash_meets_zero_bits(hash_hex, target) - Check if hash meets difficulty

MINING FUNCTIONS (moved to PiSecure-Miner):
- PiHash class - Removed (only in PiSecure-Miner)
- compute_pihash() - Removed (only in PiSecure-Miner)
- find_nonce() - Removed (only in PiSecure-Miner)

For mining, install: https://github.com/UnderhillForge/PiSecure/releases
"""


def count_zero_bits(hash_hex: str) -> int:
    """
    Count LEADING zero bits in a 256-bit hash hex string.

    This counts consecutive zero bits from the start (most significant bits),
    not total zero bits. This is the correct difficulty metric for PoW.

    Works on ANY platform (Mac, Windows, Linux, Raspberry Pi).

    Args:
        hash_hex: Hexadecimal hash string (64 chars for SHA256)

    Returns:
        Number of leading zero bits (0-256)
        Returns 0 if the input is not valid hex.

    Example:
        >>> count_zero_bits("0000abc123...")
        16  # 4 zero hex digits = 16 zero bits
    """
    try:
        value = int(hash_hex, 16)
    except ValueError:
        return 0

    # Count leading zeros by finding the position of the first 1 bit
    # In a 256-bit value, this is (256 - bit_length())
    if value == 0:
        return 256  # All zeros

    return 256 - value.bit_length()


def hash_meets_zero_bits(hash_hex: str, target_zero_bits: int) -> bool:
    """
    Check if a hash has at least the requested number of LEADING zero bits.

    This is the primary validation function used throughout PiSecure.
    Works on ANY platform - no hardware requirements.

    Args:
        hash_hex: Hexadecimal hash string
        target_zero_bits: Required minimum leading zero bits

    Returns:
        True if hash meets difficulty, False otherwise

    Example:
        >>> hash_meets_zero_bits("0000abc123...", 16)
        True  # Hash has at least 16 leading zero bits
    """
    return count_zero_bits(hash_hex) >= target_zero_bits


# Mining stubs - raise NotImplementedError pointing to private repo
class PiHash:
    """
    PiHash Mining Algorithm - MOVED TO PRIVATE REPOSITORY

    Mining is the psminer release binary for Raspberry Pi 2-5.
    This class is now a stub that raises helpful errors.

    For mining on Raspberry Pi, install:
    https://github.com/UnderhillForge/PiSecure/releases

    For validation on any platform, use:
    - count_zero_bits(hash_hex)
    - hash_meets_zero_bits(hash_hex, target_bits)
    """

    def __init__(self, rounds: int = 8, memory_mb: int = 256, npu_enabled: bool = False):
        """Initialize PiHash - Mining moved to PiSecure-Miner"""
        raise NotImplementedError(
            "PiHash mining has been moved to a private repository.\n\n"
            "To enable mining on Raspberry Pi:\n"
            "1. Download psminer: https://github.com/UnderhillForge/PiSecure/releases\n"
            "2. Build: mkdir build && cd build && cmake .. && make -j4\n"
            "3. Run: ./psminer/psminer --wallet YOUR_ADDRESS\n\n"
            "For validation on any platform, use psvalidator instead."
        )

    def compute(self, data: bytes, nonce: int, hardware_fingerprint=None) -> str:
        """Compute PiHash - Mining moved to PiSecure-Miner"""
        raise NotImplementedError("Mining moved to PiSecure-Miner private repository")

    def find_nonce(self, block_data: bytes, difficulty: int, max_attempts: int = None):
        """Find nonce for PiHash - Mining moved to PiSecure-Miner"""
        raise NotImplementedError("Mining moved to PiSecure-Miner private repository")

    def meets_difficulty(self, hash_hex: str, target_zero_bits: int) -> bool:
        """Check difficulty - VALIDATION ONLY"""
        # This can work without mining
        return hash_meets_zero_bits(hash_hex, target_zero_bits)

    def count_leading_zeros(self, hash_hex: str) -> int:
        """Count zeros - VALIDATION ONLY"""
        # This can work without mining
        return count_zero_bits(hash_hex)


def compute_pihash(data: bytes, nonce: int, hardware_fingerprint=None, rounds: int = 8,
                   memory_mb: int = 256) -> str:
    """Compute PiHash - Mining moved to PiSecure-Miner"""
    raise NotImplementedError(
        "PiHash mining has been moved to PiSecure-Miner private repository.\n"
        "https://github.com/UnderhillForge/PiSecure/releases"
    )


def find_nonce(block_data: bytes, difficulty: int, max_attempts: int = None) -> tuple:
    """Find nonce for PiHash - Mining moved to PiSecure-Miner"""
    raise NotImplementedError(
        "PiHash mining has been moved to PiSecure-Miner private repository.\n"
        "https://github.com/UnderhillForge/PiSecure/releases"
    )


def verify_pihash(data: bytes, nonce: int, target_hash: str, hardware_fingerprint=None,
                  rounds: int = 8, memory_mb: int = 256) -> bool:
    """Verify PiHash - Mining moved to PiSecure-Miner"""
    raise NotImplementedError(
        "PiHash mining has been moved to PiSecure-Miner private repository.\n"
        "https://github.com/UnderhillForge/PiSecure/releases"
    )
