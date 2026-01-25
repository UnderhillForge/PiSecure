"""
Network-related CLI commands.
"""

import os

import click

from pisecure.cli.formatters import print_table


def register(cli):
    @cli.command(name="network")
    @click.option("--enable", is_flag=True, help="Enable WebSocket P2P")
    @click.option("--disable", is_flag=True, help="Disable WebSocket P2P")
    @click.pass_context
    def network_cmd(ctx, enable, disable):
        """Configure WebSocket P2P settings."""
        if enable and disable:
            print_table(
                "Network Configuration Error",
                ["Setting", "Value"],
                [["Error", "Cannot enable and disable together"]],
            )
            return

        if enable:
            os.environ["PISECURE_WEBSOCKET_P2P"] = "1"
        elif disable:
            os.environ["PISECURE_WEBSOCKET_P2P"] = "0"

        ws_enabled = os.environ.get("PISECURE_WEBSOCKET_P2P") == "1"
        rows = [
            ["WebSocket P2P", "Enabled" if ws_enabled else "Disabled"],
            ["P2P Mode", "Hybrid (WS+HTTP)" if ws_enabled else "HTTP only"],
            ["Block Propagation", "Real-time" if ws_enabled else "Polling"],
        ]
        print_table("Network Configuration", ["Setting", "Value"], rows)

    return cli
