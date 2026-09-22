"""
PiSecure CLI - Main Entry Point

Thin wrapper that imports commands from the refactored cli submodule.
Uses InitFactory pattern to initialize services based on mode.

This file is the entry point - it initializes the system and delegates
to the appropriate command handlers.
"""

import os
import sys
from typing import Optional

import click

# Import from new architecture
from pisecure.node import NodeContext, create_default_scheduler
from pisecure.node.tasks import register_default_tasks
from pisecure.interfaces.init import InitFactory
from pisecure.common.config import Config
from pisecure.common import Ok, Err
from pisecure.cli.commands import register_all as register_cli_commands

# Import old CLI for now (temporary during migration)
try:
    from .cli_legacy import cli as legacy_cli
except ImportError:
    legacy_cli = None


@click.group()
@click.option("--testnet", is_flag=True, help="Use testnet blockchain")
@click.option("--validate-only", is_flag=True, help="Validation-only mode (no mining)")
@click.option("--quiet", is_flag=True, help="Suppress Rich formatted output")
@click.option(
    "--hybrid-storage/--no-hybrid-storage", default=True, help="Use hybrid storage"
)
@click.option(
    "--mock-hardware",
    is_flag=True,
    help="Rejected. pisecured does not fake Pi hardware.",
)
@click.pass_context
def cli(ctx, testnet, validate_only, quiet, hybrid_storage, mock_hardware):
    """
    PiSecure - Hardware-Verified Blockchain Security Framework

    Initialize the node with appropriate mode and configuration.
    """
    mock_env = os.getenv("PISECURE_MOCK_HARDWARE", "").strip().lower()
    if mock_hardware or mock_env in {"1", "true", "yes", "on"}:
        raise click.UsageError(
            "--mock-hardware and PISECURE_MOCK_HARDWARE are not allowed. "
            "pisecured validates blocks; it does not fake Pi hardware."
        )

    # Set environment variables for downstream components
    if testnet:
        os.environ["PISECURE_TESTNET"] = "1"
    if validate_only:
        os.environ["PISECURE_VALIDATE_ONLY"] = "1"
    if quiet:
        os.environ["PISECURE_QUIET"] = "1"
    if not hybrid_storage:
        os.environ["PISECURE_NO_HYBRID_STORAGE"] = "1"

    # Update Config with environment variables
    Config.TESTNET = testnet
    Config.VALIDATE_ONLY = validate_only
    Config.QUIET = quiet
    Config.USE_HYBRID_STORAGE = hybrid_storage
    Config.MOCK_HARDWARE = False

    # Create context for all commands
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config

    # Determine initialization mode
    if validate_only:
        mode = "validator"
    elif testnet:
        mode = "testing"
    else:
        mode = "full_node"

    ctx.obj["mode"] = mode

    # Prepare NodeContext with scheduler for graceful shutdown
    scheduler = create_default_scheduler()
    node_context = NodeContext(
        blockchain=None,
        wallet=None,
        miner=None,
        node=None,
        storage=None,
        scheduler=scheduler,
        testnet=testnet,
        validate_only=validate_only,
        mock_hardware=False,
        quiet=quiet,
        data_dir=Config.DATA_DIR,
        config_dir=Config.CONFIG_DIR,
    )

    node_context.start()
    register_default_tasks(node_context)
    ctx.obj["context"] = node_context


@cli.command()
@click.pass_context
def version(ctx):
    """Show PiSecure version and build information."""
    from pisecure import __version__

    click.echo(f"PiSecure {__version__}")
    click.echo(f"Mode: {ctx.obj.get('mode', 'unknown')}")
    click.echo(f"Config: {Config.get_mode_string()}")


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    from pisecure.cli.formatters import print_dict

    config_dict = {
        "testnet": Config.TESTNET,
        "validate_only": Config.VALIDATE_ONLY,
        "mock_hardware": Config.MOCK_HARDWARE,
        "use_hybrid_storage": Config.USE_HYBRID_STORAGE,
        "data_dir": Config.DATA_DIR,
        "api_host": Config.API_HOST,
        "api_port": Config.API_PORT,
    }
    print_dict(config_dict)


# If legacy CLI available, import all its commands as subcommands
# Attach modular commands before legacy fallbacks
register_cli_commands(cli)

if legacy_cli:
    for name in legacy_cli.list_commands(None):
        if name not in ["status", "mine", "version", "config"]:  # Skip duplicates
            cmd = legacy_cli.get_command(None, name)
            if cmd:
                cli.add_command(cmd, name=name)


def main():
    """Main entry point for PiSecure CLI."""
    click_context: dict = {}
    try:
        cli(obj=click_context)
    except KeyboardInterrupt:
        click.echo("\nInterrupt received. Shutting down...", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Fatal error: {e}", err=True)
        sys.exit(1)
    finally:
        context = (
            click_context.get("context") if isinstance(click_context, dict) else None
        )
        if context:
            context.shutdown()


if __name__ == "__main__":
    main()
