#!/usr/bin/env python3
"""
PiSecure Dashboard - Web Monitoring Interface for PiSecure Blockchain Nodes
===========================================================================

A lightweight web dashboard for monitoring PiSecure blockchain operations,
mining status, network health, and system performance on resource-constrained
devices like Raspberry Pi Zero 2 W.
"""

import os
import sys
import json
import time
import threading
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add PiSecure to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import psutil
import requests

# PiSecure imports
from core.blockchain import SignChain
from core.wallet import SignWallet
from core.network import DecentralizedPeerDiscovery


class PiSecureDashboard:
    """Main PiSecure dashboard application"""

    def __init__(self):
        self.app = Flask(__name__,
                        static_folder='static',
                        template_folder='templates')
        # Fix CORS for proper Socket.IO connection
        self.socketio = SocketIO(self.app, cors_allowed_origins=["*"], async_mode='threading')

        # PiSecure components
        self.blockchain = None
        self.peer_discovery = None
        self.wallet = None

        # Dashboard data
        self.system_stats = {}
        self.mining_stats = {}
        self.network_stats = {}
        self.blockchain_stats = {}

        # Stats cache to avoid recalculating on every API call
        self._stats_cache = {}
        self._cache_timeout = 2  # Cache stats for 2 seconds

        # Monitoring threads
        self.monitoring_thread = None
        self.monitoring_active = False

        # Update counters for staggered updates
        self._update_counter = 0

        # Setup routes
        self.setup_routes()

        # Setup SocketIO events
        self.setup_socketio_events()

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('dashboard.html')

        @self.app.route('/mining')
        def mining():
            """Mining status page"""
            return render_template('mining.html')

        @self.app.route('/network')
        def network():
            """Network status page"""
            return render_template('network.html')

        @self.app.route('/blockchain')
        def blockchain_explorer():
            """Blockchain explorer page"""
            return render_template('blockchain.html')

        @self.app.route('/wallets')
        def wallets():
            """Wallet management page"""
            return render_template('wallets.html')

        @self.app.route('/system')
        def system():
            """System status page"""
            return render_template('system.html')

        @self.app.route('/api/system/stats')
        def api_system_stats():
            """API endpoint for system statistics"""
            return jsonify(self.get_system_stats())

        @self.app.route('/api/blockchain/stats')
        def api_blockchain_stats():
            """API endpoint for blockchain statistics"""
            return jsonify(self.get_blockchain_stats())

        @self.app.route('/api/mining/stats')
        def api_mining_stats():
            """API endpoint for mining statistics"""
            return jsonify(self.get_mining_stats())

        @self.app.route('/api/network/stats')
        def api_network_stats():
            """API endpoint for network statistics"""
            return jsonify(self.get_network_stats())

        @self.app.route('/api/wallet/balance')
        def api_wallet_balance():
            """API endpoint for wallet balance"""
            wallet_id = request.args.get('wallet_id')
            if wallet_id:
                balance = self.get_wallet_balance(wallet_id)
                return jsonify({'balance': balance})
            return jsonify({'error': 'No wallet_id provided'})

        @self.app.route('/api/wallet/transactions')
        def api_wallet_transactions():
            """API endpoint for wallet transaction history"""
            wallet_id = request.args.get('wallet_id')
            limit = int(request.args.get('limit', 20))
            if wallet_id:
                if self.blockchain:
                    transactions = self.blockchain.get_wallet_transactions(wallet_id)
                    return jsonify({'transactions': transactions[:limit]})
                return jsonify({'transactions': []})
            return jsonify({'error': 'No wallet_id provided'})

        @self.app.route('/api/wallets/list')
        def api_wallets_list():
            """API endpoint for listing all wallets"""
            try:
                wallet = SignWallet()
                wallets = wallet.list_wallets()
                return jsonify({'wallets': wallets})
            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/wallets/create', methods=['POST'])
        def api_wallet_create():
            """API endpoint for creating a new wallet"""
            try:
                data = request.get_json()
                name = data.get('name', '').strip()
                auto_generate = data.get('auto_generate', False)

                if auto_generate:
                    # Generate a readable, unique wallet name
                    name = self._generate_wallet_name()
                elif not name:
                    return jsonify({'error': 'Wallet name is required'})

                # Check if wallet name already exists
                wallet = SignWallet()
                existing_wallets = wallet.list_wallets()
                if any(w['name'] == name for w in existing_wallets):
                    if auto_generate:
                        # If auto-generated name conflicts, try again with different suffix
                        name = self._generate_wallet_name()
                        # Check again
                        if any(w['name'] == name for w in existing_wallets):
                            return jsonify({'error': 'Could not generate unique wallet name'})
                    else:
                        return jsonify({'error': 'Wallet name already exists'})

                # Generate unique wallet ID with timestamp for extra uniqueness
                import secrets
                import time
                timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
                random_part = secrets.token_hex(6)  # 12 character hex string
                wallet_id = f"{timestamp}{random_part}"  # 16 character unique ID

                result = wallet.create_wallet(wallet_id, name)

                if result['success']:
                    return jsonify({
                        'success': True,
                        'wallet_id': result['wallet_id'],
                        'address': result['address'],
                        'name': name,
                        'auto_generated': auto_generate
                    })
                else:
                    return jsonify({'error': result.get('error', 'Failed to create wallet')})

            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/wallets/export/<wallet_id>')
        def api_wallet_export(wallet_id):
            """API endpoint for exporting wallet backup"""
            try:
                from flask import send_file
                import tempfile
                import os

                wallet = SignWallet()
                # Create temporary file for export
                with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False) as f:
                    temp_path = f.name

                # Export wallet without private key for security
                result = wallet.export_wallet(temp_path, include_private_key=False)

                if result['success']:
                    # Send file for download
                    response = send_file(
                        temp_path,
                        as_attachment=True,
                        download_name=f"{wallet_id}.dat",
                        mimetype='application/octet-stream'
                    )
                    # Clean up temp file after sending
                    @response.call_on_close
                    def cleanup():
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    return response
                else:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    return jsonify({'error': result.get('error', 'Export failed')})

            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/wallets/import', methods=['POST'])
        def api_wallet_import():
            """API endpoint for importing wallet backup"""
            try:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'})

                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'})

                if not file.filename.endswith('.dat'):
                    return jsonify({'error': 'File must be a .dat file'})

                # Save uploaded file temporarily
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    file.save(temp_file.name)
                    temp_path = temp_file.name

                try:
                    wallet = SignWallet()
                    result = wallet.import_wallet(temp_path)

                    if result['success']:
                        # If this was a cold storage wallet, unset cold storage status
                        wallet.set_cold_storage(result['wallet_id'], cold=False)
                        return jsonify({
                            'success': True,
                            'wallet_id': result['wallet_id'],
                            'address': result['address']
                        })
                    else:
                        return jsonify({'error': result.get('error', 'Import failed')})

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/wallets/cold-storage/<wallet_id>', methods=['POST'])
        def api_wallet_cold_storage(wallet_id):
            """API endpoint for cold storage operations"""
            try:
                data = request.get_json()
                action = data.get('action')  # 'export' or 'restore'

                if action not in ['export', 'restore']:
                    return jsonify({'error': 'Invalid action. Must be "export" or "restore"'})

                wallet = SignWallet()

                if action == 'export':
                    # First set wallet to cold storage
                    cold_result = wallet.set_cold_storage(wallet_id, cold=True)
                    if not cold_result['success']:
                        return jsonify({'error': cold_result.get('error', 'Failed to set cold storage')})

                    # Then export the wallet with private key
                    import tempfile
                    import os

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False) as f:
                        temp_path = f.name

                    result = wallet.export_wallet(temp_path, include_private_key=True, password='cold_storage_backup')

                    if result['success']:
                        response = send_file(
                            temp_path,
                            as_attachment=True,
                            download_name=f"{wallet_id}_cold_storage.dat",
                            mimetype='application/octet-stream'
                        )
                        @response.call_on_close
                        def cleanup():
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        return response
                    else:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                        return jsonify({'error': result.get('error', 'Cold storage export failed')})

                elif action == 'restore':
                    # Restore from cold storage - this would be handled by regular import
                    # but we need to unset cold storage status after successful import
                    return jsonify({'error': 'Use regular import for cold storage restoration'})

            except Exception as e:
                return jsonify({'error': str(e)})

        @self.app.route('/api/blockchain/blocks')
        def api_blocks():
            """API endpoint for recent blocks"""
            limit = int(request.args.get('limit', 10))
            blocks = self.get_recent_blocks(limit)
            return jsonify(blocks)

        @self.app.route('/api/blockchain/transactions')
        def api_transactions():
            """API endpoint for recent transactions"""
            limit = int(request.args.get('limit', 20))
            transactions = self.get_recent_transactions(limit)
            return jsonify(transactions)

        # Monitoring and health check endpoints
        @self.app.route('/api/health')
        def api_health():
            """API endpoint for system health status"""
            from core.monitoring import health_checker, metrics_collector

            # Collect current metrics
            blockchain_height = self.blockchain_stats.get('height', 0) if self.blockchain_stats else 0
            active_peers = len(self.network_stats.get('peers', [])) if self.network_stats else 0
            pending_transactions = self.blockchain_stats.get('pending_transactions', 0) if self.blockchain_stats else 0

            metrics_collector.collect_system_metrics(
                blockchain_height=blockchain_height,
                active_peers=active_peers,
                pending_transactions=pending_transactions
            )

            health = health_checker.check_system_health()
            return jsonify({
                'overall': health.overall,
                'checks': health.checks,
                'timestamp': health.timestamp
            })

        @self.app.route('/api/metrics')
        def api_metrics():
            """API endpoint for system metrics"""
            from core.monitoring import metrics_collector

            hours = int(request.args.get('hours', 1))
            averages = metrics_collector.get_average_metrics(hours=hours)

            if averages:
                return jsonify(averages)
            else:
                return jsonify({'error': 'No metrics available'})

        @self.app.route('/api/alerts')
        def api_alerts():
            """API endpoint for recent alerts"""
            from core.monitoring import alert_manager

            hours = int(request.args.get('hours', 24))
            alerts = alert_manager.get_recent_alerts(hours=hours)
            return jsonify({'alerts': alerts})

        @self.app.route('/monitoring')
        def monitoring():
            """System monitoring page"""
            return render_template('monitoring.html')

    def setup_socketio_events(self):
        """Setup SocketIO event handlers"""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            emit('status', {'message': 'Connected to PiSecure Dashboard'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            pass

        @self.socketio.on('request_update')
        def handle_update_request(data):
            """Handle update requests from clients"""
            update_type = data.get('type', 'all')

            if update_type == 'system' or update_type == 'all':
                emit('system_update', self.get_system_stats())

            if update_type == 'blockchain' or update_type == 'all':
                emit('blockchain_update', self.get_blockchain_stats())

            if update_type == 'mining' or update_type == 'all':
                emit('mining_update', self.get_mining_stats())

            if update_type == 'network' or update_type == 'all':
                emit('network_update', self.get_network_stats())

    def initialize_pisecure(self):
        """Initialize PiSecure components"""
        try:
            # Initialize blockchain
            self.blockchain = SignChain()

            # Initialize wallet (default) - lazy load network discovery
            self.wallet = SignWallet()

            print("✅ PiSecure components initialized (network discovery lazy-loaded)")

        except Exception as e:
            print(f"❌ Failed to initialize PiSecure: {e}")
            # Continue without PiSecure for basic system monitoring

    def load_network_config(self) -> Dict[str, Any]:
        """Load network configuration"""
        config_path = Path("/etc/pisecure/config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        print("✅ Monitoring thread started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    def _monitoring_loop(self):
        """Background monitoring loop with staggered updates"""
        while self.monitoring_active:
            try:
                self._update_counter += 1

                # Update system stats every cycle (5 seconds)
                self.system_stats = self.collect_system_stats()

                # Update blockchain stats every 2 cycles (10 seconds)
                if self._update_counter % 2 == 0:
                    self.blockchain_stats = self.collect_blockchain_stats()

                # Update mining stats every cycle (5 seconds)
                self.mining_stats = self.collect_mining_stats()

                # Update network stats every 4 cycles (20 seconds) - less frequent as it's expensive
                if self._update_counter % 4 == 0:
                    self.network_stats = self.collect_network_stats()

                # Emit updates via WebSocket
                self.socketio.emit('system_update', self.system_stats)
                self.socketio.emit('blockchain_update', self.blockchain_stats)
                self.socketio.emit('mining_update', self.mining_stats)
                self.socketio.emit('network_update', self.network_stats)

            except Exception as e:
                print(f"Monitoring error: {e}")

            time.sleep(5)  # Update every 5 seconds

    def collect_system_stats(self) -> Dict[str, Any]:
        """Collect system statistics"""
        try:
            # CPU usage - faster monitoring for better performance
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**2)  # MB
            memory_total = memory.total / (1024**2)  # MB

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB

            # Temperature (Pi-specific)
            temperature = self.get_cpu_temperature()

            # Network I/O
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent / (1024**2)  # MB
            bytes_recv = network.bytes_recv / (1024**2)  # MB

            # Uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_string = str(timedelta(seconds=int(uptime_seconds)))

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used': round(memory_used, 1),
                'memory_total': round(memory_total, 1),
                'disk_percent': disk_percent,
                'disk_used': round(disk_used, 1),
                'disk_total': round(disk_total, 1),
                'temperature': temperature,
                'network_sent': round(bytes_sent, 1),
                'network_recv': round(bytes_recv, 1),
                'uptime': uptime_string,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    def collect_blockchain_stats(self) -> Dict[str, Any]:
        """Collect blockchain statistics"""
        if not self.blockchain:
            return {'status': 'not_initialized'}

        try:
            info = self.blockchain.get_chain_info()

            return {
                'blocks': info.get('blocks', 0),
                'pending_transactions': info.get('pending_transactions', 0),
                'difficulty': info.get('difficulty', 0),
                'is_valid': info.get('is_valid', False),
                'network_health': info.get('network_health', {}),
                'latest_block': info.get('latest_block', {}),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    def collect_mining_stats(self) -> Dict[str, Any]:
        """Collect mining statistics from shared file"""
        try:
            # Try to read from shared mining stats file
            stats_file = Path("/var/lib/pisecure/mining_stats.json")
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = json.load(f)

                # Format uptime as human readable
                uptime_seconds = stats.get('uptime', 0)
                uptime_str = str(timedelta(seconds=int(uptime_seconds)))

                return {
                    'status': stats.get('status', 'unknown'),
                    'hashrate': stats.get('hashrate', 0),
                    'shares_submitted': stats.get('shares_submitted', 0),
                    'shares_accepted': stats.get('shares_accepted', 0),
                    'blocks_found': stats.get('blocks_found', 0),
                    'temperature': stats.get('temperature', 0),
                    'uptime': uptime_str,
                    'session_blocks': stats.get('session_blocks', 0),
                    'total_rewards': stats.get('total_rewards', 0),
                    'session_rewards': stats.get('session_rewards', 0),
                    'pending_transactions': stats.get('pending_transactions', 0),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Failed to read mining stats: {e}")

        # Fallback to placeholder if file doesn't exist or can't be read
        return {
            'status': 'unknown',
            'hashrate': 0,
            'shares_submitted': 0,
            'shares_accepted': 0,
            'blocks_found': 0,
            'temperature': 0,
            'uptime': '0s',
            'timestamp': datetime.now().isoformat()
        }

    def collect_network_stats(self) -> Dict[str, Any]:
        """Collect network statistics"""
        peer_discovery = self._get_peer_discovery()
        if not peer_discovery:
            return {'status': 'not_initialized'}

        try:
            peers = peer_discovery.get_active_peers()
            connection_candidates = peer_discovery.get_connection_candidates()

            return {
                'connected_peers': len(peers),
                'connection_candidates': len(connection_candidates),
                'total_known_peers': len(peer_discovery.known_peers),
                'peers': [{'address': f"{p.address}:{p.port}", 'capabilities': p.capabilities}
                         for p in peers[:10]],  # Show first 10 peers
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics with caching"""
        cache_key = 'system'
        current_time = time.time()

        # Return cached result if still fresh
        if (cache_key in self._stats_cache and
            current_time - self._stats_cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._stats_cache[cache_key]['data']

        # Collect fresh data
        stats = self.collect_system_stats()

        # Cache the result
        self._stats_cache[cache_key] = {
            'data': stats,
            'timestamp': current_time
        }

        return stats

    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get current blockchain statistics with caching"""
        cache_key = 'blockchain'
        current_time = time.time()

        # Return cached result if still fresh
        if (cache_key in self._stats_cache and
            current_time - self._stats_cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._stats_cache[cache_key]['data']

        # Collect fresh data
        stats = self.collect_blockchain_stats()

        # Cache the result
        self._stats_cache[cache_key] = {
            'data': stats,
            'timestamp': current_time
        }

        return stats

    def get_mining_stats(self) -> Dict[str, Any]:
        """Get current mining statistics with caching"""
        cache_key = 'mining'
        current_time = time.time()

        # Return cached result if still fresh
        if (cache_key in self._stats_cache and
            current_time - self._stats_cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._stats_cache[cache_key]['data']

        # Collect fresh data
        stats = self.collect_mining_stats()

        # Cache the result
        self._stats_cache[cache_key] = {
            'data': stats,
            'timestamp': current_time
        }

        return stats

    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network statistics with caching"""
        cache_key = 'network'
        current_time = time.time()

        # Return cached result if still fresh
        if (cache_key in self._stats_cache and
            current_time - self._stats_cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._stats_cache[cache_key]['data']

        # Collect fresh data
        stats = self.collect_network_stats()

        # Cache the result
        self._stats_cache[cache_key] = {
            'data': stats,
            'timestamp': current_time
        }

        return stats

    def _get_peer_discovery(self):
        """Lazy load peer discovery"""
        if self.peer_discovery is None:
            try:
                network_config = self.load_network_config()
                self.peer_discovery = DecentralizedPeerDiscovery(network_config)
            except Exception as e:
                print(f"⚠️ Failed to initialize peer discovery: {e}")
                return None
        return self.peer_discovery

    def get_wallet_balance(self, wallet_id: str) -> float:
        """Get wallet balance"""
        if self.blockchain:
            return self.blockchain.get_wallet_balance(wallet_id)
        return 0.0

    def get_recent_blocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent blocks"""
        if not self.blockchain:
            return []

        blocks = []
        start_index = max(0, len(self.blockchain.chain) - limit)

        for i in range(start_index, len(self.blockchain.chain)):
            block = self.blockchain.chain[i]
            blocks.append({
                'index': block.index,
                'hash': block.hash[:16] + '...',
                'transactions': len(block.transactions),
                'timestamp': block.timestamp,
                'nonce': block.nonce,
                'size': len(json.dumps(block.to_dict()))
            })

        return blocks[::-1]  # Most recent first

    def get_recent_transactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        if not self.blockchain:
            return []

        transactions = []

        # Get transactions from recent blocks
        for block in reversed(self.blockchain.chain[-5:]):  # Last 5 blocks
            for tx in reversed(block.transactions):
                if len(transactions) >= limit:
                    break

                tx_data = {
                    'hash': hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()[:16] + '...',
                    'type': tx.get('type', 'unknown'),
                    'timestamp': tx.get('timestamp', time.time()),
                    'block_index': block.index
                }

                # Add type-specific data
                if tx.get('type') == 'token_transfer':
                    tx_data.update({
                        'amount': tx.get('amount', 0),
                        'sender': tx.get('sender_address', '')[:16] + '...',
                        'recipient': tx.get('recipient_address', '')[:16] + '...'
                    })

                transactions.append(tx_data)

        return transactions

    def _get_peer_discovery(self):
        """Get or initialize peer discovery (lazy loading)"""
        if self.peer_discovery is None:
            try:
                from core.network import DecentralizedPeerDiscovery
                self.peer_discovery = DecentralizedPeerDiscovery()
            except Exception as e:
                print(f"Failed to initialize peer discovery: {e}")
                return None
        return self.peer_discovery

    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature (Pi-specific)"""
        try:
            # Try vcgencmd first (Pi standard)
            result = subprocess.run(['vcgencmd', 'measure_temp'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                # Parse "temp=45.2'C"
                if "temp=" in temp_str:
                    temp_value = temp_str.split('=')[1].split("'")[0]
                    return float(temp_value)

            # Fallback to thermal zone
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_milli = int(f.read().strip())
                return temp_milli / 1000.0

        except Exception:
            return None

    def _generate_wallet_name(self) -> str:
        """Generate a readable, unique wallet name using system information"""
        import platform
        import socket
        import secrets
        import hashlib

        try:
            # Get system information
            hostname = socket.gethostname().lower().replace('-', '').replace('_', '')[:8]  # Clean hostname, max 8 chars

            # Get platform info
            system = platform.system().lower()
            if system == 'linux':
                # Check if it's a Raspberry Pi
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read()
                        if 'Raspberry Pi' in cpuinfo:
                            prefix = 'pi'
                        else:
                            prefix = 'linux'
                except:
                    prefix = 'linux'
            elif system == 'darwin':
                prefix = 'mac'
            elif system == 'windows':
                prefix = 'win'
            else:
                prefix = 'host'

            # Generate unique suffix using multiple entropy sources
            entropy_sources = [
                str(socket.gethostbyname(socket.gethostname())),  # IP address
                str(platform.node()),  # Full hostname
                str(platform.machine()),  # Machine type
                secrets.token_hex(4)  # Random bytes
            ]

            # Create a hash of entropy sources for uniqueness
            entropy_string = '|'.join(entropy_sources)
            entropy_hash = hashlib.sha256(entropy_string.encode()).hexdigest()[:6]  # 6 char suffix

            # Create readable name: prefix-hostname-suffix
            if hostname and len(hostname) >= 3:
                name = f"{prefix}-{hostname}-{entropy_hash}"
            else:
                # Fallback if hostname is too short
                name = f"{prefix}-{entropy_hash}"

            # Ensure name is reasonable length and format
            name = name.replace(' ', '').replace('_', '-').lower()
            if len(name) > 32:  # Limit length
                name = name[:32]

            return name

        except Exception as e:
            # Fallback to simple random name
            return f"wallet-{secrets.token_hex(4)}"

    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Run the dashboard application"""
        print("🚀 Starting PiSecure Dashboard...")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Debug: {debug}")
        print()

        # Initialize PiSecure components
        self.initialize_pisecure()

        # Start monitoring
        self.start_monitoring()

        try:
            # Run with SocketIO
            self.socketio.run(self.app, host=host, port=port, debug=debug)

        except KeyboardInterrupt:
            print("\n⏹️  Shutting down PiSecure Dashboard...")
        finally:
            self.stop_monitoring()


def create_app():
    """Create and configure the Flask application"""
    dashboard = PiSecureDashboard()
    return dashboard.app, dashboard.socketio


if __name__ == '__main__':
    dashboard = PiSecureDashboard()
    dashboard.run()