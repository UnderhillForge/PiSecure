"""
Config - Shared configuration and constants

Centralized configuration for PiSecure.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """PiSecure configuration."""

    # Directories
    DATA_DIR: str = os.getenv("PISECURE_DATA_DIR", "/var/lib/pisecure")
    CONFIG_DIR: str = os.getenv("PISECURE_CONFIG_DIR", "/etc/pisecure")
    BLOCKCHAIN_FILE: str = os.path.join(DATA_DIR, "blockchain.json")
    PENDING_TXS_FILE: str = os.path.join(DATA_DIR, "pending_transactions.json")

    # Testnet
    TESTNET: bool = bool(os.getenv("PISECURE_TESTNET", False))
    TESTNET_DATA_DIR: str = os.path.join(DATA_DIR, "testnet")
    TESTNET_BLOCKCHAIN_FILE: str = os.path.join(TESTNET_DATA_DIR, "blockchain.json")
    TESTNET_PENDING_TXS_FILE: str = os.path.join(
        TESTNET_DATA_DIR, "pending_transactions.json"
    )

    # Modes
    VALIDATE_ONLY: bool = bool(os.getenv("PISECURE_VALIDATE_ONLY", False))
    MOCK_HARDWARE: bool = bool(os.getenv("PISECURE_MOCK_HARDWARE", False))
    QUIET: bool = bool(os.getenv("PISECURE_QUIET", False))

    # Storage
    USE_HYBRID_STORAGE: bool = not bool(os.getenv("PISECURE_NO_HYBRID_STORAGE", False))
    HYBRID_STORAGE_DIR: str = os.path.join(DATA_DIR, "hybrid")
    HYBRID_BLOCKS_PER_FILE: int = 1000  # CCoinsView-like batching
    HYBRID_DB_FILE: str = os.path.join(HYBRID_STORAGE_DIR, "index.db")

    # Mining
    MINE_BLOCK_REWARD: float = 50.0
    MINE_INITIAL_DIFFICULTY: int = 4  # 4 leading zero bits
    MINE_DIFFICULTY_ADJUSTMENT: float = 1.0
    MINE_TARGET_BLOCK_TIME: float = 60.0  # 60 seconds between blocks
    MINE_TIMEOUT: float = 300.0  # 5 minute mining timeout

    # Validator Rewards
    VALIDATOR_REWARDS_ENABLED: bool = True
    VALIDATOR_REWARDS_PERCENTAGE: float = (
        0.01  # 1% of block reward distributed among validators
    )
    VALIDATOR_REWARDS_MAX_PERCENTAGE: float = 0.05  # Network maximum (5%)
    VALIDATOR_MIN_CONFIRMATIONS: int = 5  # Minimum validators for instant confirmation
    VALIDATOR_WALLET_ADDRESS: str = ""  # Optional: wallet to link rewards to

    # Consensus
    CONSENSUS_BLOCK_SIZE_LIMIT: int = 1000000  # 1 MB
    CONSENSUS_TX_SIZE_LIMIT: int = 100000  # 100 KB
    CONSENSUS_MAX_TX_PER_BLOCK: int = 1000
    CONSENSUS_MIN_TX_FEE: float = 0.001

    # Wallet
    WALLET_DEFAULT_FEE: float = 0.001
    WALLET_MIN_AMOUNT: float = 0.00001

    # Network
    NETWORK_PEER_TIMEOUT: float = 30.0  # seconds
    NETWORK_SYNC_TIMEOUT: float = 300.0  # seconds
    NETWORK_BOOTSTRAP_PEERS: list = None  # Populated from config/peers.json
    NETWORK_MAX_PEERS: int = 50
    NETWORK_DEFAULT_PORT: int = 3142

    # API
    API_HOST: str = os.getenv("PISECURE_API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PISECURE_API_PORT", "3142"))
    API_ENABLE_CORS: bool = True
    API_RATE_LIMIT: int = 100  # requests per minute

    # Logging
    LOG_LEVEL: str = os.getenv("PISECURE_LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def get_blockchain_file(cls) -> str:
        """Get blockchain file path based on testnet setting."""
        if cls.TESTNET:
            return cls.TESTNET_BLOCKCHAIN_FILE
        return cls.BLOCKCHAIN_FILE

    @classmethod
    def get_pending_txs_file(cls) -> str:
        """Get pending transactions file path based on testnet setting."""
        if cls.TESTNET:
            return cls.TESTNET_PENDING_TXS_FILE
        return cls.PENDING_TXS_FILE

    @classmethod
    def get_data_dir(cls) -> str:
        """Get data directory path based on testnet setting."""
        if cls.TESTNET:
            return cls.TESTNET_DATA_DIR
        return cls.DATA_DIR

    @classmethod
    def get_mode_string(cls) -> str:
        """Get a string describing the current configuration mode."""
        modes = []
        if cls.TESTNET:
            modes.append("testnet")
        if cls.VALIDATE_ONLY:
            modes.append("validate-only")
        if cls.MOCK_HARDWARE:
            modes.append("mock-hardware")
        if cls.QUIET:
            modes.append("quiet")
        return ",".join(modes) if modes else "mainnet"
