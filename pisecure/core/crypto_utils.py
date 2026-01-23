"""
PiSecure Crypto Utilities - C++ Accelerated

Provides optimized cryptographic primitives using C++ bindings for hot paths.
Falls back to Python hashlib for compatibility.

Performance-critical operations use pisecure_cpp_crypto (10-50x faster).
Non-critical operations use standard hashlib (simpler, good enough).
"""

import hashlib
import os
from typing import Union

# Try to import C++ crypto module
_CPP_CRYPTO_AVAILABLE = False
try:
    import sys

    # Add build directory to path if testing locally
    build_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "build", "pisecure"
    )
    if os.path.exists(build_path) and build_path not in sys.path:
        sys.path.insert(0, build_path)

    import pisecure_cpp_crypto

    _CPP_CRYPTO_AVAILABLE = True
except ImportError:
    # C++ module not built yet - fallback to Python
    pisecure_cpp_crypto = None


def sha256(data: Union[bytes, str]) -> bytes:
    """
    Fast SHA-256 hashing using C++ implementation.

    Used for performance-critical operations:
    - Block validation hashing
    - Transaction validation hashing
    - Merkle tree construction

    Args:
        data: Input data (bytes or string)

    Returns:
        32-byte SHA-256 digest
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if _CPP_CRYPTO_AVAILABLE:
        # Use C++ implementation (10-50x faster)
        return pisecure_cpp_crypto.sha256(data)
    else:
        # Fallback to Python hashlib
        return hashlib.sha256(data).digest()


def sha256_hex(data: Union[bytes, str]) -> str:
    """
    Fast SHA-256 hashing returning hex string.

    Convenience wrapper for sha256() that returns hex digest.

    Args:
        data: Input data (bytes or string)

    Returns:
        64-character hex string
    """
    return sha256(data).hex()


def sha256d(data: Union[bytes, str]) -> bytes:
    """
    Double SHA-256 (Bitcoin-style).

    Used for enhanced security in some contexts.

    Args:
        data: Input data (bytes or string)

    Returns:
        32-byte double SHA-256 digest
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if _CPP_CRYPTO_AVAILABLE:
        return pisecure_cpp_crypto.sha256d(data)
    else:
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def sha256d_hex(data: Union[bytes, str]) -> str:
    """Double SHA-256 returning hex string."""
    return sha256d(data).hex()


def is_cpp_available() -> bool:
    """Check if C++ crypto acceleration is available."""
    return _CPP_CRYPTO_AVAILABLE


def get_implementation() -> str:
    """Get current crypto implementation name."""
    return "C++ (pisecure_cpp_crypto)" if _CPP_CRYPTO_AVAILABLE else "Python (hashlib)"


# For non-critical operations, just use hashlib directly
# (no need to go through C++ for session tokens, IDs, etc.)
def hash_for_id(data: str) -> str:
    """
    Simple hash for generating IDs (non-critical path).
    Uses Python hashlib - perfectly fine for this use case.

    Args:
        data: String to hash

    Returns:
        Hex digest (truncated to 16 chars for readability)
    """
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def hash_full(data: Union[bytes, str]) -> str:
    """
    Full SHA-256 hash for non-critical operations.
    Uses Python hashlib.

    Args:
        data: Data to hash

    Returns:
        Full 64-character hex digest
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
