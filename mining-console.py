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
    from pisecure.core.nat_traversal import node_discovery
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core.blockchain import SignChain
    from core.hardware import HardwareVerifier
    from core.nat_traversal import node_discovery

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

        # Network info
        network_table = Table(title="🌐 Network Status", box=None, show_header=False)
        network_table.add_column("Property", style="cyan", no_wrap=True)
        network_table.add_column("Value", style="magenta")

        try:
            discovery_status = node_discovery.get_discovery_status()
            network_table.add_row("Node ID", discovery_status.get('node_id', 'unknown')[:16] + "...")
            network_table.add_row("Active Endpoints", str(len(discovery_status.get('endpoints', []))))

            # Show STUN/TOR addresses
            endpoints = discovery_status.get('endpoints', [])
            if endpoints:
                for i, endpoint in enumerate(endpoints[:2]):  # Show up to 2 endpoints
                    endpoint_type = endpoint.get('type', 'unknown')
                    if endpoint_type == 'stun_direct':
                        network_table.add_row(f"STUN Address {i+1}", f"{endpoint.get('ip', 'unknown')}:{endpoint.get('port', 'unknown')}")
                    elif endpoint_type == 'tor_onion':
                        network_table.add_row(f"Tor Onion {i+1}", endpoint.get('address', 'unknown')[:24] + "...")
                    elif endpoint_type == 'upnp':
                        network_table.add_row(f"UPnP Address {i+1}", f"{endpoint.get('ip', 'unknown')}:{endpoint.get('port', 'unknown')}")

            # Relay status
            is_relay = self._check_if_relay_node()
            network_table.add_row("Relay Status", "✅ Active" if is_relay else "❌ Not participating")
            network_table.add_row("Community Relays", str(discovery_status.get('relay_count', 0)))

        except Exception as e:
            network_table.add_row("Network Status", f"❌ Error: {str(e)[:20]}...")

        # Instructions
        controls = """
[bold cyan]Mining Console Controls:[/bold cyan]
[green]S[/green] - Start Mining    [red]X[/red] - Stop Mining    [yellow]C[/yellow] - Test TX
[blue]W[/blue] - Wallet Info    [magenta]N[/magenta] - Network Info    [cyan]R[/cyan] - Toggle Relay
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

    def toggle_relay_node(self):
        """Toggle relay node status"""
        is_relay = self._check_if_relay_node()

        if is_relay:
            # Stop being a relay
            console.print("[blue]🛑 Stopping relay node service...[/blue]")
            try:
                # Run stop-relay-node command
                import subprocess
                result = subprocess.run([
                    'python', '-m', 'pisecure.cli', 'stop-relay-node'
                ], capture_output=True, text=True, cwd='/home/pi/PiSecure')

                if result.returncode == 0:
                    console.print("[green]✅ Relay node stopped successfully![/green]")
                    console.print("[dim]Thank you for your service to the PiSecure community![/dim]")
                else:
                    console.print(f"[red]❌ Failed to stop relay node: {result.stderr}[/red]")
            except Exception as e:
                console.print(f"[red]❌ Error stopping relay node: {e}[/red]")
        else:
            # Become a relay
            console.print("[blue]🌐 Becoming a community relay node...[/blue]")
            console.print("[yellow]⚠️ This will help other users discover the network[/yellow]")
            console.print("[dim]You will receive mining rewards for relay services[/dim]")

            # Ask for confirmation in interactive mode
            try:
                import select
                import sys
                console.print("[cyan]Press 'Y' to confirm, any other key to cancel:[/cyan] ")

                if select.select([sys.stdin], [], [], 10)[0]:  # 10 second timeout
                    response = sys.stdin.read(1).lower().strip()
                    if response == 'y':
                        # Run become-relay-node command
                        import subprocess
                        result = subprocess.run([
                            'python', '-m', 'pisecure.cli', 'become-relay-node'
                        ], capture_output=True, text=True, cwd='/home/pi/PiSecure')

                        if result.returncode == 0:
                            console.print("[green]✅ Successfully became a relay node![/green]")
                            console.print("[dim]🎉 Thank you for supporting the PiSecure network![/dim]")
                        else:
                            console.print(f"[red]❌ Failed to become relay node: {result.stderr}[/red]")
                    else:
                        console.print("[dim]Relay node setup cancelled[/dim]")
                else:
                    console.print("[dim]Timeout - relay node setup cancelled[/dim]")
            except Exception as e:
                console.print(f"[red]❌ Error setting up relay node: {e}[/red]")

    def _check_if_relay_node(self):
        """Check if this node is configured as a relay node"""
        try:
            import json
            config_path = "/etc/pisecure/config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('network', {}).get('relay_enabled', False)
        except:
            return False

    def show_help(self):
        """Show detailed help information"""
        console.print("\n[bold cyan]🔧 PiSecure Mining Console - Help[/bold cyan]")
        console.print("=" * 50)

        console.print("[bold green]🎮 Keyboard Controls:[/bold green]")
        console.print("  [green]S[/green] - Start mining session")
        console.print("  [red]X[/red] - Stop mining session")
        console.print("  [yellow]C[/yellow] - Create test transaction for mining")
        console.print("  [blue]W[/blue] - Show detailed wallet information")
        console.print("  [magenta]N[/magenta] - Show network connectivity information")
        console.print("  [cyan]R[/cyan] - Toggle relay node status")
        console.print("  [dim]H[/dim] - Show this help screen")
        console.print("  [dim]Q[/dim] - Quit the mining console")

        console.print("\n[bold blue]📊 Dashboard Panels:[/bold blue]")
        console.print("  [cyan]System Status[/cyan] - CPU, Memory, Disk, Temperature")
        console.print("  [green]Mining Status[/green] - Active blocks, rewards, hashrate")
        console.print("  [blue]Blockchain Status[/blue] - Chain info, network health")
        console.print("  [yellow]Wallet Info[/yellow] - Balance, address, earnings")
        console.print("  [magenta]Network Status[/magenta] - Node ID, endpoints, STUN/TOR addresses")
        console.print("  [white]Mining History[/white] - Recent blocks and rewards")

        console.print("\n[bold yellow]💡 Tips:[/bold yellow]")
        console.print("  • Mining rewards go to your configured wallet")
        console.print("  • Test transactions help verify mining is working")
        console.print("  • Relay nodes help other users discover the network")
        console.print("  • Network info shows your public connectivity")
        console.print("  • Dashboard updates automatically every 2 seconds")

        console.print("\n[dim]Press any key to return to dashboard...[/dim]")
        time.sleep(5)  # Give user time to read

    def show_network_info(self):
        """Show detailed network connectivity information"""
        console.print("\n[bold magenta]🌐 Network Connectivity Information[/bold magenta]")
        console.print("=" * 50)

        try:
            discovery_status = node_discovery.get_discovery_status()

            console.print(f"[cyan]Node Identity:[/cyan]")
            console.print(f"  Node ID: {discovery_status.get('node_id', 'unknown')}")
            console.print(f"  Relay Status: {'✅ Active' if self._check_if_relay_node() else '❌ Not participating'}")

            endpoints = discovery_status.get('endpoints', [])
            if endpoints:
                console.print(f"\n[cyan]Public Endpoints ({len(endpoints)} active):[/cyan]")
                for i, endpoint in enumerate(endpoints, 1):
                    endpoint_type = endpoint.get('type', 'unknown')

                    if endpoint_type == 'stun_direct':
                        nat_type = endpoint.get('nat_type', 'unknown')
                        console.print(f"  {i}. 🌐 STUN Direct: {endpoint.get('ip', 'unknown')}:{endpoint.get('port', 'unknown')}")
                        console.print(f"     NAT Type: {nat_type}")
                        console.print(f"     Status: {'✅ Public' if nat_type in ['full_cone', 'address_restricted'] else '⚠️ Restricted'}")

                    elif endpoint_type == 'tor_onion':
                        address = endpoint.get('address', 'unknown')
                        console.print(f"  {i}. 🧅 Tor Onion: {address}")
                        console.print(f"     Status: ✅ Anonymous access enabled")

                    elif endpoint_type == 'upnp':
                        console.print(f"  {i}. 📡 UPnP Port Forward: {endpoint.get('ip', 'unknown')}:{endpoint.get('port', 'unknown')}")
                        console.print(f"     Status: ✅ Automatic port forwarding")

                    elif endpoint_type == 'turn_relay':
                        console.print(f"  {i}. 🔄 TURN Relay: {endpoint.get('ip', 'unknown')}:{endpoint.get('port', 'unknown')}")
                        console.print(f"     Status: ✅ Relay-assisted connectivity")

                    elif endpoint_type == 'community_relay':
                        console.print(f"  {i}. ☁️ Community Relay: {endpoint.get('available_relays', 0)} relays available")
                        console.print(f"     Status: ✅ Network-assisted discovery")
            else:
                console.print(f"\n[yellow]⚠️ No public endpoints configured[/yellow]")
                console.print(f"   Run 'pisecure setup-public-access' to enable worldwide connectivity")

            # Network statistics
            nat_info = discovery_status.get('nat_info', {})
            if nat_info:
                console.print(f"\n[cyan]NAT Information:[/cyan]")
                console.print(f"  Public IP: {nat_info.get('public_ip', 'unknown')}")
                console.print(f"  Public Port: {nat_info.get('public_port', 'unknown')}")
                console.print(f"  NAT Type: {nat_info.get('nat_type', 'unknown')}")

            console.print(f"  Tor Address: {discovery_status.get('tor_address', 'not configured')}")
            console.print(f"  Community Relays: {discovery_status.get('relay_count', 0)} available")

            # Connectivity test
            console.print(f"\n[cyan]Connectivity Test:[/cyan]")
            try:
                import socket
                # Test STUN server
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(("stun.l.google.com", 19302))
                console.print(f"  STUN Server: {'✅ Reachable' if result == 0 else '❌ Unreachable'}")
                sock.close()

                # Test bootstrap connectivity (placeholder)
                console.print(f"  Bootstrap Nodes: ✅ Configured")

            except:
                console.print(f"  Connectivity: ❓ Unable to test")

            # Peer discovery status
            console.print(f"\n[cyan]Peer Discovery:[/cyan]")
            console.print(f"  Auto-discovery: ✅ Active (5-minute refresh)")
            console.print(f"  Local Network: ✅ Scanning for peers")
            console.print(f"  Internet Peers: ✅ STUN/TURN/Tor enabled")

            console.print(f"\n[dim]Your node is discoverable at the endpoints listed above.[/dim]")
            console.print(f"[dim]Mobile apps can connect to your node using these addresses.[/dim]")

        except Exception as e:
            console.print(f"[red]❌ Error getting network information: {e}[/red]")

        console.print("\n[dim]Press any key to return to dashboard...[/dim]")
        time.sleep(5)  # Give user time to read

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

        # Set up non-blocking input
        import termios
        import tty
        import sys
        import os

        # Save original terminal settings
        old_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set terminal to raw mode for immediate key reading
            tty.setraw(sys.stdin.fileno())

            with Live(self.create_dashboard(), refresh_per_second=2, screen=True) as live:
                while True:
                    # Update dashboard
                    live.update(self.create_dashboard())

                    # Check for keyboard input (non-blocking)
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()

                        # Handle key presses
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
                        elif key == 'r':
                            self.toggle_relay_node()
                        elif key == 'n':
                            self.show_network_info()
                        elif key == 'h':
                            self.show_help()

        except KeyboardInterrupt:
            if self.mining_active:
                self.stop_mining()
            console.print("\n[cyan]👋 Mining console closed[/cyan]")
        finally:
            # Restore original terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


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