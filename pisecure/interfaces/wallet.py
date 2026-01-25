"""
WalletInterface - Abstract wallet operations

Defines the contract for wallet operations without exposing implementation.
This enables wallets to be tested independently from blockchain.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WalletInfo:
    """Wallet information."""

    address: str
    balance: float
    transaction_count: int
    public_key: str


@dataclass
class TransactionRequest:
    """Request to create a transaction."""

    recipient: str
    amount: float
    fee: float = 0.001
    message: Optional[str] = None


@dataclass
class SignedTransaction:
    """A signed and ready-to-broadcast transaction."""

    tx_id: str
    sender: str
    recipient: str
    amount: float
    fee: float
    timestamp: float
    signature: str
    raw_data: bytes


class WalletInterface(ABC):
    """
    Abstract interface for wallet operations.

    Implementations should handle:
    - Private/public key management
    - Transaction signing
    - Balance calculation
    - Transaction history

    Key principle: Wallet uses Chain interface only, never depends on
    Chain implementation details.
    """

    @abstractmethod
    def get_address(self) -> str:
        """Get the wallet's public address."""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """Get the wallet's current balance."""
        pass

    @abstractmethod
    def get_public_key(self) -> str:
        """Get the wallet's public key (PEM format)."""
        pass

    @abstractmethod
    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history for this wallet."""
        pass

    @abstractmethod
    def sign_transaction(
        self, transaction_request: TransactionRequest
    ) -> Tuple[bool, SignedTransaction | str]:
        """
        Create and sign a transaction.

        Returns:
            Tuple of (success, signed_tx_or_error_message)
        """
        pass

    @abstractmethod
    def create_token_transfer(
        self, recipient: str, amount: float
    ) -> Tuple[bool, SignedTransaction | str]:
        """
        Create a token transfer transaction (convenience method).

        Returns:
            Tuple of (success, signed_tx_or_error_message)
        """
        pass

    @abstractmethod
    def get_info(self) -> WalletInfo:
        """Get comprehensive wallet information."""
        pass

    @abstractmethod
    def verify_signature(self, message: str, signature: str, public_key: str) -> bool:
        """Verify a cryptographic signature."""
        pass

    @abstractmethod
    def backup_key(self, output_path: str) -> Tuple[bool, str]:
        """
        Backup the private key to a file.

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def restore_key(self, input_path: str) -> Tuple[bool, str]:
        """
        Restore private key from a file.

        Returns:
            Tuple of (success, message)
        """
        pass
