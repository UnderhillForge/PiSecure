"""
Monitoring-related CLI commands.
"""

import time
from threading import Event

import click

from pisecure.cli.formatters import print_error, print_info, print_table
from pisecure.common.config import Config
from pisecure.core import SignChain
from pisecure import __version__


def _build_rows(info: dict) -> list:
    return [
        ["Blocks", str(info.get("blocks", 0))],
        ["Pending TX", str(info.get("pending_transactions", 0))],
        ["Difficulty", str(info.get("difficulty", 0))],
        ["Chain Valid", "Yes" if info.get("is_valid") else "No"],
    ]


def register(cli):
    @cli.command(name="status")
    @click.pass_context
    def status_cmd(ctx):
        """Print one-shot node and chain status."""
        click.echo(f"PiSecure {__version__}")
        click.echo(f"Mode: {ctx.obj.get('mode', 'unknown')}")
        click.echo(f"Config: {Config.get_mode_string()}")
        click.echo(f"Data dir: {Config.get_data_dir()}")
        click.echo(f"Bootstrap: {Config.BOOTSTRAP_URL}")
        try:
            chain = SignChain(use_hybrid_storage=Config.USE_HYBRID_STORAGE)
            info = chain.get_chain_info()
            rows = _build_rows(info)
            print_table("Chain", ["Metric", "Value"], rows)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Chain unavailable: {exc}")
            click.echo("Node process is up; chain data not initialized yet.")

    @cli.command(name="monitor")
    @click.option(
        "--refresh", default=2.0, show_default=True, help="Refresh interval seconds"
    )
    @click.option(
        "--iterations",
        default=0,
        show_default=True,
        help="Number of refresh cycles (0 = infinite)",
    )
    @click.pass_context
    def monitor_cmd(ctx, refresh, iterations):
        """Monitor blockchain status periodically using the scheduler."""
        context = ctx.obj.get("context") if isinstance(ctx.obj, dict) else None
        scheduler = getattr(context, "scheduler", None)
        if not scheduler:
            print_error("Scheduler not available; re-run CLI entrypoint")
            return

        latest = {"data": None}

        def collect():
            try:
                chain = SignChain(use_hybrid_storage=Config.USE_HYBRID_STORAGE)
                latest["data"] = chain.get_chain_info()
            except Exception as exc:  # noqa: BLE001
                latest["data"] = {"error": str(exc)}

        task_name = "monitor.collect"
        scheduler.add_interval_task(
            task_name, interval_seconds=refresh, func=collect, run_immediately=True
        )

        try:
            cycles = 0
            while True:
                if iterations and cycles >= iterations:
                    break
                time.sleep(refresh)
                data = latest.get("data") or {}
                if "error" in data:
                    print_error(f"Monitor error: {data['error']}")
                else:
                    rows = _build_rows(data)
                    print_table("Monitor", ["Metric", "Value"], rows)
                cycles += 1
        except KeyboardInterrupt:
            print_info("Monitor stopped by user")
        finally:
            scheduler.remove_task(task_name)

    return cli
