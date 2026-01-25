"""
Mining-related CLI commands.
"""

import time

import click

from pisecure.cli.formatters import (
    print_error,
    print_info,
    print_success,
    print_warning,
)
from pisecure.common.config import Config
from pisecure.core import SignChain
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
        """Mine pending transactions (requires Pi hardware or mock)."""
        try:
            chain = SignChain(use_hybrid_storage=Config.USE_HYBRID_STORAGE)
            mined = 0
            target = count if count > 0 else float("inf")
            while mined < target:
                block = chain.mine_pending_transactions(wallet)
                if block:
                    mined += 1
                    print_success(
                        f"Mined block #{block.get('index', '?')} → rewards to {wallet}"
                    )
                else:
                    print_info("No transactions to mine; waiting...")
                time.sleep(sleep_interval)
        except KeyboardInterrupt:
            print_warning("Mining stopped by user")
        except Exception as exc:  # noqa: BLE001
            print_error(f"Mining failed: {exc}")

    return cli
