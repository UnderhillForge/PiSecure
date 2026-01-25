"""
ChainInterface - Abstract blockchain operations

Defines the contract for blockchain operations without exposing implementation.
This enables wallet, API, and mining to work with any blockchain backend.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Block:
    """Block data structure."""

    index: int
    timestamp: float
    transactions: List[Dict[str, Any]]
    previous_hash: str
    hash: str
    nonce: int
    difficulty: int


@dataclass
class Transaction:
    """Transaction data structure."""

    tx_id: str
    sender: str
    recipient: str
    amount: float
    timestamp: float
    signature: Optional[str] = None


class ChainInterface(ABC):
    """
    Abstract interface for blockchain operations.

    Implementations should handle:
    - Block validation and storage
    - Transaction management
    - Chain verification
    - Mining difficulty
    - UTXO set management
    """

    @abstractmethod
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        pass

    @abstractmethod
    def get_block(self, index: int) -> Optional[Block]:
        """Get a block by index."""
        pass

    @abstractmethod
    def add_block(self, block: Block) -> bool:
        """Add a validated block to the chain."""
        pass

    @abstractmethod
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to the pending pool."""
        pass

    @abstractmethod
    def get_pending_transactions(self) -> List[Transaction]:
        """Get all pending transactions."""
        pass

    @abstractmethod
    def validate_transaction(self, transaction: Transaction) -> Tuple[bool, str]:
        """
        Validate a transaction.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def validate_chain(self) -> Tuple[bool, str]:
        """
        Validate the entire blockchain.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def validate_block(self, block: Block) -> Tuple[bool, str]:
        """
        Validate a block.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def get_difficulty(self) -> int:
        """Get the current mining difficulty."""
        pass

    @abstractmethod
    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance from UTXO set."""
        pass

    @abstractmethod
    def get_wallet_transactions(self, wallet_id: str) -> List[Transaction]:
        """Get all transactions for a wallet."""
        pass

    @abstractmethod
    def get_chain_length(self) -> int:
        """Get the number of blocks in the chain."""
        pass

    @abstractmethod
    def get_chain_info(self) -> Dict[str, Any]:
        """Get comprehensive chain information."""
        pass

    @abstractmethod
    def broadcast_transaction(
        self, transaction: Transaction, exclude_peers: Optional[List[str]] = None
    ) -> None:
        """Broadcast transaction to network peers."""
        pass
