"""
StorageInterface - Abstract storage operations

Defines the contract for data persistence without exposing implementation.
This enables swapping between JSON, SQLite, LevelDB, or hybrid storage.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class StorageInterface(ABC):
    """
    Abstract interface for storage operations.

    Implementations should handle:
    - Block storage and retrieval
    - Transaction indexing
    - UTXO set management
    - Fast lookups

    Key principle: Storage implementation is invisible to blockchain/wallet.
    """

    @abstractmethod
    def save_block(self, block_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Save a block to storage.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def get_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get a block by hash."""
        pass

    @abstractmethod
    def get_block_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get a block by index."""
        pass

    @abstractmethod
    def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """Get the most recent block."""
        pass

    @abstractmethod
    def save_transaction(self, tx_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Save a transaction to storage.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get a transaction by ID."""
        pass

    @abstractmethod
    def get_wallet_transactions(
        self, wallet_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get transactions for a wallet."""
        pass

    @abstractmethod
    def save_utxo(self, wallet_id: str, utxo_data: Dict[str, Any]) -> bool:
        """Save UTXO (unspent transaction output) for a wallet."""
        pass

    @abstractmethod
    def get_utxo(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get UTXO for a wallet."""
        pass

    @abstractmethod
    def delete_utxo(self, wallet_id: str) -> bool:
        """Delete UTXO for a wallet."""
        pass

    @abstractmethod
    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance from UTXO set."""
        pass

    @abstractmethod
    def save_metadata(self, key: str, value: Any) -> bool:
        """Save metadata (chain length, difficulty, etc.)."""
        pass

    @abstractmethod
    def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata by key."""
        pass

    @abstractmethod
    def clear_pending_transactions(self) -> bool:
        """Clear the pending transaction pool."""
        pass

    @abstractmethod
    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get all pending transactions."""
        pass

    @abstractmethod
    def backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Backup storage to a file.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def restore(self, backup_path: str) -> Tuple[bool, str]:
        """
        Restore storage from a backup file.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def get_size(self) -> int:
        """Get storage size in bytes."""
        pass

    @abstractmethod
    def verify_integrity(self) -> Tuple[bool, str]:
        """
        Verify storage integrity.

        Returns:
            Tuple of (is_valid, message)
        """
        pass
