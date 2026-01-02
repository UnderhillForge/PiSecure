"""
PiSecure REST API Server
========================

RESTful API server that exposes PiSecure blockchain functionality
to external applications and client libraries.

This server runs on PiSecure nodes and provides HTTP endpoints for:
- Blockchain queries and exploration
- Transaction submission and tracking
- Wallet operations
- Network status and peer information
- Real-time data streaming (WebSocket)

Security features:
- Rate limiting
- Request authentication (optional)
- CORS support for web applications
- Input validation and sanitization
"""

import time
import json
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import secrets

# PiSecure imports
from ..core.blockchain import SignChain
from ..core.wallet import SignWallet
from ..network.discovery import PeerDiscovery
from ..updates.auth import UpdateAuthority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlockchainAPI:
    """
    REST API server for PiSecure blockchain operations.

    Provides HTTP endpoints that allow external applications to:
    - Query blockchain state and history
    - Submit transactions to the network
    - Create and manage wallets
    - Monitor network health and peers
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 3142,
                 blockchain: Optional[SignChain] = None,
                 enable_cors: bool = True, rate_limit: str = "100 per minute"):
        """
        Initialize the Blockchain API server.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 3142)
            blockchain: SignChain instance (created if None)
            enable_cors: Enable CORS for web applications
            rate_limit: Rate limiting rule
        """
        self.host = host
        self.port = port
        self.rate_limit = rate_limit

        # Initialize Flask app
        self.app = Flask(__name__)
        if enable_cors:
            CORS(self.app)

        # Initialize rate limiter
        self.limiter = Limiter(
            get_remote_address,
            app=self.app,
            default_limits=[rate_limit]
        )

        # Initialize PiSecure components
        self.blockchain = blockchain or SignChain()
        self.wallet = SignWallet()
        self.peer_discovery = PeerDiscovery()
        self.update_authority = UpdateAuthority()

        # Setup routes
        self._setup_routes()

        # API metadata
        self.api_version = "v1"
        self.start_time = time.time()

    def _setup_routes(self):
        """Setup all API routes."""

        # Health check
        @self.app.route(f'/api/{self.api_version}/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'uptime': time.time() - self.start_time,
                'version': '0.1.0'
            })

        # Blockchain information
        @self.app.route(f'/api/{self.api_version}/blockchain/info', methods=['GET'])
        def blockchain_info():
            info = self.blockchain.get_chain_info()
            return jsonify({
                'blocks': info['blocks'],
                'pending_transactions': info['pending_transactions'],
                'difficulty': info['difficulty'],
                'is_valid': info['is_valid'],
                'network_health': info['network_health'],
                'latest_block': info.get('latest_block')
            })

        # Get specific block
        @self.app.route(f'/api/{self.api_version}/blockchain/block/<int:block_index>', methods=['GET'])
        def get_block(block_index):
            try:
                if 0 <= block_index < len(self.blockchain.chain):
                    block = self.blockchain.chain[block_index]
                    return jsonify(block)
                else:
                    return jsonify({'error': 'Block not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get latest blocks
        @self.app.route(f'/api/{self.api_version}/blockchain/blocks', methods=['GET'])
        def get_blocks():
            limit = min(int(request.args.get('limit', 10)), 100)
            offset = int(request.args.get('offset', 0))

            try:
                blocks = self.blockchain.chain[offset:offset + limit]
                return jsonify(blocks)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get transaction by hash
        @self.app.route(f'/api/{self.api_version}/blockchain/transaction/<tx_hash>', methods=['GET'])
        def get_transaction(tx_hash):
            try:
                # Search through all blocks for the transaction
                for block in reversed(self.blockchain.chain):
                    for tx in block.transactions:
                        if tx.get('hash') == tx_hash or tx.get('signature', '').startswith(tx_hash[:16]):
                            return jsonify(tx)

                return jsonify({'error': 'Transaction not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get wallet balance
        @self.app.route(f'/api/{self.api_version}/wallet/<address>/balance', methods=['GET'])
        def wallet_balance(address):
            try:
                balance = self.blockchain.get_wallet_balance(address)
                return jsonify({'address': address, 'balance': balance})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get wallet transactions
        @self.app.route(f'/api/{self.api_version}/wallet/<address>/transactions', methods=['GET'])
        def wallet_transactions(address):
            try:
                limit = min(int(request.args.get('limit', 20)), 100)
                transactions = self.blockchain.get_wallet_transactions(address)
                return jsonify({
                    'address': address,
                    'transactions': transactions[-limit:]  # Most recent first
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Submit transaction
        @self.app.route(f'/api/{self.api_version}/transaction', methods=['POST'])
        def submit_transaction():
            try:
                tx_data = request.get_json()

                if not tx_data:
                    return jsonify({'error': 'No transaction data provided'}), 400

                # Validate transaction structure
                required_fields = ['type', 'data', 'signature', 'timestamp']
                for field in required_fields:
                    if field not in tx_data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400

                # Add transaction to blockchain
                tx_hash = self.blockchain.add_transaction(tx_data)

                return jsonify({
                    'success': True,
                    'transaction_hash': tx_hash,
                    'status': 'submitted'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Create wallet
        @self.app.route(f'/api/{self.api_version}/wallet', methods=['POST'])
        def create_wallet():
            try:
                wallet_data = request.get_json() or {}

                wallet_name = wallet_data.get('name', f'api_wallet_{secrets.token_hex(4)}')
                display_name = wallet_data.get('display_name', f'API Wallet {wallet_name}')

                result = self.wallet.create_wallet(wallet_name, display_name)

                if result['success']:
                    return jsonify({
                        'success': True,
                        'wallet_id': result['wallet_id'],
                        'address': result['address'],
                        'name': wallet_name
                    })
                else:
                    return jsonify({'success': False, 'error': result.get('error')}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # List wallets
        @self.app.route(f'/api/{self.api_version}/wallets', methods=['GET'])
        def list_wallets():
            try:
                wallets = self.wallet.list_wallets()
                return jsonify({'wallets': wallets})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Network peers
        @self.app.route(f'/api/{self.api_version}/network/peers', methods=['GET'])
        def network_peers():
            try:
                peers = self.peer_discovery.get_known_peers()
                return jsonify({
                    'peers': list(peers.keys()),
                    'count': len(peers)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Network status
        @self.app.route(f'/api/{self.api_version}/network/status', methods=['GET'])
        def network_status():
            try:
                status = {
                    'connected_peers': len(self.peer_discovery.get_connected_peers()),
                    'known_peers': len(self.peer_discovery.get_known_peers()),
                    'node_id': self.peer_discovery.node_id,
                    'listening_port': self.port
                }
                return jsonify(status)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Update verification
        @self.app.route(f'/api/{self.api_version}/update/verify', methods=['POST'])
        def verify_update():
            try:
                update_data = request.get_json()

                if not update_data:
                    return jsonify({'error': 'No update data provided'}), 400

                manifest = update_data.get('manifest', {})
                signatures = update_data.get('signatures', [])

                result = self.update_authority.verify_update_signature(manifest, signatures)

                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # API documentation
        @self.app.route(f'/api/{self.api_version}/docs', methods=['GET'])
        def api_docs():
            docs = {
                'version': self.api_version,
                'base_url': f'http://{self.host}:{self.port}/api/{self.api_version}',
                'endpoints': {
                    'health': {'method': 'GET', 'path': '/health', 'description': 'API health check'},
                    'blockchain_info': {'method': 'GET', 'path': '/blockchain/info', 'description': 'Blockchain status'},
                    'get_block': {'method': 'GET', 'path': '/blockchain/block/<index>', 'description': 'Get specific block'},
                    'get_blocks': {'method': 'GET', 'path': '/blockchain/blocks', 'description': 'Get latest blocks'},
                    'get_transaction': {'method': 'GET', 'path': '/blockchain/transaction/<hash>', 'description': 'Get transaction by hash'},
                    'wallet_balance': {'method': 'GET', 'path': '/wallet/<address>/balance', 'description': 'Get wallet balance'},
                    'wallet_transactions': {'method': 'GET', 'path': '/wallet/<address>/transactions', 'description': 'Get wallet transaction history'},
                    'submit_transaction': {'method': 'POST', 'path': '/transaction', 'description': 'Submit transaction to network'},
                    'create_wallet': {'method': 'POST', 'path': '/wallet', 'description': 'Create new wallet'},
                    'list_wallets': {'method': 'GET', 'path': '/wallets', 'description': 'List available wallets'},
                    'network_peers': {'method': 'GET', 'path': '/network/peers', 'description': 'Get known network peers'},
                    'network_status': {'method': 'GET', 'path': '/network/status', 'description': 'Get network status'},
                    'verify_update': {'method': 'POST', 'path': '/update/verify', 'description': 'Verify update package signatures'}
                },
                'client_libraries': {
                    'javascript': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/javascript',
                    'typescript': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/typescript',
                    'python': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/python'
                }
            }
            return jsonify(docs)

    def run(self, debug: bool = False):
        """
        Start the API server.

        Args:
            debug: Enable debug mode
        """
        logger.info(f"🚀 Starting PiSecure API Server on {self.host}:{self.port}")
        logger.info(f"📚 API Documentation: http://{self.host}:{self.port}/api/{self.api_version}/docs")

        self.app.run(
            host=self.host,
            port=self.port,
            debug=debug,
            threaded=True
        )


# Standalone server runner
def run_server():
    """Run the API server (for command line usage)"""
    import argparse

    parser = argparse.ArgumentParser(description='PiSecure Blockchain API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=3142, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    api = BlockchainAPI(host=args.host, port=args.port)
    api.run(debug=args.debug)


if __name__ == '__main__':
    run_server()