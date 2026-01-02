#!/usr/bin/env python3
"""
PiSecure Mining Console
=======================

Interactive mining dashboard with real-time stats, controls, and monitoring.
Provides a rich terminal interface for mining operations.

Features:
- Real-time mining statistics
- System resource monitoring
- Wallet balance tracking
- Mining controls (start/stop)
- Live blockchain updates
- Hardware status monitoring

Usage: python mining-console.py
"""

import time
import json
import threading
import psutil
from pathlib import Path
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

try:
    # Try relative imports first (for package installation)
    from pisecure.core.blockchain import SignChain
    from pisecure.core.hardware import HardwareVerifier
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core.blockchain import SignChain
    from core.hardware import HardwareVerifier

console = Console()


class MiningConsole:
    """Interactive mining console with rich terminal interface"""

    def __init__(self):
        self.blockchain = SignChain()
        self.hardware = HardwareVerifier()

        # Load miner wallet from config
        self.miner_wallet = self._load_miner_wallet()

        # Mining state
        self.mining_active = False
        self.mining_thread = None
        self.stop_mining = threading.Event()

        # Stats tracking
        self.stats = {
            'blocks_mined': 0,
            'total_rewards': 0.0,
            'hashrate': 0.0,
            'uptime': 0,
            'start_time': time.time(),
            'last_block_time': None,
            'pending_txs': 0,
            'session_rewards': 0.0,
            'session_blocks': 0
        }

        # Progress tracking
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )

        self.mining_task = None

    def _load_miner_wallet(self):
        """Load miner wallet address from config"""
        try:
            config_path = "/etc/pisecure/config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('mining', {}).get('wallet_address')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def start_mining(self):
        """Start the mining process"""
        if self.mining_active:
            console.print("[yellow]⚠️ Mining is already active[/yellow]")
            return

        # Hardware verification
        result = self.hardware.verify_mining_eligibility()
        if not result['eligible']:
            console.print(f"[red]❌ Hardware verification failed: {result.get('error', 'Unknown error')}[/red]")
            return

        console.print("[green]⛏️ Starting mining session...[/green]")
        if self.miner_wallet:
            console.print(f"[dim]Rewards will go to: {self.miner_wallet[:24]}...[/dim]")
        else:
            console.print("[yellow]⚠️ No miner wallet configured - rewards will not be distributed[/yellow]")

        self.mining_active = True
        self.stop_mining.clear()
        self.stats['start_time'] = time.time()
        self.stats['session_blocks'] = 0
        self.stats['session_rewards'] = 0.0

        # Start mining thread
        self.mining_thread = threading.Thread(target=self._mining_worker, daemon=True)
        self.mining_thread.start()

        # Start progress display
        self.mining_task = self.progress.add_task("Mining blocks...", total=None)

    def stop_mining(self):
        """Stop the mining process"""
        if not self.mining_active:
            console.print("[yellow]⚠️ Mining is not active[/yellow]")
            return

        console.print("[yellow]⏹️ Stopping mining session...[/yellow]")
        self.stop_mining.set()
        self.mining_active = False

        if self.mining_thread and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=5)

        session_time = time.time() - self.stats['start_time']
        console.print(f"[green]✅ Mining stopped[/green]")
        console.print(f"[dim]Session: {self.stats['session_blocks']} blocks, {self.stats['session_rewards']:.2f} tokens in {session_time:.0f}s[/dim]")

    def _mining_worker(self):
        """Background mining worker"""
        while not self.stop_mining.is_set():
            try:
                # Update stats
                self.stats['uptime'] = time.time() - self.stats['start_time']
                self.stats['pending_txs'] = len(self.blockchain.pending_transactions)

                # Mine a block
                block = self.blockchain.mine_pending_transactions(self.miner_wallet, verbose=False)

                if block:
                    self.stats['blocks_mined'] += 1
                    self.stats['session_blocks'] += 1
                    self.stats['last_block_time'] = time.time()

                    # Calculate rough hashrate
                    if hasattr(block, 'nonce') and block.nonce > 0:
                        # Very rough approximation
                        self.stats['hashrate'] = max(0.1, block.nonce / max(1, time.time() - self.stats.get('last_block_time', time.time())))

                    # Check for mining rewards
                    reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                    if reward_txs:
                        reward_amount = reward_txs[0].get('amount', 0)
                        self.stats['total_rewards'] += reward_amount
                        self.stats['session_rewards'] += reward_amount

                    # Update progress
                    if self.mining_task:
                        self.progress.update(self.mining_task, advance=1,
                                           description=f"Mined block #{block.index}")

                    console.print(f"[green]✅ Block #{block.index} mined! Reward: {reward_amount if reward_txs else 0:.1f} tokens[/green]")
                else:
                    time.sleep(2)  # Wait before trying again

            except Exception as e:
                console.print(f"[red]Mining error: {e}[/red]")
                time.sleep(5)

    def create_dashboard(self):
        """Create the dashboard display"""
        # System stats
        system_table = Table(title="🖥️ System Status", box=None, show_header=False)
        system_table.add_column("Metric", style="cyan", no_wrap=True)
        system_table.add_column("Value", style="magenta")

        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        system_table.add_row("CPU Usage", f"{cpu_percent:.1f}%")
        system_table.add_row("Memory", f"{memory.percent:.1f}% ({memory.used/1024/1024/1024:.1f}GB)")
        system_table.add_row("Disk Usage", f"{disk.percent:.1f}% ({disk.used/1024/1024/1024:.1f}GB)")
        system_table.add_row("Temperature", f"{self._get_temperature():.1f}°C")

        # Mining stats
        mining_table = Table(title="⛏️ Mining Status", box=None, show_header=False)
        mining_table.add_column("Metric", style="cyan", no_wrap=True)
        mining_table.add_column("Value", style="green" if self.mining_active else "red")

        status_icon = "🟢" if self.mining_active else "🔴"
        mining_table.add_row("Status", f"{status_icon} {'Active' if self.mining_active else 'Stopped'}")
        mining_table.add_row("Total Blocks", str(self.stats['blocks_mined']))
        mining_table.add_row("Session Blocks", str(self.stats['session_blocks']))
        mining_table.add_row("Total Rewards", f"{self.stats['total_rewards']:.2f} tokens")
        mining_table.add_row("Session Rewards", f"{self.stats['session_rewards']:.2f} tokens")
        mining_table.add_row("Hashrate", f"{self.stats['hashrate']:.1f} KH/s")
        mining_table.add_row("Uptime", f"{self.stats['uptime']:.0f}s")

        # Blockchain stats
        chain_info = self.blockchain.get_chain_info()
        blockchain_table = Table(title="⛓️ Blockchain Status", box=None, show_header=False)
        blockchain_table.add_column("Metric", style="cyan", no_wrap=True)
        blockchain_table.add_column("Value", style="blue")

        blockchain_table.add_row("Blocks", str(chain_info['blocks']))
        blockchain_table.add_row("Pending TX", str(self.stats['pending_txs']))
        blockchain_table.add_row("Difficulty", str(chain_info['difficulty']))

        health = chain_info['network_health']
        blockchain_table.add_row("Participation", f"{health['participation']:.1%}")
        blockchain_table.add_row("Avg Block Time", f"{health['avg_block_time']:.1f}s")

        # Wallet info
        wallet_table = Table(title="🏦 Mining Wallet", box=None, show_header=False)
        wallet_table.add_column("Property", style="cyan", no_wrap=True)
        wallet_table.add_column("Value", style="yellow")

        if self.miner_wallet:
            wallet_balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            wallet_table.add_row("Address", self.miner_wallet[:32] + "...")
            wallet_table.add_row("Balance", f"{wallet_balance:.2f} tokens")
            wallet_table.add_row("Session Earnings", f"+{self.stats['session_rewards']:.2f}")
        else:
            wallet_table.add_row("Status", "⚠️ Not configured")

        # Recent blocks
        recent_blocks_table = Table(title="📦 Recent Blocks", box=None)
        recent_blocks_table.add_column("Block", style="cyan", justify="right")
        recent_blocks_table.add_column("TX Count", style="magenta", justify="right")
        recent_blocks_table.add_column("Reward", style="green", justify="right")
        recent_blocks_table.add_column("Time", style="blue")

        recent_blocks = self.blockchain.chain[-8:] if len(self.blockchain.chain) > 8 else self.blockchain.chain
        for block in reversed(recent_blocks):
            tx_count = len([tx for tx in block.transactions if tx.get('type') != 'mining_reward'])
            reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
            reward_amount = reward_txs[0].get('amount', 0) if reward_txs else 0

            block_time = time.ctime(block.timestamp)
            recent_blocks_table.add_row(
                str(block.index),
                str(tx_count),
                f"{reward_amount:.1f}",
                block_time
            )

        # Layout
        left_panel = Panel(
            Columns([system_table, mining_table], equal=True, expand=True),
            title="📊 Live Stats"
        )

        right_panel = Panel(
            Columns([blockchain_table, wallet_table], equal=True, expand=True),
            title="⛓️ Network & Wallet"
        )

        blocks_panel = Panel(recent_blocks_table, title="📦 Mining History")

        # Instructions
        controls = """
[bold cyan]Mining Console Controls:[/bold cyan]
[green]S[/green] - Start Mining    [red]X[/red] - Stop Mining
[yellow]C[/yellow] - Create Test TX    [blue]W[/blue] - Wallet Info
[dim]Q[/dim] - Quit Console    [dim]H[/dim] - Show This Help
        """

        instructions_panel = Panel(
            Align.center(Text.from_markup(controls)),
            title="🎮 Controls",
            border_style="blue"
        )

        # Main layout
        layout = Layout()
        layout.split(
            Layout(name="upper", size=12),
            Layout(name="middle"),
            Layout(name="lower", size=8)
        )

        layout["upper"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )

        layout["upper"]["left"].update(left_panel)
        layout["upper"]["right"].update(right_panel)
        layout["middle"].update(blocks_panel)
        layout["lower"].update(instructions_panel)

        return layout

    def _get_temperature(self):
        """Get system temperature"""
        try:
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps and temps['cpu_thermal']:
                return temps['cpu_thermal'][0].current
            elif 'coretemp' in temps and temps['coretemp']:
                return temps['coretemp'][0].current
        except:
            pass
        return 0.0

    def create_test_transaction(self):
        """Create a test transaction for mining"""
        try:
            import secrets

            tx = {
                "type": "test_transaction",
                "data": {
                    "message": f"Test transaction from mining console",
                    "timestamp": time.time(),
                    "test_id": secrets.token_hex(8)
                },
                "signature": f"mining_console_sig_{secrets.token_hex(4)}",
                "timestamp": time.time()
            }

            tx_hash = self.blockchain.add_transaction(tx)
            console.print(f"[green]✅ Test transaction created: {tx_hash[:16]}...[/green]")
            console.print(f"[dim]Transaction will be mined in the next block[/dim]")

        except Exception as e:
            console.print(f"[red]❌ Failed to create test transaction: {e}[/red]")

    def show_wallet_info(self):
        """Show detailed wallet information"""
        if not self.miner_wallet:
            console.print("[yellow]⚠️ No miner wallet configured[/yellow]")
            return

        try:
            balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            transactions = self.blockchain.get_wallet_transactions(self.miner_wallet)

            console.print(f"\n[bold green]🏦 Wallet Information[/bold green]")
            console.print(f"Address: {self.miner_wallet}")
            console.print(f"Balance: {balance:.2f} tokens")
            console.print(f"Total Transactions: {len(transactions)}")

            if transactions:
                console.print(f"\n[dim]Recent Transactions:[/dim]")
                for tx in transactions[-5:]:  # Show last 5
                    direction = "→" if tx['direction'] == 'incoming' else "←"
                    console.print(f"  {direction} {tx['amount']:.2f} tokens (Block #{tx['block_index']})")

        except Exception as e:
            console.print(f"[red]❌ Error getting wallet info: {e}[/red]")

    def run(self):
        """Run the interactive mining console"""
        console.clear()
        console.print("[bold cyan]🔐 PiSecure Mining Console[/bold cyan]")
        console.print("[dim]Real-time mining dashboard with controls[/dim]\n")

        # Show initial status
        if self.miner_wallet:
            console.print(f"[green]✅ Miner wallet configured: {self.miner_wallet[:24]}...[/green]")
        else:
            console.print("[yellow]⚠️ No miner wallet configured - set mining.wallet_address in /etc/pisecure/config.json[/yellow]")

        console.print("[dim]Starting live dashboard... (press 'H' for help)[/dim]\n")

        try:
            with Live(self.create_dashboard(), refresh_per_second=2, screen=True) as live:
                while True:
                    # Update dashboard
                    live.update(self.create_dashboard())

                    # Check for keyboard input (non-blocking)
                    import select
                    import sys

                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()

                        if key == 'q':
                            if self.mining_active:
                                self.stop_mining()
                            console.print("[cyan]👋 Goodbye![/cyan]")
                            break
                        elif key == 's':
                            self.start_mining()
                        elif key == 'x':
                            self.stop_mining()
                        elif key == 'c':
                            self.create_test_transaction()
                        elif key == 'w':
                            self.show_wallet_info()
                        elif key == 'h':
                            console.print("\n[bold cyan]Help - Mining Console Controls:[/bold cyan]")
                            console.print("[green]S[/green] - Start Mining")
                            console.print("[red]X[/red] - Stop Mining")
                            console.print("[yellow]C[/yellow] - Create Test Transaction")
                            console.print("[blue]W[/blue] - Show Wallet Info")
                            console.print("[dim]Q[/dim] - Quit Console")
                            console.print("[dim]H[/dim] - Show This Help\n")
                            time.sleep(3)  # Pause to read help

        except KeyboardInterrupt:
            if self.mining_active:
                self.stop_mining()
            console.print("\n[cyan]👋 Mining console closed[/cyan]")


def main():
    """Main entry point"""
    try:
        console = MiningConsole()
        console.run()
    except KeyboardInterrupt:
        console.print("\n[cyan]👋 Mining console closed[/cyan]")
    except Exception as e:
        console.print(f"[red]❌ Mining console error: {e}[/red]")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())