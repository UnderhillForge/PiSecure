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
from textual.widgets import Header, Footer, Static, DataTable, Label, ProgressBar
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console


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

class USDValuationEngine:
    """Real-time USD valuation engine for 314ST tokens"""

    def __init__(self):
        self.base_valuation = 0.01  # Base USD value per token
        self.last_update = time.time()
        self.valuation_history = []
        self.market_factors = {
            'mining_difficulty': 1,
            'network_hashrate': 0,
            'active_nodes': 1,
            'transaction_volume': 0,
            'blocks_per_hour': 6,
            'exchange_adoption': 0.1,  # 10% initial adoption
            'developer_activity': 0.5,  # Normalized developer activity
            'security_score': 0.9,     # High security rating
            'utility_score': 0.8       # High utility for exchanges
        }

    def update_market_factors(self, blockchain, mining_stats):
        """Update market factors based on current network state"""
        try:
            # Mining difficulty factor
            self.market_factors['mining_difficulty'] = blockchain.difficulty

            # Network hashrate (estimated from mining stats)
            self.market_factors['network_hashrate'] = mining_stats.get('hashrate', 0) * 1000  # Convert to KH/s

            # Active nodes (estimated from network health)
            chain_info = blockchain.get_chain_info()
            network_health = chain_info.get('network_health', {})
            participation = network_health.get('participation', 0.1)
            self.market_factors['active_nodes'] = max(1, int(participation * 100))

            # Transaction volume
            pending_txs = len(blockchain.pending_transactions)
            recent_blocks = blockchain.chain[-10:] if len(blockchain.chain) > 10 else blockchain.chain
            total_txs = sum(len(block.transactions) for block in recent_blocks)
            self.market_factors['transaction_volume'] = total_txs / max(1, len(recent_blocks))

            # Blocks per hour (recent activity)
            if len(recent_blocks) >= 2:
                time_span = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
                hours = time_span / 3600
                self.market_factors['blocks_per_hour'] = len(recent_blocks) / max(0.1, hours)

            # Exchange adoption (simulated growth)
            # This would be updated from real exchange data in production
            adoption_growth = min(0.01, mining_stats.get('uptime', 0) / 86400)  # 1% max daily growth
            self.market_factors['exchange_adoption'] = min(1.0, self.market_factors['exchange_adoption'] + adoption_growth)

        except Exception as e:
            # Fallback to default values if update fails
            pass

    def calculate_token_valuation(self):
        """Calculate real-time USD valuation per 314ST token"""
        try:
            factors = self.market_factors

            # Base valuation components
            mining_value = factors['mining_difficulty'] * 0.001  # Difficulty drives scarcity
            network_value = min(1.0, factors['active_nodes'] / 100) * 0.005  # Network effects
            utility_value = factors['utility_score'] * 0.003  # Exchange utility premium
            security_value = factors['security_score'] * 0.002  # Security premium

            # Dynamic market factors
            adoption_multiplier = 1 + (factors['exchange_adoption'] * 2)  # 2x multiplier at full adoption
            activity_multiplier = 1 + (factors['transaction_volume'] / 10)  # Activity bonus
            developer_multiplier = 1 + (factors['developer_activity'] * 0.5)  # Developer activity

            # Calculate final valuation
            base_value = self.base_valuation
            market_premium = mining_value + network_value + utility_value + security_value
            multipliers = adoption_multiplier * activity_multiplier * developer_multiplier

            token_usd_value = (base_value + market_premium) * multipliers

            # Apply realistic bounds (prevent extreme values)
            token_usd_value = max(0.001, min(10.0, token_usd_value))

            # Store in history for trend analysis
            self.valuation_history.append({
                'timestamp': time.time(),
                'value': token_usd_value,
                'factors': factors.copy()
            })

            # Keep only last 100 entries
            if len(self.valuation_history) > 100:
                self.valuation_history = self.valuation_history[-100:]

            self.last_update = time.time()
            return token_usd_value

        except Exception as e:
            # Return base value on error
            return self.base_valuation

    def get_valuation_trend(self):
        """Get valuation trend (percentage change over last hour)"""
        try:
            if len(self.valuation_history) < 2:
                return 0.0

            # Get values from last hour
            one_hour_ago = time.time() - 3600
            recent_values = [entry['value'] for entry in self.valuation_history
                           if entry['timestamp'] >= one_hour_ago]

            if len(recent_values) < 2:
                return 0.0

            current_value = recent_values[-1]
            previous_value = recent_values[0]

            if previous_value > 0:
                return ((current_value - previous_value) / previous_value) * 100
            return 0.0

        except Exception:
            return 0.0

    def get_mining_value_estimate(self, mining_stats):
        """Estimate USD value of mining rewards"""
        try:
            token_value = self.calculate_token_valuation()
            session_rewards = mining_stats.get('session_rewards', 0)
            total_rewards = mining_stats.get('total_rewards', 0)

            return {
                'token_value_usd': token_value,
                'session_rewards_usd': session_rewards * token_value,
                'total_rewards_usd': total_rewards * token_value,
                'hourly_rate_usd': self._calculate_hourly_rate(mining_stats, token_value),
                'trend_percent': self.get_valuation_trend()
            }

        except Exception:
            return {
                'token_value_usd': self.base_valuation,
                'session_rewards_usd': 0.0,
                'total_rewards_usd': 0.0,
                'hourly_rate_usd': 0.0,
                'trend_percent': 0.0
            }

    def _calculate_hourly_rate(self, mining_stats, token_value):
        """Calculate estimated hourly mining earnings in USD"""
        try:
            uptime_hours = mining_stats.get('uptime', 0) / 3600
            if uptime_hours <= 0:
                return 0.0

            session_rewards = mining_stats.get('session_rewards', 0)
            hourly_rate_tokens = session_rewards / uptime_hours

            return hourly_rate_tokens * token_value

        except Exception:
            return 0.0

    def get_market_summary(self):
        """Get comprehensive market summary"""
        token_value = self.calculate_token_valuation()
        trend = self.get_valuation_trend()

        return {
            'current_value': token_value,
            'trend_1h': trend,
            'market_factors': self.market_factors.copy(),
            'valuation_drivers': {
                'mining_difficulty': f"{self.market_factors['mining_difficulty']}x",
                'network_nodes': f"{self.market_factors['active_nodes']} nodes",
                'exchange_adoption': f"{self.market_factors['exchange_adoption']:.1%}",
                'transaction_volume': f"{self.market_factors['transaction_volume']:.1f} tx/block",
                'security_score': f"{self.market_factors['security_score']:.1%}",
                'utility_score': f"{self.market_factors['utility_score']:.1%}"
            }
        }


class StatsPanel(Static):
    """Panel displaying system and mining statistics"""

    def __init__(self, console_app):
        super().__init__()
        self.console_app = console_app
        self.mining_progress = 0.0

    def compose(self):
        yield Container(
            Static("System Stats", id="system_stats"),
            Static("Mining Stats", id="mining_stats"),
            id="stats_container"
        )
        # Add mining progress bar
        yield ProgressBar(id="mining_progress", total=100)

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
                # Check if node_discovery is available
                try:
                    discovery_status = node_discovery.get_discovery_status()
                    endpoints = discovery_status.get('endpoints', [])
                except:
                    endpoints = []

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

            # Add USD valuation information
            if self.console_app.mining_console.valuation_engine:
                try:
                    valuation_data = self.console_app.mining_console.valuation_engine.get_mining_value_estimate(stats)
                    mining_table.add_row("Token Value", f"${valuation_data['token_value_usd']:.4f} USD")
                    mining_table.add_row("Session Value", f"${valuation_data['session_rewards_usd']:.4f} USD")
                    mining_table.add_row("Hourly Rate", f"${valuation_data['hourly_rate_usd']:.4f} USD/hr")

                    trend_icon = "📈" if valuation_data['trend_percent'] >= 0 else "📉"
                    mining_table.add_row("Value Trend", f"{trend_icon} {valuation_data['trend_percent']:+.2f}%")
                except Exception as e:
                    mining_table.add_row("Token Value", "⚠️ Valuation Error")
                    mining_table.add_row("Session Value", "⚠️ Valuation Error")
                    mining_table.add_row("Hourly Rate", "⚠️ Valuation Error")
                    mining_table.add_row("Value Trend", "⚠️ Valuation Error")
            else:
                mining_table.add_row("Token Value", "❌ No Valuation")
                mining_table.add_row("Session Value", "❌ No Valuation")
                mining_table.add_row("Hourly Rate", "❌ No Valuation")
                mining_table.add_row("Value Trend", "❌ No Valuation")

            # Add mining efficiency metrics
            if stats['blocks_mined'] > 0 and stats['uptime'] > 0:
                avg_block_time = stats['uptime'] / stats['blocks_mined']
                expected_time = 600  # Expected 10 minutes per block
                efficiency = expected_time / avg_block_time if avg_block_time > 0 else 0
                efficiency_status = "⚡" if efficiency > 1 else "🐌"
                mining_table.add_row("Avg Block Time", f"{avg_block_time:.1f}s")
                mining_table.add_row("Mining Efficiency", f"{efficiency_status} {efficiency:.2f}x")
            else:
                mining_table.add_row("Avg Block Time", "N/A")
                mining_table.add_row("Mining Efficiency", "N/A")

            # Calculate mining progress (rough estimate based on difficulty)
            if mining_active and stats['hashrate'] > 0:
                difficulty = self.console_app.mining_console.blockchain.difficulty
                # Estimate progress based on attempts vs expected for difficulty
                expected_attempts = 16 ** difficulty  # Rough estimate
                current_attempts = int(stats['uptime'] * stats['hashrate'])
                self.mining_progress = min(100, (current_attempts / expected_attempts) * 100) if expected_attempts > 0 else 0
            else:
                self.mining_progress = 0

            # Update the widgets
            system_widget = self.query_one("#system_stats", Static)
            mining_widget = self.query_one("#mining_stats", Static)
            progress_bar = self.query_one("#mining_progress", ProgressBar)

            system_widget.update(Panel(system_table, border_style="blue"))
            mining_widget.update(Panel(mining_table, border_style="green"))
            progress_bar.update(progress=self.mining_progress)

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
            if blockchain:
                try:
                    chain_info = blockchain.get_chain_info()
                    blockchain_table = Table(title="⛓️ Blockchain Status", box=None, show_header=False)
                    blockchain_table.add_column("Metric", style="cyan", no_wrap=True)
                    blockchain_table.add_column("Value", style="blue")

                    blockchain_table.add_row("Blocks", str(chain_info['blocks']))
                    blockchain_table.add_row("Pending TX", str(stats['pending_txs']))
                    blockchain_table.add_row("Difficulty", str(chain_info['difficulty']))

                    health = chain_info['network_health']
                    participation = health['participation']
                    participation_icon = "🟢" if participation > 0.5 else "🟡" if participation > 0.1 else "🔴"
                    blockchain_table.add_row("Participation", f"{participation_icon} {participation:.1%}")
                    blockchain_table.add_row("Avg Block Time", f"{health['avg_block_time']:.1f}s")

                    # Network connectivity status
                    network_status = "🟢 HEALTHY"
                    if participation < 0.1:
                        network_status = "🔴 CRITICAL"
                    elif participation < 0.5:
                        network_status = "🟡 DEGRADED"
                    blockchain_table.add_row("Network Status", network_status)
                except Exception as e:
                    blockchain_table = Table(title="⛓️ Blockchain Status", box=None, show_header=False)
                    blockchain_table.add_column("Metric", style="cyan", no_wrap=True)
                    blockchain_table.add_column("Value", style="red")
                    blockchain_table.add_row("Status", f"❌ Error: {str(e)[:20]}...")
            else:
                blockchain_table = Table(title="⛓️ Blockchain Status", box=None, show_header=False)
                blockchain_table.add_column("Metric", style="cyan", no_wrap=True)
                blockchain_table.add_column("Value", style="red")
                blockchain_table.add_row("Status", "❌ Not Available")

            # Wallet info
            wallet_table = Table(title="🏦 Mining Wallet", box=None, show_header=False)
            wallet_table.add_column("Property", style="cyan", no_wrap=True)
            wallet_table.add_column("Value", style="yellow")

            if miner_wallet and blockchain:
                try:
                    wallet_balance = blockchain.get_wallet_balance(miner_wallet)
                    if self.console_app.mining_console.valuation_engine:
                        valuation_data = self.console_app.mining_console.valuation_engine.get_mining_value_estimate(stats)
                        wallet_value_usd = wallet_balance * valuation_data['token_value_usd']
                        wallet_table.add_row("Address", miner_wallet[:32] + "...")
                        wallet_table.add_row("Balance", f"{wallet_balance:.2f} tokens")
                        wallet_table.add_row("USD Value", f"${wallet_value_usd:.2f} USD")
                        wallet_table.add_row("Session Earnings", f"+{stats['session_rewards']:.2f} tokens")
                    else:
                        wallet_table.add_row("Address", miner_wallet[:32] + "...")
                        wallet_table.add_row("Balance", f"{wallet_balance:.2f} tokens")
                        wallet_table.add_row("USD Value", "❌ No Valuation")
                        wallet_table.add_row("Session Earnings", f"+{stats['session_rewards']:.2f} tokens")
                except Exception as e:
                    wallet_table.add_row("Status", f"⚠️ Error: {str(e)[:20]}...")
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

            if not blockchain:
                blocks_widget = self.query_one("#blocks_display", Static)
                blocks_widget.update(Panel("❌ Blockchain not available", border_style="red"))
                return

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

        # Color code messages based on type
        if "✅ BLOCK FOUND" in message:
            colored_message = f"[green]{message}[/green]"
        elif "❌" in message or "error" in message.lower():
            colored_message = f"[red]{message}[/red]"
        elif "🛑" in message:
            colored_message = f"[yellow]{message}[/yellow]"
        elif "⛏️" in message:
            colored_message = f"[blue]{message}[/blue]"
        elif "🔌" in message:
            colored_message = f"[cyan]{message}[/cyan]"
        else:
            colored_message = message

        self.activity_log.append(f"[{timestamp}] {colored_message}")
        # Keep only last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
        self.update_activity()


class RelayManager:
    """Manages relay functionality for network connectivity"""

    def __init__(self):
        self.relay_active = False
        self.relay_config = self._load_relay_config()
        self.relay_stats = {
            'connections_relayed': 0,
            'bytes_relayed': 0,
            'active_sessions': 0,
            'uptime': 0,
            'start_time': None
        }

    def _load_relay_config(self):
        """Load relay configuration from config file"""
        try:
            config_path = "/etc/pisecure/config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('network', {}).get('relay', {})
        except:
            return {}

    def _save_relay_config(self):
        """Save relay configuration to config file"""
        try:
            config_path = "/etc/pisecure/config.json"
            config = {}
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)

            config.setdefault('network', {})['relay'] = self.relay_config
            config['network']['relay_enabled'] = self.relay_active

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save relay config: {e}")

    def start_relay(self):
        """Start relay services"""
        if self.relay_active:
            return "Relay is already active"

        try:
            # Initialize relay services
            self.relay_active = True
            self.relay_stats['start_time'] = time.time()

            # Configure TURN server if enabled
            if self.relay_config.get('turn_enabled', False):
                self._start_turn_server()

            # Configure STUN server if enabled
            if self.relay_config.get('stun_enabled', False):
                self._start_stun_server()

            # Configure UPnP port forwarding
            if self.relay_config.get('upnp_enabled', True):
                self._configure_upnp()

            self._save_relay_config()
            return "Relay services started successfully"

        except Exception as e:
            self.relay_active = False
            return f"Failed to start relay: {e}"

    def stop_relay(self):
        """Stop relay services"""
        if not self.relay_active:
            return "Relay is not active"

        try:
            # Stop all relay services
            self._stop_turn_server()
            self._stop_stun_server()
            self._cleanup_upnp()

            self.relay_active = False
            self.relay_stats['uptime'] = time.time() - (self.relay_stats['start_time'] or time.time())
            self._save_relay_config()
            return "Relay services stopped successfully"

        except Exception as e:
            return f"Failed to stop relay: {e}"

    def _start_turn_server(self):
        """Start TURN (Traversal Using Relays around NAT) server"""
        # This would integrate with a TURN server implementation
        # For now, we'll simulate the functionality
        port = self.relay_config.get('turn_port', 3478)
        print(f"Starting TURN server on port {port}")

    def _stop_turn_server(self):
        """Stop TURN server"""
        print("Stopping TURN server")

    def _start_stun_server(self):
        """Start STUN (Session Traversal Utilities for NAT) server"""
        # This would integrate with a STUN server implementation
        port = self.relay_config.get('stun_port', 3478)
        print(f"Starting STUN server on port {port}")

    def _stop_stun_server(self):
        """Stop STUN server"""
        print("Stopping STUN server")

    def _configure_upnp(self):
        """Configure UPnP port forwarding"""
        try:
            import miniupnpc
            upnpc = miniupnpc.UPnP()
            upnpc.discoverdelay = 200
            upnpc.discover()
            upnpc.selectigd()

            # Forward PiSecure ports
            external_port = self.relay_config.get('external_port', 3142)
            internal_port = self.relay_config.get('internal_port', 3142)

            upnpc.addportmapping(
                external_port, 'TCP', upnpc.lanaddr, internal_port,
                'PiSecure Blockchain Node', ''
            )

            print(f"UPnP: Forwarded port {external_port} -> {internal_port}")

        except ImportError:
            print("UPnP: miniupnpc not available, skipping UPnP configuration")
        except Exception as e:
            print(f"UPnP configuration failed: {e}")

    def _cleanup_upnp(self):
        """Clean up UPnP port forwarding"""
        try:
            import miniupnpc
            upnpc = miniupnpc.UPnP()
            upnpc.discoverdelay = 200
            upnpc.discover()
            upnpc.selectigd()

            external_port = self.relay_config.get('external_port', 3142)
            upnpc.deleteportmapping(external_port, 'TCP')

            print(f"UPnP: Removed port forwarding for {external_port}")

        except Exception as e:
            print(f"UPnP cleanup failed: {e}")

    def get_relay_status(self):
        """Get comprehensive relay status"""
        status = {
            'active': self.relay_active,
            'config': self.relay_config,
            'stats': self.relay_stats.copy()
        }

        if self.relay_active and self.relay_stats['start_time']:
            status['stats']['uptime'] = time.time() - self.relay_stats['start_time']

        # Check actual service status
        status['services'] = {
            'turn': self._check_turn_status(),
            'stun': self._check_stun_status(),
            'upnp': self._check_upnp_status()
        }

        return status

    def _check_turn_status(self):
        """Check TURN server status"""
        if not self.relay_config.get('turn_enabled', False):
            return {'enabled': False, 'status': 'disabled'}

        # In a real implementation, this would check if the TURN server is running
        return {
            'enabled': True,
            'status': 'running' if self.relay_active else 'stopped',
            'port': self.relay_config.get('turn_port', 3478)
        }

    def _check_stun_status(self):
        """Check STUN server status"""
        if not self.relay_config.get('stun_enabled', False):
            return {'enabled': False, 'status': 'disabled'}

        return {
            'enabled': True,
            'status': 'running' if self.relay_active else 'stopped',
            'port': self.relay_config.get('stun_port', 3478)
        }

    def _check_upnp_status(self):
        """Check UPnP status"""
        try:
            import miniupnpc
            upnpc = miniupnpc.UPnP()
            upnpc.discoverdelay = 200
            upnpc.discover()
            upnpc.selectigd()

            external_port = self.relay_config.get('external_port', 3142)
            # Check if our port mapping exists
            mappings = upnpc.getportmappingnumberofentries()
            for i in range(mappings):
                try:
                    pm = upnpc.getgenericportmapping(i)
                    if pm[0] == external_port and pm[1] == 'TCP':
                        return {
                            'enabled': True,
                            'status': 'active',
                            'external_ip': upnpc.externalipaddress(),
                            'port': external_port
                        }
                except:
                    continue

            return {'enabled': True, 'status': 'inactive'}

        except ImportError:
            return {'enabled': False, 'status': 'unavailable'}
        except Exception:
            return {'enabled': True, 'status': 'error'}

    def update_config(self, new_config):
        """Update relay configuration"""
        self.relay_config.update(new_config)
        self._save_relay_config()
        return "Relay configuration updated"

    def get_network_info(self):
        """Get network connectivity information"""
        try:
            discovery_status = node_discovery.get_discovery_status()
            endpoints = discovery_status.get('endpoints', [])

            info = {
                'public_ip': 'Unknown',
                'tor_address': 'Not configured',
                'stun_endpoints': 0,
                'turn_relays': 0,
                'upnp_ports': 0,
                'relay_services': []
            }

            for endpoint in endpoints:
                ep_type = endpoint.get('type')
                if ep_type == 'stun_direct':
                    info['stun_endpoints'] += 1
                    if not info['public_ip'] or info['public_ip'] == 'Unknown':
                        info['public_ip'] = endpoint.get('ip', 'Unknown')
                elif ep_type == 'turn_relay':
                    info['turn_relays'] += 1
                elif ep_type == 'tor_onion':
                    info['tor_address'] = endpoint.get('address', 'Unknown')[:20] + "..."
                elif ep_type == 'upnp':
                    info['upnp_ports'] += 1

            # Add relay service info
            relay_status = self.get_relay_status()
            if relay_status['services']['turn']['enabled']:
                info['relay_services'].append('TURN')
            if relay_status['services']['stun']['enabled']:
                info['relay_services'].append('STUN')
            if relay_status['services']['upnp']['enabled']:
                info['relay_services'].append('UPnP')

            return info

        except Exception as e:
            return {'error': str(e)}

    def _send_activity_message(self, message):
        """Send activity message to UI"""
        if self.app:
            self.app.post_message(MiningActivityMessage(message))


class MiningLogic:
    """Mining logic backend for the console"""

    def __init__(self, app=None):
        self.app = app

        # Initialize components with error handling
        self.blockchain = None
        self.hardware = None
        self.relay_manager = None
        self.miner_wallet = None
        self.valuation_engine = None

        # Initialize components safely
        self._initialize_components()

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

    def _initialize_components(self):
        """Initialize components with error handling"""
        # Initialize blockchain
        try:
            self.blockchain = SignChain()
        except Exception as e:
            print(f"⚠️ Failed to initialize blockchain: {e}")
            self.blockchain = None

        # Initialize hardware verifier
        try:
            self.hardware = HardwareVerifier()
        except Exception as e:
            print(f"⚠️ Failed to initialize hardware verifier: {e}")
            self.hardware = None

        # Initialize relay manager
        try:
            self.relay_manager = RelayManager()
        except Exception as e:
            print(f"⚠️ Failed to initialize relay manager: {e}")
            self.relay_manager = None

        # Load miner wallet
        try:
            self.miner_wallet = self._load_miner_wallet()
        except Exception as e:
            print(f"⚠️ Failed to load miner wallet: {e}")
            self.miner_wallet = None

        # Initialize valuation engine
        try:
            self.valuation_engine = USDValuationEngine()
        except Exception as e:
            print(f"⚠️ Failed to initialize valuation engine: {e}")
            self.valuation_engine = None

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

        # Hardware verification (if available)
        if self.hardware:
            try:
                result = self.hardware.verify_mining_eligibility()
                if not result['eligible']:
                    return f"Hardware verification failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                print(f"⚠️ Hardware verification error: {e}")
                # Continue anyway - don't block mining due to verification issues

        # Check if blockchain is available
        if not self.blockchain:
            return "Blockchain not available - cannot start mining"

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

        self._send_activity_message("🛑 Stop mining requested - stopping immediately")
        self.stop_mining.set()
        self.mining_active = False

        # Wait a short time for graceful shutdown
        if hasattr(self, 'mining_thread') and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=2.0)  # Wait up to 2 seconds
            if self.mining_thread.is_alive():
                self._send_activity_message("⚠️ Mining thread still running - force stopping")
            else:
                self._send_activity_message("✅ Mining stopped gracefully")

        return "Mining stopped"

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

                # Update market factors for USD valuation (every 30 seconds)
                if int(time.time()) % 30 == 0:
                    self.valuation_engine.update_market_factors(self.blockchain, self.stats)

                # Check for stop request before starting mining
                if self.stop_mining.is_set():
                    self._send_activity_message("🛑 Mining stopped by user request")
                    break

                # Mine a block with shorter timeout for more responsive stopping
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.blockchain.mine_pending_transactions, self.miner_wallet, False)

                    try:
                        # Shorter timeout for more responsive stopping (0.5 seconds)
                        block = future.result(timeout=0.5)  # 0.5 second timeout
                    except concurrent.futures.TimeoutError:
                        # Mining timed out - check if we should stop
                        if self.stop_mining.is_set():
                            self._send_activity_message("🛑 Mining stopped immediately by user request")
                            break
                        else:
                            # Continue mining this block with another short timeout
                            try:
                                block = future.result(timeout=0.5)  # Try again briefly
                            except concurrent.futures.TimeoutError:
                                # Still no block found, send detailed progress update and continue
                                elapsed = time.time() - start_time
                                if nonce_count % 20 == 0:  # More frequent updates
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

                                time.sleep(0.01)  # Very brief pause
                                nonce_count += 1
                                continue

                if block is not None:
                    # Check if we should stop before processing the found block
                    if self.stop_mining.is_set():
                        self._send_activity_message("🛑 Block found but mining stopped by user request")
                        break

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

                    # Check if we should stop before starting next block
                    if self.stop_mining.is_set():
                        self._send_activity_message("🛑 Mining stopped after completing block")
                        break

                    # Prepare for next block
                    block_index += 1
                    nonce_count = 0
                    start_time = time.time()
                    self._send_activity_message(f"🎯 Now mining block #{block_index}")

                else:
                    # Still mining - send periodic updates
                    nonce_count += 1
                    if nonce_count % 200 == 0:  # More frequent updates
                        elapsed = time.time() - start_time
                        hashrate = nonce_count / elapsed if elapsed > 0 else 0
                        self._send_activity_message(f"⛏️ Mining... Nonce: {nonce_count:,} | Rate: {hashrate:.1f} H/s")

                    time.sleep(0.01)  # Brief pause

            except Exception as e:
                if not self.stop_mining.is_set():  # Don't log errors if we're stopping
                    self._send_activity_message(f"❌ Mining error: {e}")
                time.sleep(2)

        self._send_activity_message("🏁 Mining session ended")

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
        try:
            if self.relay_manager.relay_active:
                result = self.relay_manager.stop_relay()
                self._send_activity_message(f"🔌 Relay services stopped: {result}")
                return f"Relay stopped: {result}"
            else:
                result = self.relay_manager.start_relay()
                self._send_activity_message(f"🔌 Relay services started: {result}")
                return f"Relay started: {result}"
        except Exception as e:
            error_msg = f"Failed to toggle relay: {e}"
            self._send_activity_message(f"❌ {error_msg}")
            return error_msg


class MiningConsoleApp(App):
    """Textual-based mining console application"""

    CSS = """
    Screen {
        background: $surface;
    }

    #status_bar {
        height: 1;
        background: $primary;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    #stats_container {
        layout: horizontal;
        height: 12;
    }

    #system_stats, #mining_stats {
        width: 50%;
        margin: 0 1;
    }

    #mining_progress {
        height: 1;
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
        Binding("v", "valuation_info", "Token Valuation"),
        Binding("e", "export_stats", "Export Stats"),
        Binding("h", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.mining_console = MiningLogic(self)

    def compose(self) -> ComposeResult:
        yield Header()
        # Status indicator bar
        yield Static(self._get_status_bar(), id="status_bar")
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
            # Update status bar
            status_widget = self.query_one("#status_bar", Static)
            status_widget.update(self._get_status_bar())
        except:
            pass  # Panels might not be mounted yet

    def _get_controls_text(self):
        """Get the controls text"""
        return """
[dim]┌─[/dim][bold cyan] Mining Console Controls [/bold cyan][dim]─┐[/dim]
[dim]│[/dim] [green]S[/green] Start Mining  [red]X[/red] Stop Mining   [dim]│[/dim]
[dim]│[/dim] [yellow]C[/yellow] Test TX      [blue]W[/blue] Wallet Info  [dim]│[/dim]
[dim]│[/dim] [magenta]N[/magenta] Network     [cyan]R[/cyan] Toggle Relay [dim]│[/dim]
[dim]│[/dim] [white]V[/white] Valuation    [white]E[/white] Export Stats [dim]│[/dim]
[dim]│[/dim] [white]H[/white] Help          [white]Q[/white] Quit         [dim]│[/dim]
[dim]└─────────────────────────────────┘[/dim]
        """

    def _get_status_bar(self):
        """Get the status bar text"""
        try:
            mining_console = self.mining_console

            # Mining status
            mining_status = "🟢 MINING" if mining_console.mining_active else "🔴 STOPPED"

            # Relay status
            relay_status = "🔗 RELAY" if (mining_console.relay_manager and mining_console.relay_manager.relay_active) else "❌ NO RELAY"

            # Network status
            if mining_console.blockchain:
                try:
                    chain_info = mining_console.blockchain.get_chain_info()
                    network_status = f"⛓️ {chain_info['blocks']} BLOCKS"
                except:
                    network_status = "⛓️ BLOCKCHAIN ERROR"
            else:
                network_status = "⛓️ NO BLOCKCHAIN"

            # Wallet status
            if mining_console.blockchain and mining_console.miner_wallet:
                try:
                    wallet_balance = mining_console.blockchain.get_wallet_balance(mining_console.miner_wallet)
                    if mining_console.valuation_engine:
                        valuation_data = mining_console.valuation_engine.get_mining_value_estimate(mining_console.stats)
                        wallet_value_usd = wallet_balance * valuation_data['token_value_usd']
                        wallet_status = f"💰 ${wallet_value_usd:.2f} USD"
                    else:
                        wallet_status = f"💰 {wallet_balance:.2f} TOKENS"
                except:
                    wallet_status = "💰 WALLET ERROR"
            else:
                wallet_status = "💰 NO WALLET"

            # Token valuation status
            if mining_console.valuation_engine:
                try:
                    valuation_data = mining_console.valuation_engine.get_mining_value_estimate(mining_console.stats)
                    token_status = f"💎 ${valuation_data['token_value_usd']:.4f}"
                except:
                    token_status = "💎 VALUATION ERROR"
            else:
                token_status = "💎 NO VALUATION"

            # System status
            try:
                import psutil
                cpu_percent = psutil.cpu_percent()
                system_status = f"🖥️ CPU {cpu_percent:.0f}%"
            except:
                system_status = "🖥️ SYSTEM OK"

            return f"{mining_status} | {relay_status} | {network_status} | {wallet_status} | {token_status} | {system_status}"

        except Exception as e:
            return f"⚠️ Status Error: {str(e)[:30]}..."

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

    def action_valuation_info(self):
        """Show detailed token valuation info"""
        try:
            valuation = self.mining_console.valuation_engine.get_market_summary()
            stats = self.mining_console.stats
            mining_value = self.mining_console.valuation_engine.get_mining_value_estimate(stats)

            info_lines = [
                f"Token Value: ${valuation['current_value']:.4f} USD",
                f"1H Trend: {valuation['trend_1h']:+.2f}%",
                f"Session Earnings: ${mining_value['session_rewards_usd']:.4f} USD",
                f"Hourly Rate: ${mining_value['hourly_rate_usd']:.4f} USD/hr",
                f"Network Nodes: {valuation['valuation_drivers']['network_nodes']}",
                f"Exchange Adoption: {valuation['valuation_drivers']['exchange_adoption']}"
            ]

            self.notify(" | ".join(info_lines), severity="information")
        except Exception as e:
            self.notify(f"Failed to get valuation info: {e}", severity="error")

    def action_export_stats(self):
        """Export mining statistics"""
        try:
            import json
            from pathlib import Path

            stats = self.mining_console.stats
            blockchain = self.mining_console.blockchain
            chain_info = blockchain.get_chain_info()
            valuation = self.mining_console.valuation_engine.get_market_summary()
            mining_value = self.mining_console.valuation_engine.get_mining_value_estimate(stats)

            export_data = {
                "timestamp": time.time(),
                "mining_stats": stats,
                "blockchain_info": chain_info,
                "wallet_balance": blockchain.get_wallet_balance(self.mining_console.miner_wallet) if self.mining_console.miner_wallet else 0,
                "relay_status": self.mining_console.relay_manager.get_relay_status(),
                "usd_valuation": {
                    "current_token_value_usd": valuation['current_value'],
                    "valuation_trend_1h_percent": valuation['trend_1h'],
                    "session_earnings_usd": mining_value['session_rewards_usd'],
                    "total_earnings_usd": mining_value['total_rewards_usd'],
                    "hourly_mining_rate_usd": mining_value['hourly_rate_usd'],
                    "market_factors": valuation['market_factors'],
                    "valuation_drivers": valuation['valuation_drivers']
                }
            }

            export_file = Path.home() / f"pisecure_mining_stats_{int(time.time())}.json"
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.notify(f"Stats exported to {export_file}", severity="information")
        except Exception as e:
            self.notify(f"Failed to export stats: {e}", severity="error")

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