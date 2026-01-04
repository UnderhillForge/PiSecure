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
import threading
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
from ..core.nat_traversal import node_discovery
from ..network.discovery import PeerDiscovery
from ..core.p2p_sync import P2PSyncManager
from ..updates.auth import UpdateAuthority
from .economics import (
    TokenEconomics, DeveloperTrust, TrustType, TrustVisibility,
    token_economics, fee_distributor, foundation_trust, get_foundation_trust
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

        # API metadata (must be set before routes)
        self.api_version = "v1"
        self.start_time = time.time()

        # Initialize PiSecure components
        self.blockchain = blockchain or SignChain()
        self.wallet = SignWallet()
        self.peer_discovery = PeerDiscovery()
        self.p2p_sync = P2PSyncManager(self.blockchain, self.peer_discovery)
        self.update_authority = UpdateAuthority()

        # Setup routes
        self._setup_routes()

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

                # Trigger network discovery after transaction submission
                try:
                    from pisecure.core.nat_traversal import node_discovery
                    import threading
                    threading.Thread(target=self._trigger_discovery_on_transaction, daemon=True).start()
                except Exception as e:
                    logger.warning(f"Failed to trigger discovery after transaction: {e}")

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

        # Transfer from trust to wallet
        @self.app.route(f'/api/{self.api_version}/trust/<trust_id>/transfer-to-wallet', methods=['POST'])
        def transfer_trust_to_wallet(trust_id):
            try:
                transfer_data = request.get_json()

                if not transfer_data:
                    return jsonify({'error': 'No transfer data provided'}), 400

                wallet_address = transfer_data.get('wallet_address')
                amount = transfer_data.get('amount', 0)
                reason = transfer_data.get('reason', '')

                if not wallet_address or amount <= 0:
                    return jsonify({'error': 'wallet_address and valid amount required'}), 400

                trust = token_economics.get_trust(trust_id)
                if not trust:
                    return jsonify({'error': 'Trust not found'}), 404

                result = trust.transfer_to_wallet(wallet_address, amount, reason)

                if result.get('success'):
                    return jsonify(result)
                else:
                    return jsonify({'error': result.get('error', 'Transfer failed')}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Transfer from wallet to foundation
        @self.app.route(f'/api/{self.api_version}/foundation/contribute', methods=['POST'])
        def contribute_to_foundation():
            try:
                contribution_data = request.get_json()

                if not contribution_data:
                    return jsonify({'error': 'No contribution data provided'}), 400

                wallet_address = contribution_data.get('wallet_address')
                amount = contribution_data.get('amount', 0)
                purpose = contribution_data.get('purpose', 'community_contribution')

                if not wallet_address or amount <= 0:
                    return jsonify({'error': 'wallet_address and valid amount required'}), 400

                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                success = foundation.receive_from_wallet(wallet_address, amount, purpose)

                if success:
                    return jsonify({
                        'success': True,
                        'contribution_amount': amount,
                        'purpose': purpose,
                        'foundation_balance': foundation.balance
                    })
                else:
                    return jsonify({'error': 'Contribution failed'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Transfer from foundation to wallet
        @self.app.route(f'/api/{self.api_version}/foundation/transfer-to-wallet', methods=['POST'])
        def transfer_foundation_to_wallet():
            try:
                transfer_data = request.get_json()

                if not transfer_data:
                    return jsonify({'error': 'No transfer data provided'}), 400

                wallet_address = transfer_data.get('wallet_address')
                amount = transfer_data.get('amount', 0)
                purpose = transfer_data.get('purpose', 'community_reward')

                if not wallet_address or amount <= 0:
                    return jsonify({'error': 'wallet_address and valid amount required'}), 400

                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available - genesis keys required'}), 503

                result = foundation.transfer_to_wallet(wallet_address, amount, purpose)

                if result.get('success'):
                    return jsonify(result)
                else:
                    return jsonify({'error': result.get('error', 'Transfer failed')}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Register bootstrap operator
        @self.app.route(f'/api/{self.api_version}/bootstrap/register', methods=['POST'])
        def register_bootstrap_operator():
            try:
                operator_data = request.get_json()

                if not operator_data:
                    return jsonify({'error': 'No operator data provided'}), 400

                operator_id = operator_data.get('operator_id')
                if not operator_id:
                    return jsonify({'error': 'operator_id required'}), 400

                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                success = foundation.register_bootstrap_operator(operator_id, operator_data)

                if success:
                    return jsonify({
                        'success': True,
                        'operator_id': operator_id,
                        'message': 'Bootstrap operator registered'
                    })
                else:
                    return jsonify({'error': 'Registration failed'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Update bootstrap operator metrics
        @self.app.route(f'/api/{self.api_version}/bootstrap/<operator_id>/metrics', methods=['POST'])
        def update_bootstrap_metrics(operator_id):
            try:
                metrics_data = request.get_json()

                if not metrics_data:
                    return jsonify({'error': 'No metrics data provided'}), 400

                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                success = foundation.update_bootstrap_metrics(operator_id, metrics_data)

                if success:
                    return jsonify({
                        'success': True,
                        'operator_id': operator_id,
                        'message': 'Metrics updated'
                    })
                else:
                    return jsonify({'error': 'Metrics update failed'}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get bootstrap funding status
        @self.app.route(f'/api/{self.api_version}/bootstrap/funding-status', methods=['GET'])
        def get_bootstrap_funding_status():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available'}), 503

                status = foundation.get_bootstrap_funding_status()
                return jsonify(status)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Allocate bootstrap funding (admin/governance function)
        @self.app.route(f'/api/{self.api_version}/bootstrap/allocate-funding', methods=['POST'])
        def allocate_bootstrap_funding():
            try:
                foundation = get_foundation_trust()
                if foundation is None:
                    return jsonify({'error': 'Foundation trust not available - genesis keys required'}), 503

                allocations = foundation.allocate_bootstrap_funding()

                return jsonify({
                    'success': True,
                    'allocations': allocations,
                    'total_operators_funded': len(allocations),
                    'message': f'Funding allocated to {len(allocations)} bootstrap operators'
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

        # === PiNS (Pi Name System) ENDPOINTS ===

        # Check name availability
        @self.app.route(f'/api/{self.api_version}/names/check/<name>', methods=['GET'])
        def check_name_availability(name):
            try:
                available = self.blockchain.check_name_availability(name)
                return jsonify({
                    'name': name,
                    'available': available,
                    'registration_fee': 5.0 if available else None
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Resolve name to address
        @self.app.route(f'/api/{self.api_version}/names/<name>', methods=['GET'])
        def resolve_name(name):
            try:
                address = self.blockchain.resolve_name(name)
                if address:
                    name_info = self.blockchain.get_name_info(name)
                    return jsonify({
                        'name': name,
                        'address': address,
                        'registered_at': name_info.get('registered_at'),
                        'block_index': name_info.get('block_index'),
                        'tx_hash': name_info.get('tx_hash')
                    })
                else:
                    return jsonify({'error': f'Name "{name}" not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Register name
        @self.app.route(f'/api/{self.api_version}/names/register', methods=['POST'])
        def register_name():
            try:
                reg_data = request.get_json()

                if not reg_data:
                    return jsonify({'error': 'No registration data provided'}), 400

                name = reg_data.get('name')
                wallet_address = reg_data.get('wallet_address')

                if not name or not wallet_address:
                    return jsonify({'error': 'Name and wallet_address required'}), 400

                # Check balance for fee
                balance = self.blockchain.get_wallet_balance(wallet_address)
                if balance < 5.0:
                    return jsonify({
                        'error': f'Insufficient balance: {balance} < 5.0 tokens',
                        'current_balance': balance,
                        'required': 5.0
                    }), 400

                # Register name
                tx_hash = self.blockchain.register_name(name, wallet_address)

                return jsonify({
                    'success': True,
                    'name': name,
                    'address': wallet_address,
                    'transaction_hash': tx_hash,
                    'fee_deducted': 5.0,
                    'status': 'pending_mining'
                })

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get wallet names
        @self.app.route(f'/api/{self.api_version}/names/wallet/<wallet_address>', methods=['GET'])
        def get_wallet_names(wallet_address):
            try:
                names = self.blockchain.get_wallet_names(wallet_address)
                return jsonify({
                    'wallet_address': wallet_address,
                    'names': names,
                    'count': len(names)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # List all registered names
        @self.app.route(f'/api/{self.api_version}/names', methods=['GET'])
        def list_registered_names():
            try:
                limit = min(int(request.args.get('limit', 50)), 200)
                offset = int(request.args.get('offset', 0))

                all_names = self.blockchain.get_registered_names()
                names_subset = all_names[offset:offset + limit]

                names_info = []
                for name in names_subset:
                    name_info = self.blockchain.get_name_info(name)
                    names_info.append({
                        'name': name,
                        'address': name_info.get('address'),
                        'registered_at': name_info.get('registered_at'),
                        'block_index': name_info.get('block_index')
                    })

                return jsonify({
                    'names': names_info,
                    'total_count': len(all_names),
                    'limit': limit,
                    'offset': offset
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # === BOOTSTRAP NODE ENDPOINTS ===

        # Bootstrap peer discovery
        @self.app.route(f'/api/{self.api_version}/bootstrap/peers', methods=['GET'])
        def get_bootstrap_peers():
            """Serve initial peer list for new nodes joining the network"""
            try:
                # Get verified active peers for bootstrapping
                bootstrap_peers = self._get_verified_bootstrap_peers()

                # Add this node as a bootstrap reference
                bootstrap_info = {
                    'peers': bootstrap_peers,
                    'bootstrap_node': {
                        'host': self.host,
                        'port': self.port,
                        'node_id': self.peer_discovery.node_id,
                        'capabilities': ['api', 'p2p_sync', 'mining']
                    },
                    'network_info': {
                        'total_blocks': len(self.blockchain.chain),
                        'active_nodes': len(bootstrap_peers),
                        'protocol_version': '1.0',
                        'genesis_hash': self.blockchain.chain[0].hash if self.blockchain.chain else None
                    },
                    'last_updated': time.time(),
                    'ttl': 300  # Cache for 5 minutes
                }

                return jsonify(bootstrap_info)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Network statistics (public dashboard)
        @self.app.route(f'/api/{self.api_version}/network/stats', methods=['GET'])
        def network_statistics():
            """Public network health and statistics dashboard"""
            try:
                stats = self._calculate_network_stats()

                return jsonify({
                    'network_health': stats,
                    'mining_stats': self._get_mining_stats(),
                    'geographic_distribution': self._get_node_geography(),
                    'protocol_info': {
                        'version': '1.0',
                        'features': ['p2p_sync', 'mining_teams', 'hardware_verification'],
                        'consensus': 'proof_of_work'
                    },
                    'last_updated': time.time()
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Node registration for enhanced discovery
        @self.app.route(f'/api/{self.api_version}/nodes/register', methods=['POST'])
        def register_node():
            """Allow nodes to register themselves for better network discovery"""
            try:
                node_data = request.get_json()

                if not node_data:
                    return jsonify({'error': 'No node data provided'}), 400

                required_fields = ['address', 'port', 'node_id']
                for field in required_fields:
                    if field not in node_data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400

                # Validate node information
                node_id = node_data['node_id']
                address = node_data['address']
                port = node_data['port']

                # Basic validation
                if not isinstance(port, int) or port < 1 or port > 65535:
                    return jsonify({'error': 'Invalid port number'}), 400

                # Register or update node
                registered_node = {
                    'node_id': node_id,
                    'address': address,
                    'port': port,
                    'capabilities': node_data.get('capabilities', []),
                    'hashrate': node_data.get('hashrate', 0),
                    'location': node_data.get('location', 'unknown'),
                    'is_mining': node_data.get('is_mining', False),
                    'registered_at': time.time(),
                    'last_seen': time.time(),
                    'version': node_data.get('version', 'unknown')
                }

                # Store in registered nodes (in production, use database)
                if not hasattr(self, 'registered_nodes'):
                    self.registered_nodes = {}

                self.registered_nodes[node_id] = registered_node

                # Update peer discovery
                try:
                    self.peer_discovery.add_peer(
                        peer_id=node_id,
                        address=address,
                        port=port,
                        capabilities=registered_node['capabilities']
                    )
                except Exception as e:
                    logger.warning(f"Failed to update peer discovery: {e}")

                logger.info(f"✅ Registered node: {node_id} at {address}:{port}")

                return jsonify({
                    'success': True,
                    'node_id': node_id,
                    'registered_at': registered_node['registered_at'],
                    'bootstrap_peers': len(self._get_verified_bootstrap_peers())
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Node heartbeat/status updates
        @self.app.route(f'/api/{self.api_version}/nodes/heartbeat', methods=['POST'])
        def node_heartbeat():
            """Receive heartbeat from registered nodes"""
            try:
                heartbeat_data = request.get_json()

                if not heartbeat_data or 'node_id' not in heartbeat_data:
                    return jsonify({'error': 'node_id required'}), 400

                node_id = heartbeat_data['node_id']

                if hasattr(self, 'registered_nodes') and node_id in self.registered_nodes:
                    # Update last seen time and status
                    node_info = self.registered_nodes[node_id]
                    node_info['last_seen'] = time.time()
                    node_info.update(heartbeat_data)  # Update any provided fields

                    return jsonify({'success': True, 'updated': True})
                else:
                    return jsonify({'error': 'Node not registered'}), 404

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Get registered nodes (dashboard endpoint)
        @self.app.route(f'/api/{self.api_version}/nodes', methods=['GET'])
        def get_registered_nodes():
            """Get list of registered nodes for dashboard"""
            try:
                if not hasattr(self, 'registered_nodes'):
                    return jsonify({'nodes': [], 'total': 0})

                current_time = time.time()
                active_nodes = []
                inactive_nodes = []

                for node_id, node_info in self.registered_nodes.items():
                    last_seen = node_info.get('last_seen', 0)
                    is_active = current_time - last_seen < 3600  # Active within 1 hour

                    node_data = {
                        'node_id': node_id,
                        'address': node_info.get('address'),
                        'port': node_info.get('port'),
                        'capabilities': node_info.get('capabilities', []),
                        'hashrate': node_info.get('hashrate', 0),
                        'location': node_info.get('location', 'unknown'),
                        'is_mining': node_info.get('is_mining', False),
                        'registered_at': node_info.get('registered_at'),
                        'last_seen': last_seen,
                        'version': node_info.get('version', 'unknown'),
                        'status': 'active' if is_active else 'inactive'
                    }

                    if is_active:
                        active_nodes.append(node_data)
                    else:
                        inactive_nodes.append(node_data)

                # Sort active nodes by last seen (most recent first)
                active_nodes.sort(key=lambda x: x['last_seen'], reverse=True)

                return jsonify({
                    'nodes': active_nodes + inactive_nodes,
                    'total': len(self.registered_nodes),
                    'active': len(active_nodes),
                    'inactive': len(inactive_nodes)
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # === MINING ENDPOINTS ===

        # Start mining
        @self.app.route(f'/api/{self.api_version}/mining/start', methods=['POST'])
        def start_mining():
            try:
                mine_data = request.get_json() or {}
                wallet_address = mine_data.get('wallet_address')

                if not wallet_address:
                    # Try to get from config
                    try:
                        import json as json_lib
                        with open('/etc/pisecure/config.json', 'r') as f:
                            config = json_lib.load(f)
                        wallet_address = config.get('mining', {}).get('wallet_address')
                    except:
                        pass

                if not wallet_address:
                    return jsonify({'error': 'No wallet address provided or configured'}), 400

                # For API, we can't actually start background mining threads
                # This would need to be handled by the system mining service
                return jsonify({
                    'success': True,
                    'message': 'Mining start requested',
                    'wallet_address': wallet_address,
                    'note': 'Use systemd service for persistent mining'
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Stop mining
        @self.app.route(f'/api/{self.api_version}/mining/stop', methods=['POST'])
        def stop_mining():
            try:
                return jsonify({
                    'success': True,
                    'message': 'Mining stop requested',
                    'note': 'Use systemd service to control mining'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Mining status
        @self.app.route(f'/api/{self.api_version}/mining/status', methods=['GET'])
        def mining_status():
            try:
                # Get basic mining stats from blockchain
                chain_info = self.blockchain.get_chain_info()
                latest_block = chain_info.get('latest_block', {})

                # Calculate rough mining stats
                mining_stats = {
                    'is_mining': False,  # Can't determine from API
                    'blocks_mined': chain_info.get('blocks', 0),
                    'current_difficulty': chain_info.get('difficulty', 4),
                    'network_hashrate': 'unknown',  # Would need mining service
                    'pending_transactions': chain_info.get('pending_transactions', 0),
                    'latest_block_height': latest_block.get('index', 0),
                    'latest_block_time': latest_block.get('timestamp'),
                    'reward_per_block': self.blockchain.calculate_mining_reward(latest_block, {})
                }

                return jsonify(mining_stats)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # === ADVANCED WALLET ENDPOINTS ===

        # Sign transaction
        @self.app.route(f'/api/{self.api_version}/wallet/sign-transaction', methods=['POST'])
        def sign_transaction():
            try:
                sign_data = request.get_json()

                if not sign_data:
                    return jsonify({'error': 'No signing data provided'}), 400

                wallet_id = sign_data.get('wallet_id')
                transaction = sign_data.get('transaction')

                if not wallet_id or not transaction:
                    return jsonify({'error': 'wallet_id and transaction required'}), 400

                # Load wallet and sign
                wallet = SignWallet(f"/var/lib/pisecure/wallets/{wallet_id}.json")
                signature = wallet.sign_transaction(transaction)

                if signature:
                    transaction['signature'] = signature
                    return jsonify({
                        'success': True,
                        'transaction': transaction,
                        'signature': signature
                    })
                else:
                    return jsonify({'error': 'Failed to sign transaction'}), 500

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Export wallet (public info only)
        @self.app.route(f'/api/{self.api_version}/wallet/<wallet_id>/export', methods=['GET'])
        def export_wallet(wallet_id):
            try:
                wallet = SignWallet()
                wallet_data = wallet.load_wallet(wallet_id)

                if 'error' in wallet_data:
                    return jsonify({'error': wallet_data['error']}), 404

                # Export public information only (no private keys)
                public_export = {
                    'wallet_id': wallet_data.get('wallet_id'),
                    'name': wallet_data.get('name'),
                    'address': wallet_data.get('address'),
                    'balance': wallet_data.get('balance', 0),
                    'created_at': wallet_data.get('created_at'),
                    'transaction_count': len(wallet_data.get('transactions', []))
                }

                return jsonify(public_export)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # === UTILITY ENDPOINTS ===

        # System information
        @self.app.route(f'/api/{self.api_version}/system/info', methods=['GET'])
        def system_info():
            try:
                import psutil
                import platform

                system_stats = {
                    'hostname': platform.node(),
                    'platform': platform.platform(),
                    'python_version': platform.python_version(),
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory': {
                        'total': psutil.virtual_memory().total,
                        'available': psutil.virtual_memory().available,
                        'percent': psutil.virtual_memory().percent
                    },
                    'disk': {
                        'total': psutil.disk_usage('/').total,
                        'free': psutil.disk_usage('/').free,
                        'percent': psutil.disk_usage('/').percent
                    },
                    'uptime': psutil.boot_time(),
                    'pisecure_version': '0.1.0'
                }

                return jsonify(system_stats)

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Network discovery
        @self.app.route(f'/api/{self.api_version}/network/discover', methods=['POST'])
        def network_discovery():
            try:
                # Trigger network discovery
                discovery_result = self.peer_discovery.discover_peers()

                return jsonify({
                    'success': True,
                    'peers_discovered': len(discovery_result.get('new_peers', [])),
                    'total_known_peers': len(self.peer_discovery.get_known_peers()),
                    'result': discovery_result
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
                    # Core System
                    'health': {'method': 'GET', 'path': '/health', 'description': 'API health check'},
                    'system_info': {'method': 'GET', 'path': '/system/info', 'description': 'System information and stats'},

                    # Blockchain
                    'blockchain_info': {'method': 'GET', 'path': '/blockchain/info', 'description': 'Blockchain status and network health'},
                    'get_block': {'method': 'GET', 'path': '/blockchain/block/<index>', 'description': 'Get specific block by index'},
                    'get_blocks': {'method': 'GET', 'path': '/blockchain/blocks', 'description': 'Get latest blocks with pagination'},
                    'get_transaction': {'method': 'GET', 'path': '/blockchain/transaction/<hash>', 'description': 'Get transaction by hash'},

                    # Wallets
                    'create_wallet': {'method': 'POST', 'path': '/wallet', 'description': 'Create new wallet'},
                    'list_wallets': {'method': 'GET', 'path': '/wallets', 'description': 'List all available wallets'},
                    'wallet_balance': {'method': 'GET', 'path': '/wallet/<address>/balance', 'description': 'Get wallet balance'},
                    'wallet_transactions': {'method': 'GET', 'path': '/wallet/<address>/transactions', 'description': 'Get wallet transaction history'},
                    'export_wallet': {'method': 'GET', 'path': '/wallet/<wallet_id>/export', 'description': 'Export wallet public information'},
                    'sign_transaction': {'method': 'POST', 'path': '/wallet/sign-transaction', 'description': 'Sign transaction with wallet'},

                    # Transactions
                    'submit_transaction': {'method': 'POST', 'path': '/transaction', 'description': 'Submit signed transaction to network'},

                    # PiNS (Pi Name System)
                    'check_name': {'method': 'GET', 'path': '/names/check/<name>', 'description': 'Check if name is available for registration'},
                    'resolve_name': {'method': 'GET', 'path': '/names/<name>', 'description': 'Resolve name to wallet address'},
                    'register_name': {'method': 'POST', 'path': '/names/register', 'description': 'Register new PiNS name (5 token fee)'},
                    'get_wallet_names': {'method': 'GET', 'path': '/names/wallet/<address>', 'description': 'Get all names registered to wallet'},
                    'list_names': {'method': 'GET', 'path': '/names', 'description': 'List all registered PiNS names'},

                    # Mining
                    'mining_status': {'method': 'GET', 'path': '/mining/status', 'description': 'Get mining status and statistics'},
                    'start_mining': {'method': 'POST', 'path': '/mining/start', 'description': 'Request mining start (systemd service)'},
                    'stop_mining': {'method': 'POST', 'path': '/mining/stop', 'description': 'Request mining stop (systemd service)'},

                    # Network
                    'network_status': {'method': 'GET', 'path': '/network/status', 'description': 'Get network status and peers'},
                    'network_peers': {'method': 'GET', 'path': '/network/peers', 'description': 'Get known network peers'},
                    'network_discover': {'method': 'POST', 'path': '/network/discover', 'description': 'Trigger network peer discovery'},

                    # Token Economics (314ST)
                    'create_trust': {'method': 'POST', 'path': '/trust', 'description': 'Create developer trust fund'},
                    'get_trust': {'method': 'GET', 'path': '/trust/<trust_id>', 'description': 'Get trust fund status'},
                    'fund_trust': {'method': 'POST', 'path': '/trust/<trust_id>/fund', 'description': 'Fund trust account'},
                    'transfer_trust_to_wallet': {'method': 'POST', 'path': '/trust/<trust_id>/transfer-to-wallet', 'description': 'Transfer tokens from trust to wallet'},
                    'create_subscription_plan': {'method': 'POST', 'path': '/trust/<trust_id>/plan', 'description': 'Create subscription plan'},
                    'subscribe_user': {'method': 'POST', 'path': '/trust/<trust_id>/subscribe', 'description': 'Subscribe user to plan'},
                    'check_user_access': {'method': 'POST', 'path': '/trust/<trust_id>/access/<user_id>', 'description': 'Check user access permissions'},
                    'fee_distribution': {'method': 'GET', 'path': '/economics/fees', 'description': 'Get fee distribution rules'},

                    # Foundation Transfers (Genesis Key Required)
                    'contribute_to_foundation': {'method': 'POST', 'path': '/foundation/contribute', 'description': 'Contribute tokens from wallet to foundation'},
                    'transfer_foundation_to_wallet': {'method': 'POST', 'path': '/foundation/transfer-to-wallet', 'description': 'Transfer tokens from foundation to wallet'},

                    # Bootstrap Operators (Foundation Managed)
                    'register_bootstrap_operator': {'method': 'POST', 'path': '/bootstrap/register', 'description': 'Register bootstrap operator for funding'},
                    'update_bootstrap_metrics': {'method': 'POST', 'path': '/bootstrap/<operator_id>/metrics', 'description': 'Update operator service metrics'},
                    'get_bootstrap_funding_status': {'method': 'GET', 'path': '/bootstrap/funding-status', 'description': 'Get bootstrap funding allocation status'},
                    'allocate_bootstrap_funding': {'method': 'POST', 'path': '/bootstrap/allocate-funding', 'description': 'Allocate funding to bootstrap operators'},

                    # Foundation (Genesis Key Required)
                    'foundation_status': {'method': 'GET', 'path': '/foundation/status', 'description': 'Get foundation trust status'},
                    'create_grant': {'method': 'POST', 'path': '/foundation/grant', 'description': 'Create foundation grant proposal'},
                    'vote_on_grant': {'method': 'POST', 'path': '/foundation/grant/<grant_id>/vote', 'description': 'Vote on grant proposal'},
                    'foundation_transactions': {'method': 'GET', 'path': '/foundation/transactions', 'description': 'Get foundation transaction history'},
                    'sign_foundation_transaction': {'method': 'POST', 'path': '/foundation/sign-transaction', 'description': 'Sign transaction with genesis key'},
                    'execute_foundation_transaction': {'method': 'POST', 'path': '/foundation/execute-transaction', 'description': 'Execute signed foundation transaction'},
                    'verify_foundation_transaction': {'method': 'POST', 'path': '/foundation/verify-transaction', 'description': 'Verify foundation transaction signature'},

                    # Updates
                    'verify_update': {'method': 'POST', 'path': '/update/verify', 'description': 'Verify update package signatures'},
                },
                'client_libraries': {
                    'android': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/android',
                    'javascript': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/javascript',
                    'typescript': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/typescript',
                    'python': 'https://github.com/UnderhillForge/PiSecure/tree/main/clients/python'
                },
                'authentication': {
                    'required': False,
                    'description': 'API endpoints are currently open. Authentication may be added in future versions.',
                    'rate_limiting': '100 requests per minute per IP'
                },
                'response_format': {
                    'success_responses': 'JSON with requested data',
                    'error_responses': 'JSON with "error" field and HTTP status codes',
                    'timestamps': 'Unix timestamps (seconds since epoch)',
                    'amounts': 'PiSecure tokens (floating point)',
                    'addresses': 'Hex-encoded wallet addresses (64 characters)'
                },
                'sdk_examples': {
                    'android': {
                        'create_wallet': 'PiSecureAPI.createWallet("My Wallet")',
                        'check_balance': 'PiSecureAPI.getBalance(walletAddress)',
                        'send_transaction': 'PiSecureAPI.sendTransaction(fromAddress, toAddress, amount, memo)',
                        'register_name': 'PiSecureAPI.registerName("alice", walletAddress)',
                        'resolve_name': 'PiSecureAPI.resolveName("alice")'
                    }
                }
            }
            return jsonify(docs)

    def _start_automatic_discovery(self):
        """Start automatic network discovery on server startup"""
        logger.info("🔍 Starting automatic network discovery...")

        # Initial discovery on startup
        try:
            logger.info("Performing initial network discovery...")
            discovery_results = node_discovery.make_node_discoverable()

            if discovery_results['success_count'] > 0:
                logger.info(f"✅ Initial discovery successful: {discovery_results['success_count']} methods")
                for endpoint in discovery_results['endpoints']:
                    endpoint_type = endpoint['type']
                    if endpoint_type == 'stun_direct':
                        logger.info(f"  🌐 STUN: {endpoint['ip']}:{endpoint['port']}")
                    elif endpoint_type == 'tor_onion':
                        logger.info(f"  🧅 Tor: {endpoint['address']}")
                    elif endpoint_type == 'upnp':
                        logger.info(f"  📡 UPnP: {endpoint['ip']}:{endpoint['port']}")
            else:
                logger.warning("⚠️ Initial discovery found no endpoints - will retry periodically")

        except Exception as e:
            logger.error(f"❌ Initial discovery failed: {e}")

        # Start background thread for periodic discovery refresh
        discovery_thread = threading.Thread(
            target=self._discovery_worker,
            daemon=True,
            name="NetworkDiscovery"
        )
        discovery_thread.start()
        logger.info("🔄 Started background discovery refresh thread")

    def _discovery_worker(self):
        """Background worker for periodic network discovery refresh with event-driven triggers"""
        import time

        # Discovery intervals (in seconds) - Reduced to prevent screen flashing
        INITIAL_INTERVAL = 1800  # 30 minutes after startup (was 5 min)
        REGULAR_INTERVAL = 1800  # 30 minutes regular refresh (was 5 min)
        EVENT_TRIGGER_INTERVAL = 300  # 5 minutes for event-triggered checks (was 1 min)

        time.sleep(INITIAL_INTERVAL)  # Wait before first refresh

        last_event_check = time.time()

        while True:
            try:
                current_time = time.time()

                # Check for event-driven discovery triggers
                if current_time - last_event_check >= EVENT_TRIGGER_INTERVAL:
                    self._check_event_triggers()
                    last_event_check = current_time

                logger.debug("🔄 Refreshing network discovery...")

                # Check if network has changed (basic check)
                network_changed = self._check_network_changed()

                if network_changed:
                    logger.info("📡 Network change detected, performing full discovery...")
                    discovery_results = node_discovery.make_node_discoverable()
                    if discovery_results['success_count'] > 0:
                        logger.info(f"✅ Discovery refresh successful: {discovery_results['success_count']} methods")
                    else:
                        logger.warning("⚠️ Discovery refresh found no endpoints")
                else:
                    # Just update relay list and check endpoints (silently)
                    node_discovery.relay_network.update_relay_list()
                    current_status = node_discovery.get_discovery_status()
                    logger.debug(f"✅ Discovery status check: {len(current_status['endpoints'])} endpoints available")

            except Exception as e:
                logger.error(f"❌ Discovery refresh failed: {e}")

            time.sleep(REGULAR_INTERVAL)

    def _check_network_changed(self) -> bool:
        """Check if network configuration has changed"""
        try:
            import socket
            import subprocess

            # Get current IP (simple check)
            current_ip = None
            try:
                # Try to get external IP via STUN-like method
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect(("8.8.8.8", 80))
                current_ip = sock.getsockname()[0]
                sock.close()
            except:
                pass

            # Check if IP changed from cached discovery
            cached_status = node_discovery.get_discovery_status()
            cached_endpoints = cached_status.get('endpoints', [])

            for endpoint in cached_endpoints:
                if endpoint.get('type') == 'stun_direct' and endpoint.get('ip') != current_ip:
                    return True

            # Check if network interfaces changed
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                current_routes = result.stdout.strip()
                # In a full implementation, you'd cache and compare routes

            return False  # Assume no change for now

        except Exception as e:
            logger.debug(f"Network change check failed: {e}")
            return False

    def _check_event_triggers(self):
        """Check for event-driven discovery triggers"""
        try:
            # Trigger discovery on peer connection events
            connected_peers = len(self.peer_discovery.get_connected_peers())
            if connected_peers > 0 and hasattr(self, '_last_peer_count'):
                if connected_peers != self._last_peer_count:
                    logger.info(f"🔄 Peer count changed: {self._last_peer_count} → {connected_peers}, triggering discovery")
                    self._trigger_discovery_on_peer_event()
            self._last_peer_count = connected_peers

            # Trigger discovery on blockchain events (new blocks, high transaction volume)
            chain_info = self.blockchain.get_chain_info()
            pending_txs = chain_info.get('pending_transactions', 0)

            if pending_txs > 10:  # High transaction volume trigger
                logger.info(f"🔄 High transaction volume ({pending_txs} pending), triggering discovery")
                self._trigger_discovery_on_high_activity()

            # Trigger discovery on system events (CPU/network changes)
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent < 10:  # Low CPU usage = good time for discovery
                self._trigger_discovery_on_low_load()

        except Exception as e:
            logger.debug(f"Event trigger check failed: {e}")

    def _trigger_discovery_on_transaction(self):
        """Trigger network discovery after transaction submission"""
        try:
            from pisecure.core.nat_traversal import node_discovery
            logger.info("🔄 Triggering discovery after transaction submission...")

            # Perform a quick discovery refresh
            discovery_results = node_discovery.make_node_discoverable()
            if discovery_results['success_count'] > 0:
                logger.info(f"✅ Transaction-triggered discovery successful: {discovery_results['success_count']} methods")
            else:
                logger.debug("Transaction-triggered discovery found no new endpoints")

        except Exception as e:
            logger.warning(f"Transaction-triggered discovery failed: {e}")

    def _trigger_discovery_on_peer_event(self):
        """Trigger discovery when peer connections change"""
        try:
            from pisecure.core.nat_traversal import node_discovery
            logger.info("🔄 Triggering discovery due to peer connection changes...")

            # Quick peer exchange and endpoint refresh
            discovery_results = node_discovery.make_node_discoverable()
            if discovery_results['success_count'] > 0:
                logger.info(f"✅ Peer event discovery successful: {discovery_results['success_count']} methods")
        except Exception as e:
            logger.debug(f"Peer event discovery failed: {e}")

    def _trigger_discovery_on_high_activity(self):
        """Trigger discovery during high network activity"""
        try:
            from pisecure.core.nat_traversal import node_discovery
            logger.info("🔄 Triggering discovery due to high network activity...")

            # More aggressive discovery during high activity
            discovery_results = node_discovery.make_node_discoverable()
            if discovery_results['success_count'] > 0:
                logger.info(f"✅ High activity discovery successful: {discovery_results['success_count']} methods")
        except Exception as e:
            logger.debug(f"High activity discovery failed: {e}")

    def _trigger_discovery_on_low_load(self):
        """Trigger discovery during low system load"""
        try:
            from pisecure.core.nat_traversal import node_discovery
            logger.info("🔄 Triggering discovery during low system load...")

            # Comprehensive discovery when system has spare capacity
            discovery_results = node_discovery.make_node_discoverable()
            if discovery_results['success_count'] > 0:
                logger.info(f"✅ Low load discovery successful: {discovery_results['success_count']} methods")
        except Exception as e:
            logger.debug(f"Low load discovery failed: {e}")

    # === BOOTSTRAP NODE HELPER METHODS ===

    def _get_verified_bootstrap_peers(self) -> List[Dict[str, Any]]:
        """Get list of verified, active peers for bootstrapping new nodes"""
        try:
            # Get known peers from discovery
            known_peers = self.peer_discovery.get_known_peers()

            verified_peers = []
            current_time = time.time()

            for peer_id, peer_info in known_peers.items():
                # Check if peer is active (seen within last hour)
                last_seen = peer_info.get('last_seen', 0)
                if current_time - last_seen > 3600:  # 1 hour
                    continue

                # Check if peer has required capabilities
                capabilities = peer_info.get('capabilities', [])
                if 'p2p_sync' not in capabilities:
                    continue

                # Add to verified list
                verified_peers.append({
                    'node_id': peer_id,
                    'address': peer_info.get('address'),
                    'port': peer_info.get('port', 3142),
                    'capabilities': capabilities,
                    'last_seen': last_seen
                })

                # Limit to prevent abuse
                if len(verified_peers) >= 50:
                    break

            return verified_peers

        except Exception as e:
            logger.error(f"Failed to get verified bootstrap peers: {e}")
            return []

    def _calculate_network_stats(self) -> Dict[str, Any]:
        """Calculate comprehensive network statistics"""
        try:
            # Get blockchain info
            chain_info = self.blockchain.get_chain_info()
            network_health = chain_info.get('network_health', {})

            # Get peer counts
            known_peers = len(self.peer_discovery.get_known_peers())
            connected_peers = len(self.peer_discovery.get_connected_peers())

            # Get registered nodes if available
            registered_nodes = getattr(self, 'registered_nodes', {})
            active_registered = sum(
                1 for node in registered_nodes.values()
                if time.time() - node.get('last_seen', 0) < 3600  # Active within 1 hour
            )

            # Calculate estimated network hashrate (simplified)
            estimated_hashrate = self._estimate_network_hashrate()

            # Calculate participation score
            participation = min(1.0, active_registered / max(1, known_peers)) if known_peers > 0 else 0

            # Network health score
            health_score = (participation * 0.4) + (network_health.get('health_score', 0.5) * 0.6)

            return {
                'active_nodes': max(connected_peers, active_registered),
                'total_known_peers': known_peers,
                'connected_peers': connected_peers,
                'registered_nodes': len(registered_nodes),
                'estimated_hashrate': estimated_hashrate,
                'participation_score': participation,
                'health_score': health_score,
                'avg_block_time': network_health.get('avg_block_time', 600),
                'total_blocks': chain_info.get('blocks', 0),
                'pending_transactions': chain_info.get('pending_transactions', 0),
                'difficulty': chain_info.get('difficulty', 4)
            }

        except Exception as e:
            logger.error(f"Failed to calculate network stats: {e}")
            return {
                'active_nodes': 0,
                'total_known_peers': 0,
                'connected_peers': 0,
                'registered_nodes': 0,
                'estimated_hashrate': 0,
                'participation_score': 0,
                'health_score': 0,
                'avg_block_time': 600,
                'total_blocks': 0,
                'pending_transactions': 0,
                'difficulty': 4
            }

    def _estimate_network_hashrate(self) -> float:
        """Estimate total network hashrate based on registered nodes"""
        try:
            registered_nodes = getattr(self, 'registered_nodes', {})
            total_hashrate = 0

            for node_info in registered_nodes.values():
                # Only count recently active nodes
                if time.time() - node_info.get('last_seen', 0) < 3600:  # 1 hour
                    total_hashrate += node_info.get('hashrate', 0)

            # Add some estimation for unregistered nodes
            estimated_unregistered = max(0, len(registered_nodes) * 0.5)
            total_hashrate += estimated_unregistered * 1.0  # Assume 1 MH/s average

            return max(total_hashrate, 0.1)  # Minimum estimate

        except Exception as e:
            logger.debug(f"Hashrate estimation failed: {e}")
            return 0.1

    def _get_mining_stats(self) -> Dict[str, Any]:
        """Get comprehensive mining statistics"""
        try:
            # Get registered mining nodes
            registered_nodes = getattr(self, 'registered_nodes', {})
            mining_nodes = [
                node for node in registered_nodes.values()
                if node.get('is_mining', False) and time.time() - node.get('last_seen', 0) < 3600
            ]

            # Calculate mining statistics
            active_miners = len(mining_nodes)
            total_mining_hashrate = sum(node.get('hashrate', 0) for node in mining_nodes)

            # Get recent blocks for mining activity
            recent_blocks = self.blockchain.chain[-10:] if len(self.blockchain.chain) > 10 else self.blockchain.chain
            blocks_last_hour = sum(
                1 for block in recent_blocks
                if time.time() - block.timestamp < 3600
            )

            return {
                'active_miners': active_miners,
                'total_mining_hashrate': total_mining_hashrate,
                'blocks_last_hour': blocks_last_hour,
                'avg_blocks_per_hour': blocks_last_hour,
                'mining_nodes': [
                    {
                        'node_id': node['node_id'],
                        'hashrate': node.get('hashrate', 0),
                        'location': node.get('location', 'unknown')
                    } for node in mining_nodes[:10]  # Top 10 miners
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get mining stats: {e}")
            return {
                'active_miners': 0,
                'total_mining_hashrate': 0,
                'blocks_last_hour': 0,
                'avg_blocks_per_hour': 0,
                'mining_nodes': []
            }

    def _get_node_geography(self) -> Dict[str, Any]:
        """Get geographic distribution of registered nodes"""
        try:
            registered_nodes = getattr(self, 'registered_nodes', {})

            # Count nodes by location (simplified - would use IP geolocation in production)
            locations = {}
            for node_info in registered_nodes.values():
                location = node_info.get('location', 'unknown')
                locations[location] = locations.get(location, 0) + 1

            # Sort by count
            sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)

            return {
                'total_locations': len(locations),
                'top_locations': dict(sorted_locations[:10]),
                'distribution': locations
            }

        except Exception as e:
            logger.error(f"Failed to get node geography: {e}")
            return {
                'total_locations': 0,
                'top_locations': {},
                'distribution': {}
            }

    def run(self, debug: bool = False):
        """
        Start the API server with automatic network discovery and P2P sync.

        Args:
            debug: Enable debug mode
        """
        logger.info(f"🚀 Starting PiSecure API Server on {self.host}:{self.port}")
        logger.info(f"📚 API Documentation: http://{self.host}:{self.port}/api/{self.api_version}/docs")

        # Register this node with bootstrap service
        self._register_with_bootstrap()

        # Start automatic network discovery
        self._start_automatic_discovery()

        # Start P2P blockchain synchronization
        self.p2p_sync.start_sync()
        logger.info("🔄 Started P2P blockchain synchronization")

        # Start heartbeat reporting
        self._start_heartbeat_reporting()

        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=debug,
                threaded=True
            )
        finally:
            # Clean up on shutdown
            logger.info("🛑 Shutting down P2P sync...")
            self.p2p_sync.stop_sync()
            if hasattr(self, '_heartbeat_thread'):
                self._heartbeat_thread.join(timeout=5)

    def _register_with_bootstrap(self):
        """Register this node with the bootstrap service on startup"""
        try:
            # Get node information
            node_id = self.peer_discovery.node_id
            host = self.host if self.host != '0.0.0.0' else 'localhost'
            port = self.port

            # Get system information
            import platform
            import psutil

            # Determine location (simplified - would use IP geolocation)
            location = 'unknown'
            try:
                # Try to get a basic location hint
                hostname = platform.node()
                if 'pi' in hostname.lower() or 'raspberry' in hostname.lower():
                    location = 'raspberry-pi'
                else:
                    location = 'server'
            except:
                pass

            # Get capabilities
            capabilities = ['api', 'p2p_sync', 'mining']

            # Prepare registration data (matching bootstrap server requirements)
            registration_data = {
                'node_id': node_id,
                'node_type': 'standard',  # Default type, can be updated based on services
                'services': ['api', 'p2p_sync'],  # Services offered
                'capabilities': capabilities,
                'location': location,
                'wallet_address': None  # Will be set if available
            }

            # Determine node type based on capabilities
            if 'mining' in capabilities:
                registration_data['node_type'] = 'miner'
            elif 'block_validation' in capabilities:
                registration_data['node_type'] = 'validator'

            # Try to get wallet address from config
            try:
                import json as json_lib
                config_path = "/etc/pisecure/config.json"
                with open(config_path, 'r') as f:
                    config = json_lib.load(f)
                wallet_addr = config.get('mining', {}).get('wallet_address')
                if wallet_addr:
                    registration_data['wallet_address'] = wallet_addr
            except:
                pass

            # Register with bootstrap service
            import requests

            bootstrap_urls = [
                "https://bootstrap.pisecure.org/api/v1/nodes/register",
                "https://pisecure-bootstrap-production.up.railway.app/api/v1/nodes/register"
            ]

            registered = False
            for bootstrap_url in bootstrap_urls:
                try:
                    response = requests.post(bootstrap_url, json=registration_data, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('registration_success'):
                            logger.info(f"✅ Node registered with bootstrap: {node_id}")
                            registered = True
                            break
                        else:
                            logger.warning(f"⚠️ Bootstrap registration rejected: {result}")
                    else:
                        logger.debug(f"Bootstrap URL {bootstrap_url} returned {response.status_code}")
                except Exception as e:
                    logger.debug(f"Failed to register with {bootstrap_url}: {e}")
                    continue

            if not registered:
                logger.warning("⚠️ Could not register with any bootstrap service - node may not appear on dashboard")
            else:
                # Store our node ID for heartbeat updates
                self._registered_node_id = node_id
                logger.info(f"📡 Node {node_id} registered with bootstrap network")

        except Exception as e:
            logger.error(f"❌ Failed to register with bootstrap service: {e}")

    def _start_heartbeat_reporting(self):
        """Start periodic heartbeat reporting to bootstrap service"""
        try:
            if not hasattr(self, '_registered_node_id'):
                logger.debug("Node not registered with bootstrap - skipping heartbeat")
                return

            # Start heartbeat thread
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_worker,
                daemon=True,
                name="BootstrapHeartbeat"
            )
            self._heartbeat_thread.start()
            logger.info("💓 Started bootstrap heartbeat reporting")

        except Exception as e:
            logger.error(f"❌ Failed to start heartbeat reporting: {e}")

    def _heartbeat_worker(self):
        """Background worker for sending periodic heartbeats to bootstrap"""
        import time

        heartbeat_interval = 300  # 5 minutes
        time.sleep(60)  # Wait 1 minute before first heartbeat

        while True:
            try:
                # Get current node status
                heartbeat_data = {
                    'node_id': self._registered_node_id,
                    'is_mining': getattr(self, '_mining_active', False),
                    'hashrate': getattr(self, '_current_hashrate', 0.0),
                    'last_seen': time.time()
                }

                # Try to send heartbeat to bootstrap services
                bootstrap_urls = [
                    "https://bootstrap.pisecure.org/api/v1/nodes/status",
                    "https://pisecure-bootstrap-production.up.railway.app/api/v1/nodes/status"
                ]

                sent = False
                for bootstrap_url in bootstrap_urls:
                    try:
                        import requests
                        response = requests.post(bootstrap_url, json=heartbeat_data, timeout=10)
                        if response.status_code == 200:
                            sent = True
                            break
                    except Exception as e:
                        logger.debug(f"Heartbeat failed to {bootstrap_url}: {e}")
                        continue

                if sent:
                    logger.debug(f"💓 Heartbeat sent for node {self._registered_node_id}")
                else:
                    logger.debug("⚠️ Could not send heartbeat to any bootstrap service")

            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

            time.sleep(heartbeat_interval)


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