import time
from threading import Event

from pisecure.node.context import NodeContext
from pisecure.node.scheduler import Scheduler


def test_scheduler_runs_interval_task():
    flag = Event()
    scheduler = Scheduler(tick_seconds=0.01)
    scheduler.add_interval_task(
        name="tick",
        interval_seconds=0.02,
        func=lambda: flag.set(),
        run_immediately=True,
    )
    scheduler.start()
    try:
        assert flag.wait(0.25)
    finally:
        scheduler.stop()


def test_node_context_shutdown_stops_scheduler_and_handlers():
    class DummyScheduler:
        def __init__(self):
            self.start_called = False
            self.stop_called = False

        def start(self):
            self.start_called = True

        def stop(self):
            self.stop_called = True

    handler_called = Event()
    dummy_scheduler = DummyScheduler()
    ctx = NodeContext(scheduler=dummy_scheduler)

    ctx.register_shutdown_handler(lambda _: handler_called.set())
    ctx.start()
    assert dummy_scheduler.start_called is True

    ctx.shutdown()
    assert dummy_scheduler.stop_called is True
    assert handler_called.wait(0.1)
