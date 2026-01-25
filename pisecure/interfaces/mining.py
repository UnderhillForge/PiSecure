"""
MiningInterface - Abstract mining operations

Defines the contract for mining operations without exposing implementation.
This enables mining to be tested independently and for different algorithms.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MiningStats:
    """Mining statistics."""

    is_mining: bool
    blocks_found: int
    hash_rate: float  # hashes per second
    current_difficulty: int
    average_block_time: float
    uptime_seconds: float


@dataclass
class MiningResult:
    """Result of mining operation."""

    success: bool
    block: Optional[Dict[str, Any]]
    error_message: str = ""
    hash_attempts: int = 0
    time_elapsed: float = 0.0


class MiningInterface(ABC):
    """
    Abstract interface for mining operations.

    Implementations should handle:
    - Proof-of-work calculations
    - Block creation and validation
    - Difficulty adjustment
    - Mining hardware verification

    Key principle: Mining is independent of wallet/API/CLI.
    """

    @abstractmethod
    def start_mining(self, wallet_address: str) -> Tuple[bool, str]:
        """
        Start mining with rewards to specified wallet.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def stop_mining(self) -> bool:
        """Stop the mining process."""
        pass

    @abstractmethod
    def is_mining(self) -> bool:
        """Check if mining is currently active."""
        pass

    @abstractmethod
    def mine_block(self, wallet_address: str) -> MiningResult:
        """
        Mine a single block synchronously.

        Returns:
            MiningResult with block data or error
        """
        pass

    @abstractmethod
    def get_mining_stats(self) -> MiningStats:
        """Get comprehensive mining statistics."""
        pass

    @abstractmethod
    def set_difficulty(self, difficulty: int) -> bool:
        """Set the mining difficulty."""
        pass

    @abstractmethod
    def get_difficulty(self) -> int:
        """Get the current mining difficulty."""
        pass

    @abstractmethod
    def verify_hardware(self) -> Tuple[bool, str]:
        """
        Verify hardware meets mining requirements.

        Returns:
            Tuple of (is_verified, message)
        """
        pass

    @abstractmethod
    def get_hash_rate(self) -> float:
        """Get current hash rate in hashes per second."""
        pass

    @abstractmethod
    def estimate_time_to_block(self) -> float:
        """Estimate time to find next block (in seconds)."""
        pass
