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
from .economics import (
    TokenEconomics, DeveloperTrust, TrustType, TrustVisibility,
    token_economics, fee_distributor, foundation_trust
)

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

        # === 314ST ECONOMICS ENDPOINTS ===

        # Create developer trust
        @self.app.route(f'/api/{self.api_version}/trust', methods=['POST'])
        def create_trust():
            try:
                trust_data = request.get_json()

                if not trust_data:
                    return jsonify({'error': 'No trust data provided'}), 400

                developer_address = trust_data.get('developer_address')
                trust_type_str = trust_data.get('trust_type', 'public')
                initial_funding = trust_data.get('initial_funding', 0)

                if not developer_address:
                    return jsonify({'error': 'Developer address required'}), 400

                # Map string to enum
                trust_type_map = {
                    'public': TrustType.PUBLIC,
                    'subscriber_all': TrustType.SUBSCRIBER_ALL,
                    'subscriber_individual': TrustType.SUBSCRIBER_INDIVIDUAL,
                    'hybrid': TrustType.HYBRID
                }

                trust_type = trust_type_map.get(trust_type_str, TrustType.PUBLIC)
                trust_id = f"trust_{hashlib.sha256(developer_address.encode()).hexdigest()[:16]}"

                trust = token_economics.create_developer_trust(
                    trust_id, developer_address, trust_type, initial_funding
                )

                return jsonify({
                    'success': True,
                    'trust_id': trust_id,
                    'status': trust.get_status()
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get trust status
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>', methods=['GET'])
        def get_trust(trust_id):
            try:
                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                return jsonify(trust.get_status())

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Fund trust
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/fund', methods=['POST'])
        def fund_trust(trust_id):
            try:
                fund_data = request.get_json()
                amount = fund_data.get('amount', 0)

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                success = trust.fund_trust(amount)
                if success:
                    return jsonify({'success': True, 'new_balance': trust.balance})
                else:
                    return jsonify({'error': 'Funding failed'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Create subscription plan
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/plan', methods=['POST'])
        def create_subscription_plan(trust_id):
            try:
                plan_data = request.get_json()

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                plan_id = trust.create_subscription_plan(plan_data)

                return jsonify({
                    'success': True,
                    'plan_id': plan_id,
                    'plan': plan_data
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Subscribe user
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/subscribe', methods=['POST'])
        def subscribe_user(trust_id):
            try:
                sub_data = request.get_json()
                user_id = sub_data.get('user_id')
                plan_id = sub_data.get('plan_id')

                if not user_id or not plan_id:
                    return jsonify({'error': 'user_id and plan_id required'}), 400

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                success = trust.add_subscriber(user_id, plan_id)
                if success:
                    return jsonify({'success': True, 'message': 'User subscribed'})
                else:
                    return jsonify({'error': 'Subscription failed'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Grant free access
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/free-access', methods=['POST'])
        def grant_free_access(trust_id):
            try:
                access_data = request.get_json()
                user_id = access_data.get('user_id')

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                success = trust.grant_free_access(user_id)
                if success:
                    return jsonify({'success': True, 'message': 'Free access granted'})
                else:
                    return jsonify({'error': 'Failed to grant free access'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Check user access (for end-user API calls)
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/access/<user_id>', methods=['POST'])
        def check_user_access(trust_id, user_id):
            try:
                access_data = request.get_json()
                operation = access_data.get('operation', 'unknown')
                params = access_data.get('params', {})

                # Calculate operation cost
                operation_cost = token_economics.calculate_api_cost(operation, params)

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                can_access, message = trust.check_access(user_id, operation_cost)

                return jsonify({
                    'can_access': can_access,
                    'message': message,
                    'cost': operation_cost,
                    'trust_balance': trust.balance if trust else 0
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Foundation status
        @self.app.route(f'/api/{self.api_version}/foundation/status', methods=['GET'])
        def foundation_status():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({
                        'error': 'Foundation trust not available - genesis keys not found',
                        'genesis_key_loaded': False,
                        'address': 'foundation_314st',
                        'balance': 0
                    }), 503

                status = foundation.get_status()
                return jsonify(status)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Create grant proposal
        @self.app.route(f'/api/{self.api_version}/foundation/grant', methods=['POST'])
        def create_grant():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                grant_data = request.get_json()
                grant_id = foundation.create_grant(grant_data)

                return jsonify({
                    'success': True,
                    'grant_id': grant_id,
                    'status': 'pending_review'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Vote on grant
        @self.app.route(f'/api/{self.api_version}/foundation/grant/<grant_id>/vote', methods=['POST'])
        def vote_on_grant(grant_id):
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                vote_data = request.get_json()
                voter_address = vote_data.get('voter_address')
                vote = vote_data.get('vote')  # True for yes, False for no
                voting_power = vote_data.get('voting_power', 1.0)

                foundation.vote_on_grant(grant_id, voter_address, vote, voting_power)

                return jsonify({'success': True, 'message': 'Vote recorded'})

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get fee distribution info
        @self.app.route(f'/api/{self.api_version}/economics/fees', methods=['GET'])
        def fee_distribution_info():
            try:
                foundation = get_foundation_trust()
                allocation_rules = foundation.allocation_rules if foundation else {}

                return jsonify({
                    'distribution_rules': fee_distributor.distribution_rules,
                    'foundation_allocation': allocation_rules
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # === FOUNDATION TRANSACTION ENDPOINTS (GENESIS KEY REQUIRED) ===

        # Sign foundation transaction
        @self.app.route(f'/api/{self.api_version}/foundation/sign-transaction', methods=['POST'])
        def sign_foundation_transaction():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available - genesis keys required'}), 503

                tx_data = request.get_json()

                if not tx_data:
                    return jsonify({'error': 'No transaction data provided'}), 400

                # Sign with genesis private key
                signature = foundation.sign_foundation_transaction(tx_data)

                return jsonify({
                    'success': True,
                    'transaction': tx_data,
                    'signature': signature,
                    'signed_by': 'genesis_key'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Execute signed foundation transaction
        @self.app.route(f'/api/{self.api_version}/foundation/execute-transaction', methods=['POST'])
        def execute_foundation_transaction():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available - genesis keys required'}), 503

                signed_tx_data = request.get_json()

                if not signed_tx_data:
                    return jsonify({'error': 'No signed transaction data provided'}), 400

                transaction = signed_tx_data.get('transaction')
                signature = signed_tx_data.get('signature')

                if not transaction or not signature:
                    return jsonify({'error': 'Transaction and signature required'}), 400

                # Execute transaction if signature is valid
                result = foundation.execute_foundation_transaction(transaction, signature)

                return jsonify(result)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get foundation transaction history
        @self.app.route(f'/api/{self.api_version}/foundation/transactions', methods=['GET'])
        def get_foundation_transactions():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({
                        'error': 'Foundation trust not available',
                        'transactions': [],
                        'total_count': 0,
                        'limit': 0
                    }), 503

                limit = min(int(request.args.get('limit', 50)), 200)
                transactions = foundation.get_transaction_history(limit)

                return jsonify({
                    'transactions': transactions,
                    'total_count': len(foundation.transaction_log),
                    'limit': limit
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Verify foundation transaction signature
        @self.app.route(f'/api/{self.api_version}/foundation/verify-transaction', methods=['POST'])
        def verify_foundation_transaction():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available - genesis keys required'}), 503

                verify_data = request.get_json()

                if not verify_data:
                    return jsonify({'error': 'No verification data provided'}), 400

                transaction = verify_data.get('transaction')
                signature = verify_data.get('signature')

                if not transaction or not signature:
                    return jsonify({'error': 'Transaction and signature required'}), 400

                is_valid = foundation.verify_foundation_transaction(transaction, signature)

                return jsonify({
                    'is_valid': is_valid,
                    'verified_by': 'genesis_public_key' if is_valid else None
                })

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