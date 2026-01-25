"""
Concrete implementations of PiSecure interfaces.

These adapters wrap existing SignChain, SignWallet, etc. to implement
the abstract interfaces. This enables gradual migration without rewriting
everything at once.

The implementations are bridges between the old monolithic code and
the new interface-based architecture.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from pisecure.interfaces.chain import ChainInterface, Block, Transaction
from pisecure.interfaces.wallet import (
    WalletInterface,
    WalletInfo,
    TransactionRequest,
    SignedTransaction,
)
from pisecure.interfaces.node import NodeInterface, PeerInfo, NetworkStats
from pisecure.interfaces.mining import MiningInterface, MiningStats, MiningResult

logger = logging.getLogger(__name__)


class ChainImpl(ChainInterface):
    """
    Concrete implementation of ChainInterface.

    Wraps SignChain from pisecure.core.blockchain to provide
    interface-compatible blockchain operations.
    """

    def __init__(self, sign_chain: Any):
        """
        Initialize with existing SignChain instance.

        Args:
            sign_chain: Instance of pisecure.core.blockchain.SignChain
        """
        self.sign_chain = sign_chain

    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        try:
            latest = self.sign_chain.get_latest_block()
            return Block(
                index=latest.get("index", 0),
                timestamp=latest.get("timestamp", 0.0),
                transactions=latest.get("transactions", []),
                previous_hash=latest.get("previous_hash", ""),
                hash=latest.get("hash", ""),
                nonce=latest.get("nonce", 0),
                difficulty=latest.get("difficulty", 0),
            )
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            raise

    def get_block(self, index: int) -> Optional[Block]:
        """Get a block by index."""
        try:
            block = self.sign_chain.get_block(index)
            if not block:
                return None
            return Block(
                index=block.get("index", index),
                timestamp=block.get("timestamp", 0.0),
                transactions=block.get("transactions", []),
                previous_hash=block.get("previous_hash", ""),
                hash=block.get("hash", ""),
                nonce=block.get("nonce", 0),
                difficulty=block.get("difficulty", 0),
            )
        except Exception:
            return None

    def add_block(self, block: Block) -> bool:
        """Add a validated block to the chain."""
        try:
            block_data = {
                "index": block.index,
                "timestamp": block.timestamp,
                "transactions": block.transactions,
                "previous_hash": block.previous_hash,
                "hash": block.hash,
                "nonce": block.nonce,
                "difficulty": block.difficulty,
            }
            return self.sign_chain.add_block(block_data)
        except Exception as e:
            logger.error(f"Error adding block: {e}")
            return False

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to the pending pool."""
        try:
            tx_data = {
                "tx_id": transaction.tx_id,
                "sender": transaction.sender,
                "recipient": transaction.recipient,
                "amount": transaction.amount,
                "timestamp": transaction.timestamp,
                "signature": transaction.signature,
            }
            return self.sign_chain.add_transaction(tx_data)
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return False

    def get_pending_transactions(self) -> List[Transaction]:
        """Get all pending transactions."""
        try:
            pending = self.sign_chain.get_pending_transactions()
            return [
                Transaction(
                    tx_id=tx.get("tx_id", ""),
                    sender=tx.get("sender", ""),
                    recipient=tx.get("recipient", ""),
                    amount=tx.get("amount", 0.0),
                    timestamp=tx.get("timestamp", 0.0),
                    signature=tx.get("signature"),
                )
                for tx in pending
            ]
        except Exception as e:
            logger.error(f"Error getting pending transactions: {e}")
            return []

    def validate_transaction(self, transaction: Transaction) -> Tuple[bool, str]:
        """Validate a transaction."""
        try:
            result = self.sign_chain.validate_transaction(transaction.tx_id)
            return (result, "") if result else (False, "Transaction validation failed")
        except Exception as e:
            return (False, str(e))

    def validate_chain(self) -> Tuple[bool, str]:
        """Validate the entire blockchain."""
        try:
            result = self.sign_chain.validate_chain()
            return (result, "") if result else (False, "Chain validation failed")
        except Exception as e:
            return (False, str(e))

    def validate_block(self, block: Block) -> Tuple[bool, str]:
        """Validate a block."""
        try:
            block_data = {
                "index": block.index,
                "timestamp": block.timestamp,
                "transactions": block.transactions,
                "previous_hash": block.previous_hash,
                "hash": block.hash,
                "nonce": block.nonce,
                "difficulty": block.difficulty,
            }
            result = self.sign_chain.validate_block(block_data)
            return (result, "") if result else (False, "Block validation failed")
        except Exception as e:
            return (False, str(e))

    def get_difficulty(self) -> int:
        """Get the current mining difficulty."""
        try:
            return self.sign_chain.difficulty
        except Exception:
            return 4  # Default

    def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance from UTXO set."""
        try:
            return self.sign_chain.get_wallet_balance(wallet_id)
        except Exception:
            return 0.0

    def get_wallet_transactions(self, wallet_id: str) -> List[Transaction]:
        """Get all transactions for a wallet."""
        try:
            txs = self.sign_chain.get_wallet_transactions(wallet_id)
            return [
                Transaction(
                    tx_id=tx.get("tx_id", ""),
                    sender=tx.get("sender", ""),
                    recipient=tx.get("recipient", ""),
                    amount=tx.get("amount", 0.0),
                    timestamp=tx.get("timestamp", 0.0),
                    signature=tx.get("signature"),
                )
                for tx in txs
            ]
        except Exception:
            return []

    def get_chain_length(self) -> int:
        """Get the number of blocks in the chain."""
        try:
            return len(self.sign_chain.chain)
        except Exception:
            return 0

    def get_chain_info(self) -> Dict[str, Any]:
        """Get comprehensive chain information."""
        try:
            return self.sign_chain.get_chain_info()
        except Exception:
            return {}

    def broadcast_transaction(
        self, transaction: Transaction, exclude_peers: Optional[List[str]] = None
    ) -> None:
        """Broadcast transaction to network peers."""
        try:
            tx_data = {
                "tx_id": transaction.tx_id,
                "sender": transaction.sender,
                "recipient": transaction.recipient,
                "amount": transaction.amount,
                "timestamp": transaction.timestamp,
                "signature": transaction.signature,
            }
            if hasattr(self.sign_chain, "broadcast_transaction"):
                self.sign_chain.broadcast_transaction(tx_data, exclude_peers)
        except Exception as e:
            logger.warning(f"Error broadcasting transaction: {e}")


class WalletImpl(WalletInterface):
    """
    Concrete implementation of WalletInterface.

    Wraps SignWallet from pisecure.core.wallet_v2 to provide
    interface-compatible wallet operations.
    """

    def __init__(self, sign_wallet: Any):
        """
        Initialize with existing SignWallet instance.

        Args:
            sign_wallet: Instance of pisecure.core.wallet_v2.PiSecureWallet
        """
        self.sign_wallet = sign_wallet

    def get_address(self) -> str:
        """Get the wallet's public address."""
        try:
            return self.sign_wallet.wallet_id
        except Exception:
            return ""

    def get_balance(self) -> float:
        """Get the wallet's current balance."""
        try:
            return self.sign_wallet.get_balance()
        except Exception:
            return 0.0

    def get_public_key(self) -> str:
        """Get the wallet's public key (PEM format)."""
        try:
            return self.sign_wallet.public_key
        except Exception:
            return ""

    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history for this wallet."""
        try:
            if hasattr(self.sign_wallet, "get_transaction_history"):
                return self.sign_wallet.get_transaction_history(limit)
            return []
        except Exception:
            return []

    def sign_transaction(
        self, transaction_request: TransactionRequest
    ) -> Tuple[bool, SignedTransaction | str]:
        """Create and sign a transaction."""
        try:
            # Use wallet's create_token_transfer or similar
            if hasattr(self.sign_wallet, "create_token_transfer"):
                tx = self.sign_wallet.create_token_transfer(
                    transaction_request.recipient, transaction_request.amount
                )
                signed = SignedTransaction(
                    tx_id=tx.get("tx_id", ""),
                    sender=tx.get("sender", ""),
                    recipient=tx.get("recipient", ""),
                    amount=tx.get("amount", 0.0),
                    fee=transaction_request.fee,
                    timestamp=tx.get("timestamp", 0.0),
                    signature=tx.get("signature", ""),
                    raw_data=tx.get("raw_data", b""),
                )
                return (True, signed)
            return (False, "Wallet doesn't support transaction creation")
        except Exception as e:
            return (False, str(e))

    def create_token_transfer(
        self, recipient: str, amount: float
    ) -> Tuple[bool, SignedTransaction | str]:
        """Create a token transfer transaction."""
        req = TransactionRequest(recipient=recipient, amount=amount)
        return self.sign_transaction(req)

    def get_info(self) -> WalletInfo:
        """Get comprehensive wallet information."""
        try:
            return WalletInfo(
                address=self.get_address(),
                balance=self.get_balance(),
                transaction_count=len(self.get_transaction_history(limit=10000)),
                public_key=self.get_public_key(),
            )
        except Exception:
            return WalletInfo(
                address="", balance=0.0, transaction_count=0, public_key=""
            )

    def verify_signature(self, message: str, signature: str, public_key: str) -> bool:
        """Verify a cryptographic signature."""
        try:
            if hasattr(self.sign_wallet, "verify_signature"):
                return self.sign_wallet.verify_signature(message, signature, public_key)
            return False
        except Exception:
            return False

    def backup_key(self, output_path: str) -> Tuple[bool, str]:
        """Backup the private key to a file."""
        try:
            if hasattr(self.sign_wallet, "backup_key"):
                self.sign_wallet.backup_key(output_path)
                return (True, f"Backup saved to {output_path}")
            return (False, "Wallet doesn't support key backup")
        except Exception as e:
            return (False, str(e))

    def restore_key(self, input_path: str) -> Tuple[bool, str]:
        """Restore private key from a file."""
        try:
            if hasattr(self.sign_wallet, "restore_key"):
                self.sign_wallet.restore_key(input_path)
                return (True, "Key restored")
            return (False, "Wallet doesn't support key restoration")
        except Exception as e:
            return (False, str(e))


class NodeImpl(NodeInterface):
    """
    Concrete implementation of NodeInterface.

    Wraps P2PSyncManager and PeerDiscovery to provide
    interface-compatible node operations.
    """

    def __init__(self, p2p_manager: Any):
        """
        Initialize with existing P2PSyncManager instance.

        Args:
            p2p_manager: Instance of pisecure.core.p2p_sync.P2PSyncManager
        """
        self.p2p_manager = p2p_manager
        self.peers = {}

    def get_peer_list(self) -> List[PeerInfo]:
        """Get list of connected peers."""
        try:
            if hasattr(self.p2p_manager, "discovery") and hasattr(
                self.p2p_manager.discovery, "get_connected_peers"
            ):
                peers = self.p2p_manager.discovery.get_connected_peers()
                return [
                    PeerInfo(
                        host=p.get("host", ""),
                        port=p.get("port", 0),
                        node_id=p.get("node_id", ""),
                        version=p.get("version", "1.0.0"),
                        last_seen=p.get("last_seen", 0.0),
                        latency_ms=p.get("latency_ms", 0.0),
                    )
                    for p in peers
                ]
            return []
        except Exception:
            return []

    def connect_peer(self, host: str, port: int) -> Tuple[bool, str]:
        """Connect to a peer."""
        try:
            if hasattr(self.p2p_manager, "connect_peer"):
                result = self.p2p_manager.connect_peer(host, port)
                return (
                    (True, f"Connected to {host}:{port}")
                    if result
                    else (False, "Connection failed")
                )
            return (False, "P2P manager doesn't support connect_peer")
        except Exception as e:
            return (False, str(e))

    def disconnect_peer(self, peer_id: str) -> bool:
        """Disconnect from a peer."""
        try:
            if hasattr(self.p2p_manager, "disconnect_peer"):
                return self.p2p_manager.disconnect_peer(peer_id)
            return False
        except Exception:
            return False

    def sync_with_peers(self) -> Tuple[bool, str]:
        """Synchronize blockchain with peers."""
        try:
            if hasattr(self.p2p_manager, "sync_with_peers"):
                result = self.p2p_manager.sync_with_peers()
                return (True, "Sync complete") if result else (False, "Sync failed")
            return (False, "P2P manager doesn't support sync_with_peers")
        except Exception as e:
            return (False, str(e))

    def get_network_stats(self) -> NetworkStats:
        """Get network statistics."""
        try:
            peers = len(self.get_peer_list())
            return NetworkStats(
                connected_peers=peers,
                pending_transactions=0,
                active_miners=0,
                network_difficulty=0,
                sync_status="unknown",
            )
        except Exception:
            return NetworkStats(0, 0, 0, 0, "error")

    def is_synced(self) -> bool:
        """Check if node is synced with network."""
        try:
            if hasattr(self.p2p_manager, "is_synced"):
                return self.p2p_manager.is_synced()
            return False
        except Exception:
            return False

    def get_sync_progress(self) -> float:
        """Get sync progress as percentage."""
        try:
            if hasattr(self.p2p_manager, "get_sync_progress"):
                return self.p2p_manager.get_sync_progress()
            return 100.0 if self.is_synced() else 0.0
        except Exception:
            return 0.0

    def health_check(self) -> Dict[str, Any]:
        """Get comprehensive health check information."""
        return {
            "is_synced": self.is_synced(),
            "sync_progress": self.get_sync_progress(),
            "peers": self.get_network_stats().connected_peers,
            "status": "healthy" if self.is_synced() else "syncing",
        }

    def broadcast_transaction(self, transaction: Dict[str, Any]) -> None:
        """Broadcast a transaction to the network."""
        try:
            if hasattr(self.p2p_manager, "broadcast_transaction"):
                self.p2p_manager.broadcast_transaction(transaction)
        except Exception as e:
            logger.warning(f"Error broadcasting transaction: {e}")

    def broadcast_block(self, block: Dict[str, Any]) -> None:
        """Broadcast a block to the network."""
        try:
            if hasattr(self.p2p_manager, "broadcast_block"):
                self.p2p_manager.broadcast_block(block)
        except Exception as e:
            logger.warning(f"Error broadcasting block: {e}")

    def discover_peers(self) -> List[Tuple[str, int]]:
        """Discover new peers in the network."""
        try:
            if hasattr(self.p2p_manager, "discover_peers"):
                return self.p2p_manager.discover_peers()
            return []
        except Exception:
            return []


class MiningImpl(MiningInterface):
    """
    Concrete implementation of MiningInterface.

    Wraps SignChain mining methods to provide interface-compatible
    mining operations.
    """

    def __init__(self, sign_chain: Any, miner: Any = None):
        """
        Initialize with existing SignChain instance.

        Args:
            sign_chain: Instance of pisecure.core.blockchain.SignChain
            miner: Optional miner instance (future use)
        """
        self.sign_chain = sign_chain
        self.miner = miner
        self.is_mining_flag = False
        self.blocks_found = 0
        self.hash_attempts = 0

    def start_mining(self, wallet_address: str) -> Tuple[bool, str]:
        """Start mining with rewards to specified wallet."""
        try:
            self.is_mining_flag = True
            if hasattr(self.sign_chain, "start_mining"):
                self.sign_chain.start_mining(wallet_address)
            return (True, f"Mining started for {wallet_address}")
        except Exception as e:
            return (False, str(e))

    def stop_mining(self) -> bool:
        """Stop the mining process."""
        try:
            self.is_mining_flag = False
            if hasattr(self.sign_chain, "stop_mining"):
                self.sign_chain.stop_mining()
            return True
        except Exception:
            return False

    def is_mining(self) -> bool:
        """Check if mining is currently active."""
        return self.is_mining_flag

    def mine_block(self, wallet_address: str) -> MiningResult:
        """Mine a single block synchronously."""
        try:
            if hasattr(self.sign_chain, "mine_pending_transactions"):
                block = self.sign_chain.mine_pending_transactions(wallet_address)
                if block:
                    self.blocks_found += 1
                    return MiningResult(
                        success=True,
                        block=block,
                        hash_attempts=self.hash_attempts,
                    )
            return MiningResult(
                success=False, block=None, error_message="Mining failed"
            )
        except Exception as e:
            return MiningResult(success=False, block=None, error_message=str(e))

    def get_mining_stats(self) -> MiningStats:
        """Get comprehensive mining statistics."""
        return MiningStats(
            is_mining=self.is_mining(),
            blocks_found=self.blocks_found,
            hash_rate=0.0,  # To be calculated
            current_difficulty=self.get_difficulty(),
            average_block_time=0.0,
            uptime_seconds=0.0,
        )

    def set_difficulty(self, difficulty: int) -> bool:
        """Set the mining difficulty."""
        try:
            self.sign_chain.difficulty = difficulty
            return True
        except Exception:
            return False

    def get_difficulty(self) -> int:
        """Get the current mining difficulty."""
        try:
            return self.sign_chain.difficulty
        except Exception:
            return 4

    def verify_hardware(self) -> Tuple[bool, str]:
        """Verify hardware meets mining requirements."""
        try:
            if hasattr(self.sign_chain, "verify_hardware"):
                result = self.sign_chain.verify_hardware()
                return (
                    (result, "") if result else (False, "Hardware verification failed")
                )
            return (True, "Hardware verification skipped")
        except Exception as e:
            return (False, str(e))

    def get_hash_rate(self) -> float:
        """Get current hash rate in hashes per second."""
        return 0.0  # To be calculated

    def estimate_time_to_block(self) -> float:
        """Estimate time to find next block (in seconds)."""
        return 60.0  # Default estimate
