"""
Wallet-related CLI commands.

Amounts on `utxos` and `send` are 314ST. 1 unit on the daemon is 0.001 314ST,
so `0.050` is 50 units.
"""

import json
import os
import re
import subprocess
import tempfile
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


def _address_ok(address: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]{1,128}", address))


def _key_path(address: str) -> str:
    if not _address_ok(address):
        raise click.ClickException("address is not a safe key filename")
    return os.path.join(Config.get_data_dir(), "wallets", f"{address}.json")


def _read_keystore(address: str) -> dict:
    path = _key_path(address)
    if os.access(path, os.R_OK):
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    else:
        proc = subprocess.run(
            ["sudo", "-n", "cat", path],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            raise click.ClickException(f"no spending key for {address}")
        raw = proc.stdout.decode()
    doc = json.loads(raw)
    if doc.get("scheme") != "ed25519" or not doc.get("public_key") or not doc.get("secret_key"):
        raise click.ClickException(f"spending key for {address} is not ed25519")
    return doc


def _write_keystore(address: str, doc: dict) -> None:
    path = _key_path(address)
    payload = json.dumps(
        {
            "address": doc["address"],
            "scheme": doc["scheme"],
            "public_key": doc["public_key"],
            "secret_key": doc["secret_key"],
        },
        indent=2,
    )
    payload += "\n"
    fd, tmp = tempfile.mkstemp(prefix="pisecure-key-")
    try:
        os.write(fd, payload.encode())
        os.close(fd)
        fd = -1
        os.chmod(tmp, 0o600)
        subprocess.run(
            ["sudo", "-n", "install", "-o", "pisecure", "-g", "pisecure", "-m", "0600", tmp, path],
            check=True,
        )
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp):
            os.remove(tmp)


def _canonical_sign_bytes(tx: dict) -> bytes:
    body = {
        "version": tx["version"],
        "inputs": [
            {"prev_txid": item["prev_txid"], "vout": item["vout"]} for item in tx["inputs"]
        ],
        "outputs": [
            {"address": item["address"], "value": item["value"]} for item in tx["outputs"]
        ],
        "fee": tx["fee"],
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def _sign_inputs(tx: dict, secret_hex: str, public_hex: str) -> None:
    from nacl.signing import SigningKey

    signature = SigningKey(bytes.fromhex(secret_hex)).sign(_canonical_sign_bytes(tx)).signature.hex()
    for item in tx["inputs"]:
        item["public_key"] = public_hex
        item["signature"] = signature


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

    @wallet_group.command(name="bind")
    @click.argument("address")
    def wallet_bind(address):
        """Create an Ed25519 spending key for an address string, if missing."""
        path = _key_path(address)
        exists = os.path.exists(path) or subprocess.run(
            ["sudo", "-n", "test", "-f", path], check=False
        ).returncode == 0
        if exists:
            doc = _read_keystore(address)
            print_info(f"{address} already bound ({doc['scheme']})")
            click.echo(doc["public_key"])
            return
        from nacl.signing import SigningKey

        key = SigningKey.generate()
        _write_keystore(
            address,
            {
                "address": address,
                "scheme": "ed25519",
                "public_key": key.verify_key.encode().hex(),
                "secret_key": key.encode().hex(),
            },
        )
        print_info(f"bound {address} with ed25519")
        click.echo(key.verify_key.encode().hex())

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
        key = _read_keystore(src)
        _sign_inputs(tx, key["secret_key"], key["public_key"])
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
