"""
Blockchain-related CLI commands.
"""

import click

from pisecure.cli.formatters import print_error, print_info, print_table
from pisecure.common.config import Config
from pisecure.core import SignChain


def _build_status_rows(info: dict) -> list[list[str]]:
    rows = [
        ["Blocks", str(info.get("blocks", 0))],
        ["Pending TX", str(info.get("pending_transactions", 0))],
        ["Difficulty", str(info.get("difficulty", 0))],
        ["Chain Valid", "Yes" if info.get("is_valid") else "No"],
    ]
    latest = info.get("latest_block")
    if latest:
        rows.append(
            [
                "Latest Block",
                f"#{latest.get('index', 0)} ({len(latest.get('transactions', []))} tx)",
            ]
        )
    health = info.get("network_health")
    if health:
        rows.extend(
            [
                ["Participation", f"{health.get('participation', 0):.1%}"],
                ["Avg Block Time", f"{health.get('avg_block_time', 0):.1f}s"],
                ["Network Health", f"{health.get('health_score', 0):.1%}"],
            ]
        )
    return rows


def register(cli):
    @cli.command(name="status")
    @click.pass_context
    def status_cmd(ctx):
        """Show blockchain and system status."""
        try:
            chain = SignChain(use_hybrid_storage=Config.USE_HYBRID_STORAGE)
            info = chain.get_chain_info()
            rows = _build_status_rows(info)
            print_table("PiSecure Blockchain Status", ["Metric", "Value"], rows)
        except Exception as exc:  # noqa: BLE001
            print_error(f"Error getting status: {exc}")

    @cli.command(name="migrate-storage")
    @click.pass_context
    def migrate_storage_cmd(ctx):
        """Migrate blockchain from JSON to hybrid storage."""
        try:
            click.echo("Migrating to hybrid storage...")
            chain = SignChain(use_hybrid_storage=True)
            info = chain.get_chain_info()
            print_info(f"Migration complete. Blocks migrated: {info.get('blocks', 0)}")
            print_info(
                "Future runs default to hybrid storage; use --no-hybrid-storage to disable."
            )
        except Exception as exc:  # noqa: BLE001
            print_error(f"Migration failed: {exc}")

    return cli
