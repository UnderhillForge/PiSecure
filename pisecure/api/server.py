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
import re
import ssl
import os
from flask import Flask, request, jsonify, abort
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
from .validation import (
    validate_request, ValidationError, safe_error_response,
    log_security_event, validate_wallet_address, validate_transaction_hash,
    validate_name, validate_amount, sanitize_string
)
from .ddos_protection import ddos_protection, request_fingerprinting
from .audit_logger import AuditLogMiddleware, log_security_event, AuditEventType

# Security Headers Middleware
class SecurityHeadersMiddleware:
    """
    OWASP-compliant security headers middleware for Flask applications.

    Implements comprehensive security headers to protect against common web vulnerabilities:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options (Clickjacking protection)
    - X-Content-Type-Options (MIME sniffing protection)
    - Referrer-Policy
    - Permissions-Policy
    - Cross-Origin policies
    """

    def __init__(self, app, csp_policy: str = None, hsts_max_age: int = 31536000):
        """
        Initialize security headers middleware.

        Args:
            app: Flask application instance
            csp_policy: Custom Content Security Policy string
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
        """
        self.app = app
        self.csp_policy = csp_policy or self._get_default_csp()
        self.hsts_max_age = hsts_max_age

        # Register middleware
        self.app.after_request(self.add_security_headers)

    def _get_default_csp(self) -> str:
        """
        Get default Content Security Policy for PiSecure dashboard.

        Returns:
            CSP policy string
        """
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.socket.io; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )

    def add_security_headers(self, response):
        """
        Add comprehensive security headers to response.

        Args:
            response: Flask response object

        Returns:
            Modified response with security headers
        """
        # Content Security Policy
        response.headers['Content-Security-Policy'] = self.csp_policy

        # HTTP Strict Transport Security (HSTS)
        response.headers['Strict-Transport-Security'] = f'max-age={self.hsts_max_age}; includeSubDomains; preload'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), payment=(), usb=()'
        )

        # Cross-Origin Embedder Policy (COEP)
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'

        # Cross-Origin Opener Policy (COOP)
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'

        # Cross-Origin Resource Policy (CORP)
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

        # DNS prefetch control
        response.headers['X-DNS-Prefetch-Control'] = 'off'

        # Prevent caching of sensitive content
        if response.status_code >= 400:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

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

        # Initialize dynamic rate limiter with bootstrap intelligence
        self.limiter = Limiter(
            get_remote_address,
            app=self.app,
            default_limits=[rate_limit]
        )

        # Dynamic rate limiting configuration
        self.dynamic_rate_limiting = True
        self.base_rate_limit = rate_limit
        self.current_rate_limit = rate_limit
        self.rate_limit_check_interval = 300  # Check every 5 minutes
        self.last_rate_limit_update = 0

        # Request queuing for high load periods
        self.request_queue_enabled = True
        self.max_queued_requests = 100
        self.request_queue = []
        self.queue_processing_thread = None

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

        # Setup DDoS protection middleware (TODO: implement)
        # self._setup_ddos_protection()

        # Setup security headers middleware
        self._setup_security_headers()

        # Setup audit logging middleware
        self._setup_audit_logging()

    def _setup_security_headers(self):
        """Setup comprehensive security headers middleware"""
        # Initialize security headers middleware
        SecurityHeadersMiddleware(self.app)
        logger.info("🛡️ Security headers middleware initialized")

    def _setup_audit_logging(self):
        """Setup comprehensive audit logging middleware"""
        # Initialize audit logging middleware
        AuditLogMiddleware(self.app)
        logger.info("📋 Audit logging middleware initialized")

        # Add DDoS protection before request hook
        @self.app.before_request
        def check_ddos_protection():
            """Check request against DDoS protection before processing"""
            try:
                # Skip DDoS checks for health endpoint to prevent false positives
                if request.endpoint and 'health' in request.endpoint:
                    return

                # Check request against DDoS protection
                check_result = ddos_protection.check_request(
                    ip_address=request.remote_addr,
                    endpoint=request.path,
                    user_agent=request.headers.get('User-Agent', ''),
                    request_data=request.get_json(silent=True) if request.is_json else None
                )

                if not check_result.get('allowed', True):
                    # Request blocked by DDoS protection
                    logger.warning(f"🚫 DDoS protection blocked request from {request.remote_addr}: {check_result.get('reason', 'unknown')}")
                    abort(429, "Too many requests")

                # Apply delay if specified
                delay = check_result.get('delay', 0)
                if delay > 0:
                    import time
                    time.sleep(min(delay, 5.0))  # Max 5 second delay

                # Create fingerprint for advanced analysis
                fingerprint = request_fingerprinting.fingerprint_request(
                    ip=request.remote_addr,
                    method=request.method,
                    endpoint=request.path,
                    user_agent=request.headers.get('User-Agent', ''),
                    headers=dict(request.headers)
                )

                # Store fingerprint in request context for potential logging
                request.fingerprint = fingerprint

            except Exception as e:
                logger.error(f"DDoS protection check failed: {e}")
                # Don't block requests if DDoS check fails - fail open for safety

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
                # Convert SignBlock objects to dicts
                blocks_dict = [block.to_dict() if hasattr(block, 'to_dict') else block for block in blocks]
                return jsonify({'blocks': blocks_dict})
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
                # Validate request data
                validated_data = validate_request('transaction')
                tx_data = validated_data if validated_data else request.get_json()

                if not tx_data:
                    return jsonify({'error': 'No transaction data provided'}), 400

                # Additional validation for transaction data
                if not isinstance(tx_data.get('data'), dict):
                    return jsonify({'error': 'Transaction data must be an object'}), 400

                # Validate signature format (should be hex)
                signature = tx_data.get('signature', '')
                if not re.match(r'^[a-fA-F0-9]{128,}$', signature):  # At least 128 hex chars
                    return jsonify({'error': 'Invalid signature format'}), 400

                # Validate timestamp (not too old, not too far in future)
                timestamp = tx_data.get('timestamp', 0)
                current_time = time.time()
                if timestamp < current_time - 3600:  # Older than 1 hour
                    return jsonify({'error': 'Transaction too old'}), 400
                if timestamp > current_time + 300:  # More than 5 minutes in future
                    return jsonify({'error': 'Transaction timestamp too far in future'}), 400

                # Add transaction to blockchain
                tx_hash = self.blockchain.add_transaction(tx_data)

                # Log successful transaction for security monitoring
                log_security_event('transaction_submitted', {
                    'tx_hash': tx_hash,
                    'tx_type': tx_data.get('type'),
                    'timestamp': timestamp
                })

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

            except ValidationError as e:
                log_security_event('validation_error', {
                    'endpoint': 'transaction',
                    'error': str(e),
                    'client_ip': request.remote_addr
                }, 'warning')
                return jsonify(safe_error_response(str(e), 400)), 400
            except Exception as e:
                logger.error(f"Transaction submission error: {e}")
                return jsonify(safe_error_response('Transaction submission failed', 500)), 500

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

                # If no local verified peers, try external bootstrap servers
                if not bootstrap_peers:
                    logger.debug("No local verified peers, trying external bootstrap servers...")
                    bootstrap_peers = self._get_fallback_bootstrap_peers()

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
                    'ttl': 300,  # Cache for 5 minutes
                    'fallback_used': len(bootstrap_peers) == 0  # Indicate if fallbacks were used
                }

                return jsonify(bootstrap_info)

            except Exception as e:
                logger.error(f"Bootstrap peer discovery error: {e}")
                return jsonify({'error': 'Peer discovery temporarily unavailable'}), 503

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

        # Miner status reporting endpoint
        @self.app.route(f'/api/{self.api_version}/nodes/status', methods=['POST'])
        def report_miner_status():
            """Receive mining status reports from active miners for dashboard and intelligence"""
            try:
                status_data = request.get_json()

                if not status_data or 'node_id' not in status_data:
                    return jsonify({'error': 'node_id required'}), 400

                node_id = status_data['node_id']

                # Initialize miner status storage if needed
                if not hasattr(self, 'miner_status_reports'):
                    self.miner_status_reports = {}

                # Store the status report with timestamp
                status_report = {
                    'node_id': node_id,
                    'mining_active': status_data.get('mining_active', False),
                    'hashrate': status_data.get('hashrate', 0.0),
                    'blocks_mined': status_data.get('blocks_mined', 0),
                    'session_start_time': status_data.get('session_start_time'),
                    'temperature': status_data.get('temperature'),
                    'memory_usage': status_data.get('memory_usage'),
                    'network_metrics': status_data.get('network_metrics', {}),
                    'system_health': status_data.get('system_health', {}),
                    'wallet_address': status_data.get('wallet_address'),
                    'location': status_data.get('location', 'unknown'),
                    'hardware_model': status_data.get('hardware_model', 'unknown'),
                    'reported_at': time.time(),
                    'ip_address': request.remote_addr
                }

                # Store in miner status reports (keep last 100 reports per node for intelligence)
                if node_id not in self.miner_status_reports:
                    self.miner_status_reports[node_id] = []

                self.miner_status_reports[node_id].append(status_report)

                # Keep only last 100 reports per node to prevent memory bloat
                if len(self.miner_status_reports[node_id]) > 100:
                    self.miner_status_reports[node_id] = self.miner_status_reports[node_id][-100:]

                # Update registered node info if available
                if hasattr(self, 'registered_nodes') and node_id in self.registered_nodes:
                    node_info = self.registered_nodes[node_id]
                    node_info.update({
                        'last_seen': time.time(),
                        'is_mining': status_report['mining_active'],
                        'hashrate': status_report['hashrate'],
                        'blocks_mined': status_report['blocks_mined'],
                        'temperature': status_report['temperature'],
                        'location': status_report['location'],
                        'hardware_model': status_report['hardware_model']
                    })

                # Trigger intelligence processing
                intelligence_insights = self._process_miner_intelligence(status_report)

                return jsonify({
                    'success': True,
                    'status': 'reported',
                    'intelligence_processed': True,
                    'insights': intelligence_insights
                })

            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def _process_miner_intelligence(self, status_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process miner status reports for network intelligence and analytics

        Args:
            status_report: Miner status report from POST /nodes/status

        Returns:
            Intelligence insights and alerts
        """
        insights = {
            'processed_at': time.time(),
            'alerts': [],
            'anomalies': [],
            'recommendations': [],
            'network_impact': {}
        }

        try:
            node_id = status_report['node_id']
            hashrate = status_report.get('hashrate', 0)
            temperature = status_report.get('temperature')
            memory_usage = status_report.get('memory_usage')
            mining_active = status_report.get('mining_active', False)

            # Get historical data for this node (last 10 reports)
            historical_reports = []
            if hasattr(self, 'miner_status_reports') and node_id in self.miner_status_reports:
                recent_reports = [r for r in self.miner_status_reports[node_id][-10:]
                                if r['reported_at'] > time.time() - 3600]  # Last hour
                historical_reports = recent_reports

            # 1. Performance Analysis
            if mining_active and hashrate > 0:
                # Check for hashrate anomalies
                avg_hashrate = self._calculate_average_hashrate(historical_reports)
                if avg_hashrate > 0:
                    hashrate_variance = abs(hashrate - avg_hashrate) / avg_hashrate
                    if hashrate_variance > 0.3:  # 30% variance
                        insights['anomalies'].append({
                            'type': 'hashrate_anomaly',
                            'severity': 'warning',
                            'message': f'Hashrate deviation: {hashrate:.2f} vs avg {avg_hashrate:.2f}',
                            'current': hashrate,
                            'average': avg_hashrate
                        })

            # 2. Temperature Analysis
            if temperature is not None:
                if temperature >= 80:
                    insights['alerts'].append({
                        'type': 'thermal_emergency',
                        'severity': 'critical',
                        'message': f'Miner {node_id} at critical temperature: {temperature}°C',
                        'recommendation': 'Stop mining immediately to prevent hardware damage'
                    })
                elif temperature >= 75:
                    insights['alerts'].append({
                        'type': 'thermal_warning',
                        'severity': 'warning',
                        'message': f'Miner {node_id} running hot: {temperature}°C',
                        'recommendation': 'Consider cooling or reduced mining intensity'
                    })

            # 3. Memory Analysis
            if memory_usage is not None:
                if memory_usage >= 95:
                    insights['alerts'].append({
                        'type': 'memory_emergency',
                        'severity': 'critical',
                        'message': f'Miner {node_id} memory usage critical: {memory_usage}%',
                        'recommendation': 'Restart miner to clear memory leaks'
                    })
                elif memory_usage >= 85:
                    insights['alerts'].append({
                        'type': 'memory_warning',
                        'severity': 'warning',
                        'message': f'Miner {node_id} high memory usage: {memory_usage}%',
                        'recommendation': 'Monitor for memory leaks'
                    })

            # 4. Network Impact Analysis
            network_metrics = status_report.get('network_metrics', {})
            connected_peers = network_metrics.get('connected_peers', 0)
            p2p_messages = network_metrics.get('p2p_messages_sent', 0) + network_metrics.get('p2p_messages_received', 0)

            insights['network_impact'] = {
                'peer_connectivity': 'good' if connected_peers >= 3 else 'poor' if connected_peers == 0 else 'fair',
                'message_activity': 'high' if p2p_messages > 100 else 'normal' if p2p_messages > 10 else 'low',
                'network_contribution': self._assess_network_contribution(status_report)
            }

            # 5. Mining Efficiency Analysis
            if mining_active and hashrate > 0:
                efficiency_score = self._calculate_mining_efficiency(status_report)
                insights['mining_efficiency'] = {
                    'score': efficiency_score,
                    'rating': 'excellent' if efficiency_score >= 0.9 else 'good' if efficiency_score >= 0.7 else 'fair' if efficiency_score >= 0.5 else 'poor',
                    'temperature_penalty': temperature > 70 if temperature else False,
                    'memory_penalty': memory_usage > 80 if memory_usage else False
                }

            # 6. Generate Recommendations
            insights['recommendations'] = self._generate_miner_recommendations(status_report, insights)

        except Exception as e:
            insights['processing_error'] = str(e)

        return insights

    def _get_miner_intelligence(self, hours_back: float = 1) -> Dict[str, Any]:
        """
        Aggregate intelligence from all miner reports

        Args:
            hours_back: Hours of data to analyze

        Returns:
            Comprehensive network intelligence
        """
        intelligence = {
            'analysis_period_hours': hours_back,
            'generated_at': time.time(),
            'network_health': {},
            'performance_insights': {},
            'anomaly_summary': {},
            'recommendations': []
        }

        try:
            cutoff_time = time.time() - (hours_back * 3600)

            # Collect all recent reports
            all_reports = []
            if hasattr(self, 'miner_status_reports'):
                for node_reports in self.miner_status_reports.values():
                    recent_reports = [r for r in node_reports if r['reported_at'] >= cutoff_time]
                    all_reports.extend(recent_reports)

            if not all_reports:
                intelligence['network_health']['status'] = 'no_data'
                return intelligence

            # Network Health Analysis
            active_miners = len(set(r['node_id'] for r in all_reports if r.get('mining_active')))
            total_reports = len(all_reports)
            avg_temperature = self._calculate_average_metric(all_reports, 'temperature')
            avg_memory = self._calculate_average_metric(all_reports, 'memory_usage')
            total_hashrate = sum(r.get('hashrate', 0) for r in all_reports if r.get('mining_active'))

            intelligence['network_health'] = {
                'active_miners': active_miners,
                'total_reports': total_reports,
                'avg_temperature': avg_temperature,
                'avg_memory_usage': avg_memory,
                'total_network_hashrate': total_hashrate,
                'status': self._assess_network_health(avg_temperature, avg_memory, active_miners)
            }

            # Performance Insights
            intelligence['performance_insights'] = {
                'top_performers': self._identify_top_performers(all_reports),
                'efficiency_distribution': self._analyze_efficiency_distribution(all_reports),
                'geographic_distribution': self._analyze_geographic_distribution(all_reports),
                'hardware_distribution': self._analyze_hardware_distribution(all_reports)
            }

            # Anomaly Summary
            intelligence['anomaly_summary'] = self._summarize_anomalies(all_reports)

            # Network Recommendations
            intelligence['recommendations'] = self._generate_network_recommendations(all_reports)

        except Exception as e:
            intelligence['processing_error'] = str(e)

        return intelligence

    def _calculate_average_hashrate(self, reports: List[Dict[str, Any]]) -> float:
        """Calculate average hashrate from historical reports"""
        hashrates = [r.get('hashrate', 0) for r in reports if r.get('mining_active') and r.get('hashrate', 0) > 0]
        return sum(hashrates) / len(hashrates) if hashrates else 0

    def _calculate_average_metric(self, reports: List[Dict[str, Any]], metric: str) -> Optional[float]:
        """Calculate average of a metric across reports"""
        values = [r[metric] for r in reports if metric in r and r[metric] is not None]
        return sum(values) / len(values) if values else None

    def _assess_network_health(self, avg_temp: Optional[float], avg_memory: Optional[float], active_miners: int) -> str:
        """Assess overall network health"""
        if active_miners == 0:
            return 'inactive'

        health_score = 0

        # Temperature component
        if avg_temp is not None:
            if avg_temp < 60:
                health_score += 1
            elif avg_temp < 70:
                health_score += 0.7
            elif avg_temp < 75:
                health_score += 0.3

        # Memory component
        if avg_memory is not None:
            if avg_memory < 70:
                health_score += 1
            elif avg_memory < 80:
                health_score += 0.7
            elif avg_memory < 90:
                health_score += 0.3

        # Activity component
        if active_miners >= 5:
            health_score += 1
        elif active_miners >= 2:
            health_score += 0.7
        else:
            health_score += 0.3

        health_score /= 3  # Average the components

        if health_score >= 0.8:
            return 'excellent'
        elif health_score >= 0.6:
            return 'good'
        elif health_score >= 0.4:
            return 'fair'
        else:
            return 'poor'

    def _assess_network_contribution(self, status_report: Dict[str, Any]) -> str:
        """Assess how much a miner contributes to network health"""
        contribution_score = 0

        # Mining activity
        if status_report.get('mining_active'):
            contribution_score += 0.4

        # Hashrate contribution
        hashrate = status_report.get('hashrate', 0)
        if hashrate >= 2.0:  # Good hashrate
            contribution_score += 0.3
        elif hashrate >= 0.5:  # Decent hashrate
            contribution_score += 0.2

        # Network connectivity
        network_metrics = status_report.get('network_metrics', {})
        connected_peers = network_metrics.get('connected_peers', 0)
        if connected_peers >= 5:
            contribution_score += 0.3
        elif connected_peers >= 2:
            contribution_score += 0.2

        if contribution_score >= 0.8:
            return 'high'
        elif contribution_score >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _calculate_mining_efficiency(self, status_report: Dict[str, Any]) -> float:
        """Calculate mining efficiency score (0-1)"""
        efficiency = 1.0

        # Temperature penalties
        temperature = status_report.get('temperature')
        if temperature:
            if temperature > 80:
                efficiency *= 0.3  # Severe penalty
            elif temperature > 75:
                efficiency *= 0.6  # Heavy penalty
            elif temperature > 70:
                efficiency *= 0.8  # Moderate penalty

        # Memory penalties
        memory_usage = status_report.get('memory_usage')
        if memory_usage:
            if memory_usage > 95:
                efficiency *= 0.3
            elif memory_usage > 85:
                efficiency *= 0.7
            elif memory_usage > 75:
                efficiency *= 0.9

        # System health penalties
        system_health = status_report.get('system_health', {})
        cpu_usage = system_health.get('cpu_usage')
        if cpu_usage:
            if cpu_usage > 95:
                efficiency *= 0.5
            elif cpu_usage > 85:
                efficiency *= 0.8

        return efficiency

    def _generate_miner_recommendations(self, status_report: Dict[str, Any], insights: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations for a miner"""
        recommendations = []

        temperature = status_report.get('temperature')
        memory_usage = status_report.get('memory_usage')
        hashrate = status_report.get('hashrate', 0)

        # Temperature recommendations
        if temperature and temperature > 75:
            recommendations.append("Reduce mining intensity or improve cooling to prevent hardware damage")
        elif temperature and temperature > 70:
            recommendations.append("Consider additional cooling or mining during cooler periods")

        # Memory recommendations
        if memory_usage and memory_usage > 85:
            recommendations.append("Monitor for memory leaks - consider restarting miner periodically")
        elif memory_usage and memory_usage > 75:
            recommendations.append("Keep an eye on memory usage trends")

        # Performance recommendations
        if hashrate > 0 and hashrate < 0.5:
            recommendations.append("Consider hardware upgrade for better mining performance")

        # Network recommendations
        network_metrics = status_report.get('network_metrics', {})
        connected_peers = network_metrics.get('connected_peers', 0)
        if connected_peers < 2:
            recommendations.append("Improve network connectivity to enhance mining rewards")

        return recommendations

    def _identify_top_performers(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify top performing miners"""
        # Group by node and calculate average hashrate
        node_performance = {}
        for report in reports:
            node_id = report['node_id']
            hashrate = report.get('hashrate', 0)

            if node_id not in node_performance:
                node_performance[node_id] = {'total_hashrate': 0, 'reports': 0, 'location': report.get('location', 'unknown')}

            if hashrate > 0:
                node_performance[node_id]['total_hashrate'] += hashrate
                node_performance[node_id]['reports'] += 1

        # Calculate averages and rank
        performers = []
        for node_id, data in node_performance.items():
            if data['reports'] > 0:
                avg_hashrate = data['total_hashrate'] / data['reports']
                performers.append({
                    'node_id': node_id,
                    'avg_hashrate': avg_hashrate,
                    'location': data['location'],
                    'report_count': data['reports']
                })

        # Sort by hashrate and return top 5
        performers.sort(key=lambda x: x['avg_hashrate'], reverse=True)
        return performers[:5]

    def _analyze_efficiency_distribution(self, reports: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze efficiency distribution across miners"""
        efficiency_counts = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}

        for report in reports:
            efficiency = self._calculate_mining_efficiency(report)
            if efficiency >= 0.9:
                efficiency_counts['excellent'] += 1
            elif efficiency >= 0.7:
                efficiency_counts['good'] += 1
            elif efficiency >= 0.5:
                efficiency_counts['fair'] += 1
            else:
                efficiency_counts['poor'] += 1

        return efficiency_counts

    def _analyze_geographic_distribution(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze geographic distribution of miners"""
        locations = {}
        for report in reports:
            location = report.get('location', 'unknown')
            hashrate = report.get('hashrate', 0) if report.get('mining_active') else 0

            if location not in locations:
                locations[location] = {'count': 0, 'total_hashrate': 0}

            locations[location]['count'] += 1
            locations[location]['total_hashrate'] += hashrate

        # Convert to sorted list
        sorted_locations = sorted(
            [{'location': loc, **data} for loc, data in locations.items()],
            key=lambda x: x['total_hashrate'],
            reverse=True
        )

        return {
            'distribution': locations,
            'top_locations': sorted_locations[:5],
            'total_regions': len(locations)
        }

    def _analyze_hardware_distribution(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze hardware distribution"""
        hardware = {}
        for report in reports:
            hw_model = report.get('hardware_model', 'unknown')

            if hw_model not in hardware:
                hardware[hw_model] = {'count': 0, 'total_hashrate': 0, 'active_miners': 0}

            hardware[hw_model]['count'] += 1
            if report.get('mining_active'):
                hardware[hw_model]['active_miners'] += 1
                hardware[hw_model]['total_hashrate'] += report.get('hashrate', 0)

        # Calculate averages
        for hw_data in hardware.values():
            if hw_data['active_miners'] > 0:
                hw_data['avg_hashrate'] = hw_data['total_hashrate'] / hw_data['active_miners']
            else:
                hw_data['avg_hashrate'] = 0

        return hardware

    def _summarize_anomalies(self, reports: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize anomalies across all reports"""
        anomaly_counts = {}

        for report in reports:
            # Process intelligence for each report to count anomalies
            temp_insights = self._process_miner_intelligence(report)

            for anomaly in temp_insights.get('anomalies', []):
                anomaly_type = anomaly.get('type', 'unknown')
                anomaly_counts[anomaly_type] = anomaly_counts.get(anomaly_type, 0) + 1

        return anomaly_counts

    def _generate_network_recommendations(self, reports: List[Dict[str, Any]]) -> List[str]:
        """Generate network-wide recommendations"""
        recommendations = []

        if not reports:
            return recommendations

        # Check overall network health
        avg_temp = self._calculate_average_metric(reports, 'temperature')
        avg_memory = self._calculate_average_metric(reports, 'memory_usage')
        active_miners = len(set(r['node_id'] for r in reports if r.get('mining_active')))

        if avg_temp and avg_temp > 75:
            recommendations.append("Network experiencing high temperatures - recommend improved cooling across miners")

        if avg_memory and avg_memory > 85:
            recommendations.append("High memory usage detected network-wide - investigate potential memory leaks")

        if active_miners < 3:
            recommendations.append("Low miner participation - encourage more nodes to join mining pool")

        # Geographic diversity check
        locations = set(r.get('location', 'unknown') for r in reports)
        if len(locations) < 3:
            recommendations.append("Low geographic diversity - consider expanding to more regions")

        return recommendations

        # Get miner status and intelligence data
        @self.app.route(f'/api/{self.api_version}/nodes/status', methods=['GET'])
        def get_miner_status():
            """Get comprehensive miner status and network intelligence for dashboard"""
            try:
                # Get query parameters
                hours_back = float(request.args.get('hours', 1))  # Default last 1 hour
                include_intelligence = request.args.get('intelligence', 'true').lower() == 'true'

                current_time = time.time()
                cutoff_time = current_time - (hours_back * 3600)

                # Aggregate miner status data
                active_miners = []
                total_hashrate = 0.0
                total_blocks_mined = 0
                miners_by_location = {}
                miners_by_hardware = {}

                if hasattr(self, 'miner_status_reports'):
                    for node_id, reports in self.miner_status_reports.items():
                        # Get most recent report within time window
                        recent_reports = [r for r in reports if r['reported_at'] >= cutoff_time]
                        if recent_reports:
                            latest_report = recent_reports[-1]

                            miner_data = {
                                'node_id': node_id,
                                'mining_active': latest_report['mining_active'],
                                'hashrate': latest_report['hashrate'],
                                'blocks_mined': latest_report['blocks_mined'],
                                'temperature': latest_report['temperature'],
                                'memory_usage': latest_report['memory_usage'],
                                'location': latest_report['location'],
                                'hardware_model': latest_report['hardware_model'],
                                'wallet_address': latest_report['wallet_address'],
                                'last_report': latest_report['reported_at'],
                                'network_metrics': latest_report['network_metrics'],
                                'system_health': latest_report['system_health']
                            }

                            active_miners.append(miner_data)

                            if latest_report['mining_active']:
                                total_hashrate += latest_report['hashrate']
                                total_blocks_mined += latest_report['blocks_mined']

                            # Aggregate by location
                            location = latest_report['location']
                            if location not in miners_by_location:
                                miners_by_location[location] = []
                            miners_by_location[location].append(miner_data)

                            # Aggregate by hardware
                            hardware = latest_report['hardware_model']
                            if hardware not in miners_by_hardware:
                                miners_by_hardware[hardware] = []
                            miners_by_hardware[hardware].append(miner_data)

                # Prepare response
                response_data = {
                    'time_window_hours': hours_back,
                    'total_active_miners': len(active_miners),
                    'mining_miners': len([m for m in active_miners if m['mining_active']]),
                    'total_network_hashrate': total_hashrate,
                    'total_blocks_mined_recently': total_blocks_mined,
                    'miners': active_miners,
                    'aggregation': {
                        'by_location': {
                            location: {
                                'count': len(miners),
                                'total_hashrate': sum(m['hashrate'] for m in miners if m['mining_active']),
                                'avg_temperature': sum(m['temperature'] for m in miners if m['temperature']) / len([m for m in miners if m['temperature']]) if any(m['temperature'] for m in miners) else 0
                            }
                            for location, miners in miners_by_location.items()
                        },
                        'by_hardware': {
                            hardware: {
                                'count': len(miners),
                                'total_hashrate': sum(m['hashrate'] for m in miners if m['mining_active']),
                                'models': list(set(m['hardware_model'] for m in miners))
                            }
                            for hardware, miners in miners_by_hardware.items()
                        }
                    }
                }

                # Add intelligence data if requested
                if include_intelligence:
                    response_data['intelligence'] = self._get_miner_intelligence(hours_back)

                return jsonify(response_data)

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

    def _get_fallback_bootstrap_peers(self) -> List[Dict[str, Any]]:
        """Get fallback peers from external bootstrap servers"""
        fallback_peers = []

        # Try external bootstrap servers
        bootstrap_urls = [
            "https://bootstrap.pisecure.org/api/v1/bootstrap/peers",
            "https://pisecure-bootstrap-production.up.railway.app/api/v1/bootstrap/peers"
        ]

        for url in bootstrap_urls:
            try:
                import requests
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    peers = data.get('peers', [])
                    if peers:
                        fallback_peers.extend(peers[:10])  # Limit to 10 peers per server
                        logger.debug(f"Got {len(peers)} peers from {url}")
                        break  # Found working peers
            except Exception as e:
                logger.debug(f"Failed to get peers from {url}: {e}")
                continue

        logger.info(f"Retrieved {len(fallback_peers)} fallback bootstrap peers")
        return fallback_peers

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

    def run(self, debug: bool = False, ssl_enabled: str = "auto", ssl_cert: str = None, ssl_key: str = None):
        """
        Start the API server with automatic network discovery and P2P sync.

        Args:
            debug: Enable debug mode
            ssl_enabled: SSL mode - "auto", "force", "disable", or "optional"
            ssl_cert: Path to SSL certificate file
            ssl_key: Path to SSL private key file
        """
        # Determine SSL requirement based on configuration and environment
        ssl_required, ssl_reason = self._determine_ssl_requirement(ssl_enabled)

        # Setup SSL/TLS encryption
        ssl_context = None
        protocol = "http"

        if ssl_required:
            try:
                ssl_context = self._setup_ssl_context(ssl_cert, ssl_key)
                protocol = "https"
                logger.info(f"🔒 SSL/TLS encryption enabled - {ssl_reason}")
            except Exception as e:
                if ssl_enabled == "force":
                    logger.error(f"❌ SSL is required but setup failed: {e}")
                    logger.error("Cannot start server without SSL in force mode")
                    return
                else:
                    logger.warning(f"⚠️ SSL setup failed: {e}")
                    logger.warning("🔓 Falling back to HTTP - not recommended for public access")
                    ssl_context = None
                    protocol = "http"
        else:
            logger.info(f"🔓 HTTP mode enabled - {ssl_reason}")

        # Determine node mode based on host binding
        node_mode = "Full Node" if self.host == '0.0.0.0' else "Outbound-Only"
        logger.info(f"🚀 Starting PiSecure API Server on {protocol}://{self.host}:{self.port}")
        logger.info(f"📡 Node Mode: {node_mode} (incoming connections {'enabled' if self.host == '0.0.0.0' else 'disabled'})")
        logger.info(f"📚 API Documentation: {protocol}://{self.host}:{self.port}/api/{self.api_version}/docs")

        # Register this node with bootstrap service
        import os
        bootstrap_urls_env = os.getenv('BOOTSTRAP_URLS')
        if bootstrap_urls_env:
            self.bootstrap_urls = [url.strip() for url in bootstrap_urls_env.split(',')]
        else:
            self.bootstrap_urls = [
                "https://bootstrap.pisecure.org/api/v1/nodes/register",
                "https://pisecure-bootstrap-production.up.railway.app/api/v1/nodes/register"
            ]
        self._register_with_bootstrap()

        # Start automatic network discovery
        self._start_automatic_discovery()

        # Start P2P blockchain synchronization
        self.p2p_sync.start_sync()
        logger.info("🔄 Started P2P blockchain synchronization")

        # Start heartbeat reporting
        self._start_heartbeat_reporting()

        # Start dynamic rate limiting
        self._start_dynamic_rate_limiting()

        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=debug,
                threaded=True,
                ssl_context=ssl_context
            )
        finally:
            # Clean up on shutdown
            logger.info("🛑 Shutting down P2P sync...")
            self.p2p_sync.stop_sync()
            if hasattr(self, '_heartbeat_thread'):
                self._heartbeat_thread.join(timeout=5)
            if hasattr(self, '_rate_limit_thread'):
                self._rate_limit_thread.join(timeout=5)
            if hasattr(self, '_queue_thread'):
                self._queue_thread.join(timeout=5)

    def _setup_ssl_context(self, cert_path: str = None, key_path: str = None) -> ssl.SSLContext:
        """
        Setup SSL/TLS context for HTTPS encryption.

        Args:
            cert_path: Path to SSL certificate file
            key_path: Path to SSL private key file

        Returns:
            SSL context configured for TLS 1.3
        """
        # Create SSL context with TLS 1.3 (maximum security)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.protocol = ssl.PROTOCOL_TLS
        context.minimum_version = ssl.TLSVersion.TLSv1_2  # TLS 1.2 minimum for compatibility
        context.maximum_version = ssl.TLSVersion.TLSv1_3  # TLS 1.3 maximum for security

        # Disable insecure cipher suites
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')

        # Prefer server cipher order
        context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

        # Disable compression (CRIME attack prevention)
        context.options |= ssl.OP_NO_COMPRESSION

        # Enable session resumption
        context.options |= ssl.OP_NO_TICKET

        # Load certificate and key
        if cert_path and key_path:
            if os.path.exists(cert_path) and os.path.exists(key_path):
                context.load_cert_chain(cert_path, key_path)
                logger.info(f"✅ Loaded SSL certificate: {cert_path}")
            else:
                raise FileNotFoundError(f"SSL certificate or key file not found: {cert_path}, {key_path}")
        else:
            # Generate self-signed certificate for development
            logger.warning("⚠️ No SSL certificate provided - generating self-signed certificate")
            context = self._generate_self_signed_cert(context)

        # Verify SSL context is properly configured
        if not context.certfile:
            raise ValueError("SSL context not properly configured - no certificate loaded")

        return context

    def _generate_self_signed_cert(self, context: ssl.SSLContext) -> ssl.SSLContext:
        """
        Generate a self-signed certificate for development/testing.

        Args:
            context: SSL context to configure

        Returns:
            SSL context with self-signed certificate
        """
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        import tempfile

        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Generate public key
            public_key = private_key.public_key()

            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "PiSecure"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PiSecure Foundation"),
                x509.NameAttribute(NameOID.COMMON_NAME, "pisecure.local"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                public_key
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())

            # Save to temporary files
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pem') as cert_file:
                cert_pem = cert.public_bytes(serialization.Encoding.PEM)
                cert_file.write(cert_pem)
                cert_path = cert_file.name

            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key') as key_file:
                key_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                key_file.write(key_pem)
                key_path = key_file.name

            # Load certificate into SSL context
            context.load_cert_chain(cert_path, key_path)

            # Store paths for cleanup
            self._ssl_temp_files = [cert_path, key_path]

            logger.warning("🔐 Using self-signed certificate - not suitable for production!")
            logger.warning("   Consider obtaining a proper certificate from Let's Encrypt or similar")

            return context

        except ImportError:
            raise ImportError("cryptography library required for SSL certificate generation. Install with: pip install cryptography")

    def _cleanup_ssl_temp_files(self):
        """Clean up temporary SSL certificate files"""
        if hasattr(self, '_ssl_temp_files'):
            for temp_file in self._ssl_temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    def _get_public_ip_fallback(self) -> Optional[str]:
        """Get public IP using external services as fallback"""
        services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://icanhazip.com',
            'https://ipinfo.io/ip'
        ]
        
        for service_url in services:
            try:
                import requests
                response = requests.get(service_url, timeout=5)
                if response.status_code == 200:
                    public_ip = response.text.strip()
                    # Basic validation
                    if '.' in public_ip and len(public_ip) <= 15:
                        logger.debug(f"Got public IP {public_ip} from {service_url}")
                        return public_ip
            except Exception as e:
                logger.debug(f"Failed to get IP from {service_url}: {e}")
                continue
        
        return None

    def _register_with_bootstrap(self):
        """Register this node with the bootstrap service on startup"""
        try:
            # Get node information
            node_id = self.peer_discovery.node_id
            port = self.port
            
            # Discover public IP address (for internet-wide P2P)
            host = None
            
            # Try NAT traversal methods (STUN/UPnP)
            try:
                nat_results = node_discovery.make_node_discoverable()
                endpoints = nat_results.get('endpoints', [])
                if endpoints:
                    # Use highest priority endpoint
                    best_endpoint = max(endpoints, key=lambda e: e.get('priority', 0))
                    host = best_endpoint.get('ip') or best_endpoint.get('address')
                    if host:
                        logger.info(f"🌐 Discovered public IP: {host} via {best_endpoint.get('type')}")
            except Exception as e:
                logger.debug(f"NAT traversal failed: {e}")
            
            # Try external service fallback if NAT traversal failed
            if not host:
                host = self._get_public_ip_fallback()
                if host:
                    logger.info(f"🌐 Discovered public IP: {host} via external service")
            
            # Final fallback to local address
            if not host:
                host = self.host if self.host != '0.0.0.0' else 'localhost'
                logger.info(f"ℹ️  Running in outbound-only mode (local address: {host})")
                logger.info(f"   Mining/validation works normally - incoming connections disabled")
                logger.info(f"   To help seed the network: Enable UPnP on router or forward port 3142")

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

            registered = False
            for bootstrap_url in self.bootstrap_urls:
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

    def _start_dynamic_rate_limiting(self):
        """Start dynamic rate limiting based on bootstrap intelligence"""
        try:
            if not self.dynamic_rate_limiting:
                logger.debug("Dynamic rate limiting disabled")
                return

            # Start rate limiting thread
            self._rate_limit_thread = threading.Thread(
                target=self._rate_limit_worker,
                daemon=True,
                name="DynamicRateLimiting"
            )
            self._rate_limit_thread.start()
            logger.info("🎛️ Started dynamic rate limiting with bootstrap intelligence")

            # Start request queue processor if enabled
            if self.request_queue_enabled:
                self._queue_thread = threading.Thread(
                    target=self._queue_processor,
                    daemon=True,
                    name="RequestQueue"
                )
                self._queue_thread.start()
                logger.info("📋 Started request queue processor")

        except Exception as e:
            logger.error(f"❌ Failed to start dynamic rate limiting: {e}")

    def _rate_limit_worker(self):
        """Background worker for dynamic rate limit adjustments"""
        import time

        while True:
            try:
                # Update rate limits based on network intelligence
                self._update_rate_limits()

                # Sleep until next check
                time.sleep(self.rate_limit_check_interval)

            except Exception as e:
                logger.error(f"Rate limit worker error: {e}")
                time.sleep(60)  # Wait before retry

    def _update_rate_limits(self):
        """Update rate limits based on bootstrap intelligence"""
        try:
            current_time = time.time()

            # Don't update too frequently
            if current_time - self.last_rate_limit_update < 60:  # Minimum 1 minute between updates
                return

            # Get network load prediction from bootstrap server
            load_prediction = self._get_network_load_prediction()

            if load_prediction:
                # Calculate new rate limit based on prediction
                new_limit = self._calculate_dynamic_rate_limit(load_prediction)
                self._apply_rate_limit(new_limit)

                self.last_rate_limit_update = current_time
                logger.debug(f"🎛️ Updated rate limit to {new_limit} based on network prediction")

            else:
                # Fallback: adjust based on local metrics
                self._adjust_rate_limit_locally()

        except Exception as e:
            logger.error(f"Failed to update rate limits: {e}")

    def _get_network_load_prediction(self) -> Optional[Dict[str, Any]]:
        """Get network load prediction from bootstrap server"""
        try:
            # Try bootstrap servers for load prediction
            bootstrap_urls = [
                "https://bootstrap.pisecure.org/api/v1/intelligence/predict",
                "https://pisecure-bootstrap-production.up.railway.app/api/v1/intelligence/predict"
            ]

            for url in bootstrap_urls:
                try:
                    import requests
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        prediction = response.json()
                        logger.debug(f"Got load prediction from {url}")
                        return prediction
                except Exception as e:
                    logger.debug(f"Failed to get prediction from {url}: {e}")
                    continue

            return None

        except Exception as e:
            logger.debug(f"Network load prediction error: {e}")
            return None

    def _calculate_dynamic_rate_limit(self, prediction: Dict[str, Any]) -> str:
        """Calculate dynamic rate limit based on network prediction"""
        try:
            # Extract prediction data
            predicted_connections = prediction.get('predictions', {}).get('predicted_connections', 1000)
            confidence = prediction.get('confidence', 'medium')

            # Base calculation on predicted connections
            base_limit = self.base_rate_limit

            # Adjust based on predicted load
            if predicted_connections > 2000:  # High load
                adjustment_factor = 0.5  # Reduce to 50% of base
            elif predicted_connections > 1500:  # Medium-high load
                adjustment_factor = 0.7  # Reduce to 70% of base
            elif predicted_connections > 1000:  # Medium load
                adjustment_factor = 0.9  # Reduce to 90% of base
            elif predicted_connections < 500:  # Low load
                adjustment_factor = 1.5  # Increase to 150% of base
            else:  # Normal load
                adjustment_factor = 1.0  # Keep at base

            # Adjust based on confidence
            if confidence == 'high':
                # More aggressive adjustments with high confidence
                adjustment_factor *= 1.2 if adjustment_factor < 1.0 else 0.9
            elif confidence == 'low':
                # Conservative adjustments with low confidence
                adjustment_factor = (adjustment_factor + 1.0) / 2  # Move toward 1.0

            # Calculate new limit
            new_limit = max(10, int(base_limit * adjustment_factor))  # Minimum 10 requests per minute

            return f"{new_limit} per minute"

        except Exception as e:
            logger.error(f"Failed to calculate dynamic rate limit: {e}")
            return self.base_rate_limit

    def _adjust_rate_limit_locally(self):
        """Adjust rate limits based on local server metrics"""
        try:
            # Get local system metrics
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent

            # Calculate adjustment based on local load
            if cpu_percent > 80 or memory_percent > 85:  # High local load
                adjustment_factor = 0.6
            elif cpu_percent > 60 or memory_percent > 70:  # Medium local load
                adjustment_factor = 0.8
            elif cpu_percent < 20 and memory_percent < 50:  # Low local load
                adjustment_factor = 1.3
            else:  # Normal load
                adjustment_factor = 1.0

            new_limit = max(10, int(float(self.base_rate_limit.split()[0]) * adjustment_factor))
            new_limit_str = f"{new_limit} per minute"

            if new_limit_str != self.current_rate_limit:
                self._apply_rate_limit(new_limit_str)
                logger.debug(f"🎛️ Updated rate limit to {new_limit_str} based on local metrics")

        except Exception as e:
            logger.error(f"Failed to adjust rate limit locally: {e}")

    def _apply_rate_limit(self, new_limit: str):
        """Apply new rate limit to the limiter"""
        try:
            # Update the limiter's default limits
            self.limiter.default_limits = [new_limit]
            self.current_rate_limit = new_limit

            logger.info(f"🎛️ Applied new rate limit: {new_limit}")

        except Exception as e:
            logger.error(f"Failed to apply rate limit {new_limit}: {e}")

    def _queue_processor(self):
        """Process queued requests during high load periods"""
        import time

        while True:
            try:
                # Process queued requests if we have capacity
                current_load = self._assess_current_load()

                if current_load < 0.8:  # Less than 80% load
                    requests_to_process = min(len(self.request_queue), 5)  # Process up to 5 at a time

                    for _ in range(requests_to_process):
                        if self.request_queue:
                            queued_request = self.request_queue.pop(0)
                            # In a full implementation, you'd replay the request
                            logger.debug(f"📋 Processing queued request: {queued_request.get('endpoint', 'unknown')}")

                # Sleep before next check
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                time.sleep(30)

    def _assess_current_load(self) -> float:
        """Assess current server load (0.0 to 1.0)"""
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
            memory_percent = psutil.virtual_memory().percent / 100.0

            # Calculate combined load
            load = (cpu_percent * 0.6) + (memory_percent * 0.4)  # Weight CPU more heavily

            return min(1.0, load)

        except Exception as e:
            logger.debug(f"Load assessment error: {e}")
            return 0.5  # Assume medium load on error

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
                sent = False
                for bootstrap_url in self.bootstrap_urls:
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

    def _determine_ssl_requirement(self, ssl_enabled: str) -> tuple[bool, str]:
        """
        Determine if SSL is required based on configuration and environment.

        Args:
            ssl_enabled: SSL mode from command line/env

        Returns:
            Tuple of (ssl_required, reason)
        """
        # Force SSL mode
        if ssl_enabled == "force":
            return True, "SSL explicitly forced by configuration"

        # Disable SSL mode
        if ssl_enabled == "disable":
            return False, "SSL explicitly disabled by configuration"

        # Check environment variables
        if os.getenv('PISECURE_REQUIRE_SSL', '').lower() in ('true', '1', 'yes'):
            return True, "SSL required by environment variable"

        # Check if server is bound to public interfaces
        if self.host not in ['localhost', '127.0.0.1', '::1']:
            try:
                # Try to detect if we have public IP access
                import socket
                import urllib.request

                # Check if we can reach external services (indicating internet access)
                try:
                    with urllib.request.urlopen('https://httpbin.org/ip', timeout=5) as response:
                        data = json.loads(response.read().decode())
                        public_ip = data.get('origin', '').split(',')[0].strip()

                        # If we have a public IP, SSL is recommended
                        if public_ip and not public_ip.startswith(('127.', '192.168.', '10.', '172.')):
                            return True, f"Public IP detected ({public_ip}) - SSL recommended for security"

                except Exception:
                    # Can't determine public IP, be conservative
                    if self.host in ['0.0.0.0', '*', '::']:
                        return True, "Server bound to all interfaces - SSL recommended for security"

            except Exception:
                pass

        # Default: SSL optional for local development
        return False, "Local development - SSL optional"


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