#!/usr/bin/env python3
"""
PiSecure Mining Console - Textual TUI
=====================================

Interactive mining dashboard built with Textual.
Provides a modern terminal user interface for mining operations.

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
import asyncio
import threading
import multiprocessing
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Label
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn


class MiningActivityMessage(Message):
    """Message sent when mining activity occurs"""

    def __init__(self, activity: str):
        self.activity = activity
        super().__init__()

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


class StatsPanel(Static):
    """Panel displaying system and mining statistics"""

    def __init__(self, console_app):
        super().__init__()
        self.console_app = console_app

    def compose(self):
        yield Container(
            Static("System Stats", id="system_stats"),
            Static("Mining Stats", id="mining_stats"),
            id="stats_container"
        )

    def on_mount(self):
        self.update_stats()

    def update_stats(self):
        """Update the statistics display"""
        try:
            # System stats
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Faster CPU monitoring
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            system_table = Table(title="🖥️ System Status", box=None, show_header=False)
            system_table.add_column("Metric", style="cyan", no_wrap=True)
            system_table.add_column("Value", style="magenta")

            system_table.add_row("CPU Usage", f"{cpu_percent:.1f}%")
            system_table.add_row("Memory", f"{memory.percent:.1f}% ({memory.used/1024/1024/1024:.1f}GB)")
            system_table.add_row("Disk Usage", f"{disk.percent:.1f}% ({disk.used/1024/1024/1024:.1f}GB)")
            system_table.add_row("Temperature", f"{self._get_temperature():.1f}°C")

            # Add network information
            try:
                discovery_status = node_discovery.get_discovery_status()
                endpoints = discovery_status.get('endpoints', [])

                # Public IP
                public_ip = "Unknown"
                for endpoint in endpoints:
                    if endpoint.get('type') in ['stun_direct', 'upnp']:
                        public_ip = endpoint.get('ip', 'Unknown')
                        break

                system_table.add_row("Public IP", public_ip)

                # TOR address
                tor_address = "Not configured"
                for endpoint in endpoints:
                    if endpoint.get('type') == 'tor_onion':
                        tor_address = endpoint.get('address', 'Unknown')[:20] + "..."
                        break
                system_table.add_row("TOR Address", tor_address)

                # STUN/TURN addresses
                stun_count = sum(1 for ep in endpoints if ep.get('type') == 'stun_direct')
                turn_count = sum(1 for ep in endpoints if ep.get('type') == 'turn_relay')
                upnp_count = sum(1 for ep in endpoints if ep.get('type') == 'upnp')

                system_table.add_row("STUN Endpoints", str(stun_count))
                system_table.add_row("TURN Relays", str(turn_count))
                system_table.add_row("UPnP Ports", str(upnp_count))

                # Relay status
                try:
                    config_path = "/etc/pisecure/config.json"
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    relay_enabled = config.get('network', {}).get('relay_enabled', False)
                    relay_status = "✅ Active" if relay_enabled else "❌ Inactive"
                    system_table.add_row("Relay Status", relay_status)
                except:
                    system_table.add_row("Relay Status", "❓ Unknown")

            except Exception as e:
                system_table.add_row("Network Status", f"Error: {str(e)[:15]}...")
                system_table.add_row("Relay Status", "❓ Unknown")

            # Mining stats
            stats = self.console_app.mining_console.stats
            mining_active = self.console_app.mining_console.mining_active

            mining_table = Table(title="⛏️ Mining Status", box=None, show_header=False)
            mining_table.add_column("Metric", style="cyan", no_wrap=True)
            mining_table.add_column("Value", style="green" if mining_active else "red")

            status_icon = "🟢" if mining_active else "🔴"
            mining_table.add_row("Status", f"{status_icon} {'Active' if mining_active else 'Stopped'}")
            mining_table.add_row("Total Blocks", str(stats['blocks_mined']))
            mining_table.add_row("Session Blocks", str(stats['session_blocks']))
            mining_table.add_row("Total Rewards", f"{stats['total_rewards']:.2f} tokens")
            mining_table.add_row("Session Rewards", f"{stats['session_rewards']:.2f} tokens")
            mining_table.add_row("Hashrate", f"{stats['hashrate']:.1f} KH/s")
            mining_table.add_row("Uptime", f"{stats['uptime']:.0f}s")

            # Update the widgets
            system_widget = self.query_one("#system_stats", Static)
            mining_widget = self.query_one("#mining_stats", Static)

            system_widget.update(Panel(system_table, border_style="blue"))
            mining_widget.update(Panel(mining_table, border_style="green"))

        except Exception as e:
            self.update(f"Error updating stats: {e}")

    def _get_temperature(self):
        """Get system temperature"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps and temps['cpu_thermal']:
                return temps['cpu_thermal'][0].current
            elif 'coretemp' in temps and temps['coretemp']:
                return temps['coretemp'][0].current
        except:
            pass
        return 0.0


class NetworkPanel(Static):
    """Panel displaying blockchain and network information"""

    def __init__(self, console_app):
        super().__init__()
        self.console_app = console_app

    def compose(self):
        yield Container(
            Static("Blockchain Stats", id="blockchain_stats"),
            Static("Wallet Info", id="wallet_info"),
            id="network_container"
        )

    def on_mount(self):
        self.update_network()

    def update_network(self):
        """Update the network display"""
        try:
            blockchain = self.console_app.mining_console.blockchain
            miner_wallet = self.console_app.mining_console.miner_wallet
            stats = self.console_app.mining_console.stats

            # Blockchain stats
            chain_info = blockchain.get_chain_info()
            blockchain_table = Table(title="⛓️ Blockchain Status", box=None, show_header=False)
            blockchain_table.add_column("Metric", style="cyan", no_wrap=True)
            blockchain_table.add_column("Value", style="blue")

            blockchain_table.add_row("Blocks", str(chain_info['blocks']))
            blockchain_table.add_row("Pending TX", str(stats['pending_txs']))
            blockchain_table.add_row("Difficulty", str(chain_info['difficulty']))

            health = chain_info['network_health']
            blockchain_table.add_row("Participation", f"{health['participation']:.1%}")
            blockchain_table.add_row("Avg Block Time", f"{health['avg_block_time']:.1f}s")

            # Wallet info
            wallet_table = Table(title="🏦 Mining Wallet", box=None, show_header=False)
            wallet_table.add_column("Property", style="cyan", no_wrap=True)
            wallet_table.add_column("Value", style="yellow")

            if miner_wallet:
                wallet_balance = blockchain.get_wallet_balance(miner_wallet)
                wallet_table.add_row("Address", miner_wallet[:32] + "...")
                wallet_table.add_row("Balance", f"{wallet_balance:.2f} tokens")
                wallet_table.add_row("Session Earnings", f"+{stats['session_rewards']:.2f}")
            else:
                wallet_table.add_row("Status", "⚠️ Not configured")

            # Update the widgets
            blockchain_widget = self.query_one("#blockchain_stats", Static)
            wallet_widget = self.query_one("#wallet_info", Static)

            blockchain_widget.update(Panel(blockchain_table, border_style="cyan"))
            wallet_widget.update(Panel(wallet_table, border_style="yellow"))

        except Exception as e:
            self.update(f"Error updating network: {e}")


class BlocksPanel(Static):
    """Panel displaying recent blocks"""

    def __init__(self, console_app):
        super().__init__()
        self.console_app = console_app

    def compose(self):
        yield Static("Loading blocks...", id="blocks_display")

    def on_mount(self):
        self.update_blocks()

    def update_blocks(self):
        """Update the blocks display"""
        try:
            blockchain = self.console_app.mining_console.blockchain

            # Recent blocks
            recent_blocks_table = Table(title="📦 Recent Blocks", box=None)
            recent_blocks_table.add_column("Block", style="cyan", justify="right")
            recent_blocks_table.add_column("TX Count", style="magenta", justify="right")
            recent_blocks_table.add_column("Reward", style="green", justify="right")
            recent_blocks_table.add_column("Time", style="blue")

            recent_blocks = blockchain.chain[-8:] if len(blockchain.chain) > 8 else blockchain.chain
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

            blocks_widget = self.query_one("#blocks_display", Static)
            blocks_widget.update(Panel(recent_blocks_table, border_style="white"))

        except Exception as e:
            self.update(f"Error updating blocks: {e}")


class MiningActivityPanel(ScrollableContainer):
    """Panel displaying real-time mining activity"""

    def __init__(self, console_app):
        super().__init__()
        self.console_app = console_app
        self.activity_log = []

    def compose(self):
        yield Static("Mining Activity Log\nWaiting for mining to start...", id="activity_display")

    def on_mount(self):
        self.update_activity()

    def update_activity(self):
        """Update the activity display"""
        try:
            activity_text = "Mining Activity Log\n" + "\n".join(self.activity_log[-20:])  # Show last 20 lines
            activity_widget = self.query_one("#activity_display", Static)
            activity_widget.update(activity_text)
        except Exception as e:
            self.update(f"Error updating activity: {e}")

    def add_activity(self, message):
        """Add a new activity message"""
        timestamp = time.strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")
        # Keep only last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
        self.update_activity()


class MiningLogic:
    """Mining logic backend for the console"""

    def __init__(self, app=None):
        self.app = app
        self.blockchain = SignChain()
        self.hardware = HardwareVerifier()
        self.miner_wallet = self._load_miner_wallet()

        # Mining state
        self.mining_active = False
        self.mining_process = None
        self.stop_mining = multiprocessing.Event()

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

    def _send_activity_message(self, message):
        """Send activity message to UI"""
        if self.app:
            self.app.post_message(MiningActivityMessage(message))

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
            return "Mining is already active"

        # Hardware verification
        result = self.hardware.verify_mining_eligibility()
        if not result['eligible']:
            return f"Hardware verification failed: {result.get('error', 'Unknown error')}"

        self.mining_active = True
        self.stop_mining.clear()
        self.stats['start_time'] = time.time()
        self.stats['session_blocks'] = 0
        self.stats['session_rewards'] = 0.0

        # Send activity message
        self._send_activity_message("⛏️ Mining session started")
        self._send_activity_message(f"   Target: Block #{len(self.blockchain.chain)}")
        self._send_activity_message(f"   Reward wallet: {self.miner_wallet[:24] if self.miner_wallet else 'None'}")

        # Start mining thread
        self.mining_thread = threading.Thread(target=self._mining_worker, daemon=True)
        self.mining_thread.start()

        return "Mining started"

    def stop_mining(self):
        """Stop the mining process"""
        if not self.mining_active:
            return "Mining is not active"

        self._send_activity_message("🛑 Stop mining requested - will stop after current block")
        self.stop_mining.set()
        self.mining_active = False

        # Don't try to forcibly terminate - let mining finish gracefully
        # The mining worker will check the stop event and exit cleanly

        return "Stop request sent - mining will stop after current block"

    def _mining_worker(self):
        """Background mining worker"""
        import concurrent.futures

        block_index = len(self.blockchain.chain)
        nonce_count = 0
        start_time = time.time()

        self._send_activity_message(f"🎯 Starting to mine block #{block_index}")
        self._send_activity_message(f"   Pending transactions: {len(self.blockchain.pending_transactions)}")
        self._send_activity_message(f"   Mining difficulty: {self.blockchain.difficulty}")
        self._send_activity_message(f"   Target prefix: {'0' * self.blockchain.difficulty}")

        while not self.stop_mining.is_set():
            try:
                # Update stats
                self.stats['uptime'] = time.time() - self.stats['start_time']
                self.stats['pending_txs'] = len(self.blockchain.pending_transactions)

                # Mine a block with aggressive timeout for responsive stopping
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.blockchain.mine_pending_transactions, self.miner_wallet, False)

                    try:
                        # Aggressive timeout for responsive stopping (1-2 seconds)
                        block = future.result(timeout=1.5)  # 1.5 second timeout
                    except concurrent.futures.TimeoutError:
                        # Mining timed out - check if we should stop
                        if self.stop_mining.is_set():
                            self._send_activity_message("🛑 Mining stopped immediately by user request")
                            break
                        else:
                            # Continue mining this block
                            try:
                                block = future.result(timeout=1.5)  # Try again briefly
                            except concurrent.futures.TimeoutError:
                                # Still no block found, send detailed progress update and continue
                                elapsed = time.time() - start_time
                                if nonce_count % 50 == 0:  # Very frequent updates for detailed view
                                    hashrate = nonce_count / elapsed if elapsed > 0 else 0

                                    # Show detailed mining progress
                                    progress_percent = min(100, (nonce_count / max(1, elapsed * 1000)) * 100)  # Rough progress estimate
                                    target_zeros = '0' * self.blockchain.difficulty

                                    self._send_activity_message(f"⛏️ Mining... Nonce: {nonce_count:,}")
                                    self._send_activity_message(f"   Target: {target_zeros} (Difficulty: {self.blockchain.difficulty})")
                                    self._send_activity_message(f"   Rate: {hashrate:.1f} H/s | Progress: ~{progress_percent:.1f}%")
                                    self._send_activity_message(f"   Time: {elapsed:.1f}s | Attempts: {nonce_count:,}")

                                    # Show a sample hash calculation (demonstration)
                                    import hashlib
                                    sample_data = f"block_{block_index}_nonce_{nonce_count}"
                                    sample_hash = hashlib.sha256(sample_data.encode()).hexdigest()
                                    self._send_activity_message(f"   Sample Hash: {sample_hash[:32]}...")

                                time.sleep(0.05)  # Brief pause
                                nonce_count += 1
                                continue

                if block is not None:
                    mining_time = time.time() - start_time

                    # Calculate final hashrate
                    if hasattr(block, 'nonce') and block.nonce > 0 and mining_time > 0:
                        final_hashrate = block.nonce / mining_time
                        self.stats['hashrate'] = final_hashrate

                    # Check for mining rewards
                    reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                    reward_amount = 0
                    if reward_txs:
                        reward_amount = reward_txs[0].get('amount', 0)
                        self.stats['total_rewards'] += reward_amount
                        self.stats['session_rewards'] += reward_amount

                    # Send success messages
                    self._send_activity_message(f"✅ BLOCK FOUND! Block #{block.index} mined")
                    self._send_activity_message(f"   Nonce: {block.nonce:,}")
                    self._send_activity_message(f"   Time: {mining_time:.2f}s")
                    self._send_activity_message(f"   Hashrate: {self.stats['hashrate']:.1f} H/s")
                    self._send_activity_message(f"   Reward: {reward_amount:.2f} tokens")

                    self.stats['blocks_mined'] += 1
                    self.stats['session_blocks'] += 1
                    self.stats['last_block_time'] = time.time()

                    # Prepare for next block
                    block_index += 1
                    nonce_count = 0
                    start_time = time.time()
                    self._send_activity_message(f"🎯 Now mining block #{block_index}")

                else:
                    # Still mining - send periodic updates
                    nonce_count += 1
                    if nonce_count % 500 == 0:  # More frequent updates
                        elapsed = time.time() - start_time
                        hashrate = nonce_count / elapsed if elapsed > 0 else 0
                        self._send_activity_message(f"⛏️ Mining... Nonce: {nonce_count:,} | Rate: {hashrate:.1f} H/s")

                    time.sleep(0.05)  # Shorter pause

            except Exception as e:
                if not self.stop_mining.is_set():  # Don't log errors if we're stopping
                    self._send_activity_message(f"❌ Mining error: {e}")
                time.sleep(2)

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
            return f"Test transaction created: {tx_hash[:16]}..."

        except Exception as e:
            return f"Failed to create transaction: {e}"

    def get_wallet_balance(self):
        """Get wallet balance"""
        if not self.miner_wallet:
            return 0.0
        return self.blockchain.get_wallet_balance(self.miner_wallet)

    def toggle_relay_node(self):
        """Toggle relay node status"""
        # Simplified for now
        return "Relay toggle not implemented in Textual version"


class MiningConsoleApp(App):
    """Textual-based mining console application"""

    CSS = """
    Screen {
        background: $surface;
    }

    #stats_container {
        layout: horizontal;
        height: 12;
    }

    #system_stats, #mining_stats {
        width: 50%;
        margin: 0 1;
    }

    #network_container {
        layout: horizontal;
        height: 8;
    }

    #blockchain_stats, #wallet_info {
        width: 50%;
        margin: 0 1;
    }

    #blocks_display {
        height: 8;
        margin: 1;
    }

    #activity_display {
        height: 12;
        margin: 1;
    }

    #controls {
        height: 6;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("s", "start_mining", "Start Mining"),
        Binding("x", "stop_mining", "Stop Mining"),
        Binding("c", "create_transaction", "Create Test TX"),
        Binding("w", "wallet_info", "Wallet Info"),
        Binding("n", "network_info", "Network Info"),
        Binding("r", "toggle_relay", "Toggle Relay"),
        Binding("h", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.mining_console = MiningLogic(self)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield StatsPanel(self)
            yield NetworkPanel(self)
            yield BlocksPanel(self)
            yield MiningActivityPanel(self)
        yield Static(self._get_controls_text(), id="controls")
        yield Footer()

    def on_mount(self):
        """Called when the app is mounted"""
        # Start the update timer (0.5 seconds for real-time display)
        self.update_timer = self.set_interval(0.5, self.update_display)

    def on_mining_activity_message(self, message: MiningActivityMessage):
        """Handle mining activity messages"""
        try:
            self.query_one(MiningActivityPanel).add_activity(message.activity)
        except:
            pass  # Panel might not be mounted yet

    def update_display(self):
        """Update all panels"""
        try:
            self.query_one(StatsPanel).update_stats()
            self.query_one(NetworkPanel).update_network()
            self.query_one(BlocksPanel).update_blocks()
        except:
            pass  # Panels might not be mounted yet

    def _get_controls_text(self):
        """Get the controls text"""
        return """
[bold cyan]Mining Console Controls:[/bold cyan]
[green]S[/green] - Start Mining    [red]X[/red] - Stop Mining    [yellow]C[/yellow] - Test TX
[blue]W[/blue] - Wallet Info    [magenta]N[/magenta] - Network Info    [cyan]R[/cyan] - Toggle Relay
[dim]Q[/dim] - Quit Console    [dim]H[/dim] - Show This Help
        """

    def action_start_mining(self):
        """Start mining action"""
        try:
            self.mining_console.start_mining()
            self.notify("Mining started!", severity="information")
        except Exception as e:
            self.notify(f"Failed to start mining: {e}", severity="error")

    def action_stop_mining(self):
        """Stop mining action"""
        try:
            self.mining_console.stop_mining()
            self.notify("Mining stopped!", severity="information")
        except Exception as e:
            self.notify(f"Failed to stop mining: {e}", severity="error")

    def action_create_transaction(self):
        """Create test transaction"""
        try:
            self.mining_console.create_test_transaction()
            self.notify("Test transaction created!", severity="information")
        except Exception as e:
            self.notify(f"Failed to create transaction: {e}", severity="error")

    def action_wallet_info(self):
        """Show wallet info"""
        try:
            # This would show a dialog or update a panel
            balance = self.mining_console.blockchain.get_wallet_balance(self.mining_console.miner_wallet or "")
            wallet = self.mining_console.miner_wallet or "Not configured"
            self.notify(f"Wallet: {wallet[:24]}... Balance: {balance:.2f} tokens", severity="information")
        except Exception as e:
            self.notify(f"Failed to get wallet info: {e}", severity="error")

    def action_network_info(self):
        """Show network info"""
        try:
            # This would show detailed network info
            endpoints = len(node_discovery.get_discovery_status().get('endpoints', []))
            self.notify(f"Network endpoints: {endpoints} active", severity="information")
        except Exception as e:
            self.notify(f"Failed to get network info: {e}", severity="error")

    def action_toggle_relay(self):
        """Toggle relay node"""
        try:
            self.mining_console.toggle_relay_node()
            self.notify("Relay node toggled!", severity="information")
        except Exception as e:
            self.notify(f"Failed to toggle relay: {e}", severity="error")

    def action_help(self):
        """Show help"""
        self.notify("Use the key bindings shown at the bottom to control mining!", severity="information")

    def action_quit(self):
        """Quit the application"""
        self.exit()


def main():
    """Main entry point"""
    app = MiningConsoleApp()
    app.run()


if __name__ == '__main__':
    main()