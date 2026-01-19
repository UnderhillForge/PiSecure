#!/usr/bin/env python3
"""
PiSecure Command Line Interface
===============================

Main CLI entry point for PiSecure framework.
"""

import time
import secrets
import os
import click
from rich.console import Console
from rich.table import Table

try:
    # Try relative imports first (for package installation)
    from .core import SignChain, HardwareVerifier, SignTokenMiner
    from .core.p2p_sync import P2PSyncManager
    from .network.discovery import PeerDiscovery
    from .updates import OTAUpdater
    from .identity import DeviceIdentity, DeviceAuthenticator
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core import SignChain, HardwareVerifier, SignTokenMiner
    from core.p2p_sync import P2PSyncManager
    from network.discovery import PeerDiscovery
    from updates import OTAUpdater
    from identity import DeviceIdentity, DeviceAuthenticator

console = Console()

# Global configuration
USE_HYBRID_STORAGE = None  # None = auto-detect, True/False = explicit
USE_PLAIN_OUTPUT = False   # Global flag for plain text output


def print_output(message, style=None):
    """Print message with optional Rich styling or plain text"""
    if USE_PLAIN_OUTPUT:
        # Strip Rich markup and print plain text
        import re
        # Remove Rich markup like [green]text[/green] and [red]❌ Error[/red]
        plain_message = re.sub(r'\[.*?\]', '', message)
        # Remove all non-ASCII characters (including emojis, Unicode symbols)
        plain_message = re.sub(r'[^\x20-\x7E]+', '', plain_message)
        # Clean up extra whitespace
        plain_message = ' '.join(plain_message.split())
        if plain_message:  # Only print if there's content left
            print(plain_message)
    else:
        if style:
            console.print(message, style=style)
        else:
            console.print(message)


def strip_rich_formatting(text):
    """Strip Rich markup and emojis from text"""
    import re
    # Remove Rich markup like [green]text[/green]
    text = re.sub(r'\[.*?\]', '', text)
    # Remove all non-ASCII characters (including emojis, Unicode symbols)
    text = re.sub(r'[^\x20-\x7E]+', '', text)
    # Clean up extra whitespace
    return ' '.join(text.split()).strip()


def print_success(message):
    """Print success message"""
    if USE_PLAIN_OUTPUT:
        print(f"SUCCESS: {message}")
    else:
        console.print(f"[green]✅ {message}[/green]")


def print_error(message):
    """Print error message"""
    if USE_PLAIN_OUTPUT:
        print(f"ERROR: {message}")
    else:
        console.print(f"[red]❌ {message}[/red]")


def print_warning(message):
    """Print warning message"""
    if USE_PLAIN_OUTPUT:
        print(f"WARNING: {message}")
    else:
        console.print(f"[yellow]⚠️ {message}[/yellow]")


def print_info(message):
    """Print info message"""
    if USE_PLAIN_OUTPUT:
        print(f"INFO: {message}")
    else:
        console.print(f"[blue]ℹ️ {message}[/blue]")


@click.group()
@click.option('--hybrid-storage/--no-hybrid-storage', default=None,
              help='Use hybrid storage system (default: auto-detect)')
@click.option('--test', '--testnet', 'use_testnet', is_flag=True, default=False,
              help='Use testnet blockchain (separate from mainnet)')
@click.option('--validate-only', is_flag=True, default=False,
              help='Validation mode: verify blockchain integrity without Pi hardware (status/wallet commands only)')
@click.option('--quiet', is_flag=True, default=False,
              help='Reduce output verbosity (only show essential messages)')
@click.version_option(version="0.1.0")
def cli(hybrid_storage, use_testnet, validate_only, quiet):
    """PiSecure - Decentralized Security Framework for Raspberry Pi"""
    import logging
    
    # Store the hybrid storage preference globally
    global USE_HYBRID_STORAGE
    USE_HYBRID_STORAGE = hybrid_storage
    
    # Set quiet mode
    if quiet:
        import os
        os.environ['PISECURE_QUIET'] = '1'
        # Reduce logging noise from submodules
        logging.getLogger('pisecure.core.p2p_sync').setLevel(logging.WARNING)
        logging.getLogger('pisecure.core.nat_traversal').setLevel(logging.WARNING)
        logging.getLogger('pisecure.core.bootstrap_manager').setLevel(logging.ERROR)
        logging.getLogger('pisecure.network').setLevel(logging.WARNING)
    
    # Set testnet mode as environment variable
    if use_testnet:
        import os
        os.environ['PISECURE_TESTNET'] = '1'
        if not quiet:
            print_info("Running in TESTNET mode - using /var/lib/pisecure-testnet/")
    
    # Set validate-only mode as environment variable for core modules
    if validate_only:
        import os
        os.environ['PISECURE_VALIDATE_ONLY'] = '1'
        if not quiet:
            print_warning("⚠️  VALIDATE-ONLY MODE: Hardware checks bypassed")
            print_info("This mode is for blockchain verification only (status, wallet commands)")
            print_info("Mining is disabled - use a Raspberry Pi for mining operations")


@cli.command()
def status():
    """Show blockchain and system status"""
    try:
        blockchain = SignChain(use_hybrid_storage=USE_HYBRID_STORAGE)

        # Get blockchain info
        info = blockchain.get_chain_info()

        if USE_PLAIN_OUTPUT:
            # Plain text output
            print("PiSecure Blockchain Status")
            print("=" * 30)
            print(f"Blocks: {info['blocks']}")
            print(f"Pending TX: {info['pending_transactions']}")
            print(f"Difficulty: {info['difficulty']}")
            print(f"Chain Valid: {'Yes' if info['is_valid'] else 'No'}")

            if info['latest_block']:
                block = info['latest_block']
                print(f"Latest Block: #{block['index']} ({len(block['transactions'])} TX)")

            # Network health (if available)
            if 'network_health' in info:
                health = info['network_health']
                print(f"Participation: {health.get('participation', 0):.1%}")
                print(f"Avg Block Time: {health.get('avg_block_time', 0):.1f}s")
                print(f"Network Health: {health.get('health_score', 0):.1%}")
        else:
            # Rich formatted output
            table = Table(title="🔗 PiSecure Blockchain Status")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")

            table.add_row("Blocks", str(info['blocks']))
            table.add_row("Pending TX", str(info['pending_transactions']))
            table.add_row("Difficulty", str(info['difficulty']))
            table.add_row("Chain Valid", "✅ Yes" if info['is_valid'] else "❌ No")

            if info['latest_block']:
                block = info['latest_block']
                table.add_row("Latest Block", f"#{block['index']} ({len(block['transactions'])} TX)")

            # Network health (if available)
            if 'network_health' in info:
                health = info['network_health']
                table.add_row("Participation", f"{health.get('participation', 0):.1%}")
                table.add_row("Avg Block Time", f"{health.get('avg_block_time', 0):.1f}s")
                table.add_row("Network Health", f"{health.get('health_score', 0):.1%}")

            console.print(table)

    except Exception as e:
        print_error(f"Error getting status: {e}")


@cli.command()
def migrate_storage():
    """Migrate blockchain from JSON to hybrid storage"""
    try:
        console.print("🔄 Migrating to hybrid storage system...")
        console.print("   This will convert your JSON blockchain to block files + SQLite database")
        console.print()

        # Enable hybrid storage for migration
        blockchain = SignChain(use_hybrid_storage=True)

        info = blockchain.get_chain_info()
        console.print(f"✅ Migration complete! {info['blocks']} blocks migrated")
        console.print("   Future runs will use: --hybrid-storage flag")
        console.print("   Or set permanently in your startup scripts")

    except Exception as e:
        console.print(f"[red]❌ Migration failed: {e}[/red]")


@cli.command()
@click.option('--count', default=5, help='Number of test transactions to create')
def create_tx(count):
    """Create test transactions for mining"""
    try:
        import secrets

        blockchain = SignChain(use_hybrid_storage=USE_HYBRID_STORAGE)

        console.print(f"📦 Creating {count} test transactions...")

        for i in range(count):
            tx = {
                "type": "test_transaction",
                "data": {
                    "message": f"Test transaction #{i+1}",
                    "timestamp": time.time(),
                    "test_id": secrets.token_hex(8)
                },
                "signature": f"test_sig_{secrets.token_hex(4)}",
                "timestamp": time.time()
            }
            tx_hash = blockchain.add_transaction(tx)
            console.print(f"✅ Added test transaction: {tx_hash[:16]}...")

        console.print(f"\n💡 Created {count} test transactions. Run 'pisecure mine' to mine them!")

    except Exception as e:
        console.print(f"[red]❌ Error creating transactions: {e}[/red]")


@cli.command()
@click.option('--interactive/--background', default=True,
              help='Interactive mining with progress display')
@click.option('--wallet', help='Wallet address to receive mining rewards')
@click.option('--no-sync', is_flag=True, help='Skip network synchronization before mining')
@click.option('--safe-mode', is_flag=True, help='Enable system monitoring and thermal throttling')
@click.option('--plain', is_flag=True, help='Disable ANSI colors and formatting for plain text output')
def mine(interactive, wallet, no_sync, safe_mode, plain):
    """Start blockchain mining"""
    global USE_PLAIN_OUTPUT
    USE_PLAIN_OUTPUT = plain

    # CRITICAL: Verify hardware BEFORE allowing mining
    # Mining is NEVER allowed on non-Pi systems, regardless of flags
    import os
    try:
        from pisecure.core.pihash import PiHash
        pihash = PiHash()
        hw_fingerprint = pihash._get_hardware_fingerprint()
        
        # Verify this is actually a Raspberry Pi
        if not pihash._verify_hardware(hw_fingerprint):
            print_error("❌ MINING BLOCKED: This system is not a verified Raspberry Pi")
            print_info("PiSecure mining requires genuine Raspberry Pi hardware")
            print_info("Use 'pisecure status' or 'pisecure wallet' to interact with the blockchain")
            return
            
    except Exception as e:
        print_error(f"❌ MINING BLOCKED: Hardware verification failed - {e}")
        print_info("PiSecure mining requires genuine Raspberry Pi hardware")
        print_info("Use 'pisecure status' or 'pisecure wallet' to interact with the blockchain")
        return

    # Signal handling for graceful shutdown
    import signal
    mining_stopped = False

    def stop_mining_handler(signum, frame):
        # Immediately terminate the process - no cleanup needed
        import sys
        print_output("\nMining stopped by user")
        sys.stdout.flush()  # Ensure message is displayed
        import os
        os._exit(0)  # Force immediate termination

    # Register signal handler for SIGINT (Ctrl-C)
    signal.signal(signal.SIGINT, stop_mining_handler)
    try:
        blockchain = SignChain(use_hybrid_storage=USE_HYBRID_STORAGE)

        # Determine miner wallet address
        miner_wallet = wallet
        if not miner_wallet:
            # Try to load from config
            try:
                import json
                config_path = "/etc/pisecure/config.json"
                with open(config_path, 'r') as f:
                    config = json.load(f)
                miner_wallet = config.get('mining', {}).get('wallet_address')
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

        quiet_mode = os.environ.get('PISECURE_QUIET') == '1'
        
        if not miner_wallet:
            if not quiet_mode:
                print_warning("No miner wallet configured")
                print_info("Use --wallet to specify wallet address, or set mining.wallet_address in /etc/pisecure/config.json")
            miner_wallet = None

        # Sync with network before mining (unless disabled)
        if not no_sync:
            try:
                if not quiet_mode:
                    print_info("Syncing with network before mining...")
                peer_discovery = PeerDiscovery()
                p2p_sync = P2PSyncManager(blockchain, peer_discovery)

                initial_height = len(blockchain.chain)
                p2p_sync._perform_sync_cycle()
                final_height = len(blockchain.chain)
                blocks_synced = final_height - initial_height

                if blocks_synced > 0:
                    print_success(f"Synced {blocks_synced} blocks from network")
                elif not quiet_mode:
                    print_success("Already up-to-date with network")
            except Exception as e:
                if not quiet_mode:
                    print_warning(f"Network sync failed, proceeding with mining: {e}")
        else:
            if not quiet_mode:
                print_warning("Skipping network sync (--no-sync flag used)")

        # Initialize system monitor if safe mode is enabled
        system_monitor = None
        if safe_mode:
            try:
                from .core.monitoring import get_system_monitor
                system_monitor = get_system_monitor()
                system_monitor.start_monitoring()
                if not quiet_mode:
                    print_success("Safe mode enabled - System monitoring active")
                    print_info("Will monitor temperature, memory, and CPU usage")
            except Exception as e:
                if not quiet_mode:
                    print_warning(f"Could not enable safe mode monitoring: {e}")
                safe_mode = False

        # Initialize robust bootstrap-based status reporting
        try:
            from .core.bootstrap_manager import get_bootstrap_registry, get_status_reporter
            bootstrap_registry = get_bootstrap_registry()
            status_reporter = get_status_reporter(f"miner_{secrets.token_hex(4)}")
            if not quiet_mode:
                print_success("Bootstrap-based status reporting enabled")
                print_info("Will report to bootstrap.pisecure.org with automatic failover")
        except Exception as e:
            if not quiet_mode:
                print_warning(f"Could not initialize bootstrap reporting: {e}")
            status_reporter = None

        # Initialize miner variables
        node_id = f"miner_{secrets.token_hex(4)}"  # Generate unique node ID
        blocks_mined_session = 0
        session_start_time = time.time()
        last_discovery_check = 0
        discovery_interval = 600  # Check for new bootstrap servers every 10 minutes

        if interactive:
            # Launch MiningDashboard for interactive mining
            print_success("Starting PiSecure mining with dashboard...")
            if miner_wallet:
                print_output(f"Rewards will go to: {miner_wallet}")
            if safe_mode:
                print_output("Safe mode: Thermal throttling and memory cleanup enabled")
            print_output("Press Ctrl-C to stop")
            
            # Use MiningDashboard for rich UI
            from .monitor import MiningDashboard
            import threading
            import logging
            
            testnet = os.environ.get('PISECURE_TESTNET') == '1'
            
            # Event to signal when dashboard is ready to start mining
            mining_ready = threading.Event()
            
            dashboard = MiningDashboard(
                blockchain=blockchain,
                mode='solo',
                refresh_rate=1.0,
                testnet=testnet,
                wallet_address=miner_wallet,
                mining_ready_callback=lambda: mining_ready.set()
            )
            
            # Start mining in background thread
            def mine_loop():
                # Wait for dashboard to signal ready before starting mining
                mining_ready.wait()
                
                import os
                
                blocks_mined_session = 0
                
                # Set environment flag for PISECURE_QUIET mode
                os.environ['PISECURE_QUIET'] = '1'
                
                # Disable ALL loggers to prevent any console output that would flicker TUI
                logging.getLogger().setLevel(logging.CRITICAL)
                for logger_name in ['pisecure', 'pisecure.core.nat_traversal', 
                                   'pisecure.network.discovery', 'pisecure.core.p2p_sync',
                                   'pisecure.core.blockchain', 'urllib3', 'requests',
                                   'aiohttp', 'asyncio', 'dns', 'pip']:
                    logger = logging.getLogger(logger_name)
                    logger.setLevel(logging.CRITICAL)
                    # Remove all handlers to prevent output
                    logger.handlers.clear()
                    logger.propagate = False
                
                while not mining_stopped:
                    try:
                        # Mine with verbose=False to suppress block found messages
                        block = blockchain.mine_pending_transactions(miner_wallet, verbose=False)
                        if block:
                            blocks_mined_session += 1
                            blockchain.adapt_difficulty()
                        time.sleep(0.1)
                    except Exception as e:
                        # Log to file only
                        try:
                            with open('/tmp/pisecure_mining_errors.log', 'a') as f:
                                f.write(f"{time.time()}: {e}\n")
                        except Exception:
                            pass
                        time.sleep(1)
            
            mining_thread = threading.Thread(target=mine_loop, daemon=True)
            mining_thread.start()
            
            # Run dashboard (blocking)
            try:
                dashboard.run()
            except KeyboardInterrupt:
                print_output("\nMining stopped by user")
                return

        elif not interactive:

            try:
                while not mining_stopped:
                    # Check system resources in safe mode
                    throttle_status = None
                    if safe_mode and system_monitor:
                        throttle_status = system_monitor.check_system_resources()

                        # Display current system status
                        if throttle_status:
                            status_display = system_monitor.get_status_display(throttle_status)
                            print_info(f"System status: {status_display}")

                        # Apply cool-off strategy if needed
                        if not throttle_status['should_pause_mining']:
                            cool_off_action = system_monitor.apply_cool_off_strategy(throttle_status)
                            if cool_off_action['action'] != 'none':
                                action_msg = {
                                    'emergency_stop': 'Emergency stop triggered',
                                    'pause_mining': 'Cooling down - mining paused',
                                    'throttle_mining': 'Increased delays for cooling',
                                    'periodic_cleanup': 'Memory cleanup performed'
                                }.get(cool_off_action['action'], cool_off_action['action'])

                                if cool_off_action.get('memory_cleanup', {}).get('memory_freed_mb', 0) > 0:
                                    freed_mb = cool_off_action['memory_cleanup']['memory_freed_mb']
                                    action_msg += f" ({freed_mb:.1f}MB freed)"

                                print_warning(action_msg)
                        elif throttle_status['cool_down_time_remaining'] > 0:
                            remaining = throttle_status['cool_down_time_remaining']
                            print_warning(f"Cooling down... ({remaining:.0f}s remaining)")
                            time.sleep(min(remaining, 10))  # Sleep for remaining time or 10s max
                            continue

                    # Check stop flag before mining
                    if mining_stopped:
                        break

                    # Mine a single block (quietly - no Tor/P2P messages)
                    block = blockchain.mine_pending_transactions(miner_wallet, verbose=False)
                    if block:
                        blocks_mined_session += 1
                        print_success(f"Block mined! #{block.index}")

                        # Adapt difficulty (runs every 100 blocks toward 60s target)
                        blockchain.adapt_difficulty()

                        # Update wallet balance after mining reward
                        if miner_wallet:
                            try:
                                # Sync wallet balance with blockchain
                                blockchain_balance = blockchain.get_wallet_balance(miner_wallet)
                                # Update local wallet balance
                                try:
                                    from .core.wallet import SignWallet
                                    wallet = SignWallet()
                                    # Find wallet file for this address
                                    wallet_dir = "/var/lib/pisecure/wallets"
                                    if os.path.exists(wallet_dir):
                                        for wallet_file in os.listdir(wallet_dir):
                                            if wallet_file.endswith('.json'):
                                                try:
                                                    wallet_path = os.path.join(wallet_dir, wallet_file)
                                                    temp_wallet = SignWallet(wallet_path)
                                                    if temp_wallet.get_address() == miner_wallet:
                                                        # Update balance to match blockchain
                                                        temp_wallet.wallet_data['balance'] = blockchain_balance
                                                        temp_wallet._save_wallet()
                                                        # Count mining reward transactions in the block
                                                        reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                                                        if reward_txs:
                                                            reward_amount = reward_txs[0].get('amount', 0)
                                                            print_success(f"Mining reward: {reward_amount} tokens credited to {miner_wallet}")
                                                            print_success(f"Updated wallet balance: {blockchain_balance:.2f} tokens")
                                                        break
                                                except:
                                                    continue
                                except Exception as e:
                                    print_warning(f"Could not update wallet balance: {e}")
                            except Exception as e:
                                print_warning(f"Could not sync wallet balance: {e}")

                    # Check stop flag before status reporting
                    if mining_stopped:
                        break

                    # Queue status report for background sending (non-blocking)
                    if status_reporter:
                        current_time = time.time()

                        # Check for bootstrap server discovery periodically
                        if current_time - last_discovery_check >= discovery_interval:
                            try:
                                discovered = bootstrap_registry.discover_bootstrap_servers()
                                if discovered > 0:
                                    print_info(f"Discovered {discovered} new bootstrap server(s)")
                            except Exception as e:
                                print_warning(f"Bootstrap discovery failed: {e}")
                            last_discovery_check = current_time

                        # Queue comprehensive status report for intelligence processing
                        status_data = {
                            # Required fields for bootstrap server
                            'mining_active': True,
                            'blocks_mined': blocks_mined_session,
                            'hashrate': 0.5,  # Estimated hashrate (H/s)
                            'session_start_time': session_start_time,
                            'wallet_address': miner_wallet,
                            'hardware_model': 'pi5' if safe_mode else 'pi4',
                            'location': 'us-east',

                            # Intelligence fields for enhanced processing
                            'peers_connected': 3,  # TODO: Get actual P2P peer count
                            'syndicate_membership': None,  # TODO: Get syndicate name if applicable
                        }

                        # Add system monitoring data for intelligence
                        if safe_mode and system_monitor:
                            system_status = system_monitor.check_system_resources()
                            if system_status.get('resources'):
                                resources = system_status['resources']
                                status_data.update({
                                    'temperature': resources.temperature,
                                    'memory_usage': resources.memory_percent,
                                    'system_health': {
                                        'cpu_usage': resources.cpu_percent,
                                        'load_average': list(resources.load_average)
                                    }
                                })

                        # Queue the comprehensive status report
                        status_reporter.queue_status_report(status_data)

                    # Check stop flag before sleeping
                    if mining_stopped:
                        break

                    # Dynamic delay based on system status
                    delay = 2.0  # Default delay
                    if safe_mode and throttle_status:
                        delay = throttle_status['recommended_delay']
                        if delay > 2.0:
                            print_info(f"Throttling active - waiting {delay:.1f}s")

                    # Use shorter sleep intervals to allow signal processing
                    time.sleep(min(delay, 1.0))  # Max 1 second sleep for responsiveness

                    # Check stop flag after sleep
                    if mining_stopped:
                        break

                    # No transactions to mine, wait a bit
                    if not block:
                        print_info("No pending transactions, waiting...")
                        time.sleep(min(5.0, 1.0))  # Shorter sleep for responsiveness

            except KeyboardInterrupt:
                print_output("\nMining stopped by user")
            finally:
                # Cleanup system monitor
                if system_monitor:
                    system_monitor.stop_monitoring()
        else:
            print_success("Starting background mining...")
            if miner_wallet:
                print_output(f"Rewards will go to: {miner_wallet}")

            # For background mining, mine one block at a time (quietly)
            block = blockchain.mine_pending_transactions(miner_wallet, verbose=False)
            if block:
                print_success(f"Background mining completed - Block #{block.index} mined")
                if miner_wallet:
                    try:
                        # Sync wallet balance with blockchain
                        blockchain_balance = blockchain.get_wallet_balance(miner_wallet)
                        # Update local wallet balance
                        try:
                            from .core.wallet import SignWallet
                            wallet = SignWallet()
                            # Find wallet file for this address
                            wallet_dir = "/var/lib/pisecure/wallets"
                            if os.path.exists(wallet_dir):
                                for wallet_file in os.listdir(wallet_dir):
                                    if wallet_file.endswith('.json'):
                                        try:
                                            wallet_path = os.path.join(wallet_dir, wallet_file)
                                            temp_wallet = SignWallet(wallet_path)
                                            if temp_wallet.get_address() == miner_wallet:
                                                # Update balance to match blockchain
                                                temp_wallet.wallet_data['balance'] = blockchain_balance
                                                temp_wallet._save_wallet()
                                                # Count mining reward transactions in the block
                                                reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                                                if reward_txs:
                                                    reward_amount = reward_txs[0].get('amount', 0)
                                                    print_success(f"Mining reward: {reward_amount} tokens credited to {miner_wallet}")
                                                    print_success(f"Updated wallet balance: {blockchain_balance:.2f} tokens")
                                                break
                                        except:
                                            continue
                        except Exception as e:
                            print_warning(f"Could not update wallet balance: {e}")
                    except Exception as e:
                        print_warning(f"Could not sync wallet balance: {e}")
            else:
                print_warning("No transactions to mine")

    except KeyboardInterrupt:
        print_output("\nMining stopped by user")
    except Exception as e:
        print_error(f"Mining error: {e}")


@cli.command()
def verify_hardware():
    """Verify Raspberry Pi hardware for mining eligibility"""
    try:
        verifier = HardwareVerifier()

        console.print("[blue]🔍 Running hardware verification...[/blue]\n")

        result = verifier.verify_mining_eligibility()

        if result['eligible']:
            console.print("[green]✅ Hardware verification PASSED![/green]")
            console.print(f"📱 Device: {result['hardware_model']}")
            console.print(f"🎯 Confidence: {result['confidence_score']:.1%}")
            console.print(f"🔒 Anti-spoofing: {'✅' if result['anti_spoofing_passed'] else '❌'}")
            console.print("\n[green]🚀 This device can mine PiSecure tokens![/green]")
        else:
            console.print("[red]❌ Hardware verification FAILED[/red]")
            console.print(f"🎯 Confidence: {result['confidence_score']:.1%}")
            console.print("\n[yellow]⚠️ This device cannot mine PiSecure tokens[/yellow]")
            console.print("[dim]Only verified Raspberry Pi hardware is eligible[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Hardware verification error: {e}[/red]")


@cli.command()
@click.option('--wallet', help='Wallet name or address to monitor (or earn validation rewards)')
@click.option('--validate-rewards', is_flag=True, help='Earn validation rewards for blocks validated')
@click.option('--refresh', default=1, show_default=True, help='Refresh interval in seconds')
@click.option('--peer', help='Peer address to sync from (e.g., 192.168.1.100 or pi.local)')
def monitor(wallet, validate_rewards, refresh, peer):
    """Live blockchain/network monitor (non-mining)"""
    try:
        # Force read-only validation to avoid PiHash requirement during load
        os.environ['PISECURE_VALIDATE_ONLY'] = '1'
        # Set validation wallet if rewards enabled
        if wallet and validate_rewards:
            os.environ['PISECURE_VALIDATION_WALLET'] = wallet
        
        testnet = os.environ.get('PISECURE_TESTNET') == '1'
        
        # Initialize blockchain
        blockchain = SignChain(use_hybrid_storage=USE_HYBRID_STORAGE)
        
        # Sync with network to get latest blocks before monitoring
        print_output("🔄 Syncing with network for latest blocks...")
        try:
            peer_discovery = PeerDiscovery()
            
            # If peer address specified, add it to known peers
            if peer:
                print_output(f"   Adding peer: {peer}")
                peer_discovery.add_peer(f"manual_{peer}", peer, 3142)
            
            p2p_sync = P2PSyncManager(blockchain, peer_discovery)
            
            initial_height = len(blockchain.chain)
            p2p_sync._perform_sync_cycle()
            final_height = len(blockchain.chain)
            blocks_synced = final_height - initial_height
            
            if blocks_synced > 0:
                print_output(f"✅ Synced {blocks_synced} blocks from network (height: {initial_height} → {final_height})")
            else:
                print_output(f"✅ Already up-to-date with network ({final_height} blocks)")
        except Exception as e:
            print_output(f"⚠️  Network sync had issues: {e}")
            print_output("   Continuing with local blockchain...")
        
        # Resolve wallet name to address if needed
        wallet_address = None
        if wallet:
            try:
                from .core.wallet import SignWallet
                # Try treat as name by loading wallet
                sw = SignWallet()
                data = sw.load_wallet(wallet)
                if isinstance(data, dict) and data.get('address'):
                    wallet_address = data['address']
                else:
                    # Fallback to assuming provided is an address
                    wallet_address = wallet
            except Exception:
                wallet_address = wallet
        
        # Use MiningDashboard for rich UI monitoring
        from .monitor import MiningDashboard
        
        mode = 'validation' if validate_rewards else 'monitor'
        dashboard = MiningDashboard(
            blockchain=blockchain,
            mode=mode,
            refresh_rate=float(refresh),
            testnet=testnet,
            wallet_address=wallet_address if validate_rewards else None
        )
        
        dashboard.run()
        
    except KeyboardInterrupt:
        print_output("\nMonitor stopped")
    except Exception as e:
        print_error(f"Monitor error: {e}")

@cli.command()
def identity():
    """Show device identity and fingerprint"""
    try:
        verifier = HardwareVerifier()

        console.print("[blue]🔐 Device Identity Information[/blue]\n")

        # Hardware verification
        hw_result = verifier.verify_mining_eligibility()

        # Device role
        role = verifier.get_device_role()

        # Hardware fingerprint
        fingerprint = verifier.get_hardware_fingerprint()

        table = Table(title="🆔 Device Identity")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Hardware Model", hw_result['hardware_model'])
        table.add_row("Serial Number", hw_result['serial_number'])
        table.add_row("Device Role", role['role'].replace('_', ' ').title())
        table.add_row("Verification Score", f"{role['verification_confidence']:.1%}")
        table.add_row("Hardware Fingerprint", fingerprint[:32] + "...")

        capabilities = ", ".join(role['capabilities'])
        table.add_row("Capabilities", capabilities)

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error getting identity: {e}[/red]")


@cli.command()
@click.argument('wallet_name', required=False)
@click.option('--testnet', is_flag=True, help='Use testnet network')
def wallet(wallet_name, testnet):
    """Show wallet information and balance"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        # Adjust wallet directory for testnet
        import os
        if testnet or os.environ.get('PISECURE_TESTNET') == '1':
            wallet_dir = "/var/lib/pisecure-testnet/wallets"
        else:
            wallet_dir = "/var/lib/pisecure/wallets"

        if wallet_name:
            # Show specific wallet
            wallet = SignWallet()
            wallet_data = wallet.load_wallet(wallet_name)

            if 'error' in wallet_data:
                console.print(f"[red]❌ Wallet not found: {wallet_name}[/red]")
                return

            table = Table(title=f"🏦 Wallet: {wallet_name}")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")

            table.add_row("Wallet ID", wallet_data.get('wallet_id', 'unknown'))
            table.add_row("Name", wallet_data.get('name', 'unnamed'))
            table.add_row("Address", wallet_data.get('address', 'unknown'))
            table.add_row("Balance", f"{wallet_data.get('balance', 0):.2f}")
            table.add_row("Created", time.ctime(wallet_data.get('created_at', 0)))

            console.print(table)
        else:
            # List all wallets
            wallet = SignWallet()
            wallets = wallet.list_wallets()

            if not wallets:
                console.print("[yellow]📭 No wallets found[/yellow]")
                console.print("[dim]Wallets are automatically created when you mine or receive tokens[/dim]")
                return

            table = Table(title="🏦 Available Wallets")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Address", style="magenta", no_wrap=True)
            table.add_column("Balance", style="yellow", justify="right")
            table.add_column("Created", style="blue")

            for w in wallets:
                created_time = time.ctime(w.get('created', 0))
                table.add_row(
                    w.get('id', 'unknown'),
                    w.get('name', 'unnamed'),
                    w.get('address', 'unknown'),
                    f"{w.get('balance', 0):.2f}",
                    created_time
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Wallet error: {e}[/red]")


@cli.command()
@click.argument('package_path', type=click.Path(exists=True))
def verify_update(package_path):
    """Verify update package signature and integrity"""
    try:
        try:
            # Try relative import first
            from .updates import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates import OTAUpdater

        updater = OTAUpdater()

        console.print(f"[blue]🔍 Verifying update package: {package_path}[/blue]\n")

        # Verify package
        result = updater.verify_update(package_path, {})

        if result['verified']:
            manifest = result['manifest']
            console.print("[green]✅ Package verification successful![/green]")
            console.print(f"📦 Version: {manifest.get('version', 'unknown')}")
            console.print(f"👤 Publisher: {manifest.get('publisher', 'unknown')}")
            console.print(f"🎯 Target HW: {', '.join(manifest.get('target_hardware', ['any']))}")
            console.print(f"📝 Description: {manifest.get('description', 'No description')}")
        else:
            console.print("[red]❌ Package verification failed[/red]")
            console.print(f"Error: {result.get('error', 'Unknown error')}")
            console.print(f"Stage: {result.get('stage', 'unknown')}")

    except Exception as e:
        console.print(f"[red]❌ Verification error: {e}[/red]")


@click.group()
def update():
    """Update system management commands"""
    pass

@update.command()
@click.option('--type', 'update_type', help='Filter by update type (critical, safe, compatible, breaking)')
@click.option('--git', is_flag=True, help='Use direct GitHub updates instead of blockchain-based')
def check(update_type, git):
    """Check for available software updates"""
    try:
        if git:
            # Git-based updates
            try:
                from .updates.git_updater import git_updater
            except ImportError:
                from updates.git_updater import git_updater

            console.print("[blue]🔍 Checking for GitHub updates...[/blue]")

            # Check Git status first
            git_status = git_updater.get_git_status()
            if git_status.get('error'):
                console.print(f"[red]❌ Git status error: {git_status['error']}[/red]")
                return

            console.print(f"   Current commit: {git_status['current_commit'][:8] if git_status['current_commit'] else 'unknown'}")
            console.print(f"   Branch: {git_status['branch']}")
            console.print(f"   Working directory: {'clean' if git_status['is_clean'] else 'modified'}")

            if not git_status['github_accessible']:
                console.print("[yellow]⚠️  Cannot access GitHub API[/yellow]")
                return

            # Check for updates
            available_updates = git_updater.check_git_updates()

            if not available_updates:
                console.print("[green]✅ Your PiSecure installation is up to date with GitHub![/green]")
                return

            console.print(f"\n[yellow]📦 Found {len(available_updates)} available Git update(s):[/yellow]\n")

            # Display updates
            for update in available_updates[-5:]:  # Show latest 5
                update_type_display = update.get('type', 'unknown').upper()
                version = update.get('version', 'unknown')
                description = update.get('description', 'No description')[:50]
                commit_short = update.get('commit', '')[:8]

                # Color code by type
                if update_type_display == 'CRITICAL':
                    type_color = "[red]"
                elif update_type_display == 'SAFE':
                    type_color = "[green]"
                elif update_type_display == 'COMPATIBLE':
                    type_color = "[yellow]"
                else:
                    type_color = "[red]"

                console.print(f"{type_color}• {version} ({commit_short}) - {description}[/{type_color.replace('[', '').replace(']', '')}]")

            if len(available_updates) > 5:
                console.print(f"[dim]... and {len(available_updates) - 5} more older commits[/dim]")

            # Recommendations
            safe_updates = [u for u in available_updates if u.get('type') in ['critical', 'safe']]
            if safe_updates:
                console.print(f"\n[green]✨ {len(safe_updates)} safe update(s) available[/green]")
                console.print("[dim]Run 'pisecure update apply --git' to update to latest[/dim]")

            breaking_updates = [u for u in available_updates if u.get('type') == 'breaking']
            if breaking_updates:
                console.print(f"\n[red]⚠️  {len(breaking_updates)} breaking update(s) detected[/red]")
                console.print("[dim]Use --force with apply command if needed[/dim]")

        else:
            # Blockchain-based updates (original system)
            try:
                from .updates.updater import OTAUpdater
                from .updates.update_classifier import UpdateType
            except ImportError:
                from updates.updater import OTAUpdater
                from updates.update_classifier import UpdateType

            updater = OTAUpdater()

            console.print("[blue]🔍 Checking for PiSecure blockchain updates...[/blue]")

            # Get current version
            current_version = updater._get_current_version()
            console.print(f"   Current version: {current_version}")

            # Check for updates
            available_updates = updater.check_for_updates(current_version)

            if not available_updates:
                console.print("[green]✅ Your PiSecure installation is up to date![/green]")
                return

            # Filter by type if requested
            if update_type:
                try:
                    type_filter = UpdateType(update_type.lower())
                    available_updates = [u for u in available_updates if u.get('type') == type_filter.value]
                except ValueError:
                    console.print(f"[red]❌ Invalid update type: {update_type}[/red]")
                    console.print("[dim]Valid types: critical, safe, compatible, breaking[/dim]")
                    return

            console.print(f"\n[yellow]📦 Found {len(available_updates)} available update(s):[/yellow]\n")

            # Display updates
            for update in available_updates[:5]:  # Show latest 5
                update_type_display = update.get('type', 'unknown').upper()
                version = update.get('version', 'unknown')
                description = update.get('description', 'No description')[:60]

                # Color code by type
                if update_type_display == 'CRITICAL':
                    type_color = "[red]"
                elif update_type_display == 'SAFE':
                    type_color = "[green]"
                elif update_type_display == 'COMPATIBLE':
                    type_color = "[yellow]"
                else:
                    type_color = "[red]"

                console.print(f"{type_color}• {version} - {description}[/{type_color.replace('[', '').replace(']', '')}]")

            if len(available_updates) > 5:
                console.print(f"[dim]... and {len(available_updates) - 5} more[/dim]")

            # Recommendations
            critical_updates = [u for u in available_updates if u.get('type') == 'critical']
            if critical_updates:
                console.print(f"\n[red]🚨 {len(critical_updates)} critical update(s) available![/red]")
                console.print("[dim]Run 'pisecure update apply' to install immediately[/dim]")

            safe_updates = [u for u in available_updates if u.get('type') == 'safe']
            if safe_updates and not critical_updates:
                console.print(f"\n[green]✨ {len(safe_updates)} safe update(s) available[/green]")
                console.print("[dim]Run 'pisecure update apply' to install[/dim]")

            breaking_updates = [u for u in available_updates if u.get('type') == 'breaking']
            if breaking_updates:
                console.print(f"\n[red]⚠️  {len(breaking_updates)} breaking update(s) require network coordination[/red]")
                console.print("[dim]These may change consensus rules and need community approval[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Update check failed: {e}[/red]")

@update.command()
@click.argument('version', required=False)
@click.option('--force', is_flag=True, help='Force application (skip safety checks)')
@click.option('--skip-backup', is_flag=True, help='Skip backup creation (not recommended)')
@click.option('--git', is_flag=True, help='Apply Git-based update to specific commit')
def apply(version, force, skip_backup, git):
    """Apply available software updates"""
    try:
        if git:
            # Git-based updates
            try:
                from .updates.git_updater import git_updater
            except ImportError:
                from updates.git_updater import git_updater

            console.print("[blue]🔄 Applying Git-based PiSecure updates...[/blue]")

            # Check Git status first
            git_status = git_updater.get_git_status()
            if git_status.get('error'):
                console.print(f"[red]❌ Git status error: {git_status['error']}[/red]")
                return

            console.print(f"   Current commit: {git_status['current_commit'][:8] if git_status['current_commit'] else 'unknown'}")

            if not git_status['github_accessible']:
                console.print("[yellow]⚠️  Cannot access GitHub API[/yellow]")
                return

            # Get available updates
            available_updates = git_updater.check_git_updates()

            if not available_updates:
                console.print("[green]✅ Already up to date with GitHub![/green]")
                return

            # Select commit to apply
            target_commit = None
            if version:
                # Find specific commit
                for update in available_updates:
                    if update.get('commit', '').startswith(version) or update.get('version', '').endswith(version):
                        target_commit = update.get('commit')
                        break
                if not target_commit:
                    console.print(f"[red]❌ Commit {version} not found in available updates[/red]")
                    return
            else:
                # Apply latest safe update
                safe_updates = [u for u in available_updates if u.get('type') in ['critical', 'safe']]
                if safe_updates:
                    target_commit = safe_updates[0].get('commit')
                else:
                    console.print("[yellow]⚠️  No safe Git updates available[/yellow]")
                    console.print("[dim]Use --force to apply latest anyway[/dim]")
                    if not force:
                        return
                    target_commit = available_updates[0].get('commit')

            console.print(f"   Target commit: {target_commit[:8]}")

            # Safety check for breaking changes
            update_info = next((u for u in available_updates if u.get('commit') == target_commit), {})
            if update_info.get('type') == 'breaking' and not force:
                console.print("[red]⚠️  This commit contains breaking changes[/red]")
                console.print("[dim]Use --force to apply anyway[/dim]")
                return

            # Apply Git update
            apply_result = git_updater.apply_git_update(target_commit, force=force)

            if apply_result['success']:
                console.print("[green]✅ Git update applied successfully![/green]")
                console.print(f"   New commit: {apply_result['commit'][:8]}")
                console.print(f"   Version: {apply_result['version']}")

                if apply_result.get('services_restarted'):
                    console.print("[green]✅ Services restarted[/green]")
                else:
                    console.print("[yellow]🔄 Service restart recommended[/yellow]")
            else:
                console.print(f"[red]❌ Git update failed: {apply_result.get('error', 'Unknown error')}[/red]")

        else:
            # Blockchain-based updates (original system)
            try:
                from .updates.updater import OTAUpdater
                from .updates.update_classifier import UpdateClassifier, UpdateType
            except ImportError:
                from updates.updater import OTAUpdater
                from updates.update_classifier import UpdateClassifier, UpdateType

            updater = OTAUpdater()
            classifier = UpdateClassifier()

            console.print("[blue]🔄 Applying PiSecure blockchain updates...[/blue]")

            # Get current version
            current_version = updater._get_current_version()
            console.print(f"   Current version: {current_version}")

            # Get available updates
            available_updates = updater.check_for_updates(current_version)

            if not available_updates:
                console.print("[green]✅ No updates available - already up to date![/green]")
                return

            # Select update to apply
            target_update = None
            if version:
                # Find specific version
                for update in available_updates:
                    if update.get('version') == version:
                        target_update = update
                        break
                if not target_update:
                    console.print(f"[red]❌ Version {version} not found in available updates[/red]")
                    return
            else:
                # Apply latest safe update
                safe_updates = [u for u in available_updates if u.get('type') in ['critical', 'safe']]
                if safe_updates:
                    target_update = safe_updates[0]  # Latest safe update
                else:
                    console.print("[yellow]⚠️  No safe updates available[/yellow]")
                    console.print("[dim]Use --version to specify a specific update[/dim]")
                    return

            update_version = target_update.get('version')
            update_type = target_update.get('type', 'unknown')

            console.print(f"   Target update: {update_version}")
            console.print(f"   Update type: {update_type.upper()}")

            # Safety check for non-critical updates
            if not force and update_type not in ['critical']:
                console.print(f"\n[yellow]⚠️  This is a {update_type.upper()} update[/yellow]")

                if update_type == 'breaking':
                    console.print("[red]Breaking updates may change consensus rules[/red]")
                    console.print("[red]Network coordination required - do not apply without community approval[/red]")
                    return
                elif update_type == 'compatible':
                    console.print("[yellow]Compatible updates may require testing[/yellow]")
                    if not click.confirm("Continue with update?", default=False):
                        console.print("[dim]Update cancelled[/dim]")
                        return

            # Download update
            console.print("[dim]Downloading update...[/dim]")
            download_result = updater.download_update(target_update)

            if not download_result['success']:
                console.print(f"[red]❌ Download failed: {download_result['error']}[/red]")
                return

            package_path = download_result['local_path']

            # Verify update
            console.print("[dim]Verifying update...[/dim]")
            verify_result = updater.verify_update(package_path, target_update)

            if not verify_result['verified']:
                console.print(f"[red]❌ Verification failed: {verify_result.get('error')}[/red]")
                return

            manifest = verify_result['manifest']

            # Additional safety check using classifier
            changed_files = manifest.get('changed_files', [])
            is_safe, safety_reason = classifier.verify_update_safety(manifest, changed_files)

            if not is_safe and not force:
                console.print(f"[red]❌ Safety check failed: {safety_reason}[/red]")
                console.print("[dim]Use --force to override (not recommended)[/dim]")
                return

            # Apply update
            console.print("[dim]Applying update...[/dim]")

            apply_result = updater.apply_update(
                package_path,
                manifest,
                progress_callback=lambda current, total: console.print(f"[dim]Installing... {current}/{total} files[/dim]")
            )

            if apply_result['success']:
                console.print("[green]✅ Update applied successfully![/green]")
                console.print(f"   New version: {apply_result['version']}")
                console.print(f"   Backup ID: {apply_result['backup_id']}")

                # Check if restart needed
                if manifest.get('restart_required', True):
                    console.print("[yellow]🔄 System restart recommended[/yellow]")
                    if click.confirm("Restart services now?", default=False):
                        # Restart services
                        import subprocess
                        try:
                            subprocess.run(['sudo', 'systemctl', 'restart', 'pisecure*'], shell=True, check=True)
                            console.print("[green]✅ Services restarted[/green]")
                        except Exception as e:
                            console.print(f"[red]❌ Service restart failed: {e}[/red]")
                            console.print("[dim]Manual restart may be required[/dim]")
            else:
                console.print(f"[red]❌ Update failed: {apply_result.get('error', 'Unknown error')}[/red]")

                # Check if rollback was attempted
                if apply_result.get('rollback_attempted'):
                    console.print("[yellow]⚠️  Automatic rollback was attempted[/yellow]")
                    if not apply_result.get('rollback_attempted'):
                        console.print("[red]Manual intervention may be required[/red]")

    except Exception as e:
        console.print(f"[red]❌ Update application failed: {e}[/red]")


@cli.command()
def update_status():
    """Show current update system status"""
    try:
        try:
            # Try relative import first
            from .updates.updater import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates.updater import OTAUpdater

        updater = OTAUpdater()

        console.print("[blue]📊 PiSecure Update System Status[/blue]")
        console.print("=" * 40)

        # Get system status
        status = updater.get_system_status()

        console.print(f"[cyan]Current Version:[/cyan] {status['current_version']}")
        console.print(f"[cyan]Available Updates:[/cyan] {status['available_updates']}")
        console.print(f"[cyan]Backups Available:[/cyan] {status['backups_count']}")
        console.print(f"[cyan]Cached Updates:[/cyan] {status['cached_updates']}")
        console.print(f"[cyan]Update History:[/cyan] {status['update_history']}")

        # Last update check
        import time
        last_check = time.ctime(status.get('last_update_check', 0))
        console.print(f"[cyan]Last Update Check:[/cyan] {last_check}")

        # Recent update history
        history = updater.get_update_history()
        if history:
            console.print(f"\n[cyan]Recent Updates:[/cyan]")
            for entry in history[-3:]:  # Last 3 updates
                event_type = entry.get('event_type', 'unknown')
                version = entry.get('version', 'unknown')
                timestamp = time.ctime(entry.get('timestamp', 0))

                if event_type == 'applied':
                    console.print(f"   ✅ {version} - Applied on {timestamp}")
                elif event_type == 'rolled_back':
                    console.print(f"   🔄 {version} - Rolled back on {timestamp}")
                else:
                    console.print(f"   • {version} - {event_type.title()} on {timestamp}")

        # Update recommendations
        if status['available_updates'] > 0:
            console.print(f"\n[yellow]💡 {status['available_updates']} update(s) available[/yellow]")
            console.print("[dim]Run 'pisecure update check' for details[/dim]")
            console.print("[dim]Run 'pisecure update apply' to install safe updates[/dim]")

        if status['backups_count'] == 0:
            console.print(f"\n[yellow]⚠️  No update backups available[/yellow]")
            console.print("[dim]Consider creating a manual backup before major updates[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Update status check failed: {e}[/red]")


@cli.command()
@click.argument('version', required=False)
def update_rollback(version):
    """Rollback to previous version"""
    try:
        try:
            # Try relative import first
            from .updates.updater import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates.updater import OTAUpdater

        updater = OTAUpdater()

        if version:
            console.print(f"[blue]🔄 Rolling back to version: {version}[/blue]")
        else:
            console.print("[blue]🔄 Rolling back to latest backup[/blue]")

        if not click.confirm("This will revert system changes. Continue?", default=False):
            console.print("[dim]Rollback cancelled[/dim]")
            return

        result = updater.rollback_update(version)

        if result['success']:
            console.print("[green]✅ Rollback completed successfully![/green]")
            console.print("[yellow]🔄 System restart recommended[/yellow]")

            if click.confirm("Restart services now?", default=False):
                import subprocess
                try:
                    subprocess.run(['sudo', 'systemctl', 'restart', 'pisecure*'], shell=True, check=True)
                    console.print("[green]✅ Services restarted[/green]")
                except Exception as e:
                    console.print(f"[red]❌ Service restart failed: {e}[/red]")
        else:
            console.print(f"[red]❌ Rollback failed: {result.get('error', 'Unknown error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Rollback failed: {e}[/red]")


@cli.command()
def update_history():
    """Show update history and changelog"""
    try:
        try:
            # Try relative import first
            from .updates.updater import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates.updater import OTAUpdater

        updater = OTAUpdater()

        console.print("[blue]📚 PiSecure Update History[/blue]")
        console.print("=" * 35)

        history = updater.get_update_history()

        if not history:
            console.print("[yellow]📭 No update history available[/yellow]")
            return

        for entry in reversed(history[-10:]):  # Show last 10 entries
            import time
            timestamp = time.ctime(entry.get('timestamp', 0))
            event_type = entry.get('event_type', 'unknown')
            version = entry.get('version', 'unknown')

            if event_type == 'applied':
                console.print(f"✅ {timestamp} - Applied {version}")
            elif event_type == 'rolled_back':
                error = entry.get('error', 'Unknown reason')
                console.print(f"🔄 {timestamp} - Rolled back {version} ({error})")
            elif event_type == 'manual_rollback':
                console.print(f"🔄 {timestamp} - Manual rollback to {version}")
            else:
                console.print(f"• {timestamp} - {event_type.title()} {version}")

    except Exception as e:
        console.print(f"[red]❌ Update history retrieval failed: {e}[/red]")


@cli.command()
def update_emergency_rollback():
    """Perform emergency rollback to last known good state"""
    try:
        console.print("[red]🚨 EMERGENCY ROLLBACK[/red]")
        console.print("[red]This will revert to the last known good system state[/red]")
        console.print("[red]Only use in case of critical system failure[/red]")
        console.print()

        if not click.confirm("Are you sure you want to perform emergency rollback?", default=False):
            console.print("[dim]Emergency rollback cancelled[/dim]")
            return

        try:
            # Try relative import first
            from .updates.updater import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates.updater import OTAUpdater

        updater = OTAUpdater()

        console.print("[yellow]Initiating emergency rollback...[/yellow]")

        result = updater.emergency_rollback()

        if result['success']:
            console.print("[green]✅ Emergency rollback completed[/green]")
            console.print("[yellow]🔄 System restart required[/yellow]")
        else:
            console.print(f"[red]❌ Emergency rollback failed: {result.get('error', 'Unknown error')}[/red]")
            console.print("[red]Manual system recovery may be required[/red]")

    except Exception as e:
        console.print(f"[red]❌ Emergency rollback failed: {e}[/red]")


# Alias for backward compatibility
@cli.command()
def update():
    """Check for and apply updates (alias for update apply)"""
    console.print("[blue]🔄 Running 'pisecure update apply'[/blue]")
    console.print()

    # Call the apply command
    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(update_apply, [])

    if result.exit_code != 0:
        console.print(f"[red]❌ Update failed: {result.output}[/red]")
    else:
        console.print(result.output)


@cli.command()
@click.argument('backup_path', type=click.Path())
@click.option('--wallet', help='Wallet ID to backup (default: current wallet)')
@click.option('--include-private-key', is_flag=True, help='Include encrypted private key in backup')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password for private key encryption')
def backup_wallet(backup_path, wallet, include_private_key, password):
    """Create encrypted wallet backup with private key"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        if wallet:
            # Backup specific wallet
            wallet_instance = SignWallet()
            wallet_data = wallet_instance.load_wallet(wallet)
            if 'error' in wallet_data:
                console.print(f"[red]❌ Wallet not found: {wallet}[/red]")
                return

            # Create wallet instance for the specific wallet
            wallet_file = f"/var/lib/pisecure/wallets/{wallet}.json"
            wallet_instance = SignWallet(wallet_file)

        else:
            # Backup current/default wallet
            wallet_instance = SignWallet()
            wallet = wallet_instance.get_wallet_id()
            if not wallet:
                console.print("[red]❌ No wallet loaded[/red]")
                return

        console.print(f"[blue]🔐 Creating wallet backup for: {wallet}[/blue]")

        if include_private_key and not password:
            console.print("[red]❌ Password required for private key backup[/red]")
            return

        # Create backup
        result = wallet_instance.create_wallet_backup(backup_path, password if include_private_key else None)

        if result['success']:
            console.print("[green]✅ Wallet backup created successfully![/green]")
            console.print(f"   📁 Backup file: {result['export_path']}")
            console.print(f"   📊 File size: {result['file_size']} bytes")
            console.print(f"   🔑 Private key included: {'✅ Yes (encrypted)' if result.get('includes_private_key') else '❌ No'}")

            if include_private_key:
                console.print("[yellow]⚠️  Remember your password - it's required to restore the private key![/yellow]")
                console.print("[dim]Store this backup securely - it contains your wallet credentials[/dim]")
        else:
            console.print(f"[red]❌ Backup failed: {result['error']}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Backup error: {e}[/red]")


@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.option('--wallet-name', help='Name for restored wallet (optional)')
@click.option('--password', prompt=True, hide_input=True, help='Password for private key decryption')
def restore_wallet(backup_path, wallet_name, password):
    """Restore wallet from encrypted backup"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        console.print(f"[blue]📥 Restoring wallet from: {backup_path}[/blue]")

        # Check if backup contains private key
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)

            has_private_key = 'encrypted_private_key' in backup_data
            wallet_id = backup_data.get('wallet_id', 'unknown')

            console.print(f"   👛 Wallet ID: {wallet_id}")
            console.print(f"   🔑 Private key included: {'✅ Yes' if has_private_key else '❌ No'}")

            if has_private_key and not password:
                console.print("[red]❌ Password required to decrypt private key[/red]")
                return

        except Exception as e:
            console.print(f"[red]❌ Invalid backup file: {e}[/red]")
            return

        # Create wallet instance
        wallet_instance = SignWallet()

        # Restore from backup
        result = wallet_instance.restore_wallet_backup(backup_path, password if has_private_key else None)

        if result['success']:
            console.print("[green]✅ Wallet restored successfully![/green]")
            console.print(f"   👛 Wallet ID: {result['wallet_id']}")
            console.print(f"   🏦 Address: {result['address']}")
            console.print(f"   🔑 Private key restored: {'✅ Yes' if result.get('private_key_restored') else '❌ No'}")

            # Rename wallet if requested
            if wallet_name and wallet_name != result['wallet_id']:
                console.print(f"[blue]🔄 Renaming wallet to: {wallet_name}[/blue]")
                # Load the restored wallet and update name
                restored_wallet = SignWallet(f"/var/lib/pisecure/wallets/{result['wallet_id']}.json")
                restored_wallet.wallet_data['wallet_id'] = wallet_name
                restored_wallet.wallet_data['name'] = wallet_name
                restored_wallet._save_wallet()

                # Rename files
                import shutil
                old_json = f"/var/lib/pisecure/wallets/{result['wallet_id']}.json"
                new_json = f"/var/lib/pisecure/wallets/{wallet_name}.json"
                old_pem = f"/var/lib/pisecure/wallets/keys/{result['wallet_id']}.pem"
                new_pem = f"/var/lib/pisecure/wallets/keys/{wallet_name}.pem"

                shutil.move(old_json, new_json)
                if os.path.exists(old_pem):
                    shutil.move(old_pem, new_pem)

                console.print(f"[green]✅ Wallet renamed to: {wallet_name}[/green]")

        else:
            console.print(f"[red]❌ Restore failed: {result['error']}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Restore error: {e}[/red]")


@cli.command()
@click.argument('backup_path', type=click.Path())
@click.option('--wallet', help='Wallet ID to export (default: current wallet)')
def export_wallet(backup_path, wallet):
    """Export wallet metadata (without private key)"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        if wallet:
            wallet_file = f"/var/lib/pisecure/wallets/{wallet}.json"
            wallet_instance = SignWallet(wallet_file)
        else:
            wallet_instance = SignWallet()

        console.print(f"[blue]📤 Exporting wallet metadata...[/blue]")

        result = wallet_instance.export_wallet(backup_path, include_private_key=False)

        if result['success']:
            console.print("[green]✅ Wallet metadata exported successfully![/green]")
            console.print(f"   📁 Export file: {result['export_path']}")
            console.print(f"   📊 File size: {result['file_size']} bytes")
            console.print("[yellow]⚠️  Private key NOT included - use 'backup-wallet' for full backup[/yellow]")
        else:
            console.print(f"[red]❌ Export failed: {result['error']}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Export error: {e}[/red]")


@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.option('--wallet-name', help='Name for imported wallet (optional)')
def import_wallet(backup_path, wallet_name):
    """Import wallet metadata (without private key)"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        wallet_instance = SignWallet()
        result = wallet_instance.import_wallet(backup_path)

        if result['success']:
            console.print("[green]✅ Wallet metadata imported successfully![/green]")
            console.print(f"   👛 Wallet ID: {result['wallet_id']}")
            console.print(f"   🏦 Address: {result['address']}")
            console.print(f"   🔑 Private key restored: {'✅ Yes' if result.get('private_key_restored') else '❌ No'}")

            if wallet_name and wallet_name != result['wallet_id']:
                # Rename imported wallet
                wallet_instance.wallet_data['wallet_id'] = wallet_name
                wallet_instance.wallet_data['name'] = wallet_name
                wallet_instance._save_wallet()
                console.print(f"[green]✅ Wallet renamed to: {wallet_name}[/green]")

            console.print("[yellow]⚠️  If this backup included a private key, use 'restore-wallet' instead[/yellow]")
        else:
            console.print(f"[red]❌ Import failed: {result['error']}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Import error: {e}[/red]")


@cli.command()
@click.option('--wallet', help='Wallet ID to sync (default: all wallets)')
def sync_wallet(wallet):
    """Sync wallet balance with blockchain state"""
    try:
        from .core import SignChain

        blockchain = SignChain(use_hybrid_storage=USE_HYBRID_STORAGE)

        console.print("[blue]🔄 Syncing wallet balances with blockchain...[/blue]")

        if wallet:
            # Sync specific wallet
            try:
                from .core.wallet import SignWallet
                wallet_file = f"/var/lib/pisecure/wallets/{wallet}.json"
                wallet_instance = SignWallet(wallet_file)

                if 'error' in wallet_instance.wallet_data:
                    console.print(f"[red]❌ Wallet not found: {wallet}[/red]")
                    return

                address = wallet_instance.get_address()
                blockchain_balance = blockchain.get_wallet_balance(address)

                # Update wallet balance
                wallet_instance.wallet_data['balance'] = blockchain_balance
                wallet_instance._save_wallet()

                console.print(f"[green]✅ Synced wallet {wallet}[/green]")
                console.print(f"   🏦 Address: {address}")
                console.print(f"   💰 Balance: {blockchain_balance:.2f} tokens")

            except Exception as e:
                console.print(f"[red]❌ Failed to sync wallet {wallet}: {e}[/red]")
        else:
            # Sync all wallets
            try:
                from .core.wallet import SignWallet
                import os

                wallet_dir = "/var/lib/pisecure/wallets"
                if not os.path.exists(wallet_dir):
                    console.print("[yellow]⚠️ No wallet directory found[/yellow]")
                    return

                synced_count = 0
                total_balance = 0.0

                for wallet_file in os.listdir(wallet_dir):
                    if wallet_file.endswith('.json'):
                        try:
                            wallet_path = os.path.join(wallet_dir, wallet_file)
                            temp_wallet = SignWallet(wallet_path)

                            if 'error' not in temp_wallet.wallet_data:
                                address = temp_wallet.get_address()
                                blockchain_balance = blockchain.get_wallet_balance(address)

                                # Update balance
                                temp_wallet.wallet_data['balance'] = blockchain_balance
                                temp_wallet._save_wallet()

                                synced_count += 1
                                total_balance += blockchain_balance

                                console.print(f"   ✅ {temp_wallet.get_wallet_id()}: {blockchain_balance:.2f} tokens")

                        except Exception as e:
                            console.print(f"   ⚠️ Skipped {wallet_file}: {e}")

                console.print(f"\n[green]✅ Synced {synced_count} wallets[/green]")
                console.print(f"   💰 Total balance across all wallets: {total_balance:.2f} tokens")

            except Exception as e:
                console.print(f"[red]❌ Failed to sync wallets: {e}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Wallet sync error: {e}[/red]")


@cli.command()
@click.option('--wallet', help='Wallet ID to show (default: current wallet)')
def wallet_info(wallet):
    """Show detailed wallet information"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        if wallet:
            wallet_file = f"/var/lib/pisecure/wallets/{wallet}.json"
            wallet_instance = SignWallet(wallet_file)
        else:
            wallet_instance = SignWallet()

        wallet_id = wallet_instance.get_wallet_id()
        if not wallet_id:
            console.print("[red]❌ No wallet loaded[/red]")
            return

        console.print(f"[blue]👛 Wallet Information: {wallet_id}[/blue]")
        console.print("=" * 40)

        console.print(f"[cyan]Wallet ID:[/cyan] {wallet_id}")
        console.print(f"[cyan]Name:[/cyan] {wallet_instance.wallet_data.get('name', 'Unnamed')}")
        console.print(f"[cyan]Address:[/cyan] {wallet_instance.get_address()}")
        console.print(f"[cyan]Balance:[/cyan] {wallet_instance.get_balance():.2f} tokens")

        # Check if private key exists
        key_file = wallet_instance.keys_dir / f"{wallet_id}.pem"
        has_private_key = key_file.exists()
        console.print(f"[cyan]Private Key:[/cyan] {'✅ Available' if has_private_key else '❌ Not found'}")

        created_at = wallet_instance.wallet_data.get('created_at', 0)
        if created_at:
            import time
            console.print(f"[cyan]Created:[/cyan] {time.ctime(created_at)}")

        # Transaction count
        transactions = wallet_instance.get_transaction_history()
        console.print(f"[cyan]Transactions:[/cyan] {len(transactions)}")

        # File locations
        wallet_file = wallet_instance.wallet_file
        console.print(f"[cyan]Wallet File:[/cyan] {wallet_file}")
        console.print(f"[cyan]Key File:[/cyan] {key_file}")

        console.print()
        console.print("[green]💡 Wallet Commands:[/green]")
        console.print("  Backup (with private key): pisecure backup-wallet /path/to/backup.json --include-private-key")
        console.print("  Restore: pisecure restore-wallet /path/to/backup.json")
        console.print("  Export metadata only: pisecure export-wallet /path/to/export.json")

    except Exception as e:
        console.print(f"[red]❌ Wallet info error: {e}[/red]")


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
@click.option('--port', type=int, default=3142, help='Port to listen on (default: 3142)')
@click.option('--ssl-enabled', type=click.Choice(['auto', 'force', 'disable']), default='auto',
              help='SSL mode: auto (smart detection), force (require SSL), disable (HTTP only)')
@click.option('--ssl-cert', help='Path to SSL certificate file (.pem)')
@click.option('--ssl-key', help='Path to SSL private key file (.key)')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def server(host, port, ssl_enabled, ssl_cert, ssl_key, debug):
    """Start the PiSecure API server with automatic SSL detection"""
    try:
        # Import the API server
        try:
            # Try relative import first
            from .api.server import BlockchainAPI
        except ImportError:
            # Fall back to absolute import
            from api.server import BlockchainAPI

        console.print("[blue]🚀 Starting PiSecure API Server[/blue]")
        console.print(f"   Host: {host}")
        console.print(f"   Port: {port}")
        console.print(f"   SSL Mode: {ssl_enabled}")

        if ssl_enabled == 'auto':
            console.print("[dim]   SSL Detection: Automatic (recommended for most users)[/dim]")
            console.print("[dim]     - HTTP for local development (localhost/127.0.0.1)[/dim]")
            console.print("[dim]     - HTTPS for public access or when required[/dim]")
        elif ssl_enabled == 'force':
            console.print("[dim]   SSL Mode: Forced HTTPS[/dim]")
            console.print("[dim]     - Server will fail to start without SSL certificate[/dim]")
        elif ssl_enabled == 'disable':
            console.print("[dim]   SSL Mode: HTTP only[/dim]")
            console.print("[dim]     - No SSL/TLS encryption[/dim]")

        if ssl_cert and ssl_key:
            console.print(f"   SSL Certificate: {ssl_cert}")
            console.print(f"   SSL Key: {ssl_key}")
        elif ssl_enabled in ['auto', 'force']:
            console.print("[dim]   SSL Certificate: Auto-generated (self-signed for development)[/dim]")

        console.print()

        # Create and start the API server
        api = BlockchainAPI(host=host, port=port)
        api.run(debug=debug, ssl_enabled=ssl_enabled, ssl_cert=ssl_cert, ssl_key=ssl_key)

    except Exception as e:
        console.print(f"[red]❌ Failed to start API server: {e}[/red]")
        console.print()
        console.print("[yellow]💡 Troubleshooting:[/yellow]")
        console.print("  1. Check if port 3142 is available: lsof -i :3142")
        console.print("  2. For SSL issues, try --ssl-enabled=disable")
        console.print("  3. For public access, use --ssl-enabled=auto")
        console.print("  4. For custom SSL certs, provide --ssl-cert and --ssl-key")


# Register subcommand groups
cli.add_command(update)





def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()