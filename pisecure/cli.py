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


@cli.command()
@click.option('--apply/--no-apply', default=False, help='Apply the update after verification')
def check_updates(apply):
    """Check for available updates"""
    try:
        try:
            # Try relative import first
            from .updates import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates import OTAUpdater

        updater = OTAUpdater()

        console.print(f"[blue]🔍 Checking for updates (current: {__import__('pisecure').__version__})[/blue]\n")

        updates = updater.check_for_updates(__import__('pisecure').__version__)

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
        try:
            # Try relative import first
            from .updates import OTAUpdater
        except ImportError:
            # Fall back to absolute import
            from updates import OTAUpdater

        updater = OTAUpdater()

        console.print(f"[blue]📥 Downloading update: {update_hash}[/blue]")

        # Create minimal update info
        update_info = {'update_hash': update_hash}

        result = updater.download_update(update_info)

        if result['success']:
            console.print(f"[green]✅ Update downloaded: {result['size']} bytes[/green]")
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
def list_plugins():
    """List installed plugins"""
    try:
        try:
            # Try relative import first
            from .plugins import plugin_manager
        except ImportError:
            # Fall back to absolute import
            from plugins import plugin_manager

        plugins = plugin_manager.list_plugins()

        if not plugins:
            console.print("[yellow]📭 No plugins installed[/yellow]")
            console.print("[dim]Install plugins with: pisecure install-plugin <plugin_file>[/dim]")
            return

        table = Table(title="🔌 Installed Plugins")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("Description", style="white")

        for plugin in plugins:
            table.add_row(
                plugin['name'],
                plugin['version'],
                plugin['description']
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Plugin list error: {e}[/red]")


@cli.command()
@click.argument('plugin_file', type=click.Path(exists=True))
def install_plugin(plugin_file):
    """Install a plugin from file"""
    try:
        try:
            # Try relative import first
            from .plugins import plugin_manager
        except ImportError:
            # Fall back to absolute import
            from plugins import plugin_manager

        console.print(f"[blue]🔌 Installing plugin: {plugin_file}[/blue]")

        if plugin_manager.load_plugin(plugin_file):
            console.print("[green]✅ Plugin installed successfully[/green]")
            console.print("[yellow]🔄 Restart services to activate plugin features[/yellow]")
        else:
            console.print("[red]❌ Plugin installation failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Plugin installation error: {e}[/red]")


@cli.command()
@click.argument('plugin_name')
def uninstall_plugin(plugin_name):
    """Uninstall a plugin"""
    try:
        try:
            # Try relative import first
            from .plugins import plugin_manager
        except ImportError:
            # Fall back to absolute import
            from plugins import plugin_manager

        console.print(f"[blue]🔌 Uninstalling plugin: {plugin_name}[/blue]")

        if plugin_manager.unload_plugin(plugin_name):
            console.print("[green]✅ Plugin uninstalled successfully[/green]")
            console.print("[yellow]🔄 Restart services to complete removal[/yellow]")
        else:
            console.print(f"[red]❌ Plugin '{plugin_name}' not found or uninstall failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Plugin uninstallation error: {e}[/red]")


@cli.command()
@click.argument('plugin_name')
@click.argument('description', default="")
def create_plugin_template(plugin_name, description):
    """Create a plugin template file"""
    try:
        try:
            # Try relative import first
            from .plugins import plugin_manager
        except ImportError:
            # Fall back to absolute import
            from plugins import plugin_manager

        if not description:
            description = f"{plugin_name} plugin for PiSecure"

        template = plugin_manager.create_plugin_template(plugin_name, description)

        filename = f"{plugin_name.lower().replace(' ', '_')}_plugin.py"
        filepath = f"/opt/pisecure/plugins/{filename}"

        # Ensure plugins directory exists
        import os
        os.makedirs("/opt/pisecure/plugins", exist_ok=True)

        with open(filepath, 'w') as f:
            f.write(template)

        console.print(f"[green]✅ Plugin template created: {filepath}[/green]")
        console.print("[blue]📝 Edit the file to implement your plugin functionality[/blue]")
        console.print(f"[dim]Install with: pisecure install-plugin {filepath}[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Template creation error: {e}[/red]")


@cli.command()
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Private key password')
def generate_signing_key(password):
    """Generate a new update signing keypair"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_signer
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_signer

        console.print("[blue]🔐 Generating update signing keypair...[/blue]")

        result = update_signer.generate_keypair(password=password)

        if result['success']:
            console.print("[green]✅ Signing keypair generated successfully![/green]")
            console.print(f"   Public Key: {result['public_key'][:50]}...")
            console.print(f"   Key Size: {result['key_size']} bits")
            console.print(f"   Algorithm: {result['algorithm']}")
            console.print("[yellow]⚠️ Secure the private key file - it contains your signing credentials[/yellow]")
        else:
            console.print(f"[red]❌ Key generation failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Key generation error: {e}[/red]")


@cli.command()
@click.argument('key_id')
@click.argument('public_key_file', type=click.Path(exists=True))
@click.option('--permissions', default='sign_updates', help='Comma-separated permissions')
def register_update_key(key_id, public_key_file, permissions):
    """Register an authorized update signing key"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_authority
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_authority

        # Read public key
        with open(public_key_file, 'r') as f:
            public_key_pem = f.read()

        permissions_list = [p.strip() for p in permissions.split(',')]

        console.print(f"[blue]📝 Registering update key: {key_id}[/blue]")

        result = update_authority.register_authority_key(
            key_id=key_id,
            public_key_pem=public_key_pem,
            permissions=permissions_list
        )

        if result['success']:
            console.print("[green]✅ Update key registered successfully![/green]")
            if result.get('tx_hash'):
                console.print(f"   Blockchain TX: {result['tx_hash']}")
        else:
            console.print(f"[red]❌ Key registration failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Key registration error: {e}[/red]")


@cli.command()
@click.argument('key_id')
def revoke_update_key(key_id):
    """Revoke an authorized update signing key"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_authority
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_authority

        console.print(f"[blue]🚫 Revoking update key: {key_id}[/blue]")

        result = update_authority.revoke_authority_key(key_id=key_id)

        if result['success']:
            console.print("[green]✅ Update key revoked successfully![/green]")
            if result.get('tx_hash'):
                console.print(f"   Blockchain TX: {result['tx_hash']}")
        else:
            console.print(f"[red]❌ Key revocation failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Key revocation error: {e}[/red]")


@cli.command()
def list_update_keys():
    """List authorized update signing keys"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_authority
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_authority

        keys_info = update_authority.list_authorized_keys()

        console.print(f"[blue]🔑 Authorized Update Keys (Threshold: {keys_info['threshold']})[/blue]\n")

        if keys_info['active_keys']:
            console.print("[green]✅ Active Keys:[/green]")
            for key_id, key_info in keys_info['active_keys'].items():
                console.print(f"   {key_id}:")
                console.print(f"     Added: {time.ctime(key_info.get('added_at', 0))}")
                console.print(f"     Permissions: {', '.join(key_info.get('permissions', []))}")
        else:
            console.print("[yellow]⚠️ No active keys[/yellow]")

        if keys_info['revoked_keys']:
            console.print(f"\n[red]🚫 Revoked Keys: {', '.join(keys_info['revoked_keys'])}[/red]")

    except Exception as e:
        console.print(f"[red]❌ List keys error: {e}[/red]")


@cli.command()
@click.argument('threshold', type=int)
def set_update_threshold(threshold):
    """Set the minimum signatures required for updates"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_authority
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_authority

        console.print(f"[blue]⚙️ Setting update threshold to: {threshold}[/blue]")

        result = update_authority.set_threshold(threshold=threshold)

        if result['success']:
            console.print("[green]✅ Update threshold set successfully![/green]")
            if result.get('tx_hash'):
                console.print(f"   Blockchain TX: {result['tx_hash']}")
        else:
            console.print(f"[red]❌ Threshold update failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Threshold update error: {e}[/red]")


@cli.command()
@click.argument('update_data_file', type=click.Path(exists=True))
def sign_update(update_data_file):
    """Sign update data with the local private key"""
    try:
        try:
            # Try relative import first
            from .updates.auth import update_signer
        except ImportError:
            # Fall back to absolute import
            from updates.auth import update_signer

        # Read update data
        with open(update_data_file, 'r') as f:
            update_data = json.load(f)

        console.print("[blue]✍️ Signing update data...[/blue]")

        signature = update_signer.sign_update(update_data)

        if signature:
            # Add signature to update data
            if 'signatures' not in update_data:
                update_data['signatures'] = []

            # Get public key info for signature
            public_key = update_signer.get_public_key()
            if public_key:
                # Extract key ID from public key (this would need a lookup)
                key_id = "local_signing_key"  # In practice, this would be looked up

                update_data['signatures'].append({
                    'key_id': key_id,
                    'signature': signature
                })

                # Save signed update
                signed_file = update_data_file.replace('.json', '_signed.json')
                with open(signed_file, 'w') as f:
                    json.dump(update_data, f, indent=2)

                console.print("[green]✅ Update signed successfully![/green]")
                console.print(f"   Signature: {signature[:32]}...")
                console.print(f"   Signed file: {signed_file}")
            else:
                console.print("[red]❌ Could not get public key for signature[/red]")
        else:
            console.print("[red]❌ Update signing failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Update signing error: {e}[/red]")


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
@click.option('--name', help='Human-readable wallet name (optional)')
def create_wallet(wallet_name, name):
    """Create a new wallet with optional custom name registration"""
    try:
        try:
            # Try relative import first
            from .core.wallet import SignWallet
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet
            from core.blockchain import SignChain

        wallet = SignWallet()

        if name:
            # User wants a custom name - check if it's available and show fee warning
            blockchain = SignChain()

            if not blockchain.check_name_availability(name):
                console.print(f"[red]❌ Name '{name}' is already registered[/red]")
                return

            # Check bootstrap wallet balance for fee
            bootstrap_wallet = "node-" + wallet_name.split('-')[-1] if '-' in wallet_name else wallet_name
            try:
                bootstrap_balance = blockchain.get_wallet_balance(wallet_name)  # Assume current wallet is bootstrap
                if bootstrap_balance < 5.0:
                    console.print(f"[yellow]⚠️ Insufficient balance for name registration[/yellow]")
                    console.print(f"   Current balance: {bootstrap_balance} tokens")
                    console.print(f"   Required: 5.0 tokens")
                    console.print(f"   Mine more tokens first, then run: pisecure register-name {name}")
                    name = None  # Don't register name
                else:
                    console.print(f"[blue]🏷️ Custom Name Registration[/blue]")
                    console.print(f"   Name: {name}")
                    console.print(f"   Fee: 5 PiSecure tokens")
                    console.print(f"   Current balance: {bootstrap_balance} tokens")
                    console.print(f"   After registration: {bootstrap_balance - 5.0} tokens")

                    if not click.confirm("Continue with name registration?", default=True):
                        console.print("[dim]Name registration cancelled[/dim]")
                        name = None
            except:
                console.print(f"[yellow]⚠️ Could not check balance - name registration disabled[/yellow]")
                name = None

        console.print(f"[blue]🔐 Creating wallet: {wallet_name}[/blue]")

        result = wallet.create_wallet(wallet_name, name)

        if result['success']:
            console.print("[green]✅ Wallet created successfully![/green]")
            console.print(f"   Wallet ID: {result['wallet_id']}")
            console.print(f"   Address: {result['address']}")
            console.print(f"   Key file: {result['key_file']}")
            console.print(f"   Data file: {result['wallet_file']}")

            if name:
                console.print(f"   Custom Name: {name} (PiNS registered)")
                console.print(f"   Registration Fee: 5 tokens deducted")
        else:
            console.print(f"[red]❌ Wallet creation failed: {result.get('error')}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Create wallet error: {e}[/red]")


@cli.command()
@click.argument('name')
@click.option('--wallet', help='Wallet address to register name for (uses config wallet if not specified)')
def register_name(name, wallet):
    """Register a PiNS name for your wallet"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain

        blockchain = SignChain()

        # Determine wallet address
        if not wallet:
            # Try to load from config
            try:
                import json
                config_path = "/etc/pisecure/config.json"
                with open(config_path, 'r') as f:
                    config = json.load(f)
                wallet = config.get('mining', {}).get('wallet_address')
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                console.print("[red]❌ No wallet configured. Use --wallet to specify wallet address[/red]")
                return

        if not wallet:
            console.print("[red]❌ No wallet address available[/red]")
            return

        # Check name availability
        if not blockchain.check_name_availability(name):
            console.print(f"[red]❌ Name '{name}' is already registered[/red]")
            return

        # Check wallet balance
        balance = blockchain.get_wallet_balance(wallet)
        if balance < 5.0:
            console.print(f"[red]❌ Insufficient balance for registration[/red]")
            console.print(f"   Required: 5.0 tokens")
            console.print(f"   Current balance: {balance} tokens")
            console.print(f"   Mine more tokens first!")
            return

        console.print(f"[blue]🏷️ Registering PiNS name: {name}[/blue]")
        console.print(f"   Wallet: {wallet[:24]}...")
        console.print(f"   Fee: 5 PiSecure tokens")
        console.print(f"   Current balance: {balance} tokens")
        console.print(f"   After registration: {balance - 5.0} tokens")

        if not click.confirm("Register this name?", default=True):
            console.print("[dim]Name registration cancelled[/dim]")
            return

        # Register the name
        tx_hash = blockchain.register_name(name, wallet)

        console.print("[green]✅ Name registration submitted![/green]")
        console.print(f"   Name: {name}")
        console.print(f"   Wallet: {wallet}")
        console.print(f"   Transaction: {tx_hash[:16]}...")
        console.print(f"   Status: Pending (will be mined in next block)")

        # Mine the transaction immediately if possible
        console.print("[dim]Mining registration transaction...[/dim]")
        block = blockchain.mine_pending_transactions(verbose=False)
        if block:
            console.print(f"[green]✅ Name registered in block #{block.index}![/green]")
            console.print(f"   Fee deducted: 5 tokens")
        else:
            console.print("[yellow]⚠️ Name registration pending - will be mined in next block[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Name registration error: {e}[/red]")


@cli.command()
@click.argument('name')
def resolve_name(name):
    """Resolve a PiNS name to wallet address"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain

        blockchain = SignChain()

        address = blockchain.resolve_name(name)

        if address:
            console.print(f"[green]✅ Name Resolution[/green]")
            console.print(f"   Name: {name}")
            console.print(f"   Address: {address}")

            # Show registration info
            name_info = blockchain.get_name_info(name)
            if name_info:
                console.print(f"   Registered: {time.ctime(name_info['registered_at'])}")
                console.print(f"   Block: #{name_info.get('block_index', 'pending')}")
        else:
            console.print(f"[red]❌ Name '{name}' not found[/red]")

    except Exception as e:
        console.print(f"[red]❌ Name resolution error: {e}[/red]")


@cli.command()
@click.argument('name')
def check_name(name):
    """Check if a PiNS name is available"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain

        blockchain = SignChain()

        available = blockchain.check_name_availability(name)

        if available:
            console.print(f"[green]✅ Name '{name}' is available for registration[/green]")
            console.print(f"   Registration fee: 5 PiSecure tokens")
        else:
            name_info = blockchain.get_name_info(name)
            if name_info:
                console.print(f"[red]❌ Name '{name}' is already registered[/red]")
                console.print(f"   Owner: {name_info['address'][:24]}...")
                console.print(f"   Registered: {time.ctime(name_info['registered_at'])}")

    except Exception as e:
        console.print(f"[red]❌ Name check error: {e}[/red]")


@cli.command()
@click.argument('wallet_address')
def wallet_names(wallet_address):
    """List all PiNS names registered to a wallet"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain

        blockchain = SignChain()

        names = blockchain.get_wallet_names(wallet_address)

        if names:
            console.print(f"[green]🏷️ PiNS Names for {wallet_address[:24]}...[/green]")
            for name in names:
                name_info = blockchain.get_name_info(name)
                console.print(f"   • {name} (registered {time.ctime(name_info['registered_at'])})")
        else:
            console.print(f"[dim]No PiNS names registered for this wallet[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Wallet names error: {e}[/red]")


@cli.command()
def list_names():
    """List all registered PiNS names"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain

        blockchain = SignChain()

        names = blockchain.get_registered_names()

        if names:
            table = Table(title="🏷️ Registered PiNS Names")
            table.add_column("Name", style="cyan")
            table.add_column("Address", style="green", no_wrap=True)
            table.add_column("Registered", style="blue")

            for name in sorted(names):
                name_info = blockchain.get_name_info(name)
                table.add_row(
                    name,
                    name_info['address'][:24] + "...",
                    time.ctime(name_info['registered_at'])
                )

            console.print(table)
        else:
            console.print("[dim]No PiNS names registered yet[/dim]")
            console.print("[dim]Register your first name with: pisecure register-name <name>[/dim]")

    except Exception as e:
        console.print(f"[red]❌ List names error: {e}[/red]")


@cli.command()
def setup_public_access():
    """Setup automatic public access using NAT traversal, Tor, and relays"""
    try:
        try:
            # Try relative import first
            from .core.nat_traversal import node_discovery
        except ImportError:
            # Fall back to absolute import
            from core.nat_traversal import node_discovery

        console.print("[blue]🌐 Setting up automatic public access for your PiSecure node...[/blue]")
        console.print("[dim]This will make your node discoverable worldwide without manual configuration[/dim]")
        console.print()

        # Run discovery setup
        results = node_discovery.make_node_discoverable()

        console.print("[green]✅ Public access setup complete![/green]")
        console.print(f"   Node ID: {results['node_id']}")
        console.print(f"   Methods: {', '.join(results['methods_attempted'])}")
        console.print(f"   Success: {results['success_count']} methods working")
        console.print()

        # Show endpoints
        if results['endpoints']:
            console.print("[blue]🔗 Available Access Methods:[/blue]")
            for endpoint in results['endpoints']:
                endpoint_type = endpoint['type']
                if endpoint_type == 'stun_direct':
                    console.print(f"   🌐 Direct P2P: {endpoint['ip']}:{endpoint['port']} (NAT: {endpoint['nat_type']})")
                elif endpoint_type == 'tor_onion':
                    console.print(f"   🧅 Tor Onion: {endpoint['address']}")
                elif endpoint_type == 'upnp':
                    console.print(f"   📡 UPnP: {endpoint['ip']}:{endpoint['port']}")
                elif endpoint_type == 'turn_relay':
                    console.print(f"   🔄 TURN Relay: {endpoint['ip']}:{endpoint['port']}")
                elif endpoint_type == 'community_relay':
                    console.print(f"   ☁️ Community Relays: {endpoint['available_relays']} available")
        else:
            console.print("[yellow]⚠️ No public access methods succeeded[/yellow]")
            console.print("[dim]Your node may still be accessible locally or via manual configuration[/dim]")

        console.print()
        console.print("[green]🎉 Your PiSecure node is now set up for worldwide access![/green]")
        console.print("[dim]Mobile apps can now discover and connect to your node automatically[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Public access setup failed: {e}[/red]")


@cli.command()
def node_discovery_status():
    """Show current node discovery and public access status"""
    try:
        try:
            # Try relative import first
            from .core.nat_traversal import node_discovery
        except ImportError:
            # Fall back to absolute import
            from core.nat_traversal import node_discovery

        status = node_discovery.get_discovery_status()

        console.print("[blue]🔍 Node Discovery Status[/blue]")
        console.print(f"   Node ID: {status['node_id']}")
        console.print()

        # Show endpoints
        if status['endpoints']:
            console.print("[green]✅ Active Endpoints:[/green]")
            for endpoint in status['endpoints']:
                endpoint_type = endpoint['type']
                if endpoint_type == 'stun_direct':
                    console.print(f"   🌐 Direct P2P: {endpoint['ip']}:{endpoint['port']}")
                    console.print(f"      NAT Type: {endpoint.get('nat_type', 'unknown')}")
                elif endpoint_type == 'tor_onion':
                    console.print(f"   🧅 Tor Onion: {endpoint}")
                elif endpoint_type == 'upnp':
                    console.print(f"   📡 UPnP: {endpoint['ip']}:{endpoint['port']}")
                elif endpoint_type == 'turn_relay':
                    console.print(f"   🔄 TURN Relay: {endpoint['ip']}:{endpoint['port']}")
        else:
            console.print("[yellow]⚠️ No active endpoints[/yellow]")

        # Show network status
        if status['nat_info']:
            console.print()
            console.print("[blue]📊 NAT Information:[/blue]")
            nat_info = status['nat_info']
            console.print(f"   Public IP: {nat_info.get('public_ip', 'unknown')}")
            console.print(f"   Public Port: {nat_info.get('public_port', 'unknown')}")
            console.print(f"   NAT Type: {nat_info.get('nat_type', 'unknown')}")

        if status['tor_address']:
            console.print(f"   Tor Address: {status['tor_address']}")

        console.print(f"   Community Relays: {status['relay_count']}")

    except Exception as e:
        console.print(f"[red]❌ Discovery status error: {e}[/red]")


@cli.command()
def test_connectivity():
    """Test connectivity to bootstrap nodes and public endpoints"""
    try:
        import socket
        import time

        console.print("[blue]🔗 Testing PiSecure Network Connectivity[/blue]")
        console.print()

        # Test bootstrap nodes
        bootstrap_nodes = [
            ("bootstrap.pisecure.net", 3141),
            ("stun.l.google.com", 19302),  # Test STUN
        ]

        console.print("[cyan]Testing Bootstrap Nodes:[/cyan]")
        for host, port in bootstrap_nodes:
            try:
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                response_time = (time.time() - start_time) * 1000

                if result == 0:
                    console.print(f"   ✅ {host}:{port} - Reachable ({response_time:.0f}ms)")
                else:
                    console.print(f"   ❌ {host}:{port} - Unreachable")
                sock.close()
            except Exception as e:
                console.print(f"   ❌ {host}:{port} - Error: {e}")

        console.print()
        console.print("[cyan]Local Node Status:[/cyan]")

        # Test local services
        local_services = [
            ("localhost", 3142, "API Server"),
            ("localhost", 5000, "Dashboard"),
        ]

        for host, port, service in local_services:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))

                if result == 0:
                    console.print(f"   ✅ {service} - Running on {host}:{port}")
                else:
                    console.print(f"   ❌ {service} - Not accessible on {host}:{port}")
                sock.close()
            except Exception as e:
                console.print(f"   ❌ {service} - Error: {e}")

    except Exception as e:
        console.print(f"[red]❌ Connectivity test error: {e}[/red]")


@cli.command()
def network_health():
    """Show overall network health and connectivity statistics"""
    try:
        try:
            # Try relative import first
            from .core.blockchain import SignChain
            from .core.nat_traversal import node_discovery
        except ImportError:
            # Fall back to absolute import
            from core.blockchain import SignChain
            from core.nat_traversal import node_discovery

        blockchain = SignChain()
        chain_info = blockchain.get_chain_info()

        console.print("[blue]🌐 PiSecure Network Health Report[/blue]")
        console.print("=" * 50)

        # Blockchain health
        console.print(f"[cyan]Blockchain Status:[/cyan]")
        console.print(f"   Blocks: {chain_info['blocks']}")
        console.print(f"   Difficulty: {chain_info['difficulty']}")
        console.print(f"   Chain Valid: {'✅ Yes' if chain_info['is_valid'] else '❌ No'}")
        console.print(f"   Pending TX: {chain_info['pending_transactions']}")

        # Network health
        health = chain_info['network_health']
        console.print(f"   Participation: {health['participation']:.1%}")
        console.print(f"   Avg Block Time: {health['avg_block_time']:.1f}s")
        console.print(f"   Network Health: {health['health_score']:.1%}")

        # Node discovery status
        discovery_status = node_discovery.get_discovery_status()
        console.print()
        console.print(f"[cyan]Node Discovery:[/cyan]")
        console.print(f"   Node ID: {discovery_status['node_id']}")
        console.print(f"   Active Endpoints: {len(discovery_status['endpoints'])}")
        console.print(f"   Community Relays: {discovery_status['relay_count']}")

        # Check if this node is a relay
        is_relay = _check_if_relay_node()
        console.print(f"   Relay Status: {'✅ Active' if is_relay else '❌ Not participating'}")

        # PiNS statistics
        names_count = len(blockchain.get_registered_names())
        console.print(f"   PiNS Names: {names_count}")

        # Overall assessment
        console.print()
        health_score = health['health_score']
        if health_score > 0.8:
            assessment = "[green]Excellent - Network is healthy[/green]"
        elif health_score > 0.6:
            assessment = "[yellow]Good - Network is functioning[/yellow]"
        else:
            assessment = "[red]Needs attention - Network health is low[/red]"

        console.print(f"[cyan]Overall Assessment:[/cyan] {assessment}")

        # Recommendations
        console.print()
        console.print("[cyan]Recommendations:[/cyan]")
        if len(discovery_status['endpoints']) == 0:
            console.print("   • Run 'pisecure setup-public-access' to enable worldwide access")
        if not is_relay and len(discovery_status['endpoints']) > 0:
            console.print("   • Consider becoming a relay node: 'pisecure become-relay-node'")
        if chain_info['pending_transactions'] > 10:
            console.print("   • High pending transactions - mining may be slow")
        if health['participation'] < 0.5:
            console.print("   • Low network participation - consider increasing mining activity")
        if names_count == 0:
            console.print("   • No PiNS names registered - consider registering your first name")

    except Exception as e:
        console.print(f"[red]❌ Network health check error: {e}[/red]")


def _check_if_relay_node():
    """Check if this node is configured as a relay node"""
    try:
        import json
        config_path = "/etc/pisecure/config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('network', {}).get('relay_enabled', False)
    except:
        return False


@cli.command()
@click.option('--port', default=3143, help='Port to run relay service on')
@click.option('--max-connections', default=50, help='Maximum concurrent relay connections')
@click.option('--bandwidth-limit', default=10, help='Bandwidth limit in MB/s (0 = unlimited)')
def become_relay_node(port, max_connections, bandwidth_limit):
    """Become a community relay node to help other users discover the network"""
    try:
        console.print("[blue]🌐 Becoming a PiSecure Community Relay Node[/blue]")
        console.print()
        console.print("[yellow]⚠️  Important Information:[/yellow]")
        console.print("   • Relay nodes help new users discover the PiSecure network")
        console.print("   • You will receive mining rewards for relay services")
        console.print("   • Your node will be publicly listed as a community relay")
        console.print("   • You can stop being a relay at any time")
        console.print()
        console.print("[cyan]Configuration:[/cyan]")
        console.print(f"   • Relay Port: {port}")
        console.print(f"   • Max Connections: {max_connections}")
        console.print(f"   • Bandwidth Limit: {bandwidth_limit} MB/s" if bandwidth_limit > 0 else "   • Bandwidth Limit: Unlimited")
        console.print()

        if not click.confirm("Do you want to become a community relay node?", default=True):
            console.print("[dim]Relay node setup cancelled[/dim]")
            return

        # Check if node has public access
        try:
            from .core.nat_traversal import node_discovery
            discovery_status = node_discovery.get_discovery_status()
            if len(discovery_status['endpoints']) == 0:
                console.print("[yellow]⚠️  Your node doesn't have public access configured[/yellow]")
                console.print("[dim]Setting up public access first...[/dim]")
                # Run setup-public-access
                from .core.nat_traversal import node_discovery
                results = node_discovery.make_node_discoverable()
                if results['success_count'] == 0:
                    console.print("[red]❌ Could not configure public access[/red]")
                    console.print("[dim]Please run 'pisecure setup-public-access' first[/dim]")
                    return
        except Exception as e:
            console.print(f"[red]❌ Error checking public access: {e}[/red]")
            return

        # Configure relay settings
        relay_config = {
            'enabled': True,
            'port': port,
            'max_connections': max_connections,
            'bandwidth_limit': bandwidth_limit,
            'node_id': None  # Will be set when relay service starts
        }

        # Update system configuration
        try:
            import json
            config_path = "/etc/pisecure/config.json"

            # Read existing config
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}

            # Update network config
            if 'network' not in config:
                config['network'] = {}
            config['network']['relay_enabled'] = True
            config['network']['relay_config'] = relay_config

            # Write updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            console.print(f"[red]❌ Error updating configuration: {e}[/red]")
            return

        # Create relay service
        relay_service_path = "/etc/systemd/system/pisecure-relay.service"
        try:
            relay_service = f"""[Unit]
Description=PiSecure Community Relay Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/PiSecure
ExecStart=/home/pi/PiSecure/pisecure_env/bin/python -c "
from pisecure.core.nat_traversal import CommunityRelayNetwork
import time
relay = CommunityRelayNetwork()
relay.start_relay_service(port={port}, max_connections={max_connections}, bandwidth_limit={bandwidth_limit})
"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pisecure-relay

[Install]
WantedBy=multi-user.target
"""

            with open(relay_service_path, 'w') as f:
                f.write(relay_service)

            # Reload systemd and start service
            import subprocess
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'pisecure-relay'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'pisecure-relay'], check=True)

        except Exception as e:
            console.print(f"[red]❌ Error creating relay service: {e}[/red]")
            return

        console.print("[green]✅ Successfully became a community relay node![/green]")
        console.print()
        console.print("[cyan]Relay Node Details:[/cyan]")
        console.print(f"   • Status: Active")
        console.print(f"   • Port: {port}")
        console.print(f"   • Max Connections: {max_connections}")
        console.print(f"   • Bandwidth Limit: {bandwidth_limit} MB/s" if bandwidth_limit > 0 else "   • Bandwidth Limit: Unlimited")
        console.print()
        console.print("[green]🎉 Thank you for supporting the PiSecure network![/green]")
        console.print("[dim]You will receive mining rewards for relay services[/dim]")
        console.print()
        console.print("[cyan]Management Commands:[/cyan]")
        console.print("   • Check status: sudo systemctl status pisecure-relay")
        console.print("   • View logs: sudo journalctl -u pisecure-relay -f")
        console.print("   • Stop relay: pisecure stop-relay-node")

    except Exception as e:
        console.print(f"[red]❌ Become relay node error: {e}[/red]")


@cli.command()
def stop_relay_node():
    """Stop being a community relay node"""
    try:
        console.print("[blue]🛑 Stopping PiSecure Community Relay Service[/blue]")
        console.print()

        # Stop and disable service
        import subprocess
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'pisecure-relay'], check=True)
            subprocess.run(['sudo', 'systemctl', 'disable', 'pisecure-relay'], check=True)
            console.print("[green]✅ Relay service stopped[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]⚠️  Error stopping relay service: {e}[/yellow]")

        # Update configuration
        try:
            import json
            config_path = "/etc/pisecure/config.json"

            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}

            if 'network' in config:
                config['network']['relay_enabled'] = False
                if 'relay_config' in config['network']:
                    config['network']['relay_config']['enabled'] = False

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            console.print("[green]✅ Relay configuration disabled[/green]")

        except Exception as e:
            console.print(f"[yellow]⚠️  Error updating configuration: {e}[/yellow]")

        # Remove service file
        try:
            import os
            service_path = "/etc/systemd/system/pisecure-relay.service"
            if os.path.exists(service_path):
                os.remove(service_path)
                subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
                console.print("[green]✅ Relay service files cleaned up[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Error cleaning up service files: {e}[/yellow]")

        console.print()
        console.print("[green]✅ Successfully stopped being a relay node[/green]")
        console.print("[dim]Thank you for your service to the PiSecure community![/dim]")

    except Exception as e:
        console.print(f"[red]❌ Stop relay node error: {e}[/red]")


@cli.command()
def relay_status():
    """Show relay node status and statistics"""
    try:
        console.print("[blue]📡 PiSecure Relay Node Status[/blue]")
        console.print("=" * 40)

        # Check if relay is enabled in config
        is_relay = _check_if_relay_node()
        console.print(f"[cyan]Relay Status:[/cyan] {'✅ Enabled' if is_relay else '❌ Disabled'}")

        if is_relay:
            # Check service status
            import subprocess
            try:
                result = subprocess.run(['sudo', 'systemctl', 'is-active', 'pisecure-relay'],
                                      capture_output=True, text=True)
                service_active = result.stdout.strip() == 'active'
                console.print(f"[cyan]Service Status:[/cyan] {'✅ Running' if service_active else '❌ Stopped'}")
            except:
                console.print(f"[cyan]Service Status:[/cyan] ❓ Unknown")

            # Show relay configuration
            try:
                import json
                config_path = "/etc/pisecure/config.json"
                with open(config_path, 'r') as f:
                    config = json.load(f)

                relay_config = config.get('network', {}).get('relay_config', {})
                if relay_config:
                    console.print()
                    console.print(f"[cyan]Relay Configuration:[/cyan]")
                    console.print(f"   • Port: {relay_config.get('port', 'unknown')}")
                    console.print(f"   • Max Connections: {relay_config.get('max_connections', 'unknown')}")
                    console.print(f"   • Bandwidth Limit: {relay_config.get('bandwidth_limit', 'unknown')} MB/s")
            except:
                pass

            # Show relay statistics (placeholder - would be implemented in relay service)
            console.print()
            console.print(f"[cyan]Relay Statistics:[/cyan]")
            console.print("   • Active Connections: (feature coming soon)"            console.print("   • Total Connections: (feature coming soon)"            console.print("   • Data Relayed: (feature coming soon)"            console.print("   • Uptime: (feature coming soon)"        else:
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
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

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
        try:
            # Try relative import first
            from .core.wallet import SignWallet
        except ImportError:
            # Fall back to absolute import
            from core.wallet import SignWallet

        wallet = SignWallet()
        success = wallet.import_wallet(backup_path)

        if success:
            console.print(f"[green]✅ Wallet imported from {backup_path}[/green]")
        else:
            console.print(f"[red]❌ Import failed[/red]")

    except Exception as e:
        console.print(f"[red]❌ Import error: {e}[/red]")


def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()