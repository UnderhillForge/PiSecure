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
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # PiSecure components
        self.blockchain = None
        self.peer_discovery = None
        self.wallet = None

        # Dashboard data
        self.system_stats = {}
        self.mining_stats = {}
        self.network_stats = {}
        self.blockchain_stats = {}

        # Monitoring threads
        self.monitoring_thread = None
        self.monitoring_active = False

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

            # Initialize peer discovery
            network_config = self.load_network_config()
            self.peer_discovery = DecentralizedPeerDiscovery(network_config)

            # Initialize wallet (default)
            self.wallet = SignWallet()

            print("✅ PiSecure components initialized")

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
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Update system stats
                self.system_stats = self.collect_system_stats()

                # Update blockchain stats if available
                if self.blockchain:
                    self.blockchain_stats = self.collect_blockchain_stats()

                # Update mining stats (placeholder)
                self.mining_stats = self.collect_mining_stats()

                # Update network stats
                if self.peer_discovery:
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
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

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
        """Collect mining statistics"""
        # Placeholder - would integrate with actual mining process
        return {
            'status': 'active',  # active, paused, stopped
            'hashrate': 2.3,  # MH/s
            'shares_submitted': 145,
            'shares_accepted': 142,
            'blocks_found': 5,
            'temperature': 45.2,
            'uptime': '2h 15m',
            'timestamp': datetime.now().isoformat()
        }

    def collect_network_stats(self) -> Dict[str, Any]:
        """Collect network statistics"""
        if not self.peer_discovery:
            return {'status': 'not_initialized'}

        try:
            peers = self.peer_discovery.get_active_peers()
            connection_candidates = self.peer_discovery.get_connection_candidates()

            return {
                'connected_peers': len(peers),
                'connection_candidates': len(connection_candidates),
                'total_known_peers': len(self.peer_discovery.known_peers),
                'peers': [{'address': f"{p.address}:{p.port}", 'capabilities': p.capabilities}
                         for p in peers[:10]],  # Show first 10 peers
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        return self.system_stats or self.collect_system_stats()

    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get current blockchain statistics"""
        return self.blockchain_stats or self.collect_blockchain_stats()

    def get_mining_stats(self) -> Dict[str, Any]:
        """Get current mining statistics"""
        return self.mining_stats or self.collect_mining_stats()

    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network statistics"""
        return self.network_stats or self.collect_network_stats()

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