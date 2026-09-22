"""
Config - Shared configuration and constants

Centralized configuration for PiSecure.
"""

import os
from dataclasses import dataclass
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    """PiSecure configuration."""

    # Directories
    DATA_DIR: str = os.getenv("PISECURE_DATA_DIR", "/var/lib/pisecure")
    CONFIG_DIR: str = os.getenv("PISECURE_CONFIG_DIR", "/etc/pisecure")
    BLOCKCHAIN_FILE: str = os.path.join(DATA_DIR, "blockchain.json")
    PENDING_TXS_FILE: str = os.path.join(DATA_DIR, "pending_transactions.json")

    # Testnet
    TESTNET: bool = _env_bool("PISECURE_TESTNET", False)
    TESTNET_DATA_DIR: str = os.path.join(DATA_DIR, "testnet")
    TESTNET_BLOCKCHAIN_FILE: str = os.path.join(TESTNET_DATA_DIR, "blockchain.json")
    TESTNET_PENDING_TXS_FILE: str = os.path.join(
        TESTNET_DATA_DIR, "pending_transactions.json"
    )

    # Modes
    VALIDATE_ONLY: bool = _env_bool("PISECURE_VALIDATE_ONLY", False)
    # Env cannot turn this on. The CLI rejects PISECURE_MOCK_HARDWARE.
    MOCK_HARDWARE: bool = False
    QUIET: bool = _env_bool("PISECURE_QUIET", False)

    # Storage
    USE_HYBRID_STORAGE: bool = not _env_bool("PISECURE_NO_HYBRID_STORAGE", False)
    HYBRID_STORAGE_DIR: str = os.path.join(DATA_DIR, "hybrid")
    HYBRID_BLOCKS_PER_FILE: int = 1000
    HYBRID_DB_FILE: str = os.path.join(HYBRID_STORAGE_DIR, "index.db")

    # Mining
    # 0.2 314ST. Miner gets this minus the validator 1%. Difficulty stays in 2–4.
    MINE_BLOCK_REWARD: float = 0.2
    MINE_INITIAL_DIFFICULTY: int = 4
    MINE_DIFFICULTY_ADJUSTMENT: float = 1.0
    MINE_TARGET_BLOCK_TIME: float = 60.0
    MINE_TIMEOUT: float = 300.0

    # Validator Rewards
    VALIDATOR_REWARDS_ENABLED: bool = True
    VALIDATOR_REWARDS_PERCENTAGE: float = 0.01
    VALIDATOR_REWARDS_MAX_PERCENTAGE: float = 0.05
    VALIDATOR_MIN_CONFIRMATIONS: int = 5
    VALIDATOR_WALLET_ADDRESS: str = os.getenv("PISECURE_VALIDATOR_WALLET", "")

    # Consensus
    CONSENSUS_BLOCK_SIZE_LIMIT: int = 1000000
    CONSENSUS_TX_SIZE_LIMIT: int = 100000
    CONSENSUS_MAX_TX_PER_BLOCK: int = 1000
    CONSENSUS_MIN_TX_FEE: float = 0.001

    # Wallet
    WALLET_DEFAULT_FEE: float = 0.001
    WALLET_MIN_AMOUNT: float = 0.00001

    # Network
    NETWORK_PEER_TIMEOUT: float = 30.0
    NETWORK_SYNC_TIMEOUT: float = 300.0
    NETWORK_BOOTSTRAP_PEERS: Optional[list] = None
    NETWORK_MAX_PEERS: int = 50
    NETWORK_DEFAULT_PORT: int = 3142
    BOOTSTRAP_URL: str = os.getenv(
        "PISECURE_BOOTSTRAP_URL", "https://bootstrap.pisecure.org"
    )

    # API
    API_HOST: str = os.getenv("PISECURE_API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PISECURE_API_PORT", "3142"))
    API_ENABLE_CORS: bool = True
    API_RATE_LIMIT: int = 100

    # Logging
    LOG_LEVEL: str = os.getenv("PISECURE_LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def get_blockchain_file(cls) -> str:
        if cls.TESTNET:
            return cls.TESTNET_BLOCKCHAIN_FILE
        return cls.BLOCKCHAIN_FILE

    @classmethod
    def get_pending_txs_file(cls) -> str:
        if cls.TESTNET:
            return cls.TESTNET_PENDING_TXS_FILE
        return cls.PENDING_TXS_FILE

    @classmethod
    def get_data_dir(cls) -> str:
        if cls.TESTNET:
            return cls.TESTNET_DATA_DIR
        return cls.DATA_DIR

    @classmethod
    def get_mode_string(cls) -> str:
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
