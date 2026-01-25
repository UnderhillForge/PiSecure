"""
Python fallback for C++ PiHash bindings.

Provides a compatible interface for tests when native module isn't built.
"""

import hashlib
from typing import List


def compute_pihash(data: List[int], nonce: int) -> str:
    """Compute a deterministic SHA-256 hash over data and nonce.

    This mirrors the C++ binding signature used in tests:
    - data: list of byte values (0-255)
    - nonce: integer
    Returns 64-char hex string.
    """
    if data is None:
        data = []
    try:
        data_bytes = bytes(int(x) & 0xFF for x in data)
    except Exception:
        # Fallback: treat as empty if malformed
        data_bytes = b""

    # Combine data with nonce in a simple deterministic way
    nonce_bytes = nonce.to_bytes(8, byteorder="big", signed=False)
    payload = data_bytes + nonce_bytes
    return hashlib.sha256(payload).hexdigest()
