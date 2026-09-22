"""
Mining-related CLI commands.
"""

import click

from pisecure.cli.formatters import (
    print_error,
    print_info,
    print_success,
)
from pisecure.core.hardware import HardwareVerifier


def register(cli):
    @cli.command(name="verify-hardware")
    @click.pass_context
    def verify_hardware_cmd(ctx):
        """Verify Raspberry Pi hardware for mining eligibility."""
        try:
            verifier = HardwareVerifier()
            result = verifier.verify_mining_eligibility()
            if result.get("eligible"):
                print_success("Hardware verification passed")
                print_info(f"Device: {result.get('hardware_model', 'unknown')}")
                print_info(f"Confidence: {result.get('confidence_score', 0):.1%}")
            else:
                print_error("Hardware verification failed")
                print_info(f"Confidence: {result.get('confidence_score', 0):.1%}")
        except Exception as exc:  # noqa: BLE001
            print_error(f"Verification error: {exc}")

    @cli.command(name="mine")
    @click.option("--wallet", required=True, help="Wallet address for mining rewards")
    @click.option(
        "--count", default=1, show_default=True, help="Blocks to mine (0=until stopped)"
    )
    @click.option(
        "--sleep",
        "sleep_interval",
        default=0.1,
        show_default=True,
        help="Delay between attempts (seconds)",
    )
    @click.pass_context
    def mine_cmd(ctx, wallet, count, sleep_interval):
        """Disabled. Block production belongs to psminer on an official Pi."""
        raise click.ClickException(
            "pisecure mine is disabled. Only psminer on an official Raspberry Pi "
            "2/3/4/5 may produce blocks. This CLI does not mine and does not "
            f"fake hardware (ignored wallet {wallet})."
        )

    return cli
