"""
Blockchain-related CLI commands.
"""

import click

from pisecure.cli.formatters import print_error, print_info
from pisecure.common.config import Config
from pisecure.core import SignChain


def register(cli):
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
