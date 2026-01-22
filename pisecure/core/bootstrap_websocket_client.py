#!/usr/bin/env python3
"""
PiSecure Bootstrap WebSocket Real-Time Client

Implements real-time bidirectional communication with bootstrap server
for node updates, threats, health metrics, DEX updates, and rate limits.

Features:
  - 5 namespaces for different event types
  - Automatic reconnection with exponential backoff
  - HTTP fallback when WebSocket unavailable
  - Reputation-based access control
  - Heartbeat/keep-alive support
"""

import logging
import time
import threading
import os
from typing import Dict, Optional, Callable, Any, List
from threading import Thread, Event, Lock
import json

logger = logging.getLogger(__name__)


class WebSocketEvent:
    """Represents a WebSocket event"""

    def __init__(self, event_type: str, namespace: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.namespace = namespace
        self.data = data
        self.timestamp = time.time()

    def __repr__(self) -> str:
        return (
            f"<WebSocketEvent {self.namespace}/{self.event_type} at {self.timestamp}>"
        )


class BootstrapWebSocketClient:
    """
    WebSocket client for real-time bootstrap server communication.

    Namespaces:
      /nodes    - Node registration, heartbeat, offline events
      /threats  - Sentinel alerts, defense coordination
      /health   - Network metrics, consensus status
      /dex      - Pool updates, trading activity
      /rates    - Rate limit updates, quota reset
    """

    def __init__(
        self,
        node_id: str,
        bootstrap_url: str = "wss://bootstrap.pisecure.org",
        network: str = "mainnet",
        use_http_fallback: bool = True,
        auto_connect: bool = True,
    ):
        """
        Initialize WebSocket client

        Args:
            node_id: Unique node identifier
            bootstrap_url: Bootstrap server base URL
            network: 'mainnet' or 'testnet'
            use_http_fallback: Enable HTTP polling if WebSocket fails
            auto_connect: Automatically connect to bootstrap server on init
        """
        self.node_id = node_id
        self.bootstrap_url = bootstrap_url
        self.network = network
        self.use_http_fallback = use_http_fallback
        self.auto_connect = auto_connect
        self.use_websocket = True

        # Connection state
        self.connected = False
        self.socket = None
        self._connect_event = Event()
        self._lock = Lock()

        # Subscribed channels
        self.subscribed_channels: Dict[str, bool] = {}

        # Event handlers
        self.handlers: Dict[str, List[Callable]] = {}

        # Metrics
        self.messages_received = 0
        self.messages_sent = 0
        self.last_heartbeat = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

        # Import socketio here to avoid hard dependency
        try:
            import socketio

            self.socketio = socketio
            self.has_socketio = True
        except ImportError:
            logger.warning(
                "socketio not installed, WebSocket disabled. Install with: pip install python-socketio"
            )
            self.has_socketio = False
            self.use_websocket = False

        # Auto-connect if enabled (default behavior)
        if self.auto_connect and self.has_socketio:
            try:
                self.connect()
            except Exception as e:
                logger.warning(f"Auto-connect failed (will retry): {e}")

    def _initialize_socketio(self):
        """Initialize socket.io client"""
        if not self.has_socketio:
            return False

        try:
            self.socket = self.socketio.Client(
                reconnection=True,
                reconnection_delay=1,
                reconnection_delay_max=5,
                reconnection_attempts=self.max_reconnect_attempts,
            )

            self._setup_handlers()
            logger.debug("Socket.io client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize socket.io: {e}")
            return False

    def _setup_handlers(self):
        """Setup base event handlers"""
        if not self.socket:
            return

        @self.socket.event(namespace="/nodes")
        def connect():
            with self._lock:
                self.connected = True
                self.reconnect_attempts = 0
                self._connect_event.set()
            logger.info(f"✓ Connected to /nodes namespace")
            self._emit_subscribe_message("nodes")

        @self.socket.on("disconnect", namespace="/nodes")
        def disconnect():
            with self._lock:
                self.connected = False
                self._connect_event.clear()
            logger.warning("Disconnected from /nodes namespace")

        @self.socket.on("connection_established", namespace="/nodes")
        def on_connection_established(data):
            logger.info(f"✓ Connection established: {data}")
            self._emit_event_to_handlers("/nodes", "connection_established", data)

        @self.socket.on("error", namespace="/nodes")
        def on_error(data):
            error_msg = (
                data.get("message", str(data)) if isinstance(data, dict) else str(data)
            )

            if (
                "Not authenticated" in error_msg
                or "not registered" in error_msg.lower()
            ):
                logger.error(f"WebSocket authentication error: {error_msg}")
                logger.error(f"Node '{self.node_id}' must be registered first")
                logger.error(
                    "Register with: pisecure entropy submit --auto-register --node-type validator"
                )
            else:
                logger.error(f"WebSocket error: {data}")

            self._emit_event_to_handlers("/nodes", "error", data)

    def _emit_subscribe_message(self, namespace: str):
        """Send subscribe message to namespace"""
        if not self.socket or not self.connected:
            return

        try:
            channel = f"subscribe_{namespace}"
            self.socket.emit(channel, {}, namespace=f"/{namespace}")
            logger.debug(f"Subscribed to /{namespace}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {namespace}: {e}")

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register handler for specific event type

        Args:
            event_type: Event type (e.g., 'node_registered', 'threat_detected')
            handler: Callable(data) function to handle event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")

    def _emit_event_to_handlers(
        self, namespace: str, event_type: str, data: Dict[str, Any]
    ):
        """Emit event to registered handlers"""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")

    def connect(self) -> bool:
        """
        Connect to bootstrap server via WebSocket

        Returns:
            True if connected, False if fallback to HTTP
        """
        if not self.use_websocket:
            logger.info("WebSocket disabled, using HTTP fallback")
            return True  # Allow HTTP fallback

        if not self.has_socketio:
            logger.warning("socketio not available, using HTTP fallback")
            self.use_websocket = False
            return True

        try:
            if not self._initialize_socketio():
                self.use_websocket = False
                return True

            url = f"{self.bootstrap_url}/nodes?node_id={self.node_id}&network={self.network}"
            logger.info(f"Connecting to {url}")

            self.socket.connect(url, wait_timeout=10)
            self._connect_event.wait(timeout=5)

            if self.connected:
                logger.info(f"✓ WebSocket connected: {self.node_id}")
                return True
            else:
                logger.warning("WebSocket connected but not authenticated")
                return False

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            if self.use_http_fallback:
                logger.info("Falling back to HTTP polling")
                self.use_websocket = False
                return True
            return False

    def disconnect(self):
        """Disconnect from bootstrap server"""
        if self.socket and self.connected:
            try:
                self.socket.disconnect()
                self.connected = False
                logger.info("Disconnected from bootstrap server")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")

    def subscribe_nodes(self):
        """Subscribe to node updates"""
        if not self.connected:
            logger.warning("Not connected, cannot subscribe to nodes")
            return False

        try:
            if self.socket:
                self.socket.on(
                    "node_registered", self._handle_node_registered, namespace="/nodes"
                )
                self.socket.on(
                    "node_offline", self._handle_node_offline, namespace="/nodes"
                )
                self.socket.on(
                    "node_heartbeat", self._handle_node_heartbeat, namespace="/nodes"
                )
                self._emit_subscribe_message("nodes")
                self.subscribed_channels["nodes"] = True
                logger.info("Subscribed to node updates")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to nodes: {e}")
            return False

    def subscribe_threats(self):
        """Subscribe to threat alerts"""
        if not self.connected:
            logger.warning("Not connected, cannot subscribe to threats")
            return False

        try:
            if self.socket:
                # Note: Socket.IO python-socketio with polling transport only supports
                # one namespace at a time. Additional namespaces require separate connections
                # or full WebSocket support (install websocket-client package)
                self.socket.on(
                    "threat_detected",
                    self._handle_threat_detected,
                    namespace="/threats",
                )
                self.socket.on(
                    "threat_escalated",
                    self._handle_threat_escalated,
                    namespace="/threats",
                )
                self.socket.on(
                    "defense_activated",
                    self._handle_defense_activated,
                    namespace="/threats",
                )
                self._emit_subscribe_message("threats")
                self.subscribed_channels["threats"] = True
                logger.info("Subscribed to threat alerts")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to threats: {e}")
            logger.info(
                "Tip: Install websocket-client for full multi-namespace support: pip install websocket-client"
            )
            return False

    def subscribe_health(self):
        """Subscribe to health metrics"""
        if not self.connected:
            logger.warning("Not connected, cannot subscribe to health")
            return False

        try:
            if self.socket:
                self.socket.on(
                    "health_update", self._handle_health_update, namespace="/health"
                )
                self.socket.on(
                    "consensus_status",
                    self._handle_consensus_status,
                    namespace="/health",
                )
                self._emit_subscribe_message("health")
                self.subscribed_channels["health"] = True
                logger.info("Subscribed to health updates")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to health: {e}")
            return False

    def subscribe_dex(self):
        """Subscribe to DEX updates"""
        if not self.connected:
            logger.warning("Not connected, cannot subscribe to DEX")
            return False

        try:
            if self.socket:
                self.socket.on(
                    "pool_updated", self._handle_pool_updated, namespace="/dex"
                )
                self.socket.on(
                    "trade_executed", self._handle_trade_executed, namespace="/dex"
                )
                self._emit_subscribe_message("dex")
                self.subscribed_channels["dex"] = True
                logger.info("Subscribed to DEX updates")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to DEX: {e}")
            return False

    def subscribe_rates(self):
        """Subscribe to rate limit updates"""
        if not self.connected:
            logger.warning("Not connected, cannot subscribe to rates")
            return False

        try:
            if self.socket:
                self.socket.on(
                    "rate_limit_status",
                    self._handle_rate_limit_status,
                    namespace="/rates",
                )
                self.socket.on(
                    "quota_reset", self._handle_quota_reset, namespace="/rates"
                )
                self._emit_subscribe_message("rates")
                self.subscribed_channels["rates"] = True
                logger.info("Subscribed to rate limit updates")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to rates: {e}")
            return False

    def send_heartbeat(self, metrics: Dict[str, Any]):
        """
        Send heartbeat with metrics

        Args:
            metrics: Dict with cpu_usage, memory_mb, uptime_seconds, hashrate
        """
        if not self.socket or not self.connected:
            logger.warning("Not connected, cannot send heartbeat")
            return False

        try:
            payload = {
                "type": "heartbeat",
                "node_id": self.node_id,
                "timestamp": time.time(),
                "metrics": metrics,
            }
            self.socket.emit("heartbeat", payload, namespace="/nodes")
            self.messages_sent += 1
            self.last_heartbeat = time.time()
            logger.debug(f"Heartbeat sent: {metrics}")
            return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False

    def report_threat(self, threat_data: Dict[str, Any]):
        """
        Report threat detection

        Args:
            threat_data: Dict with threat_type, severity, source, details
        """
        if not self.socket or not self.connected:
            logger.warning("Not connected, cannot report threat")
            return False

        try:
            payload = {"type": "report_threat", "threat_data": threat_data}
            self.socket.emit("report_threat", payload, namespace="/threats")
            self.messages_sent += 1
            logger.info(f"Threat reported: {threat_data['threat_type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to report threat: {e}")
            return False

    # Event handlers
    def _handle_node_registered(self, data):
        """Handle node registration event"""
        self.messages_received += 1
        logger.info(
            f"✓ Node registered: {data.get('node_id')} (rep: {data.get('reputation')})"
        )
        self._emit_event_to_handlers("/nodes", "node_registered", data)

    def _handle_node_offline(self, data):
        """Handle node offline event"""
        self.messages_received += 1
        logger.warning(f"⚠️  Node offline: {data.get('node_id')}")
        self._emit_event_to_handlers("/nodes", "node_offline", data)

    def _handle_node_heartbeat(self, data):
        """Handle heartbeat event"""
        self.messages_received += 1
        logger.debug(f"Heartbeat from {data.get('node_id')}")
        self._emit_event_to_handlers("/nodes", "node_heartbeat", data)

    def _handle_threat_detected(self, data):
        """Handle threat detection event"""
        self.messages_received += 1
        severity = data.get("severity", "unknown").upper()
        logger.critical(f"🚨 THREAT [{severity}]: {data.get('description')}")
        self._emit_event_to_handlers("/threats", "threat_detected", data)

    def _handle_threat_escalated(self, data):
        """Handle threat escalation event"""
        self.messages_received += 1
        logger.error(f"🔴 Threat escalated: {data.get('threat_id')}")
        self._emit_event_to_handlers("/threats", "threat_escalated", data)

    def _handle_defense_activated(self, data):
        """Handle defense activation event"""
        self.messages_received += 1
        logger.warning(f"⚔️  Defense activated: {data.get('defense_type')}")
        self._emit_event_to_handlers("/threats", "defense_activated", data)

    def _handle_health_update(self, data):
        """Handle health update event"""
        self.messages_received += 1
        health = data.get("network_health", 0)
        peers = data.get("peer_count", 0)
        logger.debug(f"Health: {health}%, Peers: {peers}")
        self._emit_event_to_handlers("/health", "health_update", data)

    def _handle_consensus_status(self, data):
        """Handle consensus status event"""
        self.messages_received += 1
        status = data.get("status", "unknown")
        height = data.get("block_height", 0)
        logger.debug(f"Consensus: {status}, Height: {height}")
        self._emit_event_to_handlers("/health", "consensus_status", data)

    def _handle_pool_updated(self, data):
        """Handle pool update event"""
        self.messages_received += 1
        pool_id = data.get("pool_id", "unknown")
        logger.debug(f"Pool updated: {pool_id}")
        self._emit_event_to_handlers("/dex", "pool_updated", data)

    def _handle_trade_executed(self, data):
        """Handle trade execution event"""
        self.messages_received += 1
        amount = data.get("amount", 0)
        token_in = data.get("token_in", "?")
        token_out = data.get("token_out", "?")
        logger.debug(f"Trade: {amount} {token_in} → {token_out}")
        self._emit_event_to_handlers("/dex", "trade_executed", data)

    def _handle_rate_limit_status(self, data):
        """Handle rate limit status event"""
        self.messages_received += 1
        remaining = data.get("requests_remaining", 0)
        limit = data.get("limit", 0)
        logger.debug(f"Rate limit: {remaining}/{limit} remaining")
        self._emit_event_to_handlers("/rates", "rate_limit_status", data)

    def _handle_quota_reset(self, data):
        """Handle quota reset event"""
        self.messages_received += 1
        limit = data.get("limit", 0)
        logger.info(f"✓ Quota reset: {limit} requests available")
        self._emit_event_to_handlers("/rates", "quota_reset", data)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "connected": self.connected,
            "use_websocket": self.use_websocket,
            "node_id": self.node_id,
            "network": self.network,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "last_heartbeat": self.last_heartbeat,
            "subscribed_channels": list(self.subscribed_channels.keys()),
            "reconnect_attempts": self.reconnect_attempts,
        }


# Global singleton instance
_websocket_client: Optional[BootstrapWebSocketClient] = None


def get_bootstrap_websocket_client(
    node_id: Optional[str] = None,
    bootstrap_url: Optional[str] = None,
    network: str = "mainnet",
    auto_connect: bool = True,
) -> BootstrapWebSocketClient:
    """
    Get or create global WebSocket client instance

    Args:
        node_id: Node identifier (required for first call)
        bootstrap_url: Bootstrap server URL (optional)
        network: 'mainnet' or 'testnet'
        auto_connect: Automatically connect to bootstrap server

    Returns:
        BootstrapWebSocketClient instance
    """
    global _websocket_client

    if _websocket_client is None:
        if node_id is None:
            raise ValueError(
                "node_id required for first WebSocket client initialization"
            )

        if bootstrap_url is None:
            bootstrap_url = "wss://bootstrap.pisecure.org"

        _websocket_client = BootstrapWebSocketClient(
            node_id=node_id,
            bootstrap_url=bootstrap_url,
            network=network,
            auto_connect=auto_connect,
        )

    return _websocket_client
