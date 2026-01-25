"""
Background task registration for NodeContext.

Provides lightweight periodic tasks:
- Peer sync (if node service provides sync_with_peers)
- Chain metrics collection (if blockchain provides get_chain_info)
"""

from __future__ import annotations

import time
from typing import Optional

from pisecure.common.config import Config


def register_default_tasks(
    ctx,
    *,
    metrics_interval: float = 5.0,
    sync_interval: float = 15.0,
) -> bool:
    """Attach default background tasks to the context scheduler.

    Returns True if tasks were registered, False otherwise.
    """
    scheduler = getattr(ctx, "scheduler", None)
    if not scheduler:
        return False

    # Track uptime
    start_time = time.time()

    def collect_metrics():
        blockchain = getattr(ctx, "blockchain", None)
        if blockchain and hasattr(blockchain, "get_chain_info"):
            try:
                info = blockchain.get_chain_info()
                ctx.set_metric("blocks", info.get("blocks", 0))
                ctx.set_metric("pending_tx", info.get("pending_transactions", 0))
                ctx.set_metric("difficulty", info.get("difficulty", 0))

                latest = info.get("latest_block") or {}
                ctx.set_metric("height", latest.get("index", info.get("blocks", 0)))

                health = info.get("network_health") or {}
                ctx.set_metric("network_health_score", health.get("health_score"))
                ctx.set_metric("network_participation", health.get("participation"))
                ctx.set_metric("avg_block_time", health.get("avg_block_time"))
            except Exception as exc:  # noqa: BLE001
                ctx.set_metric("metrics_error", str(exc))
        ctx.set_metric("uptime_seconds", time.time() - start_time)
        ctx.set_metric("mode", Config.get_mode_string())

    def sync_peers():
        node = getattr(ctx, "node", None)
        if not node:
            return

        # Peer discovery / sync
        if hasattr(node, "sync_with_peers"):
            try:
                ok, msg = node.sync_with_peers()
                ctx.set_metric("last_sync_ok", bool(ok))
                if not ok and msg:
                    ctx.set_metric("last_sync_error", msg)
            except Exception as exc:  # noqa: BLE001
                ctx.set_metric("last_sync_ok", False)
                ctx.set_metric("last_sync_error", str(exc))

        # Peer stats
        if hasattr(node, "get_peer_list"):
            try:
                peers = node.get_peer_list() or []
                ctx.peers = {f"peer_{i}": p for i, p in enumerate(peers)}
                ctx.set_metric("peers", len(peers))
            except Exception as exc:  # noqa: BLE001
                ctx.set_metric("peers_error", str(exc))

        # Network stats
        if hasattr(node, "get_network_stats"):
            try:
                stats = node.get_network_stats()
                ctx.set_metric("network_pending_tx", stats.pending_transactions)
                ctx.set_metric("network_difficulty", stats.network_difficulty)
                ctx.set_metric("network_sync_status", stats.sync_status)
            except Exception as exc:  # noqa: BLE001
                ctx.set_metric("network_stats_error", str(exc))

        if hasattr(node, "is_synced"):
            try:
                ctx.is_synced = bool(node.is_synced())
                ctx.set_metric("is_synced", ctx.is_synced)
            except Exception as exc:  # noqa: BLE001
                ctx.set_metric("is_synced_error", str(exc))

    scheduler.add_interval_task(
        "metrics.collect",
        interval_seconds=metrics_interval,
        func=collect_metrics,
        run_immediately=True,
    )
    scheduler.add_interval_task(
        "peers.sync", interval_seconds=sync_interval, func=sync_peers, initial_delay=5.0
    )
    return True
