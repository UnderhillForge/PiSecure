"""
NodeContext - Centralized node state container

Instead of scattered globals and implicit dependencies, NodeContext bundles
all node services and is passed explicitly where needed.

This pattern enables:
- Testable code (can mock context)
- Multiple node instances (each with its own context)
- Clear dependencies (services bundled together)
- Easier threading (pass context to threads)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, List
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class NodeContext:
    """
    Centralized container for all node services.

    Instead of:
        blockchain = get_blockchain()  # global
        wallet = get_wallet()           # global
        miner = get_miner()             # global

    Use:
        ctx = NodeContext(...)
        ctx.blockchain
        ctx.wallet
        ctx.miner
    """

    # Core services
    blockchain: Any = None  # ChainInterface
    wallet: Optional[Any] = None  # WalletInterface
    miner: Optional[Any] = None  # MiningInterface
    node: Optional[Any] = None  # NodeInterface
    storage: Optional[Any] = None  # StorageInterface
    scheduler: Optional[Any] = None  # Scheduler service

    # Configuration
    testnet: bool = False
    validate_only: bool = False
    mock_hardware: bool = False
    quiet: bool = False
    data_dir: str = "/var/lib/pisecure"
    config_dir: str = "/etc/pisecure"

    # Runtime state
    is_running: bool = False
    is_synced: bool = False
    peers: Dict[str, Any] = field(default_factory=dict)
    pending_transactions: list = field(default_factory=list)

    # Callbacks and hooks
    hooks: Dict[str, list] = field(default_factory=dict)  # Hook name -> [callbacks]

    # Threading/synchronization
    lock: Lock = field(default_factory=Lock)
    _shutdown_handlers: List[Callable] = field(default_factory=list)

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default hook categories."""
        self.hooks = {
            "blockchain.new_block": [],
            "blockchain.new_transaction": [],
            "node.peer_connected": [],
            "node.peer_disconnected": [],
            "miner.block_found": [],
            "wallet.transaction_signed": [],
            "node.sync_started": [],
            "node.sync_completed": [],
            "node.shutdown_started": [],
            "node.shutdown_completed": [],
        }

    def register_hook(self, event_name: str, callback: Callable) -> None:
        """Register a callback for an event."""
        with self.lock:
            if event_name not in self.hooks:
                self.hooks[event_name] = []
            self.hooks[event_name].append(callback)
            logger.debug(f"Registered hook: {event_name}")

    def trigger_hook(self, event_name: str, *args, **kwargs) -> None:
        """Trigger all callbacks for an event."""
        with self.lock:
            callbacks = self.hooks.get(event_name, [])

        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook {event_name} error: {e}")

    def set_metric(self, name: str, value: Any) -> None:
        """Set a metric value."""
        with self.lock:
            self.metrics[name] = value

    def get_metric(self, name: str, default: Any = None) -> Any:
        """Get a metric value."""
        with self.lock:
            return self.metrics.get(name, default)

    def start(self) -> None:
        """Mark node as running."""
        with self.lock:
            self.is_running = True
            logger.info("NodeContext started")

        # Start scheduler if attached
        if self.scheduler and hasattr(self.scheduler, "start"):
            try:
                self.scheduler.start()
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to start scheduler: %s", exc)

    def stop(self) -> None:
        """Mark node as stopped."""
        with self.lock:
            self.is_running = False
            logger.info("NodeContext stopped")

        # Stop scheduler when stopping node
        try:
            if self.scheduler and hasattr(self.scheduler, "stop"):
                self.scheduler.stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to stop scheduler: %s", exc)

    def shutdown(self) -> None:
        """
        Gracefully shutdown all services.

        Calls shutdown handlers, stops scheduler if attached, then stops node.
        """
        logger.info("NodeContext shutdown initiated")
        errors: List[str] = []

        self.trigger_hook("node.shutdown_started", self)

        # Invoke registered shutdown handlers
        for handler in list(self._shutdown_handlers):
            try:
                handler(self)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                logger.error("Shutdown handler error: %s", exc)

        # Stop scheduler if present
        try:
            if self.scheduler and hasattr(self.scheduler, "stop"):
                self.scheduler.stop()
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            logger.error("Error stopping scheduler: %s", exc)

        self.stop()
        self.trigger_hook("node.shutdown_completed", self)

        if errors:
            logger.warning("Shutdown completed with %d error(s)", len(errors))
        else:
            logger.info("NodeContext shutdown complete")

    def register_shutdown_handler(self, handler: Callable) -> None:
        """Register a shutdown handler (called on graceful shutdown)."""
        self._shutdown_handlers.append(handler)

    def attach_scheduler(self, scheduler: Any) -> None:
        """Attach a scheduler to coordinate background tasks."""
        self.scheduler = scheduler

    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive context information."""
        with self.lock:
            return {
                "is_running": self.is_running,
                "is_synced": self.is_synced,
                "testnet": self.testnet,
                "validate_only": self.validate_only,
                "mock_hardware": self.mock_hardware,
                "peers_count": len(self.peers),
                "pending_transactions": len(self.pending_transactions),
                "metrics": dict(self.metrics),
                "hooks_registered": {k: len(v) for k, v in self.hooks.items()},
            }
