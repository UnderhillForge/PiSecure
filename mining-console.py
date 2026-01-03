#!/usr/bin/env python3
"""
PiSecure Mining Console
=======================

Interactive mining dashboard with real-time stats, controls, and monitoring.
Provides a Textual-based terminal user interface for mining operations.

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
import sys
import os
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Log, Button, Label
import logging
from datetime import datetime
from textual.binding import Binding
from textual import events
from textual.timer import Timer
from textual.css.query import NoMatches
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.align import Align

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


class TextualLogHandler(logging.Handler):
    """Custom logging handler that writes to Textual Log widget"""

    def __init__(self, log_widget):
        super().__init__()
        self.log_widget = log_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        """Emit a log record to the Textual log widget"""
        try:
            msg = self.format(record)
            # Add the message to the log widget
            self.log_widget.write(f"[{record.levelname}] {msg}")
        except Exception:
            self.handleError(record)


class MiningApp(App):
    """Textual-based mining console application"""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary-darken-2;
        color: $text;
        text-style: bold;
        border-bottom: solid $primary;
    }

    Footer {
        background: $primary-darken-2;
        color: $text;
        border-top: solid $primary;
    }

    /* Main dashboard layout - btop-inspired */
    #dashboard {
        layout: grid;
        grid-size: 4 3;
        grid-gutter: 0;
        height: 100%;
    }

    /* Top row - key metrics */
    #cpu-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    #memory-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    #mining-status-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
        column-span: 2;
    }

    /* Second row - blockchain and wallet */
    #blockchain-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    #wallet-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    #network-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    #uptime-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
    }

    /* Third row - performance graphs */
    #hashrate-graph {
        border: solid $primary;
        padding: 1;
        background: $panel;
        row-span: 2;
    }

    #reward-graph {
        border: solid $primary;
        padding: 1;
        background: $panel;
        row-span: 2;
    }

    #blocks-graph {
        border: solid $primary;
        padding: 1;
        background: $panel;
        column-span: 2;
    }

    /* Fourth row - mining log */
    #mining-log-panel {
        border: solid $primary;
        padding: 1;
        background: $panel;
        column-span: 4;
        height: 100%;
    }

    #mining-log {
        height: 100%;
        background: $surface;
        color: $text;
    }

    /* Panel headers */
    .panel-header {
        text-style: bold;
        color: $primary;
        background: $primary-darken-3;
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }

    /* Status indicators */
    .status-active {
        color: $success;
        text-style: bold;
    }

    .status-inactive {
        color: $error;
        text-style: bold;
    }

    .metric-value {
        color: $accent;
        text-style: bold;
    }

    .metric-label {
        color: $text-muted;
        text-style: dim;
    }

    /* Progress bars */
    .progress-bar {
        width: 100%;
        height: 1;
        background: $surface-darken-2;
    }

    .progress-fill {
        background: $primary;
        height: 1;
    }

    /* Charts and graphs styling */
    .chart {
        width: 100%;
        height: 3;
        background: $surface;
        border: solid $primary-darken-2;
    }
    """

    BINDINGS = [
        Binding("s", "start_mining", "Start Mining"),
        Binding("x", "stop_mining", "Stop Mining"),
        Binding("c", "create_test_tx", "Create Test TX"),
        Binding("w", "show_wallet", "Show Wallet"),
        Binding("n", "show_network", "Show Network"),
        Binding("r", "toggle_relay", "Toggle Relay"),
        Binding("h", "show_help", "Show Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.blockchain = SignChain()
        self.hardware = HardwareVerifier()
        self.miner_wallet = self._load_miner_wallet()

        # Mining state
        self.mining_active = False
        self.mining_thread = None
        self.stop_event = threading.Event()

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

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger('mining_console')

    def _setup_logging(self):
        """Setup logging to write to the Textual Log widget"""
        # This will be called after UI is ready in on_mount
        pass

    def _load_miner_wallet(self):
        """Load miner wallet address from config"""
        try:
            config_path = "/etc/pisecure/config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('mining', {}).get('wallet_address')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def compose(self) -> ComposeResult:
        """Create the btop-inspired dashboard layout"""
        yield Header()

        # Main dashboard grid (4 columns x 3 rows)
        with Container(id="dashboard"):
            # Top row - CPU, Memory, Mining Status (spans 2 columns)
            yield Static(self._create_cpu_panel(), id="cpu-panel")
            yield Static(self._create_memory_panel(), id="memory-panel")
            yield Static(self._create_mining_status_panel(), id="mining-status-panel")

            # Second row - Blockchain, Wallet, Network, Uptime
            yield Static(self._create_blockchain_panel(), id="blockchain-panel")
            yield Static(self._create_wallet_panel(), id="wallet-panel")
            yield Static(self._create_network_panel(), id="network-panel")
            yield Static(self._create_uptime_panel(), id="uptime-panel")

            # Third row - Hashrate Graph, Reward Graph, Blocks Graph (spans 2 columns)
            yield Static(self._create_hashrate_graph(), id="hashrate-graph")
            yield Static(self._create_reward_graph(), id="reward-graph")
            yield Static(self._create_blocks_graph(), id="blocks-graph")

            # Fourth row - Mining Log (spans all 4 columns)
            with Container(id="mining-log-panel"):
                yield Log(id="mining-log")

        yield Footer()

    # Btop-style panel methods
    def _create_cpu_panel(self):
        """Create CPU monitoring panel (btop style)"""
        cpu_percent = psutil.cpu_percent(interval=1)

        content = f"""
[bold blue]CPU[/bold blue]
[bright_cyan]{cpu_percent:5.1f}%[/bright_cyan]

[bright_green]├─[/bright_green] Usage: {cpu_percent:.1f}%
[bright_green]├─[/bright_green] Cores: {psutil.cpu_count()}
[bright_green]└─[/bright_green] Freq: {psutil.cpu_freq().current:.0f}MHz
        """.strip()

        return content

    def _create_memory_panel(self):
        """Create memory monitoring panel (btop style)"""
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        mem_used_gb = memory.used / 1024 / 1024 / 1024
        mem_total_gb = memory.total / 1024 / 1024 / 1024

        content = f"""
[bold green]MEM[/bold green]
[bright_green]{mem_percent:5.1f}%[/bright_green]

[bright_cyan]├─[/bright_cyan] Used: {mem_used_gb:.1f}GB
[bright_cyan]├─[/bright_cyan] Total: {mem_total_gb:.1f}GB
[bright_cyan]└─[/bright_cyan] Free: {memory.available/1024/1024/1024:.1f}GB
        """.strip()

        return content

    def _create_mining_status_panel(self):
        """Create mining status panel (spans 2 columns)"""
        status_icon = "🟢" if self.mining_active else "🔴"
        status_text = "Active" if self.mining_active else "Stopped"

        content = f"""
[bold yellow]MINING STATUS[/bold yellow]
{status_icon} {status_text}

[bright_magenta]├─[/bright_magenta] Blocks: {self.stats['session_blocks']}/{self.stats['blocks_mined']}
[bright_magenta]├─[/bright_magenta] Rewards: {self.stats['session_rewards']:.2f} tokens
[bright_magenta]├─[/bright_magenta] Hashrate: {self.stats['hashrate']:.1f} KH/s
[bright_magenta]└─[/bright_magenta] Uptime: {self.stats['uptime']:.0f}s
        """.strip()

        return content

    def _create_blockchain_panel(self):
        """Create blockchain information panel"""
        chain_info = self.blockchain.get_chain_info()

        content = f"""
[bold cyan]BLOCKCHAIN[/bold cyan]

[bright_blue]├─[/bright_blue] Height: {chain_info['blocks']}
[bright_blue]├─[/bright_blue] Pending: {self.stats['pending_txs']}
[bright_blue]├─[/bright_blue] Difficulty: {chain_info['difficulty']}
[bright_blue]└─[/bright_blue] Health: {chain_info['network_health']['participation']:.1%}
        """.strip()

        return content

    def _create_wallet_panel(self):
        """Create wallet information panel"""
        if self.miner_wallet:
            wallet_balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            content = f"""
[bold magenta]WALLET[/bold magenta]

[bright_magenta]├─[/bright_magenta] Balance: {wallet_balance:.2f}
[bright_magenta]├─[/bright_magenta] Earnings: +{self.stats['session_rewards']:.2f}
[bright_magenta]├─[/bright_magenta] Address: {self.miner_wallet[:12]}...
[bright_magenta]└─[/bright_magenta] Status: ✓ Connected
            """.strip()
        else:
            content = f"""
[bold magenta]WALLET[/bold magenta]

[bright_red]├─[/bright_red] Status: ⚠️ Not configured
[bright_red]├─[/bright_red] Balance: N/A
[bright_red]├─[/bright_red] Earnings: N/A
[bright_red]└─[/bright_red] Address: N/A
            """.strip()

        return content

    def _create_network_panel(self):
        """Create network status panel"""
        try:
            discovery_status = node_discovery.get_discovery_status()
            endpoints = len(discovery_status.get('endpoints', []))
            relay_status = "✓" if self._check_if_relay_node() else "✗"

            content = f"""
[bold red]NETWORK[/bold red]

[bright_red]├─[/bright_red] Peers: {endpoints}
[bright_red]├─[/bright_red] Relay: {relay_status}
[bright_red]├─[/bright_red] Node ID: {discovery_status.get('node_id', 'unknown')[:8]}...
[bright_red]└─[/bright_red] Status: {'🟢' if endpoints > 0 else '🔴'} Connected
            """.strip()
        except:
            content = f"""
[bold red]NETWORK[/bold red]

[bright_red]├─[/bright_red] Peers: Unknown
[bright_red]├─[/bright_red] Relay: Unknown
[bright_red]├─[/bright_red] Node ID: Unknown
[bright_red]└─[/bright_red] Status: 🔴 Offline
            """.strip()

        return content

    def _create_uptime_panel(self):
        """Create uptime and temperature panel"""
        temp = self._get_temperature()
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_hours = uptime_seconds / 3600

        content = f"""
[bold white]SYSTEM[/bold white]

[bright_white]├─[/bright_white] Uptime: {uptime_hours:.1f}h
[bright_white]├─[/bright_white] Temperature: {temp:.1f}°C
[bright_white]├─[/bright_white] Load: {os.getloadavg()[0]:.2f}
[bright_white]└─[/bright_white] Processes: {len(psutil.pids())}
        """.strip()

        return content

    def _create_hashrate_graph(self):
        """Create hashrate graph panel"""
        hashrate = self.stats['hashrate']
        # Create a simple ASCII graph
        graph_height = 3
        max_hashrate = max(10, hashrate * 1.5)  # Auto-scale

        content = f"""
[bold blue]HASHRATE[/bold blue]
[bright_blue]{hashrate:.1f} KH/s[/bright_blue]

[bright_cyan]{self._create_mini_graph(hashrate, max_hashrate, graph_height)}[/bright_cyan]
        """.strip()

        return content

    def _create_reward_graph(self):
        """Create reward graph panel"""
        rewards = self.stats['session_rewards']
        # Simple reward tracking
        content = f"""
[bold green]REWARDS[/bold green]
[bright_green]{rewards:.2f} tokens[/bright_green]

[bright_green]{self._create_reward_bar(rewards)}[/bright_green]
        """.strip()

        return content

    def _create_blocks_graph(self):
        """Create blocks mined graph (spans 2 columns)"""
        blocks = self.stats['session_blocks']
        content = f"""
[bold yellow]BLOCKS MINED[/bold yellow]
[bright_yellow]{blocks} blocks[/bright_yellow]

[bright_yellow]{self._create_blocks_display(blocks)}[/bright_yellow]
        """.strip()

        return content



    def _create_mini_graph(self, value, max_value, height):
        """Create a simple ASCII graph"""
        if max_value == 0:
            return "▁" * 10

        normalized = min(1.0, value / max_value)
        filled = int(normalized * 10)
        return "█" * filled + "░" * (10 - filled)

    def _create_reward_bar(self, rewards):
        """Create a reward progress bar"""
        max_reward = max(10, rewards * 1.5)
        filled = int((rewards / max_reward) * 10)
        return "█" * filled + "░" * (10 - filled) + f" {rewards:.1f}"

    def _create_blocks_display(self, blocks):
        """Create blocks display"""
        block_icons = "▣" * min(blocks, 20)
        remaining = max(0, 20 - blocks)
        block_icons += "▢" * remaining
        return block_icons + f" {blocks} mined"

    def _create_mining_stats(self):
        """Create mining statistics panel"""
        status_icon = "🟢" if self.mining_active else "🔴"

        table = Table(title="⛏️ Mining Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green" if self.mining_active else "red")

        table.add_row("Status", f"{status_icon} {'Active' if self.mining_active else 'Stopped'}")
        table.add_row("Total Blocks", str(self.stats['blocks_mined']))
        table.add_row("Session Blocks", str(self.stats['session_blocks']))
        table.add_row("Total Rewards", f"{self.stats['total_rewards']:.2f} tokens")
        table.add_row("Session Rewards", f"{self.stats['session_rewards']:.2f} tokens")
        table.add_row("Hashrate", f"{self.stats['hashrate']:.1f} KH/s")
        table.add_row("Uptime", f"{self.stats['uptime']:.0f}s")

        return Panel(table, title="Mining Status")

    def _create_blockchain_stats(self):
        """Create blockchain statistics panel"""
        chain_info = self.blockchain.get_chain_info()

        table = Table(title="⛓️ Blockchain Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="blue")

        table.add_row("Blocks", str(chain_info['blocks']))
        table.add_row("Pending TX", str(self.stats['pending_txs']))
        table.add_row("Difficulty", str(chain_info['difficulty']))

        health = chain_info['network_health']
        table.add_row("Participation", f"{health['participation']:.1%}")
        table.add_row("Avg Block Time", f"{health['avg_block_time']:.1f}s")

        return Panel(table, title="Blockchain Status")

    def _create_wallet_stats(self):
        """Create wallet statistics panel"""
        table = Table(title="🏦 Mining Wallet")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        if self.miner_wallet:
            wallet_balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            table.add_row("Address", self.miner_wallet[:32] + "...")
            table.add_row("Balance", f"{wallet_balance:.2f} tokens")
            table.add_row("Session Earnings", f"+{self.stats['session_rewards']:.2f}")
        else:
            table.add_row("Status", "⚠️ Not configured")

        return Panel(table, title="Wallet Info")

    def _create_blocks_table(self):
        """Create recent blocks table"""
        table = Table(title="📦 Recent Blocks")
        table.add_column("Block", style="cyan", justify="right")
        table.add_column("TX Count", style="magenta", justify="right")
        table.add_column("Reward", style="green", justify="right")
        table.add_column("Time", style="blue")

        recent_blocks = self.blockchain.chain[-8:] if len(self.blockchain.chain) > 8 else self.blockchain.chain
        for block in reversed(recent_blocks):
            tx_count = len([tx for tx in block.transactions if tx.get('type') != 'mining_reward'])
            reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
            reward_amount = reward_txs[0].get('amount', 0) if reward_txs else 0

            block_time = time.ctime(block.timestamp)
            table.add_row(
                str(block.index),
                str(tx_count),
                f"{reward_amount:.1f}",
                block_time
            )

        return Panel(table, title="Mining History")

    def _create_controls(self):
        """Create control buttons panel"""
        controls = """
[bold cyan]Mining Console Controls:[/bold cyan]
[green]S[/green] - Start Mining    [red]X[/red] - Stop Mining    [yellow]C[/yellow] - Test TX
[blue]W[/blue] - Wallet Info    [magenta]N[/magenta] - Network Info    [cyan]R[/cyan] - Toggle Relay
[dim]Q[/dim] - Quit Console    [dim]H[/dim] - Show Help
        """
        return Panel(controls, title="Controls")

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

    def on_mount(self):
        """Called when the app is mounted"""
        self.title = "🔐 PiSecure Mining Console"
        self.sub_title = "Real-time mining dashboard"

        # Setup logging now that UI is ready
        log_widget = self.query_one("#mining-log", Log)
        handler = TextualLogHandler(log_widget)
        handler.setLevel(logging.DEBUG)

        # Configure logger
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        self.logger.propagate = False

        # Log startup information
        self.logger.info("PiSecure Mining Console started")
        self.logger.info(f"Blockchain height: {len(self.blockchain.chain)}")
        self.logger.info(f"Miner wallet: {self.miner_wallet or 'Not configured'}")

        # Start update timer
        self.update_timer = self.set_interval(2.0, self.update_stats)

        # Check hardware verification
        self._verify_hardware()

    def _verify_hardware(self):
        """Verify hardware requirements"""
        result = self.hardware.verify_mining_eligibility()
        if not result['eligible']:
            self.notify(
                f"❌ Hardware verification failed: {result.get('error', 'Unknown error')}",
                severity="error",
                timeout=10
            )

    def update_stats(self):
        """Update statistics periodically"""
        self.stats['uptime'] = time.time() - self.stats['start_time']
        self.stats['pending_txs'] = len(self.blockchain.pending_transactions)

        # Update the UI
        try:
            self.query_one("#system").update(self._create_system_stats())
            self.query_one("#mining").update(self._create_mining_stats())
            self.query_one("#blockchain").update(self._create_blockchain_stats())
            self.query_one("#wallet").update(self._create_wallet_stats())
            self.query_one("#blocks").update(self._create_blocks_table())
        except NoMatches:
            pass  # UI not ready yet

    def action_start_mining(self):
        """Start mining action"""
        self.logger.info("User requested to start mining")

        if self.mining_active:
            self.logger.warning("Mining start requested but mining is already active")
            self.notify("Mining is already active", severity="warning")
            return

        # Hardware verification
        self.logger.info("Performing hardware verification before starting mining")
        result = self.hardware.verify_mining_eligibility()
        if not result['eligible']:
            self.logger.error(f"Hardware verification failed: {result.get('error', 'Unknown error')}")
            self.notify(f"Hardware verification failed: {result.get('error', 'Unknown error')}", severity="error")
            return

        self.logger.info("Hardware verification passed, starting mining session")
        self.mining_active = True
        self.stop_event.clear()
        self.stats['start_time'] = time.time()
        self.stats['session_blocks'] = 0
        self.stats['session_rewards'] = 0.0

        # Start mining thread
        self.logger.info("Starting mining worker thread")
        self.mining_thread = threading.Thread(target=self._mining_worker, daemon=True)
        self.mining_thread.start()

        self.notify("⛏️ Mining session started", severity="information")

    def action_stop_mining(self):
        """Stop mining action"""
        self.logger.info("User requested to stop mining")

        if not self.mining_active:
            self.logger.warning("Mining stop requested but mining is not active")
            self.notify("Mining is not active", severity="warning")
            return

        self.logger.info("Stopping mining session")
        self.mining_active = False
        self.stop_event.set()

        if self.mining_thread and self.mining_thread.is_alive():
            self.logger.debug("Waiting for mining thread to stop")
            self.mining_thread.join(timeout=5)
            if self.mining_thread.is_alive():
                self.logger.warning("Mining thread did not stop within timeout")

        session_time = time.time() - self.stats['start_time']
        session_blocks = self.stats['session_blocks']
        session_rewards = self.stats['session_rewards']

        self.logger.info(f"Mining session stopped - Duration: {session_time:.1f}s, Blocks: {session_blocks}, Rewards: {session_rewards:.2f} tokens")
        self.notify(f"✅ Mining stopped - Session: {session_blocks} blocks, {session_rewards:.2f} tokens", severity="information")

    def _mining_worker(self):
        """Background mining worker"""
        self.logger.info("Mining worker thread started")
        self.logger.info(f"Miner wallet: {self.miner_wallet or 'None'}")
        self.logger.info(f"Current blockchain height: {len(self.blockchain.chain)}")
        self.logger.info(f"Pending transactions: {len(self.blockchain.pending_transactions)}")

        while not self.stop_event.is_set():
            try:
                self.logger.debug("Checking for pending transactions to mine")
                pending_count = len(self.blockchain.pending_transactions)

                if pending_count > 0:
                    self.logger.info(f"Found {pending_count} pending transactions, starting mining process")

                    # Log details of pending transactions
                    for i, tx in enumerate(self.blockchain.pending_transactions[:3]):  # Log first 3
                        self.logger.debug(f"Pending TX {i+1}: type={tx.get('type', 'unknown')}, timestamp={tx.get('timestamp', 'unknown')}")

                    # Mine a block
                    self.logger.info("Calling blockchain.mine_pending_transactions()")
                    start_time = time.time()
                    block = self.blockchain.mine_pending_transactions(self.miner_wallet, verbose=False)
                    mining_duration = time.time() - start_time

                    if block:
                        self.logger.info(f"Block mined successfully in {mining_duration:.2f}s")
                        self.logger.info(f"Block details: index={block.index}, nonce={block.nonce}, hash={block.hash[:16]}...")

                        self.stats['blocks_mined'] += 1
                        self.stats['session_blocks'] += 1
                        self.stats['last_block_time'] = time.time()

                        # Calculate rough hashrate
                        if hasattr(block, 'nonce') and block.nonce > 0:
                            time_taken = time.time() - self.stats.get('last_block_time', time.time())
                            self.stats['hashrate'] = max(0.1, block.nonce / max(1, time_taken))
                            self.logger.info(f"Calculated hashrate: {self.stats['hashrate']:.1f} H/s")

                        # Check for mining rewards
                        reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                        if reward_txs:
                            reward_amount = reward_txs[0].get('amount', 0)
                            self.stats['total_rewards'] += reward_amount
                            self.stats['session_rewards'] += reward_amount
                            self.logger.info(f"Mining reward: {reward_amount:.2f} tokens to {self.miner_wallet}")
                        else:
                            self.logger.warning("No mining reward found in block")

                        # Log transaction details
                        tx_count = len([tx for tx in block.transactions if tx.get('type') != 'mining_reward'])
                        self.logger.info(f"Block contains {tx_count} user transactions + mining reward")

                        self.notify(f"✅ Block #{block.index} mined! Reward: {reward_amount:.2f} tokens", severity="success")
                    else:
                        self.logger.warning("Mining attempt returned None (no block found)")
                        self.logger.debug(f"Mining duration: {mining_duration:.2f}s")
                        time.sleep(2)  # Wait before trying again
                else:
                    self.logger.debug("No pending transactions, checking again in 2 seconds")
                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"Mining worker exception: {e}", exc_info=True)
                self.notify(f"Mining error: {e}", severity="error")
                time.sleep(5)

        self.logger.info("Mining worker thread stopped")

    def action_create_test_tx(self):
        """Create test transaction"""
        self.logger.info("User requested to create test transaction")

        try:
            import secrets

            test_id = secrets.token_hex(8)
            self.logger.debug(f"Generated test transaction ID: {test_id}")

            tx = {
                "type": "test_transaction",
                "data": {
                    "message": "Test transaction from mining console",
                    "timestamp": time.time(),
                    "test_id": test_id
                },
                "signature": f"mining_console_sig_{secrets.token_hex(4)}",
                "timestamp": time.time()
            }

            self.logger.debug("Adding test transaction to blockchain")
            tx_hash = self.blockchain.add_transaction(tx)
            self.logger.info(f"Test transaction created successfully: {tx_hash}")

            self.notify(f"✅ Test transaction created: {tx_hash[:16]}...", severity="information")

        except Exception as e:
            self.logger.error(f"Failed to create test transaction: {e}", exc_info=True)
            self.notify(f"❌ Failed to create test transaction: {e}", severity="error")

    def action_show_wallet(self):
        """Show wallet information"""
        if not self.miner_wallet:
            self.notify("⚠️ No miner wallet configured", severity="warning")
            return

        try:
            balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            transactions = self.blockchain.get_wallet_transactions(self.miner_wallet)

            wallet_info = f"""
🏦 Wallet Information
Address: {self.miner_wallet}
Balance: {balance:.2f} tokens
Total Transactions: {len(transactions)}
            """.strip()

            self.notify(wallet_info, severity="information", timeout=10)

        except Exception as e:
            self.notify(f"❌ Error getting wallet info: {e}", severity="error")

    def action_show_network(self):
        """Show network information"""
        try:
            discovery_status = node_discovery.get_discovery_status()

            network_info = f"""
🌐 Network Status
Node ID: {discovery_status.get('node_id', 'unknown')[:16]}...
Active Endpoints: {len(discovery_status.get('endpoints', []))}
Relay Status: {'✅ Active' if self._check_if_relay_node() else '❌ Not participating'}
            """.strip()

            self.notify(network_info, severity="information", timeout=10)

        except Exception as e:
            self.notify(f"❌ Error getting network info: {e}", severity="error")

    def action_toggle_relay(self):
        """Toggle relay node status"""
        is_relay = self._check_if_relay_node()

        if is_relay:
            # Stop being a relay
            try:
                import subprocess
                result = subprocess.run([
                    'python', '-m', 'pisecure.cli', 'stop-relay-node'
                ], capture_output=True, text=True, cwd='/home/pi/PiSecure')

                if result.returncode == 0:
                    self.notify("✅ Relay node stopped successfully", severity="information")
                else:
                    self.notify(f"❌ Failed to stop relay node: {result.stderr}", severity="error")
            except Exception as e:
                self.notify(f"❌ Error stopping relay node: {e}", severity="error")
        else:
            # Become a relay
            try:
                import subprocess
                result = subprocess.run([
                    'python', '-m', 'pisecure.cli', 'become-relay-node'
                ], capture_output=True, text=True, cwd='/home/pi/PiSecure')

                if result.returncode == 0:
                    self.notify("✅ Successfully became a relay node", severity="information")
                else:
                    self.notify(f"❌ Failed to become relay node: {result.stderr}", severity="error")
            except Exception as e:
                self.notify(f"❌ Error setting up relay node: {e}", severity="error")

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

    def action_show_help(self):
        """Show help information"""
        help_text = """
🔧 PiSecure Mining Console - Help

🎮 Keyboard Controls:
  S - Start mining session
  X - Stop mining session
  C - Create test transaction for mining
  W - Show detailed wallet information
  N - Show network connectivity information
  R - Toggle relay node status
  H - Show this help screen
  Q - Quit the mining console

📊 Dashboard Panels:
  System Status - CPU, Memory, Disk, Temperature
  Mining Status - Active blocks, rewards, hashrate
  Blockchain Status - Chain info, network health
  Wallet Info - Balance, address, earnings
  Network Status - Node ID, endpoints, STUN/TOR addresses
  Mining History - Recent blocks and rewards

💡 Tips:
  • Mining rewards go to your configured wallet
  • Test transactions help verify mining is working
  • Relay nodes help other users discover the network
        """.strip()

        self.notify(help_text, severity="information", timeout=15)

    def action_quit(self):
        """Quit the application"""
        if self.mining_active:
            self.action_stop_mining()
        self.exit()


def main():
    """Main entry point"""
    app = MiningApp()
    app.run()


if __name__ == '__main__':
    main()