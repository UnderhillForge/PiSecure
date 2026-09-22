"""
Wallet-related CLI commands.

Amounts on `utxos` and `send` are 314ST. 1 unit on the daemon is 0.001 314ST,
so `0.050` is 50 units.
"""

import json
import os
import time
from decimal import Decimal, ROUND_DOWN

import click

from pisecure.cli.formatters import print_error, print_info, print_table, print_warning
from pisecure.common.config import Config
from pisecure.core import WalletManager


def _units_from_314st(text: str) -> int:
    """Convert a 314ST decimal string to daemon units (1 unit = 0.001 314ST)."""
    try:
        units = (Decimal(text) * Decimal(1000)).to_integral_value(rounding=ROUND_DOWN)
    except Exception as exc:  # noqa: BLE001
        raise click.ClickException(f"Amount must be 314ST, for example 0.050: {exc}") from exc
    if units <= 0:
        raise click.ClickException("Amount must be greater than 0")
    return int(units)


def _daemon_rpc(method: str, params):
    from websocket import create_connection

    host = os.environ.get("PISECURED_HOST", "127.0.0.1")
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    port = os.environ.get("PISECURED_PORT", "3144")
    ws = create_connection(f"ws://{host}:{port}", timeout=10)
    try:
        ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
        reply = json.loads(ws.recv())
    finally:
        ws.close()
    if "error" in reply:
        message = reply["error"].get("message", str(reply["error"]))
        raise click.ClickException(message)
    return reply.get("result")


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
    @cli.group(name="wallet")
    def wallet_group():
        """Spend coins tracked by the running pisecured node."""

    @wallet_group.command(name="utxos")
    @click.argument("address")
    def wallet_utxos(address):
        """List daemon UTXOs for an address. Amounts are 314ST."""
        result = _daemon_rpc("listunspent", {"address": address})
        rows = []
        for utxo in result.get("utxos", []):
            rows.append(
                [
                    utxo.get("txid", ""),
                    str(utxo.get("vout", "")),
                    str(utxo.get("units", "")),
                    utxo.get("amount", ""),
                ]
            )
        if not rows:
            print_warning(f"No UTXOs for {address}")
            return
        print_table(
            f"{address}: {result.get('amount')} 314ST ({result.get('units')} units)",
            ["txid", "vout", "units", "314ST"],
            rows,
        )

    @wallet_group.command(name="send")
    @click.argument("src")
    @click.argument("dst")
    @click.argument("amount")
    @click.option(
        "--fee",
        default="0.001",
        show_default=True,
        help="Fee in 314ST. 0.001 is 1 unit.",
    )
    def wallet_send(src, dst, amount, fee):
        """Spend src's daemon UTXO. amount and --fee are 314ST, not raw units."""
        pay = _units_from_314st(amount)
        fee_units = _units_from_314st(fee)
        unspent = _daemon_rpc("listunspent", {"address": src})
        chosen = None
        for utxo in unspent.get("utxos", []):
            if int(utxo.get("units", 0)) >= pay + fee_units:
                chosen = utxo
                break
        if chosen is None:
            raise click.ClickException(
                f"{src} has no UTXO covering {pay} units plus fee {fee_units}"
            )
        change = int(chosen["units"]) - pay - fee_units
        outputs = [{"address": dst, "value": pay}]
        if change > 0:
            outputs.append({"address": src, "value": change})
        tx = {
            "version": 1,
            "inputs": [{"prev_txid": chosen["txid"], "vout": int(chosen["vout"])}],
            "outputs": outputs,
            "fee": fee_units,
        }
        result = _daemon_rpc("sendtransaction", tx)
        if result.get("status") != "accepted":
            raise click.ClickException(result.get("reason", "send rejected"))
        print_info(
            f"sent {amount} 314ST ({pay} units) from {src} to {dst}, "
            f"fee {fee} 314ST ({fee_units} units), change {change} units"
        )
        click.echo(result["txid"])

    @wallet_group.command(name="files")
    @click.argument("wallet_name", required=False)
    @click.option("--testnet", is_flag=True, help="Use testnet network")
    @click.pass_context
    def wallet_cmd(ctx, wallet_name, testnet):
        """Show on-disk wallet files. This is not the daemon UTXO set."""
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
