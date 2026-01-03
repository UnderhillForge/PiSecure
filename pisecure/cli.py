#!/usr/bin/env python3
"""
PiSecure Command Line Interface
===============================

Main CLI entry point for PiSecure framework.
"""

import time
import click
from rich.console import Console
from rich.table import Table

try:
    # Try relative imports first (for package installation)
    from .core import SignChain, HardwareVerifier, SignTokenMiner
    from .updates import OTAUpdater
    from .identity import DeviceIdentity, DeviceAuthenticator
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from core import SignChain, HardwareVerifier, SignTokenMiner
    from updates import OTAUpdater
    from identity import DeviceIdentity, DeviceAuthenticator

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PiSecure - Decentralized Security Framework for Raspberry Pi"""
    pass


@cli.command()
def status():
    """Show blockchain and system status"""
    try:
        blockchain = SignChain()

        # Get blockchain info
        info = blockchain.get_chain_info()

        # Create status table
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

        # Network health
        health = chain_info['network_health']
        table.add_row("Participation", f"{health['participation']:.1%}")
        table.add_row("Avg Block Time", f"{health['avg_block_time']:.1f}s")
        table.add_row("Network Health", f"{health['health_score']:.1%}")

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error getting status: {e}[/red]")


@cli.command()
@click.option('--count', default=5, help='Number of test transactions to create')
def create_tx(count):
    """Create test transactions for mining"""
    try:
        import secrets

        blockchain = SignChain()

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
def mine(interactive, wallet):
    """Start blockchain mining"""
    try:
        blockchain = SignChain()

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

        if not miner_wallet:
            console.print("[yellow]⚠️ No miner wallet configured[/yellow]")
            console.print("[dim]Use --wallet to specify wallet address, or set mining.wallet_address in /etc/pisecure/config.json[/dim]")
            miner_wallet = None

        if interactive:
            console.print("[green]⛏️ Starting interactive mining...[/green]")
            if miner_wallet:
                console.print(f"[dim]Rewards will go to: {miner_wallet}[/dim]")
            console.print("[dim]Press Ctrl-C to stop[/dim]\n")

            try:
                while True:
                    # Mine a single block
                    block = blockchain.mine_pending_transactions(miner_wallet, verbose=True)
                    if block:
                        console.print(f"[green]✅ Block mined! #{block.index}[/green]")
                        # Brief pause before next mining attempt
                        time.sleep(2)
                    else:
                        # No transactions to mine, wait a bit
                        console.print("[dim]No pending transactions, waiting...[/dim]")
                        time.sleep(5)

            except KeyboardInterrupt:
                console.print("\n[yellow]⏹️ Mining stopped by user[/yellow]")
        else:
            console.print("[green]⛏️ Starting background mining...[/green]")
            if miner_wallet:
                console.print(f"[dim]Rewards will go to: {miner_wallet}[/dim]")

            # For background mining, mine one block at a time
            block = blockchain.mine_pending_transactions(miner_wallet, verbose=False)
            if block:
                console.print(f"[green]✅ Background mining completed - Block #{block.index} mined[/green]")
                if miner_wallet:
                    # Count mining reward transactions in the block
                    reward_txs = [tx for tx in block.transactions if tx.get('type') == 'mining_reward']
                    if reward_txs:
                        reward_amount = reward_txs[0].get('amount', 0)
                        console.print(f"[green]💰 Mining reward: {reward_amount} tokens credited to {miner_wallet}[/green]")
            else:
                console.print("[yellow]⚠️ No transactions to mine[/yellow]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Mining stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Mining error: {e}[/red]")


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
def wallet(wallet_name):
    """Show wallet information and balance"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

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
                console.print("[dim]Create your first wallet with: pisecure create-wallet <name>[/dim]")
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


# Register subcommand groups
cli.add_command(update)

def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()
            console.print()
            console.print("[yellow]⚠️  This node is not configured as a relay[/yellow]")
            console.print("[dim]Run 'pisecure become-relay-node' to become a relay[/dim]")

        # Show network relay statistics
        try:
            from .core.nat_traversal import CommunityRelayNetwork
            relay_network = CommunityRelayNetwork()
            relay_network.update_relay_list()

            console.print()
            console.print(f"[cyan]Network Relay Statistics:[/cyan]")
            console.print(f"   • Available Relays: {len(relay_network.relays)}")
            console.print(f"   • Last Updated: {time.ctime(relay_network.last_update) if relay_network.last_update else 'Never'}")

        except Exception as e:
            console.print(f"[yellow]⚠️  Could not load network relay stats: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Relay status error: {e}[/red]")


@cli.command()
@click.argument('wallet_name', required=False)
def show_wallet(wallet_name):
    """Show wallet information"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        wallet = SignWallet()

        if wallet_name:
            # Show specific wallet
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
            wallets = wallet.list_wallets()

            if not wallets:
                console.print("[yellow]📭 No wallets found[/yellow]")
                console.print("[dim]Create your first wallet with: pisecure create-wallet <name>[/dim]")
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
        console.print(f"[red]❌ Show wallet error: {e}[/red]")


@cli.command()
@click.argument('recipient_address')
@click.argument('amount', type=float)
@click.option('--from-wallet', help='Sender wallet ID')
@click.option('--memo', help='Transaction memo')
def transfer_tokens(recipient_address, amount, from_wallet, memo):
    """Transfer tokens to another wallet"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        if not from_wallet:
            console.print("[red]❌ Must specify sender wallet with --from-wallet[/red]")
            return

        wallet = SignWallet()
        wallet_data = wallet.load_wallet(from_wallet)

        if 'error' in wallet_data:
            console.print(f"[red]❌ Wallet not found: {from_wallet}[/red]")
            return

        # Load wallet with private key for signing
        wallet = SignWallet(f"/var/lib/pisecure/wallets/{from_wallet}.json")

        console.print(f"[blue]💸 Transferring {amount} tokens[/blue]")
        console.print(f"   From: {from_wallet}")
        console.print(f"   To: {recipient_address}")
        if memo:
            console.print(f"   Memo: {memo}")

        # Create transfer transaction
        transaction = wallet.create_transfer_transaction(recipient_address, amount, memo)

        if 'error' in transaction:
            console.print(f"[red]❌ Transaction creation failed: {transaction['error']}[/red]")
            return

        # Add to blockchain
        blockchain = SignChain()
        tx_hash = blockchain.add_transaction(transaction)

        console.print("[green]✅ Transaction submitted successfully![/green]")
        console.print(f"   Transaction Hash: {tx_hash}")
        console.print("[yellow]💡 Transaction will be mined in the next block[/yellow]")

        # Optionally mine immediately
        console.print("[dim]Mining transaction...[/dim]")
        mined_block = blockchain.mine_pending_transactions(verbose=True)
        if mined_block:
            console.print(f"[green]✅ Transaction mined in block #{mined_block.index}[/green]")

    except Exception as e:
        console.print(f"[red]❌ Transfer error: {e}[/red]")


@cli.command()
@click.argument('wallet_address')
def wallet_balance(wallet_address):
    """Check wallet balance"""
    try:
        blockchain = SignChain()

        balance = blockchain.get_wallet_balance(wallet_address)

        console.print(f"[green]💰 Wallet Balance[/green]")
        console.print(f"   Address: {wallet_address}")
        console.print(f"   Balance: {balance:.2f} tokens")

    except Exception as e:
        console.print(f"[red]❌ Balance check error: {e}[/red]")


@cli.command()
@click.argument('wallet_address')
def wallet_history(wallet_address):
    """Show wallet transaction history"""
    try:
        blockchain = SignChain()

        transactions = blockchain.get_wallet_transactions(wallet_address)

        if not transactions:
            console.print(f"[yellow]📭 No transactions found for wallet: {wallet_address}[/yellow]")
            return

        table = Table(title=f"📊 Transaction History: {wallet_address[:16]}...")
        table.add_column("TX Hash", style="cyan", no_wrap=True)
        table.add_column("Block", style="magenta", justify="right")
        table.add_column("Direction", style="green")
        table.add_column("Amount", style="yellow", justify="right")
        table.add_column("Time", style="blue")

        for tx in transactions[-20:]:  # Show last 20 transactions
            direction_icon = "⬅️" if tx['direction'] == 'incoming' else "➡️"
            tx_time = time.ctime(tx.get('timestamp', 0))
            table.add_row(
                tx['tx_hash'][:16] + "...",
                str(tx['block_index']),
                f"{direction_icon} {tx['direction']}",
                f"{tx['amount']:.2f}",
                tx_time
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ History error: {e}[/red]")


@cli.command()
@click.option('--name', help='Custom device name')
@click.option('--org', default='PiSecure Network', help='Organization name')
@click.option('--skip-cert', is_flag=True, help='Skip certificate generation')
def init_identity(name, org, skip_cert):
    """Initialize device identity"""
    try:
        identity = DeviceIdentity()

        console.print(f"[blue]🔐 Initializing device identity...[/blue]")
        console.print(f"   Name: {name or 'auto-generated'}")
        console.print(f"   Organization: {org}")

        result = identity.initialize_device(
            device_name=name,
            organization=org,
            auto_generate_cert=not skip_cert
        )

        if result['success']:
            console.print(f"[green]✅ Device identity initialized![/green]")
            console.print(f"   Device ID: {result['device_id']}")
            console.print(f"   Fingerprint: {result['fingerprint'][:32]}...")
            console.print(f"   Certificate: {'✅ Generated' if result.get('certificate_generated') else '❌ Skipped'}")
        else:
            console.print(f"[red]❌ Identity initialization failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Identity initialization error: {e}[/red]")


@cli.command()
def show_identity():
    """Show current device identity"""
    try:
        identity = DeviceIdentity()

        if not identity.is_initialized():
            console.print("[yellow]⚠️ Device identity not initialized[/yellow]")
            console.print("[dim]Run 'pisecure init-identity' to initialize[/dim]")
            return

        device_info = identity.get_identity()

        table = Table(title="🆔 Device Identity")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Device ID", device_info.get('device_id', 'unknown'))
        table.add_row("Device Name", device_info.get('device_name', 'none'))
        table.add_row("Organization", device_info.get('organization', 'unknown'))
        table.add_row("Fingerprint", device_info.get('fingerprint', 'unknown')[:32] + "...")
        table.add_row("Certificate Status", device_info.get('certificate_status', 'unknown'))

        capabilities = ", ".join(device_info.get('capabilities', []))
        table.add_row("Capabilities", capabilities)

        # Fingerprint verification
        fp_verify = device_info.get('fingerprint_verification', {})
        if fp_verify.get('verified'):
            table.add_row("Fingerprint Check", "✅ Verified")
        else:
            table.add_row("Fingerprint Check", "❌ Mismatch")

        console.print(table)

        # Certificate details if available
        if device_info.get('certificate_status') == 'active':
            cert_info = device_info.get('certificate', {})
            if cert_info:
                console.print(f"\n[blue]📜 Certificate Details:[/blue]")
                console.print(f"   Serial: {cert_info.get('serial', 'unknown')}")
                console.print(f"   Valid Until: {cert_info.get('not_after', 'unknown')}")
                console.print(f"   Fingerprint: {cert_info.get('fingerprint', 'unknown')[:32]}...")

    except Exception as e:
        console.print(f"[red]❌ Show identity error: {e}[/red]")


@cli.command()
def verify_identity():
    """Verify device identity integrity"""
    try:
        identity = DeviceIdentity()

        if not identity.is_initialized():
            console.print("[yellow]⚠️ Device identity not initialized[/yellow]")
            return

        console.print("[blue]🔍 Verifying device identity...[/blue]")

        result = identity.verify_identity()

        if result['verified']:
            console.print("[green]✅ Device identity verified![/green]")
        else:
            console.print("[red]❌ Device identity verification failed[/red]")

        if result.get('issues'):
            console.print(f"\n[red]🚨 Issues found:[/red]")
            for issue in result['issues']:
                console.print(f"   • {issue}")

        if result.get('warnings'):
            console.print(f"\n[yellow]⚠️ Warnings:[/yellow]")
            for warning in result['warnings']:
                console.print(f"   • {warning}")

        console.print(f"\n[blue]🔧 Current capabilities: {', '.join(result.get('capabilities', []))}[/blue]")

    except Exception as e:
        console.print(f"[red]❌ Identity verification error: {e}[/red]")


@cli.command()
@click.argument('cert_pem', type=click.Path(exists=True))
def authenticate_device(cert_pem):
    """Authenticate remote device using certificate"""
    try:
        authenticator = DeviceAuthenticator()

        console.print(f"[blue]🔐 Authenticating device with certificate: {cert_pem}[/blue]")

        # Read certificate
        with open(cert_pem, 'r') as f:
            cert_pem_data = f.read()

        result = authenticator.authenticate_device(cert_pem_data)

        if result['authenticated']:
            console.print("[green]✅ Device authentication successful![/green]")
            console.print(f"   Device ID: {result['device_id']}")
            console.print(f"   Session Token: {result['session_token'][:32]}...")
            console.print(f"   Expires: {time.ctime(result['expires_at'])}")
        else:
            console.print("[red]❌ Device authentication failed[/red]")
            console.print(f"   Error: {result.get('error', 'Unknown error')}")
            console.print(f"   Stage: {result.get('stage', 'unknown')}")

    except Exception as e:
        console.print(f"[red]❌ Authentication error: {e}[/red]")


@cli.command()
def list_sessions():
    """List active authentication sessions"""
    try:
        authenticator = DeviceAuthenticator()

        sessions = authenticator.list_active_sessions()

        if not sessions:
            console.print("[yellow]📭 No active sessions[/yellow]")
            return

        table = Table(title="🔐 Active Authentication Sessions")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("Device ID", style="green")
        table.add_column("Authenticated", style="magenta")
        table.add_column("Expires", style="yellow")

        for session in sessions:
            table.add_row(
                session['session_id'][:16] + "...",
                session['device_id'],
                time.ctime(session['authenticated_at']),
                time.ctime(session['expires_at'])
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ List sessions error: {e}[/red]")


@cli.command()
def rotate_certificate():
    """Rotate device certificate for security"""
    try:
        identity = DeviceIdentity()

        if not identity.is_initialized():
            console.print("[yellow]⚠️ Device identity not initialized[/yellow]")
            return

        console.print("[blue]🔄 Rotating device certificate...[/blue]")

        result = identity.rotate_certificate()

        if result['success']:
            console.print("[green]✅ Certificate rotated successfully![/green]")
            console.print(f"   New Fingerprint: {result['new_fingerprint'][:32]}...")
            console.print(f"   Rotated At: {time.ctime(result['rotated_at'])}")
        else:
            console.print(f"[red]❌ Certificate rotation failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Certificate rotation error: {e}[/red]")


@cli.command()
def export_identity():
    """Export device identity for backup"""
    try:
        identity = DeviceIdentity()

        if not identity.is_initialized():
            console.print("[yellow]⚠️ Device identity not initialized[/yellow]")
            return

        export_path = f"/tmp/pisecure_identity_{int(time.time())}.json"

        if identity.export_identity(export_path):
            console.print(f"[green]✅ Identity exported to: {export_path}[/green]")
            console.print("[yellow]⚠️ Secure this file - it contains sensitive identity information[/yellow]")
        else:
            console.print("[red]❌ Identity export failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Identity export error: {e}[/red]")


@cli.command()
@click.argument('plugin_name')
def import_identity(identity_file):
    """Import device identity from backup"""
    try:
        identity = DeviceIdentity()

        console.print(f"[blue]📥 Importing identity from: {identity_file}[/blue]")

        if identity.import_identity(identity_file):
            console.print("[green]✅ Identity imported successfully![/green]")
            console.print("[yellow]🔄 Device identity has been updated[/yellow]")
        else:
            console.print("[red]❌ Identity import failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Identity import error: {e}[/red]")


# === ENHANCED UPDATE SYSTEM ===

@cli.command()
@click.option('--type', 'update_type', help='Filter by update type (critical, safe, compatible, breaking)')
@click.option('--git', is_flag=True, help='Use direct GitHub updates instead of blockchain-based')
def update_check(update_type, git):
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


@cli.command()
@click.argument('version', required=False)
@click.option('--force', is_flag=True, help='Force application (skip safety checks)')
@click.option('--skip-backup', is_flag=True, help='Skip backup creation (not recommended)')
@click.option('--git', is_flag=True, help='Apply Git-based update to specific commit')
def update_apply(version, force, skip_backup, git):
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
                console.print(f"[red]❌ Verification failed: {verify_result['error']}[/red]")
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
                console.print(f"[red]❌ Wallet '{wallet}' not found[/red]")
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

        console.print(f"[blue]📥 Importing wallet metadata from: {backup_path}[/blue]")

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


# Register subcommand groups
cli.add_command(update)

def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()