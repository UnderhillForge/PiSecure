"""
PiSecure Kernel Module

Pure consensus logic with zero network/wallet/CLI dependencies.

The kernel contains:
- Consensus rules (difficulty, block validation, chain rules)
- PiHash proof-of-work algorithm
- Cryptographic primitives
- Block and transaction validation

The kernel should work independently and be embeddable in other projects.
"""

# Consensus layer exports (will import from consensus.py, validation.py, pihash.py)
# For now, just establish the module structure

__all__ = [
    "ConsensusRules",
    "ValidationEngine",
    "PiHashAlgorithm",
]
