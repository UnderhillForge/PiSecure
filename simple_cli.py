#!/usr/bin/env python3
"""
Simple PiSecure CLI for testing entry point
"""

import click
from rich.console import Console

console = Console()

@click.group()
def cli():
    """PiSecure - Simple Test CLI"""
    pass

@cli.command()
def test():
    """Test command"""
    console.print("[green]✅ PiSecure CLI is working![/green]")

@cli.command()
def status():
    """Show basic status"""
    try:
        from pisecure.core import SignChain, HardwareVerifier
        console.print("[green]✅ Imports working![/green]")
        console.print(f"SignChain: {SignChain}")
        console.print(f"HardwareVerifier: {HardwareVerifier}")
    except Exception as e:
        console.print(f"[red]❌ Import error: {e}[/red]")

if __name__ == '__main__':
    cli()