"""
PiSecure 314ST Token Economics
==============================

Advanced tokenomics system implementing:
- 314ST-powered API access control
- Developer trust funds
- Multi-stakeholder fee distribution
- Foundation trust governance
- Subscription management
"""

import time
import json
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature


class TrustType(Enum):
    PUBLIC = "public"                    # Free access for all (developer pays)
    SUBSCRIBER_ALL = "subscriber_all"    # All subscribers pay equally
    SUBSCRIBER_INDIVIDUAL = "subscriber_individual"  # Per-user subscriptions
    HYBRID = "hybrid"                    # Mix of free and paid access


class TrustVisibility(Enum):
    PUBLIC = "public"      # Anyone can discover and join
    PRIVATE = "private"    # Invite-only, developer controlled


@dataclass
class SubscriptionPlan:
    plan_id: str
    name: str
    monthly_cost_314st: float
    features: List[str]
    limits: Dict[str, Any]
    active: bool = True


@dataclass
class UserSubscription:
    user_id: str
    plan_id: str
    trust_id: str
    start_date: float
    last_payment: float
    auto_renew: bool
    usage_this_period: float


class FeeDistribution:
    """Multi-stakeholder fee distribution system"""

    def __init__(self):
        self.distribution_rules = {
            'miner': 0.60,           # 60% to block miner
            'stakers': 0.20,         # 20% to token stakers
            'loan_holders': 0.10,   # 10% to PiSecure loan holders
            'foundation': 0.05,     # 5% to 314ST Foundation
            'burn': 0.05            # 5% burned (deflationary)
        }

    def distribute_transaction_fee(self, fee_amount: float, miner_address: str) -> Dict[str, Any]:
        """Distribute transaction fee across all stakeholders"""
        distributions = {}

        # Miner reward (60%)
        miner_reward = fee_amount * self.distribution_rules['miner']
        distributions['miner'] = {'address': miner_address, 'amount': miner_reward}

        # Staker rewards (20%) - proportional to stake
        staker_pool = fee_amount * self.distribution_rules['stakers']
        staker_distributions = self._calculate_staker_rewards(staker_pool)
        distributions['stakers'] = staker_distributions

        # Loan holder rewards (10%)
        loan_pool = fee_amount * self.distribution_rules['loan_holders']
        loan_distributions = self._calculate_loan_holder_rewards(loan_pool)
        distributions['loan_holders'] = loan_distributions

        # Foundation contribution (5%)
        foundation_amount = fee_amount * self.distribution_rules['foundation']
        distributions['foundation'] = {'address': 'foundation_trust', 'amount': foundation_amount}

        # Burn tokens (5%)
        burn_amount = fee_amount * self.distribution_rules['burn']
        distributions['burn'] = {'address': 'burn_address', 'amount': burn_amount}

        return distributions

    def _calculate_staker_rewards(self, total_amount: float) -> List[Dict[str, Any]]:
        """Calculate proportional rewards for token stakers"""
        # Simplified: equal distribution among active stakers
        # In reality, this would query the staking contract
        active_stakers = self._get_active_stakers()
        if not active_stakers:
            return []

        reward_per_staker = total_amount / len(active_stakers)
        return [
            {'address': staker, 'amount': reward_per_staker}
            for staker in active_stakers
        ]

    def _calculate_loan_holder_rewards(self, total_amount: float) -> List[Dict[str, Any]]:
        """Calculate rewards for PiSecure loan holders"""
        # Simplified: distribution to loan contract holders
        loan_holders = self._get_loan_holders()
        if not loan_holders:
            return []

        reward_per_holder = total_amount / len(loan_holders)
        return [
            {'address': holder, 'amount': reward_per_holder}
            for holder in loan_holders
        ]

    def _get_active_stakers(self) -> List[str]:
        """Get list of active token stakers"""
        # Placeholder - would query staking contract
        return ['staker_1', 'staker_2', 'staker_3']

    def _get_loan_holders(self) -> List[str]:
        """Get list of loan holders"""
        # Placeholder - would query loan contract
        return ['loan_holder_1', 'loan_holder_2']


class DeveloperTrust:
    """Developer trust fund for end-user API access"""

    def __init__(self, trust_id: str, developer_address: str,
                 trust_type: TrustType, initial_funding: float = 0):
        self.trust_id = trust_id
        self.developer = developer_address
        self.trust_type = trust_type
        self.balance = initial_funding
        self.visibility = TrustVisibility.PUBLIC
        self.subscribers: Dict[str, UserSubscription] = {}
        self.free_access_users: set = set()
        self.subscription_plans: Dict[str, SubscriptionPlan] = {}
        self.daily_usage: Dict[str, float] = {}
        self.created_at = time.time()

    def fund_trust(self, amount: float) -> bool:
        """Add tokens to trust fund"""
        if amount <= 0:
            return False
        self.balance += amount
        return True

    def set_visibility(self, visibility: TrustVisibility):
        """Set trust visibility"""
        self.visibility = visibility

    def create_subscription_plan(self, plan_data: Dict[str, Any]) -> str:
        """Create a new subscription plan"""
        plan_id = f"plan_{hashlib.sha256(json.dumps(plan_data, sort_keys=True).encode()).hexdigest()[:16]}"

        plan = SubscriptionPlan(
            plan_id=plan_id,
            name=plan_data['name'],
            monthly_cost_314st=plan_data['monthly_cost'],
            features=plan_data['features'],
            limits=plan_data['limits']
        )

        self.subscription_plans[plan_id] = plan
        return plan_id

    def add_subscriber(self, user_id: str, plan_id: str) -> bool:
        """Add a paying subscriber"""
        if plan_id not in self.subscription_plans:
            return False

        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            trust_id=self.trust_id,
            start_date=time.time(),
            last_payment=time.time(),
            auto_renew=True,
            usage_this_period=0
        )

        self.subscribers[user_id] = subscription
        return True

    def grant_free_access(self, user_id: str) -> bool:
        """Grant unlimited access to a user"""
        self.free_access_users.add(user_id)
        return True

    def check_access(self, user_id: str, operation_cost: float) -> tuple[bool, str]:
        """Check if user can perform operation and deduct cost"""

        # Free access users
        if user_id in self.free_access_users:
            return True, "Free access granted"

        # Check subscription
        if user_id in self.subscribers:
            return self._check_subscription_access(user_id, operation_cost)

        # Public trust - use trust funds
        if self.trust_type == TrustType.PUBLIC:
            return self._check_public_access(operation_cost)

        return False, "Access denied"

    def _check_subscription_access(self, user_id: str, operation_cost: float) -> tuple[bool, str]:
        """Check subscription-based access"""
        subscription = self.subscribers[user_id]
        plan = self.subscription_plans[subscription.plan_id]

        # Check usage limits
        daily_used = self.daily_usage.get(user_id, 0)
        daily_limit = plan.limits.get('daily_cost_limit', float('inf'))

        if daily_used + operation_cost > daily_limit:
            return False, "Daily usage limit exceeded"

        # Deduct from usage tracking
        self.daily_usage[user_id] = daily_used + operation_cost
        return True, "Subscription access granted"

    def _check_public_access(self, operation_cost: float) -> tuple[bool, str]:
        """Check public access using trust funds"""
        if self.balance >= operation_cost:
            self.balance -= operation_cost
            return True, "Public access granted"
        return False, "Trust fund depleted"

    def process_monthly_billing(self) -> List[Dict[str, Any]]:
        """Process monthly subscription payments"""
        billing_events = []

        for user_id, subscription in list(self.subscribers.items()):
            plan = self.subscription_plans[subscription.plan_id]
            monthly_cost = plan.monthly_cost_314st

            # Check if payment is due (simplified monthly check)
            days_since_payment = (time.time() - subscription.last_payment) / 86400
            if days_since_payment >= 30:
                if self.balance >= monthly_cost:
                    self.balance -= monthly_cost
                    subscription.last_payment = time.time()
                    billing_events.append({
                        'user_id': user_id,
                        'amount': monthly_cost,
                        'status': 'paid'
                    })
                else:
                    # Cancel subscription if payment fails
                    del self.subscribers[user_id]
                    billing_events.append({
                        'user_id': user_id,
                        'amount': monthly_cost,
                        'status': 'cancelled'
                    })

        return billing_events

    def get_status(self) -> Dict[str, Any]:
        """Get trust status"""
        return {
            'trust_id': self.trust_id,
            'developer': self.developer,
            'trust_type': self.trust_type.value,
            'visibility': self.visibility.value,
            'balance': self.balance,
            'subscribers_count': len(self.subscribers),
            'free_users_count': len(self.free_access_users),
            'plans_count': len(self.subscription_plans),
            'created_at': self.created_at
        }


class FoundationTrust:
    """314ST Foundation community trust - secured by genesis private key"""

    def __init__(self):
        self.address = 'foundation_314st'
        self.balance = 0
        self.genesis_private_key = self._load_genesis_private_key()
        self.genesis_public_key = self._load_genesis_public_key()

        self.allocation_rules = {
            'development': 0.40,      # 40% Core development
            'grants': 0.30,          # 30% Developer grants
            'marketing': 0.15,       # 15% Ecosystem growth
            'reserve': 0.15          # 15% Strategic reserve
        }
        self.funds_allocated = {category: 0 for category in self.allocation_rules}
        self.active_grants: List[Dict[str, Any]] = []
        self.governance_proposals: List[Dict[str, Any]] = []
        self.transaction_log: List[Dict[str, Any]] = []

    def _load_genesis_private_key(self):
        """Load genesis private key from file"""
        try:
            priv_key_path = Path(__file__).parent.parent / 'updates' / 'genesis_auth_priv.key'
            with open(priv_key_path, 'rb') as f:
                private_key_data = f.read()

            # Try to load as PEM format
            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=None
            )
            return private_key
        except Exception as e:
            raise RuntimeError(f"Failed to load genesis private key: {e}")

    def _load_genesis_public_key(self):
        """Load genesis public key from file"""
        try:
            pub_key_path = Path(__file__).parent.parent / 'updates' / 'genesis_auth_pub.key'
            with open(pub_key_path, 'rb') as f:
                public_key_data = f.read()

            # Try to load as PEM format
            public_key = serialization.load_pem_public_key(public_key_data)
            return public_key
        except Exception as e:
            raise RuntimeError(f"Failed to load genesis public key: {e}")

    def receive_contribution(self, amount: float, source: str):
        """Receive fee contribution"""
        self.balance += amount

    def allocate_funds(self) -> Dict[str, float]:
        """Allocate funds according to rules"""
        allocations = {}

        for category, percentage in self.allocation_rules.items():
            allocation_amount = self.balance * percentage
            if allocation_amount > 0:
                self.funds_allocated[category] += allocation_amount
                allocations[category] = allocation_amount
                self.balance -= allocation_amount

        return allocations

    def create_grant(self, project_data: Dict[str, Any]) -> str:
        """Create a developer grant"""
        grant_id = f"grant_{hashlib.sha256(json.dumps(project_data, sort_keys=True).encode()).hexdigest()[:16]}"

        grant = {
            'grant_id': grant_id,
            'project_name': project_data['project_name'],
            'developer': project_data['developer'],
            'funding_requested': project_data['funding_requested'],
            'milestones': project_data['milestones'],
            'status': 'pending_review',
            'created_at': time.time(),
            'votes_for': 0,
            'votes_against': 0
        }

        self.active_grants.append(grant)
        return grant_id

    def vote_on_grant(self, grant_id: str, voter_address: str, vote: bool, voting_power: float):
        """Vote on grant proposal"""
        for grant in self.active_grants:
            if grant['grant_id'] == grant_id:
                if vote:
                    grant['votes_for'] += voting_power
                else:
                    grant['votes_against'] += voting_power
                break

    def approve_grant(self, grant_id: str) -> bool:
        """Approve grant if it has majority support"""
        for grant in self.active_grants:
            if grant['grant_id'] == grant_id:
                total_votes = grant['votes_for'] + grant['votes_against']
                if total_votes > 0 and grant['votes_for'] / total_votes > 0.5:
                    grant['status'] = 'approved'
                    return True
        return False

    def sign_foundation_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """Sign foundation transaction with genesis private key"""
        # Create canonical transaction representation
        tx_string = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))

        # Sign with genesis private key
        signature = self.genesis_private_key.sign(
            tx_string.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Return hex-encoded signature
        return signature.hex()

    def verify_foundation_transaction(self, transaction_data: Dict[str, Any], signature: str) -> bool:
        """Verify foundation transaction signature with genesis public key"""
        try:
            # Create canonical transaction representation
            tx_string = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))

            # Decode signature
            signature_bytes = bytes.fromhex(signature)

            # Verify with genesis public key
            self.genesis_public_key.verify(
                signature_bytes,
                tx_string.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    def execute_foundation_transaction(self, transaction_data: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """Execute a foundation transaction if signature is valid"""
        # Verify signature first
        if not self.verify_foundation_transaction(transaction_data, signature):
            return {'success': False, 'error': 'Invalid genesis signature'}

        tx_type = transaction_data.get('type')
        amount = transaction_data.get('amount', 0)
        recipient = transaction_data.get('recipient')
        purpose = transaction_data.get('purpose', 'unspecified')

        # Execute based on transaction type
        if tx_type == 'fund_allocation':
            return self._execute_allocation_transaction(amount, recipient, purpose)
        elif tx_type == 'grant_payment':
            return self._execute_grant_transaction(amount, recipient, purpose)
        elif tx_type == 'reserve_transfer':
            return self._execute_reserve_transaction(amount, recipient, purpose)
        else:
            return {'success': False, 'error': 'Unknown transaction type'}

    def _execute_allocation_transaction(self, amount: float, category: str, purpose: str) -> Dict[str, Any]:
        """Execute fund allocation to development categories"""
        if amount > self.balance:
            return {'success': False, 'error': 'Insufficient foundation balance'}

        if category not in self.allocation_rules:
            return {'success': False, 'error': 'Invalid allocation category'}

        # Execute allocation
        self.funds_allocated[category] += amount
        self.balance -= amount

        # Log transaction
        self._log_transaction({
            'type': 'allocation',
            'category': category,
            'amount': amount,
            'purpose': purpose,
            'timestamp': time.time()
        })

        return {
            'success': True,
            'transaction_type': 'allocation',
            'category': category,
            'amount': amount,
            'new_balance': self.balance
        }

    def _execute_grant_transaction(self, amount: float, grant_id: str, purpose: str) -> Dict[str, Any]:
        """Execute grant payment"""
        if amount > self.balance:
            return {'success': False, 'error': 'Insufficient foundation balance'}

        # Find grant
        grant = None
        for g in self.active_grants:
            if g['grant_id'] == grant_id:
                grant = g
                break

        if not grant:
            return {'success': False, 'error': 'Grant not found'}

        if grant['status'] != 'approved':
            return {'success': False, 'error': 'Grant not approved'}

        # Execute payment (simplified - would transfer to grant recipient)
        self.balance -= amount

        # Log transaction
        self._log_transaction({
            'type': 'grant_payment',
            'grant_id': grant_id,
            'amount': amount,
            'recipient': grant['developer'],
            'purpose': purpose,
            'timestamp': time.time()
        })

        return {
            'success': True,
            'transaction_type': 'grant_payment',
            'grant_id': grant_id,
            'amount': amount,
            'recipient': grant['developer'],
            'new_balance': self.balance
        }

    def _execute_reserve_transaction(self, amount: float, purpose: str, details: str) -> Dict[str, Any]:
        """Execute reserve fund transaction"""
        if amount > self.balance:
            return {'success': False, 'error': 'Insufficient foundation balance'}

        # Execute transfer to reserve
        self.funds_allocated['reserve'] += amount
        self.balance -= amount

        # Log transaction
        self._log_transaction({
            'type': 'reserve_transfer',
            'amount': amount,
            'purpose': purpose,
            'details': details,
            'timestamp': time.time()
        })

        return {
            'success': True,
            'transaction_type': 'reserve_transfer',
            'amount': amount,
            'new_balance': self.balance
        }

    def _log_transaction(self, transaction: Dict[str, Any]):
        """Log foundation transaction for transparency"""
        self.transaction_log.append(transaction)

        # Keep only last 1000 transactions to prevent unbounded growth
        if len(self.transaction_log) > 1000:
            self.transaction_log = self.transaction_log[-1000:]

    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get foundation transaction history"""
        return self.transaction_log[-limit:] if limit > 0 else self.transaction_log

    def get_status(self) -> Dict[str, Any]:
        """Get foundation status"""
        return {
            'address': self.address,
            'balance': self.balance,
            'funds_allocated': self.funds_allocated,
            'active_grants': len(self.active_grants),
            'allocation_rules': self.allocation_rules,
            'total_transactions': len(self.transaction_log),
            'genesis_key_loaded': self.genesis_private_key is not None
        }


class EndUserWallet:
    """Invisible blockchain wallet for end users"""

    def __init__(self, user_identifier: str, developer_trust: Optional[DeveloperTrust] = None):
        # Create privacy-preserving user ID
        self.user_id = hashlib.sha256(user_identifier.encode()).hexdigest()
        self.trust = developer_trust
        self.created_at = time.time()

    def make_api_call(self, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API call using trust funds"""
        if not self.trust:
            return {'error': 'No trust fund configured'}

        # Calculate operation cost (simplified)
        operation_cost = self._calculate_cost(operation, params or {})

        # Check access and deduct cost
        can_access, message = self.trust.check_access(self.user_id, operation_cost)

        if not can_access:
            return {'error': message}

        # Simulate API call (would call actual PiSecure API)
        result = self._execute_operation(operation, params or {})
        result['cost'] = operation_cost
        result['trust_balance'] = self.trust.balance

        return result

    def _calculate_cost(self, operation: str, params: Dict[str, Any]) -> float:
        """Calculate operation cost in 314ST"""
        base_costs = {
            'get_weather': 0.001,
            'send_message': 0.002,
            'store_data': 0.005,
            'query_database': 0.001,
            'run_analysis': 0.01
        }

        base_cost = base_costs.get(operation, 0.001)

        # Adjust based on parameters
        if 'data_size' in params:
            base_cost *= (1 + params['data_size'] / 1000)  # Scale with data size

        return base_cost

    def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual operation (simplified)"""
        # This would call the real PiSecure API
        return {
            'operation': operation,
            'params': params,
            'result': f'Successfully executed {operation}',
            'timestamp': time.time()
        }


class TokenEconomics:
    """314ST token economics management"""

    def __init__(self):
        self.fee_distributor = FeeDistribution()
        self.foundation_trust = FoundationTrust()
        self.developer_trusts: Dict[str, DeveloperTrust] = {}
        self.api_costs = self._initialize_api_costs()

    def _initialize_api_costs(self) -> Dict[str, float]:
        """Initialize API operation costs in 314ST"""
        return {
            # Basic operations
            'health_check': 0.0001,
            'get_blockchain_info': 0.0005,

            # Data operations
            'submit_transaction': 0.001,
            'get_transaction': 0.0001,
            'get_wallet_balance': 0.0002,

            # Advanced operations
            'bulk_query': 0.01,
            'analytics_query': 0.1,
            'export_data': 0.05,

            # Developer operations
            'create_trust': 0.1,
            'manage_subscription': 0.01,
            'foundation_vote': 0.001
        }

    def calculate_api_cost(self, operation: str, params: Dict[str, Any] = None) -> float:
        """Calculate cost for API operation"""
        base_cost = self.api_costs.get(operation, 0.001)
        params = params or {}

        # Scale costs based on parameters
        if operation == 'bulk_query' and 'limit' in params:
            base_cost *= min(params['limit'] / 100, 10)  # Max 10x multiplier

        if operation == 'export_data' and 'size_mb' in params:
            base_cost *= (1 + params['size_mb'])  # Scale with data size

        return base_cost

    def process_transaction_fee(self, fee_amount: float, miner_address: str) -> Dict[str, Any]:
        """Process transaction fee distribution"""
        distributions = self.fee_distributor.distribute_transaction_fee(fee_amount, miner_address)

        # Send foundation contribution
        if 'foundation' in distributions:
            foundation_amount = distributions['foundation']['amount']
            self.foundation_trust.receive_contribution(foundation_amount, 'transaction_fee')

        return distributions

    def create_developer_trust(self, trust_id: str, developer_address: str,
                              trust_type: TrustType, initial_funding: float = 0) -> DeveloperTrust:
        """Create a new developer trust"""
        trust = DeveloperTrust(trust_id, developer_address, trust_type, initial_funding)
        self.developer_trusts[trust_id] = trust
        return trust

    def get_trust(self, trust_id: str) -> Optional[DeveloperTrust]:
        """Get developer trust by ID"""
        return self.developer_trusts.get(trust_id)

    def get_foundation_status(self) -> Dict[str, Any]:
        """Get foundation trust status"""
        return self.foundation_trust.get_status()

    def process_monthly_billing(self) -> Dict[str, List[Dict[str, Any]]]:
        """Process monthly billing for all trusts"""
        billing_results = {}

        for trust_id, trust in self.developer_trusts.items():
            billing_events = trust.process_monthly_billing()
            if billing_events:
                billing_results[trust_id] = billing_events

        return billing_results


# Global instances
fee_distributor = FeeDistribution()
foundation_trust = None  # Lazy loaded - only created when needed
token_economics = TokenEconomics()


def get_foundation_trust():
    """
    Lazy load foundation trust only when needed for foundation operations.
    This allows the API server to start without requiring genesis keys.
    """
    global foundation_trust
    if foundation_trust is None:
        try:
            foundation_trust = FoundationTrust()
        except RuntimeError as e:
            # If genesis keys are not available, foundation operations are disabled
            # This is normal for end-user installations
            return None
    return foundation_trust

__all__ = [
    'TrustType',
    'TrustVisibility',
    'SubscriptionPlan',
    'UserSubscription',
    'FeeDistribution',
    'DeveloperTrust',
    'FoundationTrust',
    'EndUserWallet',
    'TokenEconomics',
    'fee_distributor',
    'foundation_trust',
    'token_economics'
]