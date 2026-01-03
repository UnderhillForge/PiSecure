#!/usr/bin/env python3
"""
PiSecure Mining Console
=======================

Interactive mining dashboard with real-time stats, controls, and monitoring.
Bashtop-inspired terminal user interface for mining operations.

Features:
- Real-time CPU/hashrate graphs with history
- System resource monitoring with colorful bars
- Wallet balance tracking
- Mining controls (start/stop)
- Live blockchain updates
- Process-style mining log

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
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Log, Button, Label, Sparkline, ProgressBar
import logging
from datetime import datetime
from textual.binding import Binding
from textual import events
from textual.timer import Timer
from textual.css.query import NoMatches
from collections import deque

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

    def __init__(self, log_widget, app):
        super().__init__()
        self.log_widget = log_widget
        self.app = app
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        """Emit a log record to the Textual log widget (thread-safe)"""
        try:
            msg = self.format(record)
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted = f"[dim]{timestamp}[/dim] {msg}"
            # Use call_from_thread for thread-safe updates
            self.app.call_from_thread(self.log_widget.write_line, formatted)
        except Exception:
            self.handleError(record)


class MiningApp(App):
    """Bashtop-inspired mining console application"""

    CSS = """
    Screen {
        background: #0d1117;
    }

    /* Header styling */
    #top-bar {
        height: 3;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 1;
    }

    #menu-section {
        width: auto;
        color: #7ee787;
    }

    #time-display {
        width: auto;
        text-align: right;
        color: #58a6ff;
    }

    #status-indicator {
        width: auto;
        color: #f0883e;
    }

    /* CPU/Hashrate graph section */
    #cpu-graph-section {
        height: 10;
        background: #0d1117;
        border: solid #30363d;
        padding: 0 1;
    }

    #cpu-sparkline {
        height: 8;
        background: #0d1117;
    }

    #cpu-info-box {
        width: 25;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    /* Main content area */
    #main-content {
        layout: horizontal;
        height: 100%;
    }

    /* Left column - memory and disks style */
    #left-column {
        width: 35%;
        layout: vertical;
        background: #0d1117;
    }

    #mem-section {
        height: 10;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    #mining-stats-section {
        height: 10;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    #wallet-section {
        height: auto;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    /* Middle column - blockchain and net stats */
    #middle-column {
        width: 30%;
        layout: vertical;
        background: #0d1117;
    }

    #blockchain-section {
        height: 12;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    #network-section {
        height: 16;
        background: #161b22;
        border: solid #30363d;
        padding: 0 1;
    }

    /* Right column - mining terminal */
    #right-column {
        width: 35%;
        layout: vertical;
        background: #0d1117;
    }

    #processes-section {
        height: 28;
        max-height: 28;
        background: #161b22;
        border: solid #30363d;
        overflow: hidden;
    }

    #mining-log {
        height: 26;
        max-height: 26;
        background: #0d1117;
        color: #c9d1d9;
        border: none;
        overflow-y: auto;
    }

    /* Progress bar styling */
    .mem-bar {
        height: 1;
        margin: 0;
    }

    .progress-label {
        color: #8b949e;
    }

    /* Color classes for bars */
    .bar-green {
        color: #7ee787;
    }

    .bar-yellow {
        color: #d29922;
    }

    .bar-red {
        color: #f85149;
    }

    .bar-blue {
        color: #58a6ff;
    }

    .bar-purple {
        color: #bc8cff;
    }

    .bar-cyan {
        color: #39c5cf;
    }

    /* Section headers */
    .section-header {
        color: #58a6ff;
        text-style: bold;
        background: #21262d;
        padding: 0 1;
    }

    /* Footer command bar */
    Footer {
        background: #161b22;
        color: #8b949e;
        border-top: solid #30363d;
    }

    /* Text colors */
    .text-green {
        color: #7ee787;
    }

    .text-red {
        color: #f85149;
    }

    .text-yellow {
        color: #d29922;
    }

    .text-blue {
        color: #58a6ff;
    }

    .text-cyan {
        color: #39c5cf;
    }

    .text-dim {
        color: #484f58;
    }

    .text-white {
        color: #c9d1d9;
    }
    """

    BINDINGS = [
        Binding("s", "start_mining", "Start", show=True),
        Binding("x", "stop_mining", "Stop", show=True),
        Binding("c", "create_test_tx", "CreateTX", show=True),
        Binding("w", "show_wallet", "Wallet", show=True),
        Binding("n", "show_network", "Network", show=True),
        Binding("r", "toggle_relay", "Relay", show=True),
        Binding("i", "show_info", "Info", show=True),
        Binding("h", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
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

        # CPU/Hashrate history for graphs (last 60 samples)
        self.cpu_history = deque([0.0] * 60, maxlen=60)
        self.hashrate_history = deque([0.0] * 60, maxlen=60)
        self.memory_history = deque([0.0] * 60, maxlen=60)

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
            'session_blocks': 0,
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'temperature': 0.0
        }

        # Network update counter (update every 20 seconds)
        self.network_update_counter = 0
        self.network_update_interval = 20

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger('mining_console')

    def _setup_logging(self):
        """Setup logging to write to the Textual Log widget"""
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
        """Create the bashtop-inspired dashboard layout"""
        # Top bar with menu, time, and status
        with Container(id="top-bar"):
            with Horizontal():
                yield Static("[bold green]⛏ pisecure[/bold green]  [dim]mining[/dim]", id="menu-section")
                yield Static(self._get_time_display(), id="time-display")
                yield Static(self._get_status_indicator(), id="status-indicator")

        # CPU/Hashrate graph section at top
        with Container(id="cpu-graph-section"):
            with Horizontal():
                yield Static(self._create_cpu_graph(), id="cpu-graph")
                yield Static(self._create_cpu_info_box(), id="cpu-info-box")

        # Main content area with 3 columns
        with Container(id="main-content"):
            # Left column - Memory and Mining Stats
            with Container(id="left-column"):
                yield Static(self._create_memory_section(), id="mem-section")
                yield Static(self._create_mining_stats_section(), id="mining-stats-section")
                yield Static(self._create_wallet_section(), id="wallet-section")

            # Middle column - Blockchain and Net Stats
            with Container(id="middle-column"):
                yield Static(self._create_blockchain_section(), id="blockchain-section")
                yield Static(self._create_network_section(), id="network-section")

            # Right column - Mining Terminal
            with Container(id="right-column"):
                with Container(id="processes-section"):
                    yield Static("[bold green][Mining Term][/bold green]", id="mining-term-header")
                    yield Log(id="mining-log")

        yield Footer()

    def _get_time_display(self):
        """Get current time display"""
        now = datetime.now()
        return f"[bold cyan]{now.strftime('%H:%M:%S')}[/bold cyan]"

    def _get_status_indicator(self):
        """Get mining status indicator"""
        if self.mining_active:
            return "[bold green]● MINING[/bold green]"
        else:
            return "[bold red]○ IDLE[/bold red]"

    def _create_cpu_graph(self):
        """Create ASCII-art CPU usage graph like bashtop"""
        # Braille-style graph characters
        graph_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

        # Get CPU history as graph
        cpu_percent = psutil.cpu_percent(interval=0)
        self.cpu_history.append(cpu_percent)

        # Create multi-line graph
        lines = []
        lines.append("[bold cyan]cpu[/bold cyan]")

        # Generate 6-row graph
        for row in range(6, 0, -1):
            threshold = row * (100 / 6)
            line = ""
            for val in self.cpu_history:
                if val >= threshold:
                    # Color based on level
                    if row >= 5:
                        line += "[red]█[/red]"
                    elif row >= 3:
                        line += "[yellow]█[/yellow]"
                    else:
                        line += "[green]█[/green]"
                elif val >= threshold - (100 / 6):
                    # Partial fill
                    idx = int((val % (100/6)) / (100/6) * len(graph_chars))
                    idx = min(idx, len(graph_chars) - 1)
                    if row >= 5:
                        line += f"[red]{graph_chars[idx]}[/red]"
                    elif row >= 3:
                        line += f"[yellow]{graph_chars[idx]}[/yellow]"
                    else:
                        line += f"[green]{graph_chars[idx]}[/green]"
                else:
                    line += "[dim]░[/dim]"
            lines.append(line)

        # Bottom axis
        lines.append("[dim]" + "─" * 60 + "[/dim]")
        lines.append(f"[dim]up {self._format_uptime()}[/dim]")

        return "\n".join(lines)

    def _create_cpu_info_box(self):
        """Create CPU info box like bashtop"""
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent()
            load = os.getloadavg()

            # Get CPU model
            cpu_model = "ARM"
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line.lower() or 'hardware' in line.lower():
                            cpu_model = line.split(':')[1].strip()[:20]
                            break
            except:
                pass

            # CPU temperature
            temp = self._get_temperature()

            return f"""[bold cyan]{cpu_model}[/bold cyan]

[green]CPU[/green]  [bold white]{cpu_percent:5.1f}%[/bold white]
[cyan]Core1[/cyan] [dim]{'█' * int(cpu_percent / 10)}{'░' * (10 - int(cpu_percent / 10))}[/dim]
[yellow]L AVG:[/yellow] [white]{load[0]:.2f} {load[1]:.2f} {load[2]:.2f}[/white]
[red]Temp:[/red] [white]{temp:.1f}°C[/white]
[blue]Freq:[/blue] [white]{cpu_freq.current:.0f}MHz[/white]"""
        except:
            return "[bold cyan]CPU Info[/bold cyan]\n\nN/A"

    def _create_memory_section(self):
        """Create memory section with colorful progress bars like bashtop"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')

        mem_gb = mem.used / (1024**3)
        mem_total_gb = mem.total / (1024**3)
        avail_gb = mem.available / (1024**3)

        # Calculate bar widths
        bar_width = 20
        mem_bar = int((mem.percent / 100) * bar_width)
        avail_bar = int(((mem.available / mem.total) * 100 / 100) * bar_width)
        swap_bar = int((swap.percent / 100) * bar_width) if swap.total > 0 else 0
        disk_bar = int((disk.percent / 100) * bar_width)

        return f"""[bold cyan][Mem][/bold cyan]

[white]Memory:[/white]    [bold white]{mem_gb:.2f} GiB[/bold white]
[white]Used:[/white]      [green]{'█' * mem_bar}[/green][dim]{'░' * (bar_width - mem_bar)}[/dim] [white]{mem.percent:.0f}%[/white]

[white]Avail:[/white]     [bold white]{avail_gb:.2f} GiB[/bold white]
            [cyan]{'█' * avail_bar}[/cyan][dim]{'░' * (bar_width - avail_bar)}[/dim] [white]{100 - mem.percent:.0f}%[/white]

[white]Swap:[/white]      [bold white]{swap.used / (1024**3):.2f} GiB[/bold white]
[white]Free:[/white]{swap.percent:.0f}%  [yellow]{'█' * swap_bar}[/yellow][dim]{'░' * (bar_width - swap_bar)}[/dim]"""

    def _create_mining_stats_section(self):
        """Create mining statistics section like bashtop disks section"""
        status_icon = "●" if self.mining_active else "○"
        status_color = "green" if self.mining_active else "red"

        # Hashrate bar
        bar_width = 20
        hashrate_normalized = min(100, self.stats['hashrate'] / 10)  # Scale to 0-100
        hashrate_bar = int((hashrate_normalized / 100) * bar_width)

        return f"""[bold magenta][Mining][/bold magenta]

[white]Status:[/white]  [{status_color}]{status_icon} {'ACTIVE' if self.mining_active else 'STOPPED'}[/{status_color}]
[white]Hashrate:[/white] [bold white]{self.stats['hashrate']:.1f} KH/s[/bold white]
          [magenta]{'█' * hashrate_bar}[/magenta][dim]{'░' * (bar_width - hashrate_bar)}[/dim]

[white]Session:[/white]  [cyan]{self.stats['session_blocks']}[/cyan] blocks
[white]Total:[/white]    [cyan]{self.stats['blocks_mined']}[/cyan] blocks
[white]Rewards:[/white]  [green]+{self.stats['session_rewards']:.2f}[/green] tokens"""

    def _create_wallet_section(self):
        """Create wallet info section"""
        if self.miner_wallet:
            try:
                balance = self.blockchain.get_wallet_balance(self.miner_wallet)
                addr_short = self.miner_wallet[:16] + "..."
            except:
                balance = 0.0
                addr_short = "Error loading"

            return f"""[bold yellow][Wallet][/bold yellow]

[white]Address:[/white] [cyan]{addr_short}[/cyan]
[white]Balance:[/white] [bold green]{balance:.2f}[/bold green] tokens
[white]Earned:[/white]  [green]+{self.stats['session_rewards']:.2f}[/green]
[white]Status:[/white]  [green]● Connected[/green]"""
        else:
            return f"""[bold yellow]wallet[/bold yellow]

[white]Status:[/white]  [red]○ Not Configured[/red]
[dim]Set wallet in config[/dim]"""

    def _create_blockchain_section(self):
        """Create blockchain info section like bashtop"""
        try:
            chain_info = self.blockchain.get_chain_info()
            health = chain_info['network_health']

            # Progress bar for health
            bar_width = 15
            health_pct = int(health['participation'] * 100)
            health_bar = int((health_pct / 100) * bar_width)

            return f"""[bold blue][Blockchain][/bold blue]

[white]Height:[/white]    [bold cyan]{chain_info['blocks']}[/bold cyan]
[white]Pending:[/white]   [yellow]{self.stats['pending_txs']}[/yellow] txs
[white]Difficulty:[/white][cyan]{chain_info['difficulty']}[/cyan]

[white]Health:[/white]
[green]{'█' * health_bar}[/green][dim]{'░' * (bar_width - health_bar)}[/dim] [white]{health_pct}%[/white]

[white]Block Time:[/white][cyan]{health['avg_block_time']:.1f}s[/cyan]"""
        except:
            return "[bold blue]blockchain[/bold blue]\n\nLoading..."

    def _create_network_section(self):
        """Create network section like bashtop net section"""
        try:
            discovery_status = node_discovery.get_discovery_status()
            endpoints = len(discovery_status.get('endpoints', []))
            node_id = discovery_status.get('node_id', 'unknown')[:8]
            is_relay = self._check_if_relay_node()

            # Mock network stats
            net_io = psutil.net_io_counters()
            bytes_sent = net_io.bytes_sent / (1024**2)  # MB
            bytes_recv = net_io.bytes_recv / (1024**2)

            return f"""[bold red][Net Stats][/bold red]

[white]Node:[/white]      [cyan]{node_id}...[/cyan]
[white]Peers:[/white]     [green]{endpoints}[/green]
[white]Relay:[/white]     {'[green]●[/green]' if is_relay else '[red]○[/red]'}

[green]▼ Download[/green]
  [white]Total:[/white]   [cyan]{bytes_recv:.1f} MiB[/cyan]

[red]▲ Upload[/red]
  [white]Total:[/white]   [cyan]{bytes_sent:.1f} MiB[/cyan]"""
        except:
            return "[bold red]net[/bold red]\n\nOffline"

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

    def _format_uptime(self):
        """Format uptime string"""
        uptime = time.time() - self.stats['start_time']
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    def _check_if_relay_node(self):
        """Check if this node is configured as a relay node"""
        try:
            config_path = "/etc/pisecure/config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('network', {}).get('relay_enabled', False)
        except:
            return False

    def on_mount(self):
        """Called when the app is mounted"""
        self.title = "PiSecure Mining Console"
        self.sub_title = "Bashtop-inspired mining dashboard"

        # Setup logging now that UI is ready
        try:
            log_widget = self.query_one("#mining-log", Log)
            handler = TextualLogHandler(log_widget, self)
            handler.setLevel(logging.DEBUG)

            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(handler)
            self.logger.propagate = False

            # Silence INFO logs from network traversal module
            logging.getLogger('pisecure.core.nat_traversal').setLevel(logging.WARNING)
            logging.getLogger('pisecure.core.net_traversal').setLevel(logging.WARNING)

            # Log startup information
            self.logger.info("PiSecure Mining Console started")
            self.logger.info(f"Blockchain height: {len(self.blockchain.chain)}")
            self.logger.info(f"Miner wallet: {self.miner_wallet or 'Not configured'}")
            self.logger.info("Press 'h' for help, 's' to start mining")
        except NoMatches:
            pass

        # Start update timer
        self.update_timer = self.set_interval(1.0, self.update_stats)

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
        self.stats['cpu_percent'] = psutil.cpu_percent()
        self.stats['memory_percent'] = psutil.virtual_memory().percent
        self.stats['temperature'] = self._get_temperature()

        # Update CPU history
        self.cpu_history.append(self.stats['cpu_percent'])

        # Update all UI panels
        try:
            self.query_one("#time-display").update(self._get_time_display())
            self.query_one("#status-indicator").update(self._get_status_indicator())
            self.query_one("#cpu-graph").update(self._create_cpu_graph())
            self.query_one("#cpu-info-box").update(self._create_cpu_info_box())
            self.query_one("#mem-section").update(self._create_memory_section())
            self.query_one("#mining-stats-section").update(self._create_mining_stats_section())
            self.query_one("#wallet-section").update(self._create_wallet_section())
            self.query_one("#blockchain-section").update(self._create_blockchain_section())
            self.query_one("#network-section").update(self._create_network_section())
        except NoMatches:
            pass

    def action_start_mining(self):
        """Start mining action"""
        self.logger.info("User requested to start mining")

        if self.mining_active:
            self.logger.warning("Mining already active")
            self.notify("Mining is already active", severity="warning")
            return

        # Hardware verification
        self.logger.info("Performing hardware verification")
        result = self.hardware.verify_mining_eligibility()
        if not result['eligible']:
            self.logger.error(f"Hardware verification failed: {result.get('error')}")
            self.notify(f"Hardware verification failed: {result.get('error')}", severity="error")
            return

        self.logger.info("Starting mining session")
        self.mining_active = True
        self.stop_event.clear()
        self.stats['start_time'] = time.time()
        self.stats['session_blocks'] = 0
        self.stats['session_rewards'] = 0.0

        # Start mining thread
        self.mining_thread = threading.Thread(target=self._mining_worker, daemon=True)
        self.mining_thread.start()

        self.notify("⛏️ Mining started", severity="information")

    def action_stop_mining(self):
        """Stop mining action"""
        self.logger.info("Stopping mining")

        if not self.mining_active:
            self.notify("Mining is not active", severity="warning")
            return

        self.mining_active = False
        self.stop_event.set()

        if self.mining_thread and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=5)

        session_blocks = self.stats['session_blocks']
        session_rewards = self.stats['session_rewards']

        self.logger.info(f"Mining stopped - {session_blocks} blocks, {session_rewards:.2f} tokens")
        self.notify(f"✅ Mining stopped - {session_blocks} blocks mined", severity="information")

    def _mining_worker(self):
        """Background mining worker"""
        self.logger.info("⛏️  Mining worker started")
        self.logger.info(f"📍 Wallet: {self.miner_wallet[:20] + '...' if self.miner_wallet else 'None'}")
        self.logger.info(f"📦 Chain height: {len(self.blockchain.chain)}")
        self.logger.info(f"⚙️  Difficulty: {self.blockchain.difficulty}")

        while not self.stop_event.is_set():
            try:
                pending_count = len(self.blockchain.pending_transactions)

                if pending_count > 0:
                    self.logger.info(f"🔍 Found {pending_count} pending transaction(s)")
                    self.logger.info(f"⛏️  Starting mining attempt...")

                    start_time = time.time()
                    
                    # Mine with progress updates
                    block = self.blockchain.mine_pending_transactions(self.miner_wallet, verbose=False)
                    mining_duration = time.time() - start_time

                    if block:
                        # Calculate hashrate
                        nonce = getattr(block, 'nonce', 0)
                        if nonce > 0:
                            self.stats['hashrate'] = max(0.1, nonce / max(1, mining_duration)) / 1000
                        
                        self.logger.info(f"🎉 BLOCK #{block.index} MINED!")
                        self.logger.info(f"   ├─ Hash: {block.hash[:32]}...")
                        self.logger.info(f"   ├─ Nonce: {nonce:,}")
                        self.logger.info(f"   ├─ Time: {mining_duration:.2f}s")
                        self.logger.info(f"   └─ Rate: {self.stats['hashrate']:.1f} KH/s")

                        self.stats['blocks_mined'] += 1
                        self.stats['session_blocks'] += 1
                        self.stats['last_block_time'] = time.time()

                        # Check for rewards
                        reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                        if reward_txs:
                            reward_amount = reward_txs[0].get('amount', 0)
                            self.stats['total_rewards'] += reward_amount
                            self.stats['session_rewards'] += reward_amount
                            self.logger.info(f"💰 Reward: +{reward_amount:.2f} tokens → wallet")

                        # Log transaction summary
                        tx_count = len(block.transactions)
                        self.logger.info(f"📝 Block contains {tx_count} transaction(s)")

                        self.notify(f"✅ Block #{block.index} mined!", severity="success")
                    else:
                        self.logger.warning("⚠️  Mining attempt failed (exceeded nonce limit)")
                        time.sleep(2)
                else:
                    # Periodically log waiting status
                    # Always mine - blockchain handles empty blocks
                    self.logger.info("⛏️ Mining empty block (no pending transactions)")
                    start_time = time.time()
                    block = self.blockchain.mine_pending_transactions(self.miner_wallet, verbose=False)
                    mining_duration = time.time() - start_time

            except Exception as e:
                self.logger.error(f"Mining error: {e}")
                time.sleep(5)

        self.logger.info("Mining worker stopped")

    def action_create_test_tx(self):
        """Create test transaction"""
        self.logger.info("Creating test transaction")

        try:
            import secrets
            test_id = secrets.token_hex(8)

            tx = {
                "type": "test_transaction",
                "data": {
                    "message": "Test from mining console",
                    "timestamp": time.time(),
                    "test_id": test_id
                },
                "signature": f"mining_console_sig_{secrets.token_hex(4)}",
                "timestamp": time.time()
            }

            tx_hash = self.blockchain.add_transaction(tx)
            self.logger.info(f"✅ Test TX: {tx_hash[:16]}...")
            self.notify(f"✅ Test transaction created", severity="information")

        except Exception as e:
            self.logger.error(f"Failed to create TX: {e}")
            self.notify(f"❌ Failed: {e}", severity="error")

    def action_show_wallet(self):
        """Show wallet information"""
        if not self.miner_wallet:
            self.notify("⚠️ No wallet configured", severity="warning")
            return

        try:
            balance = self.blockchain.get_wallet_balance(self.miner_wallet)
            transactions = self.blockchain.get_wallet_transactions(self.miner_wallet)

            self.notify(f"🏦 Balance: {balance:.2f} tokens | TXs: {len(transactions)}", timeout=10)

        except Exception as e:
            self.notify(f"❌ Error: {e}", severity="error")

    def action_show_network(self):
        """Show network information"""
        try:
            discovery_status = node_discovery.get_discovery_status()
            endpoints = len(discovery_status.get('endpoints', []))

            self.notify(f"🌐 Peers: {endpoints} | Relay: {'✅' if self._check_if_relay_node() else '❌'}", timeout=10)

        except Exception as e:
            self.notify(f"❌ Error: {e}", severity="error")

    def action_toggle_relay(self):
        """Toggle relay node status"""
        is_relay = self._check_if_relay_node()

        try:
            import subprocess
            cmd = 'stop-relay-node' if is_relay else 'become-relay-node'
            result = subprocess.run(
                ['python', '-m', 'pisecure.cli', cmd],
                capture_output=True, text=True, cwd='/home/pi/PiSecure'
            )

            if result.returncode == 0:
                status = "stopped" if is_relay else "started"
                self.notify(f"✅ Relay {status}", severity="information")
            else:
                self.notify(f"❌ Failed: {result.stderr}", severity="error")
        except Exception as e:
            self.notify(f"❌ Error: {e}", severity="error")

    def action_show_info(self):
        """Show system info"""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        temp = self._get_temperature()
        blocks = len(self.blockchain.chain)

        self.notify(f"CPU: {cpu}% | MEM: {mem}% | Temp: {temp}°C | Blocks: {blocks}", timeout=10)

    def action_show_help(self):
        """Show help information"""
        help_text = "S=Start X=Stop C=CreateTX W=Wallet N=Network R=Relay I=Info Q=Quit"
        self.notify(help_text, timeout=15)

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