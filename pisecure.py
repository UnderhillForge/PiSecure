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

from .core import SignChain, HardwareVerifier, SignTokenMiner
from .updates import OTAUpdater
from .identity import DeviceIdentity, DeviceAuthenticator

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
        health = info['network_health']
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
def mine(interactive):
    """Start blockchain mining"""
    try:
        miner = SignTokenMiner(SignChain())

        if interactive:
            console.print("[green]⛏️ Starting interactive mining...[/green]")
            console.print("[dim]Press Ctrl-C to stop[/dim]\n")

            success = miner.start_interactive_mining()
            if not success:
                console.print("[red]❌ Mining failed - hardware verification required[/red]")
        else:
            console.print("[green]⛏️ Starting background mining...[/green]")
            success = miner.start_mining()
            if success:
                console.print("[green]✅ Background mining started[/green]")
            else:
                console.print("[red]❌ Mining blocked - hardware verification failed[/red]")

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
@click.argument('token_id', required=False)
def wallet(token_id):
    """Show wallet status and tokens"""
    try:
        from .core.wallet import SignWallet

        wallet = SignWallet()

        if token_id:
            # Show specific token
            token_data = None
            for t in wallet.wallet_data.get('tokens', []):
                if t.get('token_id') == token_id:
                    token_data = t
                    break

            if token_data:
                from .core.tokens import SignToken
                token = SignToken.from_dict(token_data)

                table = Table(title=f"🏷️ Token: {token_id}")
                table.add_column("Property", style="cyan", no_wrap=True)
                table.add_column("Value", style="magenta")

                table.add_row("Token ID", token.token_id)
                table.add_row("Type", token.token_type)
                table.add_row("Issued By", token.issued_by)
                table.add_row("Permissions", ", ".join(token.permissions))
                table.add_row("Issued At", time.ctime(token.issued_at))
                table.add_row("Expires At", time.ctime(token.expires_at))
                table.add_row("Blockchain TX", token.blockchain_tx[:16] + "..." if token.blockchain_tx else "None")

                console.print(table)
            else:
                console.print(f"[red]❌ Token {token_id} not found in wallet[/red]")
        else:
            # Show wallet overview
            tokens = wallet.wallet_data.get('tokens', [])
            transfers = wallet.get_transfer_history()

            table = Table(title="👛 Wallet Status")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")

            table.add_row("Wallet ID", wallet.wallet_data['wallet_id'][:16] + "...")
            table.add_row("Total Tokens", str(len(tokens)))
            table.add_row("Total Transfers", str(len(transfers)))
            table.add_row("Created", time.ctime(wallet.wallet_data['created_at']))

            console.print(table)

            if tokens:
                console.print("\n[blue]🪙 Tokens:[/blue]")
                token_table = Table()
                token_table.add_column("Token ID", style="cyan", no_wrap=True)
                token_table.add_column("Type", style="green")
                token_table.add_column("Permissions", style="yellow")

                for token_data in tokens[:5]:  # Show first 5
                    perms = ", ".join(token_data.get('permissions', []))
                    token_table.add_row(
                        token_data['token_id'][:16] + "...",
                        token_data.get('token_type', 'unknown'),
                        perms
                    )

                if len(tokens) > 5:
                    token_table.add_row("...", "...", f"+{len(tokens)-5} more")

                console.print(token_table)

    except Exception as e:
        console.print(f"[red]❌ Wallet error: {e}[/red]")


@cli.command()
@click.argument('package_path', type=click.Path(exists=True))
def verify_update(package_path):
    """Verify update package signature and integrity"""
    try:
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


@cli.command()
@click.option('--apply/--no-apply', default=False, help='Apply the update after verification')
def check_updates(apply):
    """Check for available updates"""
    try:
        import pisecure
        current_version = pisecure.__version__

        updater = OTAUpdater()

        console.print(f"[blue]🔍 Checking for updates (current: {current_version})[/blue]\n")

        updates = updater.check_for_updates(current_version)

        if not updates:
            console.print("[green]✅ No updates available - you have the latest version[/green]")
            return

        console.print(f"[yellow]📦 Found {len(updates)} available update(s):[/yellow]\n")

        # Show available updates
        table = Table(title="📦 Available Updates")
        table.add_column("Version", style="cyan", no_wrap=True)
        table.add_column("Publisher", style="green")
        table.add_column("Size", style="magenta", justify="right")
        table.add_column("Description", style="white")

        for update in updates:
            size_mb = update.get('size', 0) / (1024 * 1024) if update.get('size') else 0
            table.add_row(
                update.get('version', 'unknown'),
                update.get('publisher', 'unknown'),
                f"{size_mb:.1f} MB" if size_mb > 0 else "unknown",
                update.get('description', 'No description')[:50] + "..." if len(update.get('description', '')) > 50 else update.get('description', 'No description')
            )

        console.print(table)

        if apply and updates:
            # Apply latest update
            latest_update = updates[0]
            console.print(f"\n[yellow]📥 Downloading latest update: {latest_update.get('version')}[/yellow]")

            download_result = updater.download_update(latest_update)
            if not download_result['success']:
                console.print(f"[red]❌ Download failed: {download_result.get('error')}[/red]")
                return

            # Verify update
            verify_result = updater.verify_update(download_result['local_path'], latest_update)
            if not verify_result['verified']:
                console.print(f"[red]❌ Verification failed: {verify_result.get('error')}[/red]")
                return

            # Apply update
            apply_result = updater.apply_update(
                download_result['local_path'],
                verify_result['manifest']
            )

            if apply_result['success']:
                console.print(f"[green]✅ Update applied successfully: {apply_result.get('version')}[/green]")
                console.print("[yellow]🔄 Restarting services may be required[/yellow]")
            else:
                console.print(f"[red]❌ Update failed: {apply_result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Update check error: {e}[/red]")


@cli.command()
@click.argument('update_hash')
@click.option('--apply/--no-apply', default=False, help='Apply the update after download')
def download_update(update_hash, apply):
    """Download specific update by hash"""
    try:
        updater = OTAUpdater()

        console.print(f"[blue]📥 Downloading update: {update_hash}[/blue]")

        # Create minimal update info
        update_info = {'update_hash': update_hash}

        result = updater.download_update(update_info)

        if result['success']:
            console.print(f"[green]✅ Update downloaded successfully[/green]")
            console.print(f"📁 Local path: {result['local_path']}")
            console.print(f"📊 Size: {result['size']} bytes")
            console.print(f"🌐 Source: {result.get('source', 'unknown')}")

            if apply:
                # Verify and apply
                verify_result = updater.verify_update(result['local_path'], update_info)
                if verify_result['verified']:
                    apply_result = updater.apply_update(result['local_path'], verify_result['manifest'])
                    if apply_result['success']:
                        console.print(f"[green]✅ Update applied: {apply_result.get('version')}[/green]")
                    else:
                        console.print(f"[red]❌ Apply failed: {apply_result.get('error')}[/red]")
                else:
                    console.print(f"[red]❌ Verification failed: {verify_result.get('error')}[/red]")
        else:
            console.print(f"[red]❌ Download failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Download error: {e}[/red]")


@cli.command()
def update_status():
    """Show update system status"""
    try:
        updater = OTAUpdater()

        status = updater.get_system_status()

        table = Table(title="🔄 Update System Status")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")

        table.add_row("Current Version", status.get('current_version', 'unknown'))
        table.add_row("Available Updates", str(status.get('available_updates', 0)))
        table.add_row("Backups Available", str(status.get('backups_count', 0)))
        table.add_row("Cached Updates", str(status.get('cached_updates', 0)))
        table.add_row("Update History", str(status.get('update_history', 0)))
        table.add_row("Last Check", time.ctime(status.get('last_update_check', time.time())))

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Status error: {e}[/red]")


@cli.command()
@click.argument('backup_id', required=False)
def rollback(backup_id):
    """Rollback to previous version"""
    try:
        updater = OTAUpdater()

        if backup_id:
            # Rollback to specific backup
            console.print(f"[blue]🔄 Rolling back to backup: {backup_id}[/blue]")
            result = updater.rollback.rollback_to_backup(backup_id)
        else:
            # Rollback to latest
            console.print("[blue]🔄 Rolling back to latest backup[/blue]")
            result = updater.rollback_update()

        if result.get('success'):
            console.print("[green]✅ Rollback successful[/green]")
            console.print(f"📦 Backup ID: {result.get('backup_id')}")
            console.print(f"📋 Files restored: {result.get('files_restored', 0)}")
            console.print(f"⚡ Version restored: {result.get('version_restored', 'unknown')}")
        else:
            console.print(f"[red]❌ Rollback failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Rollback error: {e}[/red]")


@cli.command()
def emergency_rollback():
    """Emergency rollback to last known good state"""
    try:
        updater = OTAUpdater()

        console.print("[red]🚨 Performing emergency rollback...[/red]")
        result = updater.emergency_rollback()

        if result.get('success'):
            console.print("[green]✅ Emergency rollback successful[/green]")
        else:
            console.print(f"[red]❌ Emergency rollback failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Emergency rollback error: {e}[/red]")


@cli.command()
def list_backups():
    """List available rollback backups"""
    try:
        updater = OTAUpdater()

        backups = updater.rollback.list_backups()

        if not backups:
            console.print("[yellow]📭 No backups available[/yellow]")
            return

        table = Table(title="📦 Available Backups")
        table.add_column("Backup ID", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("Created", style="magenta")
        table.add_column("Files", style="yellow", justify="right")
        table.add_column("Size", style="blue", justify="right")

        for backup in backups:
            size_mb = backup.get('total_size', 0) / (1024 * 1024)
            created_time = time.ctime(backup.get('timestamp', 0))
            table.add_row(
                backup.get('backup_id', 'unknown')[:20] + "...",
                backup.get('version', 'unknown'),
                created_time,
                str(len(backup.get('files_backed_up', []))),
                f"{size_mb:.1f} MB"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ List backups error: {e}[/red]")


@cli.command()
@click.argument('wallet_name')
@click.option('--name', help='Human-readable wallet name')
def create_wallet(wallet_name, name):
    """Create a new wallet"""
    try:
        from .core.wallet import SignWallet

        wallet = SignWallet()

        console.print(f"[blue]🔐 Creating wallet: {wallet_name}[/blue]")

        result = wallet.create_wallet(wallet_name, name)

        if result['success']:
            console.print("[green]✅ Wallet created successfully![/green]")
            console.print(f"   Wallet ID: {result['wallet_id']}")
            console.print(f"   Address: {result['address']}")
            console.print(f"   Key file: {result['key_file']}")
            console.print(f"   Data file: {result['wallet_file']}")
        else:
            console.print(f"[red]❌ Wallet creation failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Create wallet error: {e}[/red]")


@cli.command()
@click.argument('wallet_name', required=False)
def show_wallet(wallet_name):
    """Show wallet information"""
    try:
        from .core.wallet import SignWallet

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
        from .core.wallet import SignWallet

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
@click.argument('identity_file', type=click.Path(exists=True))
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


@cli.command()
@click.argument('backup_path', type=click.Path())
def export_wallet(backup_path):
    """Export wallet to backup file"""
    try:
        from .core.wallet import SignWallet

        wallet = SignWallet()
        wallet.export_wallet(backup_path)

        console.print(f"[green]✅ Wallet exported to {backup_path}[/green]")

    except Exception as e:
        console.print(f"[red]❌ Export failed: {e}[/red]")


@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
def import_wallet(backup_path):
    """Import wallet from backup file"""
    try:
        from .core.wallet import SignWallet

        wallet = SignWallet()
        success = wallet.import_wallet(backup_path)

        if success:
            console.print(f"[green]✅ Wallet imported from {backup_path}[/green]")
        else:
            console.print(f"[red]❌ Import failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Import error: {e}[/red]")


if __name__ == '__main__':
    cli()