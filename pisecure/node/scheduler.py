"""
Lightweight background scheduler for PiSecure.

Provides simple interval-based tasks with graceful shutdown.
Designed for small periodic jobs (sync, metrics, cleanup) without
bringing in heavyweight dependencies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Container for a scheduled task."""

    name: str
    interval: float
    func: Callable[[], None]
    initial_delay: float = 0.0
    run_immediately: bool = False
    last_run: float = field(default_factory=lambda: 0.0)
    started_at: float = field(default_factory=lambda: time.time())

    def is_due(self, now: float) -> bool:
        """Determine if the task should run."""
        if self.run_immediately and self.last_run == 0.0:
            return now >= self.started_at
        if now < self.started_at + self.initial_delay:
            return False
        return now - self.last_run >= self.interval


class Scheduler:
    """Lightweight scheduler managing background tasks."""

    def __init__(self, tick_seconds: float = 0.5) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Optional[Thread] = None
        self._tick_seconds = tick_seconds

    def add_interval_task(
        self,
        name: str,
        interval_seconds: float,
        func: Callable[[], None],
        *,
        initial_delay: float = 0.0,
        run_immediately: bool = False,
    ) -> None:
        """Register a recurring task."""
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        task = ScheduledTask(
            name=name,
            interval=interval_seconds,
            func=func,
            initial_delay=initial_delay,
            run_immediately=run_immediately,
        )
        with self._lock:
            self._tasks[name] = task
        logger.debug(
            "Scheduler task registered: %s (interval=%.2fs)", name, interval_seconds
        )

    def remove_task(self, name: str) -> None:
        """Remove a scheduled task."""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                logger.debug("Scheduler task removed: %s", name)

    def start(self) -> None:
        """Start scheduler loop in background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, name="pisecure-scheduler", daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop scheduler and wait for completion."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("Scheduler stopped")

    def _run(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            now = time.time()
            with self._lock:
                tasks = list(self._tasks.values())
            for task in tasks:
                if self._stop_event.is_set():
                    break
                if not task.is_due(now):
                    continue
                try:
                    task.func()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Scheduler task '%s' failed: %s", task.name, exc)
                task.last_run = time.time()
            self._stop_event.wait(self._tick_seconds)

    def is_running(self) -> bool:
        """Return True if scheduler thread is active."""
        return bool(self._thread and self._thread.is_alive())


def create_default_scheduler() -> Scheduler:
    """Factory for a scheduler with sensible defaults."""
    return Scheduler(tick_seconds=0.5)
