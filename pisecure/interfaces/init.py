"""
InitFactory - Service initialization pattern

Enables different initialization configurations (full node, validator, CLI, testing)
without hardcoding startup logic. Each mode can initialize only needed components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class InitConfig:
    """Configuration for service initialization."""

    mode: str  # 'full_node', 'validator', 'cli', 'testing', 'api'
    testnet: bool = False
    quiet: bool = False
    validate_only: bool = False
    mock_hardware: bool = False
    data_dir: Optional[str] = None
    config_dir: Optional[str] = None
    extra_options: Optional[Dict[str, Any]] = None


class InitFactory(ABC):
    """
    Abstract factory for service initialization.

    Enables different initialization modes:
    - full_node: Complete node with mining (needs blockchain + wallet + mining)
    - validator: Validation only (needs blockchain only)
    - cli: Command-line interface (needs blockchain + wallet + mining + API)
    - api: REST API server (needs blockchain + wallet)
    - testing: Unit testing (mocked services)

    Key principle: Choose what to initialize based on mode.
    """

    @abstractmethod
    def create_blockchain(self, config: InitConfig) -> Any:
        """Create and initialize blockchain service."""
        pass

    @abstractmethod
    def create_wallet(self, config: InitConfig) -> Any:
        """Create and initialize wallet service."""
        pass

    @abstractmethod
    def create_miner(self, config: InitConfig) -> Any:
        """Create and initialize mining service."""
        pass

    @abstractmethod
    def create_node(self, config: InitConfig) -> Any:
        """Create and initialize node service."""
        pass

    @abstractmethod
    def create_storage(self, config: InitConfig) -> Any:
        """Create and initialize storage service."""
        pass

    @abstractmethod
    def initialize_all(self, config: InitConfig) -> Dict[str, Any]:
        """
        Initialize all services for a given mode.

        Returns dictionary with services like:
        {
            'blockchain': ChainInterface,
            'wallet': WalletInterface,
            'miner': MiningInterface,
            'node': NodeInterface,
            'storage': StorageInterface,
        }
        """
        pass

    @abstractmethod
    def shutdown_all(self, services: Dict[str, Any]) -> None:
        """Gracefully shutdown all services."""
        pass
