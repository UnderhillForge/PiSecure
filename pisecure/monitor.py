"""
PiSecure Mining Dashboard - Real-time monitoring for solo and Syndicate mining
Inspired by HandyMiner-CLI with Pi-specific metrics
"""

import time
import sys
from collections import deque
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from pisecure.core.blockchain import SignChain
from pisecure.core.system_monitor import SystemMonitor
from pisecure.core.syndicate import MiningSyndicate


@dataclass
class DashboardState:
    """Track dashboard state and historical data"""
    mode: str = "solo"  # solo or syndicate
    refresh_rate: float = 1.0
    start_time: float = field(default_factory=time.time)
    
    # Historical data for sparklines (last 60 samples)
    hashrate_history: deque = field(default_factory=lambda: deque(maxlen=60))
    temp_history: deque = field(default_factory=lambda: deque(maxlen=60))
    zeros_history: deque = field(default_factory=lambda: deque(maxlen=60))
    
    # Session tracking
    session_blocks: int = 0
    session_rewards: float = 0.0
    last_block_time: Optional[float] = None


class MiningDashboard:
    """Interactive mining dashboard with Rich UI"""
    
    def __init__(
        self,
        blockchain: SignChain,
        mode: str = "solo",
        refresh_rate: float = 1.0,
        syndicate: Optional[MiningSyndicate] = None,
        testnet: bool = False,
        wallet_address: Optional[str] = None
    ):
        self.blockchain = blockchain
        self.mode = mode
        self.refresh_rate = refresh_rate
        self.syndicate = syndicate
        self.testnet = testnet
        self.wallet_address = wallet_address
        self.console = Console()
        self.state = DashboardState(mode=mode, refresh_rate=refresh_rate)
        self.system_monitor = SystemMonitor()
        
        # Debug: Log blockchain instance ID (guard against missing attributes in validation mode)
        try:
            with open('/tmp/pisecure_dashboard_instance.log', 'w') as f:
                f.write(f"Dashboard blockchain ID: {id(blockchain)}\n")
                if hasattr(blockchain, 'mining_session'):
                    f.write(f"Mining session dict ID: {id(blockchain.mining_session)}\n")
                else:
                    f.write(f"Mining session: not available (validation mode)\n")
        except Exception:
            pass
        
    def create_sparkline(self, data: deque, max_value: Optional[float] = None) -> str:
        """Create Unicode sparkline chart from data"""
        if not data or len(data) == 0:
            return "▁" * 20
        
        # Sparkline characters from lowest to highest
        chars = "▁▂▃▄▅▆▇█"
        
        # Normalize data to 0-7 range
        min_val = min(data)
        max_val = max_value if max_value else max(data)
        
        if max_val == min_val:
            return chars[0] * len(data)
        
        normalized = []
        for val in data:
            norm = (val - min_val) / (max_val - min_val)
            idx = min(int(norm * (len(chars) - 1)), len(chars) - 1)
            normalized.append(chars[idx])
        
        return "".join(normalized)
    
    def get_temp_color(self, temp: float) -> str:
        """Get color based on temperature thresholds"""
        if temp >= 80:
            return "red"
        elif temp >= 75:
            return "bright_red"
        elif temp >= 70:
            return "yellow"
        return "green"
    
    def get_throttle_color(self, throttle: str) -> str:
        """Get color based on throttle status"""
        if throttle in ["EMERGENCY_STOP", "PAUSED"]:
            return "red"
        elif throttle == "HEAVY_THROTTLE":
            return "yellow"
        elif throttle == "LIGHT_THROTTLE":
            return "cyan"
        return "green"
    
    def format_uptime(self, seconds: float) -> str:
        """Format seconds into human-readable uptime"""
        td = timedelta(seconds=int(seconds))
        days = td.days
        hours = td.seconds // 3600
        mins = (td.seconds % 3600) // 60
        secs = td.seconds % 60
        
        if days > 0:
            return f"{days}d {hours}h {mins}m"
        elif hours > 0:
            return f"{hours}h {mins}m {secs}s"
        elif mins > 0:
            return f"{mins}m {secs}s"
        else:
            return f"{secs}s"
    
    def format_hashrate(self, hashrate: float) -> str:
        """Format hashrate with appropriate unit"""
        if hashrate >= 1000:
            return f"{hashrate/1000:.2f} KH/s"
        else:
            return f"{hashrate:.2f} H/s"
    
    def build_header_panel(self) -> Panel:
        """Build header with PiSecure branding"""
        network = "TESTNET" if self.testnet else "MAINNET"
        mode_display = "🔗 Syndicate Pool" if self.mode == "syndicate" else "⛏️  Solo Mining"
        
        header_text = Text()
        header_text.append("π", style="bold cyan")
        header_text.append("Secure Mining Dashboard", style="bold white")
        header_text.append(f"  |  {network}", style="bold magenta" if self.testnet else "bold green")
        header_text.append(f"  |  {mode_display}", style="bold yellow")
        
        return Panel(header_text, box=box.DOUBLE, style="cyan")
    
    def build_mining_status_panel(self, stats: Dict[str, Any]) -> Panel:
        """Build mining status panel with current work"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        # Mining status
        mining_active = stats.get("mining_active", False)
        status_icon = "🟢" if mining_active else "🔴"
        status_text = "ACTIVE" if mining_active else "IDLE"
        table.add_row(f"{status_icon} Status", f"[bold]{status_text}[/bold]")
        
        # Current hashrate with sparkline
        hashrate = stats.get("hashrate", 0.0)
        self.state.hashrate_history.append(hashrate)
        sparkline = self.create_sparkline(self.state.hashrate_history, max_value=2.5)
        table.add_row("⚡ Hashrate", f"{self.format_hashrate(hashrate)} {sparkline}")
        
        # Current work
        target_zeros = stats.get("target_zeros", 0)
        best_zeros = stats.get("best_zeros", 0)
        self.state.zeros_history.append(best_zeros)
        progress_pct = (best_zeros / target_zeros * 100) if target_zeros > 0 else 0
        zeros_sparkline = self.create_sparkline(self.state.zeros_history, max_value=target_zeros)
        table.add_row("🎯 Progress", f"{best_zeros}/{target_zeros} zeros ({progress_pct:.1f}%) {zeros_sparkline}")
        
        # Nonce and hashes
        nonce = stats.get("current_nonce", 0)
        hashes_tried = stats.get("hashes_tried", 0)
        table.add_row("🔢 Nonce", f"{nonce:,}")
        table.add_row("🔨 Hashes", f"{hashes_tried:,}")
        
        # Estimated time to block
        est_time = stats.get("estimated_time_to_block", None)
        if est_time and est_time > 0:
            table.add_row("⏱️  Est. Time", self.format_uptime(est_time))
        
        return Panel(table, title="⛏️  Mining Status", border_style="green", box=box.ROUNDED)
    
    def build_hardware_panel(self) -> Panel:
        """Build hardware health panel with thermal monitoring"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        
        # Get system status
        sys_status = self.system_monitor.get_system_status()
        
        # CPU Temperature with sparkline
        temp = sys_status.get("temperature", 0.0)
        self.state.temp_history.append(temp)
        temp_color = self.get_temp_color(temp)
        temp_sparkline = self.create_sparkline(self.state.temp_history, max_value=85.0)
        table.add_row("🌡️  CPU Temp", f"[{temp_color}]{temp:.1f}°C[/{temp_color}] {temp_sparkline}")
        
        # Throttle status
        throttle = sys_status.get("throttle_status", "NORMAL")
        throttle_color = self.get_throttle_color(throttle)
        table.add_row("🚦 Throttle", f"[{throttle_color}]{throttle}[/{throttle_color}]")
        
        # Memory usage
        mem_percent = sys_status.get("memory_percent", 0.0)
        mem_color = "red" if mem_percent > 90 else "yellow" if mem_percent > 80 else "green"
        table.add_row("💾 Memory", f"[{mem_color}]{mem_percent:.1f}%[/{mem_color}]")
        
        # Pi model
        pi_model = sys_status.get("pi_model", "Unknown")
        table.add_row("🔧 Hardware", f"[bold]{pi_model}[/bold]")
        
        return Panel(table, title="🖥️  Hardware Health", border_style="blue", box=box.ROUNDED)
    
    def build_session_panel(self, stats: Dict[str, Any]) -> Panel:
        """Build session statistics panel"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        # Session uptime
        uptime = time.time() - self.state.start_time
        table.add_row("⏰ Uptime", self.format_uptime(uptime))
        
        # Blocks found this session (since dashboard started)
        blocks_found = stats.get("session_blocks_found", self.state.session_blocks)
        table.add_row("📦 Blocks (Session)", f"[bold green]{blocks_found}[/bold green]")
        
        # Rewards earned
        rewards = blocks_found * 50  # 50 314ST per block
        table.add_row("💰 Rewards", f"[bold yellow]{rewards:.2f} 314ST[/bold yellow]")
        
        # Average block time
        if blocks_found > 0 and self.state.last_block_time:
            avg_block_time = uptime / blocks_found
            table.add_row("⏱️  Avg Block", self.format_uptime(avg_block_time))
        
        # Network difficulty (use target_zeros for PiHash)
        difficulty = stats.get("target_zeros", stats.get("difficulty", 0))
        table.add_row("🎯 Difficulty", f"{difficulty} zeros")
        
        return Panel(table, title="📊 Session Stats", border_style="yellow", box=box.ROUNDED)
    
    def build_syndicate_panel(self, stats: Dict[str, Any]) -> Panel:
        """Build Syndicate pool panel (graceful fallback if unavailable)"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        if not self.syndicate:
            # Graceful fallback
            table.add_row("Status", "[yellow]Not connected[/yellow]")
            table.add_row("Info", "Use --mode syndicate to join pool")
            return Panel(table, title="🔗 Syndicate Pool", border_style="dim", box=box.ROUNDED)
        
        try:
            # Get syndicate stats
            syn_stats = self.syndicate.get_stats()
            
            # Pool info
            pool_name = syn_stats.get("syndicate_name", "Unknown")
            total_members = syn_stats.get("total_members", 0)
            table.add_row("🏊 Pool", f"[bold]{pool_name}[/bold]")
            table.add_row("👥 Members", f"{total_members}")
            
            # Total pool hashrate
            total_hashpower = syn_stats.get("total_hashpower", 0.0)
            table.add_row("⚡ Pool Rate", self.format_hashrate(total_hashpower))
            
            # Your contribution
            your_hashrate = stats.get("hashrate", 0.0)
            if total_hashpower > 0:
                share_pct = (your_hashrate / total_hashpower) * 100
                table.add_row("📊 Your Share", f"[bold green]{share_pct:.2f}%[/bold green]")
            
            # Blocks found by pool
            pool_blocks = syn_stats.get("total_blocks_found", 0)
            table.add_row("📦 Pool Blocks", f"{pool_blocks}")
            
            # Your rewards (if member stats available)
            member_id = getattr(self, "member_id", None)
            if member_id:
                member_stats = self.syndicate.get_member_stats(member_id)
                if member_stats:
                    your_blocks = member_stats.get("blocks_found", 0)
                    your_rewards = your_blocks * 50 * 0.85  # 85% after 5% fee + 10% finder bonus
                    table.add_row("💰 Your Rewards", f"[bold yellow]{your_rewards:.2f} 314ST[/bold yellow]")
            
        except Exception as e:
            # Graceful error handling
            table.add_row("Status", f"[red]Error: {str(e)}[/red]")
            table.add_row("Info", "Connection lost or pool unavailable")
        
        return Panel(table, title="🔗 Syndicate Pool", border_style="magenta", box=box.ROUNDED)
    
    def build_blockchain_panel(self, stats: Dict[str, Any]) -> Panel:
        """Build blockchain status panel"""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        try:
            # Chain info (uses cached validation, no lock needed)
            chain_info = self.blockchain.get_chain_info()
            
            total_blocks = chain_info.get("total_blocks", 0)
            pending_txs = chain_info.get("pending_transactions", 0)
            is_valid = chain_info.get("is_valid_chain", False)
            
            table.add_row("⛓️  Total Blocks", f"{total_blocks:,}")
            table.add_row("📨 Pending TXs", f"{pending_txs}")
            
            validity_icon = "✅" if is_valid else "❌"
            validity_text = "VALID" if is_valid else "INVALID"
            table.add_row("🔐 Chain Valid", f"{validity_icon} {validity_text}")
            
            # Latest block - safe access with try-except
            try:
                if len(self.blockchain.chain) > 0:
                    latest_block = self.blockchain.chain[-1]
                    block_time = datetime.fromtimestamp(latest_block.timestamp).strftime("%H:%M:%S")
                    table.add_row("🕐 Last Block", block_time)
            except (IndexError, AttributeError):
                # Chain modified during read, skip this update
                pass
                
        except Exception as e:
            # Graceful error handling
            table.add_row("Status", f"[yellow]Reading...[/yellow]")
        
        return Panel(table, title="⛓️  Blockchain", border_style="cyan", box=box.ROUNDED)
    
    def build_layout(self, stats: Dict[str, Any]) -> Layout:
        """Build complete dashboard layout"""
        layout = Layout()
        
        # Main structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Body layout
        if self.mode == "syndicate":
            # Show syndicate panel in syndicate mode
            layout["body"].split_row(
                Layout(name="left_col"),
                Layout(name="right_col")
            )
            layout["left_col"].split_column(
                Layout(name="mining", ratio=2),
                Layout(name="session", ratio=1)
            )
            layout["right_col"].split_column(
                Layout(name="hardware", ratio=1),
                Layout(name="syndicate", ratio=1),
                Layout(name="blockchain", ratio=1)
            )
            layout["syndicate"].update(self.build_syndicate_panel(stats))
        else:
            # Solo mode - no syndicate panel
            layout["body"].split_row(
                Layout(name="left_col"),
                Layout(name="right_col")
            )
            layout["left_col"].split_column(
                Layout(name="mining", ratio=2),
                Layout(name="session", ratio=1)
            )
            layout["right_col"].split_column(
                Layout(name="hardware", ratio=1),
                Layout(name="blockchain", ratio=1)
            )
        
        # Populate panels
        layout["header"].update(self.build_header_panel())
        layout["mining"].update(self.build_mining_status_panel(stats))
        layout["hardware"].update(self.build_hardware_panel())
        layout["session"].update(self.build_session_panel(stats))
        layout["blockchain"].update(self.build_blockchain_panel(stats))
        
        # Footer
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold red")
        footer_text.append(" to exit  |  Refresh: ", style="dim")
        footer_text.append(f"{self.refresh_rate}s", style="bold cyan")
        footer_text.append("  |  Mode: ", style="dim")
        footer_text.append(self.mode.upper(), style="bold yellow")
        layout["footer"].update(Panel(footer_text, style="dim"))
        
        return layout
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Gather current mining and blockchain stats"""
        stats = {}
        
        # Try reading from status file first (faster, no dict access)
        try:
            with open('/tmp/pisecure_mining_status.txt', 'r') as f:
                content = f.read().strip()
                if content:
                    nonce, hashes, best_zeros, target = content.split(',')
                    stats['current_nonce'] = int(nonce)
                    stats['hashes_tried'] = int(hashes)
                    stats['best_zeros'] = int(best_zeros)
                    stats['target_zeros'] = int(target)
                    # Calculate hashrate from file data
                    if hasattr(self.blockchain, 'mining_session') and self.blockchain.mining_session.get('start_time'):
                        elapsed = time.time() - self.blockchain.mining_session['start_time']
                        if elapsed > 0:
                            stats['hashrate'] = int(hashes) / elapsed
                    stats['mining_active'] = True
        except:
            pass
        
        # Fallback to dict reads if file method fails
        if not stats:
            # Get mining stats from blockchain (only if mining_session exists)
            if hasattr(self.blockchain, 'get_live_mining_stats'):
                try:
                    mining_stats = self.blockchain.get_live_mining_stats()
                    stats.update(mining_stats)
                except:
                    pass
        
        # Get session state if available
        if hasattr(self.blockchain, 'get_mining_session_state'):
            try:
                session_state = self.blockchain.get_mining_session_state()
                stats.update(session_state)
            except:
                pass
        
        # Update session tracking
        if stats.get("session_blocks_found", 0) > self.state.session_blocks:
            self.state.session_blocks = stats["session_blocks_found"]
            self.state.last_block_time = time.time()
        
        # Add wallet info if monitoring with validation rewards
        if self.wallet_address and self.mode == 'validation':
            try:
                balance = self.blockchain.get_wallet_balance(self.wallet_address)
                validation_rewards = self.blockchain.get_validation_rewards(self.wallet_address)
                stats['wallet_address'] = self.wallet_address
                stats['wallet_balance'] = balance
                stats['validation_rewards'] = validation_rewards
            except Exception:
                pass
        
        return stats
    
    def run(self):
        """Run the interactive dashboard"""
        self.console.print("\n[bold cyan]🚀 Starting PiSecure Mining Dashboard...[/bold cyan]\n")
        time.sleep(1)
        
        # Debug logging
        debug_log = open('/tmp/pisecure_dashboard_debug.log', 'w')
        debug_log.write(f"Dashboard started at {time.time()}\n")
        debug_log.flush()
        
        try:
            with Live(
                self.build_layout({}),
                console=self.console,
                refresh_per_second=1/self.refresh_rate,
                screen=True
            ) as live:
                iteration = 0
                while True:
                    iteration += 1
                    try:
                        # Debug
                        if iteration <= 5:
                            debug_log.write(f"Dashboard iteration {iteration}\n")
                            debug_log.flush()
                        
                        # Gather current stats
                        stats = self.get_current_stats()
                        
                        # Debug
                        if iteration <= 5:
                            debug_log.write(f"Stats: mining_active={stats.get('mining_active')}, hashrate={stats.get('hashrate')}\n")
                            debug_log.flush()
                        
                        # Update display
                        live.update(self.build_layout(stats))
                        
                        # Sleep for refresh interval
                        time.sleep(self.refresh_rate)
                        
                    except KeyboardInterrupt:
                        debug_log.write("KeyboardInterrupt in inner loop\n")
                        debug_log.flush()
                        break
                    except Exception as e:
                        # Show errors but keep running
                        debug_log.write(f"Error in dashboard loop: {e}\n")
                        import traceback
                        debug_log.write(traceback.format_exc())
                        debug_log.flush()
                        self.console.print(f"[yellow]Warning: {e}[/yellow]")
                        time.sleep(self.refresh_rate)
        
        except KeyboardInterrupt:
            debug_log.write("KeyboardInterrupt in outer try\n")
            debug_log.flush()
            pass
        except Exception as e:
            debug_log.write(f"Error in Live context: {e}\n")
            import traceback
            debug_log.write(traceback.format_exc())
            debug_log.flush()
        finally:
            debug_log.write("Dashboard stopping\n")
            debug_log.close()
            self.console.print("\n[bold yellow]👋 Dashboard stopped[/bold yellow]\n")


def main():
    """Entry point for testing dashboard standalone"""
    console = Console()
    console.print("[yellow]Use 'pisecure monitor' command to launch dashboard[/yellow]")
    console.print("[dim]This module is not meant to be run directly[/dim]")


if __name__ == "__main__":
    main()
