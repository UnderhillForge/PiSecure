import time

from pisecure.node.context import NodeContext
from pisecure.node.tasks import register_default_tasks


class DummyScheduler:
    def __init__(self):
        self.tasks = {}

    def add_interval_task(self, name, interval_seconds, func, **kwargs):
        self.tasks[name] = func

    def remove_task(self, name):
        self.tasks.pop(name, None)


def test_register_default_tasks_registers_and_updates_metrics():
    class DummyChain:
        def get_chain_info(self):
            return {
                "blocks": 5,
                "pending_transactions": 2,
                "difficulty": 4,
                "latest_block": {"index": 5},
                "network_health": {
                    "health_score": 0.9,
                    "participation": 0.75,
                    "avg_block_time": 12.3,
                },
            }

    class DummyNode:
        def sync_with_peers(self):
            return True, "ok"

        def get_peer_list(self):
            return ["p1", "p2"]

        def get_network_stats(self):
            class Stats:
                pending_transactions = 3
                network_difficulty = 7
                sync_status = "partial"

            return Stats()

        def is_synced(self):
            return False

    scheduler = DummyScheduler()
    ctx = NodeContext(blockchain=DummyChain(), node=DummyNode(), scheduler=scheduler)

    registered = register_default_tasks(ctx, metrics_interval=0.01, sync_interval=0.01)
    assert registered is True
    assert "metrics.collect" in scheduler.tasks
    assert "peers.sync" in scheduler.tasks

    # Manually run tasks to update metrics
    scheduler.tasks["metrics.collect"]()
    scheduler.tasks["peers.sync"]()

    assert ctx.get_metric("blocks") == 5
    assert ctx.get_metric("pending_tx") == 2
    assert ctx.get_metric("difficulty") == 4
    assert ctx.get_metric("height") == 5
    assert ctx.get_metric("network_health_score") == 0.9
    assert ctx.get_metric("network_participation") == 0.75
    assert ctx.get_metric("avg_block_time") == 12.3
    assert ctx.get_metric("peers") == 2
    assert ctx.get_metric("network_pending_tx") == 3
    assert ctx.get_metric("network_difficulty") == 7
    assert ctx.get_metric("network_sync_status") == "partial"
    assert ctx.get_metric("is_synced") is False
    assert ctx.get_metric("last_sync_ok") is True


def test_register_default_tasks_without_scheduler_returns_false():
    ctx = NodeContext()
    assert register_default_tasks(ctx) is False
