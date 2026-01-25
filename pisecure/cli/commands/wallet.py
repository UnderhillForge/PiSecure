"""
Wallet-related CLI commands.
"""

import time

import click

from pisecure.cli.formatters import print_error, print_table, print_warning
from pisecure.common.config import Config
from pisecure.core import PiSecureWallet, WalletManager


def _wallet_rows(wallets):
    rows = []
    for w in wallets:
        rows.append(
            [
                w.get("wallet_id", "unknown"),
                w.get("name", ""),
                w.get("address", ""),
                f"{w.get('balance', 0):.2f}",
                time.ctime(w.get("created_at", 0)),
            ]
        )
    return rows


def register(cli):
    @cli.command(name="wallet")
    @click.argument("wallet_name", required=False)
    @click.option("--testnet", is_flag=True, help="Use testnet network")
    @click.pass_context
    def wallet_cmd(ctx, wallet_name, testnet):
        """Show wallet information or list wallets."""
        try:
            wallet_dir = (
                "/var/lib/pisecure-testnet/wallets"
                if (testnet or Config.TESTNET)
                else "/var/lib/pisecure/wallets"
            )
            manager = WalletManager(wallet_dir)

            if wallet_name:
                wallet = manager.load_wallet(wallet_name)
                if not wallet:
                    print_error(f"Wallet not found: {wallet_name}")
                    return

                balance = wallet.get_balance()
                rows = [
                    ["Wallet Name", wallet.wallet_name],
                    ["Balance", f"{balance:.2f}"],
                    ["Path", wallet_dir],
                ]
                print_table(f"Wallet: {wallet_name}", ["Field", "Value"], rows)
            else:
                wallets = manager.list_wallets() or []
                if not wallets:
                    print_warning("No wallets found")
                    return

                rows = []
                for name in wallets:
                    w = manager.load_wallet(name)
                    balance = w.get_balance() if w else 0.0
                    rows.append([name, f"{balance:.2f}", wallet_dir])

                print_table(
                    "Available Wallets",
                    ["Name", "Balance", "Location"],
                    rows,
                )
        except Exception as exc:  # noqa: BLE001
            print_error(f"Wallet command failed: {exc}")

    return cli
