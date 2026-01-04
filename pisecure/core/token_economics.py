#!/usr/bin/env python3
"""
PiSecure 314ST Token Economics System
=====================================

Comprehensive token economics implementation including:
- Developer trust funds and subscriptions
- Foundation operations and grants
- Fee distribution and burning mechanisms
- Economic data tracking and analytics
- Cross-exchange settlement systems
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

from .blockchain import SignChain
from .consensus import PiSecureConsensus, Syndicate

logger = logging.getLogger(__name__)

class TrustType(Enum):
    """Types of developer trust funds"""
    PUBLIC = "public"
    PRIVATE = "private"
    FOUNDATION = "foundation"
    EXCHANGE = "exchange"

@dataclass
class TrustFund:
    """Developer trust fund structure"""
    trust_id: str
    developer_address: str
    trust_type: TrustType
    balance: float
    total_funding: float
    subscribers: int
    monthly_revenue: float
    created_at: float
    last_activity: float
    subscription_plans: List[Dict[str, Any]]
    revenue_history: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['trust_type'] = self.trust_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrustFund':
        data_copy = data.copy()
        data_copy['trust_type'] = TrustType(data['trust_type'])
        return cls(**data_copy)

@dataclass
class Subscription:
    """User subscription to trust fund"""
    subscription_id: str
    user_address: str
    trust_id: str
    plan_id: str
    amount: float
    billing_cycle: str  # monthly, yearly
    next_billing: float
    status: str  # active, cancelled, expired
    created_at: float
    last_payment: float
    payments: List[Dict[str, Any]]

class EconomicMetrics:
    """Economic data tracking and analytics"""

    def __init__(self):
        self.total_supply = 100000000.0  # 100M 314ST tokens total
        self.circulating_supply = 25000000.0  # 25M currently circulating
        self.burned_tokens = 0.0
        self.foundation_balance = 10000000.0  # 10M foundation reserve

        # Fee distribution tracking
        self.fee_distribution = {
            'foundation_share': 0.1,  # 10% to foundation
            'miner_share': 0.5,       # 50% to miners
            'developer_trusts': 0.3,  # 30% to developer trusts
            'burn_rate': 0.1          # 10% burned
        }

        # Transaction fee structure
        self.fee_structure = {
            'transaction_fee': 0.001,    # 0.1% of transaction value
            'api_call_fee': 0.0001,      # 0.01% for API calls
            'name_registration': 5.0,    # Fixed 5 tokens for PiNS
            'trust_creation': 100.0,     # Fixed 100 tokens to create trust
            'exchange_listing': 1000.0   # Fixed 1000 tokens for exchange listing
        }

        # Historical data
        self.price_history: List[Dict[str, Any]] = []
        self.volume_history: List[Dict[str, Any]] = []
        self.staking_rewards: List[Dict[str, Any]] = []

        # Exchange rates (simulated)
        self.exchange_rates = {
            'usd': 0.10,    # $0.10 per 314ST
            'eur': 0.09,    # €0.09 per 314ST
            'btc': 0.000001 # 0.000001 BTC per 314ST
        }

    def calculate_transaction_fee(self, transaction_value: float,
                                transaction_type: str = 'transfer') -> float:
        """Calculate fee for transaction"""
        base_fee = transaction_value * self.fee_structure['transaction_fee']

        # Minimum fees
        min_fees = {
            'transfer': 0.01,
            'trust_funding': 0.1,
            'name_registration': 5.0,
            'exchange_settlement': 1.0
        }

        return max(base_fee, min_fees.get(transaction_type, 0.01))

    def distribute_transaction_fee(self, fee_amount: float) -> Dict[str, float]:
        """Distribute transaction fee according to economic rules"""
        distribution = {}

        # Foundation share
        distribution['foundation'] = fee_amount * self.fee_distribution['foundation_share']

        # Developer trusts share (distributed proportionally)
        distribution['developer_trusts'] = fee_amount * self.fee_distribution['developer_trusts']

        # Burn tokens
        distribution['burned'] = fee_amount * self.fee_distribution['burn_rate']

        # Miner share (remainder)
        distribution['miners'] = fee_amount * self.fee_distribution['miner_share']

        return distribution

    def update_price_data(self, price_usd: float, volume_24h: float):
        """Update price and volume data"""
        timestamp = time.time()

        self.price_history.append({
            'timestamp': timestamp,
            'price_usd': price_usd,
            'volume_24h': volume_24h,
            'market_cap': self.circulating_supply * price_usd
        })

        # Keep only last 30 days
        cutoff = timestamp - (30 * 24 * 60 * 60)
        self.price_history = [p for p in self.price_history if p['timestamp'] > cutoff]

        # Update exchange rates
        self.exchange_rates['usd'] = price_usd

    def get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        current_price = self.price_history[-1] if self.price_history else {'price_usd': 0.10}

        return {
            'current_price_usd': current_price['price_usd'],
            'volume_24h': current_price.get('volume_24h', 0),
            'market_cap': self.circulating_supply * current_price['price_usd'],
            'circulating_supply': self.circulating_supply,
            'total_supply': self.total_supply,
            'burned_tokens': self.burned_tokens,
            'exchange_rates': self.exchange_rates,
            'price_change_24h': self._calculate_price_change()
        }

    def _calculate_price_change(self) -> float:
        """Calculate 24h price change percentage"""
        if len(self.price_history) < 2:
            return 0.0

        current = self.price_history[-1]['price_usd']
        previous = self.price_history[-2]['price_usd']

        if previous == 0:
            return 0.0

        return ((current - previous) / previous) * 100

class TokenEconomicsEngine:
    """
    Comprehensive 314ST token economics engine

    Manages:
    - Developer trust funds and subscriptions
    - Foundation operations and grants
    - Fee distribution and burning
    - Economic data tracking
    - Cross-exchange settlement
    """

    def __init__(self, blockchain: Optional[SignChain] = None):
        self.blockchain = blockchain

        # Core data structures
        self.trust_funds: Dict[str, TrustFund] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        self.economic_metrics = EconomicMetrics()

        # Foundation data
        self.foundation_grants: List[Dict[str, Any]] = []
        self.foundation_transactions: List[Dict[str, Any]] = []
        self.genesis_key_loaded = False

        # Cross-exchange settlement
        self.pending_settlements: Dict[str, Dict[str, Any]] = {}

        # Threading
        self.economics_thread: Optional[threading.Thread] = None
        self.running = False

        # Statistics
        self.stats = {
            'total_trust_funds': 0,
            'active_subscriptions': 0,
            'monthly_revenue': 0.0,
            'foundation_grants': 0,
            'burned_tokens': 0.0,
            'cross_exchange_settlements': 0
        }

        logger.info("💰 314ST Token Economics Engine initialized")

    def start(self):
        """Start economics engine"""
        if self.running:
            return

        self.running = True
        self.economics_thread = threading.Thread(
            target=self._economics_worker,
            daemon=True,
            name="TokenEconomics"
        )
        self.economics_thread.start()

        logger.info("🚀 Token economics engine started")

    def stop(self):
        """Stop economics engine"""
        self.running = False
        if self.economics_thread and self.economics_thread.is_alive():
            self.economics_thread.join(timeout=5)

        logger.info("🛑 Token economics engine stopped")

    def _economics_worker(self):
        """Background economics worker"""
        while self.running:
            try:
                self._process_subscriptions()
                self._update_economic_metrics()
                self._cleanup_expired_data()
            except Exception as e:
                logger.error(f"Economics worker error: {e}")

            time.sleep(60)  # Run every minute

    def create_trust_fund(self, developer_address: str, trust_type: TrustType,
                         initial_funding: float, metadata: Dict[str, Any] = None) -> str:
        """Create a new developer trust fund"""
        trust_id = hashlib.sha256(f"trust_{developer_address}_{time.time()}".encode()).hexdigest()[:16]

        trust = TrustFund(
            trust_id=trust_id,
            developer_address=developer_address,
            trust_type=trust_type,
            balance=initial_funding,
            total_funding=initial_funding,
            subscribers=0,
            monthly_revenue=0.0,
            created_at=time.time(),
            last_activity=time.time(),
            subscription_plans=[],
            revenue_history=[],
            metadata=metadata or {}
        )

        self.trust_funds[trust_id] = trust
        self.stats['total_trust_funds'] += 1

        logger.info(f"🏦 Created trust fund {trust_id} for {developer_address}")
        return trust_id

    def fund_trust(self, trust_id: str, amount: float, funder_address: str) -> bool:
        """Fund a trust account"""
        if trust_id not in self.trust_funds:
            return False

        trust = self.trust_funds[trust_id]
        trust.balance += amount
        trust.total_funding += amount
        trust.last_activity = time.time()

        # Record funding transaction
        funding_record = {
            'timestamp': time.time(),
            'funder': funder_address,
            'amount': amount,
            'trust_balance': trust.balance
        }

        trust.revenue_history.append(funding_record)

        logger.info(f"💰 Trust {trust_id} funded with {amount} tokens by {funder_address}")
        return True

    def create_subscription_plan(self, trust_id: str, plan_data: Dict[str, Any]) -> str:
        """Create a subscription plan for a trust fund"""
        if trust_id not in self.trust_funds:
            raise ValueError("Trust fund not found")

        trust = self.trust_funds[trust_id]

        plan_id = hashlib.sha256(f"plan_{trust_id}_{time.time()}".encode()).hexdigest()[:12]

        plan = {
            'plan_id': plan_id,
            'name': plan_data['name'],
            'description': plan_data.get('description', ''),
            'price': plan_data['price'],
            'billing_cycle': plan_data.get('billing_cycle', 'monthly'),
            'features': plan_data.get('features', []),
            'created_at': time.time(),
            'active_subscribers': 0
        }

        trust.subscription_plans.append(plan)
        return plan_id

    def subscribe_to_plan(self, trust_id: str, user_address: str,
                         plan_id: str) -> str:
        """Subscribe user to a trust plan"""
        if trust_id not in self.trust_funds:
            raise ValueError("Trust fund not found")

        trust = self.trust_funds[trust_id]

        # Find plan
        plan = None
        for p in trust.subscription_plans:
            if p['plan_id'] == plan_id:
                plan = p
                break

        if not plan:
            raise ValueError("Plan not found")

        # Create subscription
        subscription_id = hashlib.sha256(f"sub_{user_address}_{plan_id}_{time.time()}".encode()).hexdigest()[:16]

        # Calculate next billing
        now = time.time()
        if plan['billing_cycle'] == 'monthly':
            next_billing = now + (30 * 24 * 60 * 60)  # 30 days
        elif plan['billing_cycle'] == 'yearly':
            next_billing = now + (365 * 24 * 60 * 60)  # 365 days
        else:
            next_billing = now + (30 * 24 * 60 * 60)  # Default monthly

        subscription = Subscription(
            subscription_id=subscription_id,
            user_address=user_address,
            trust_id=trust_id,
            plan_id=plan_id,
            amount=plan['price'],
            billing_cycle=plan['billing_cycle'],
            next_billing=next_billing,
            status='active',
            created_at=now,
            last_payment=now,
            payments=[{
                'timestamp': now,
                'amount': plan['price'],
                'status': 'completed'
            }]
        )

        self.subscriptions[subscription_id] = subscription
        trust.subscribers += 1
        plan['active_subscribers'] += 1
        self.stats['active_subscriptions'] += 1

        logger.info(f"📝 User {user_address} subscribed to plan {plan_id} in trust {trust_id}")
        return subscription_id

    def _process_subscriptions(self):
        """Process subscription billing and payments"""
        current_time = time.time()

        for subscription in list(self.subscriptions.values()):
            if (subscription.status == 'active' and
                current_time >= subscription.next_billing):

                try:
                    # Process payment
                    success = self._process_subscription_payment(subscription)

                    if success:
                        # Calculate next billing
                        if subscription.billing_cycle == 'monthly':
                            subscription.next_billing += (30 * 24 * 60 * 60)
                        elif subscription.billing_cycle == 'yearly':
                            subscription.next_billing += (365 * 24 * 60 * 60)

                        subscription.last_payment = current_time

                        # Record payment
                        subscription.payments.append({
                            'timestamp': current_time,
                            'amount': subscription.amount,
                            'status': 'completed'
                        })

                    else:
                        # Payment failed
                        subscription.status = 'payment_failed'
                        logger.warning(f"💸 Subscription payment failed for {subscription.subscription_id}")

                except Exception as e:
                    logger.error(f"Subscription processing error: {e}")

    def _process_subscription_payment(self, subscription: Subscription) -> bool:
        """Process subscription payment"""
        # In production, this would integrate with wallet system
        # For now, simulate successful payment

        trust = self.trust_funds.get(subscription.trust_id)
        if trust:
            trust.balance += subscription.amount
            trust.monthly_revenue += subscription.amount
            trust.last_activity = time.time()

            # Record revenue
            trust.revenue_history.append({
                'timestamp': time.time(),
                'type': 'subscription',
                'amount': subscription.amount,
                'subscriber': subscription.user_address,
                'subscription_id': subscription.subscription_id
            })

        return True

    def create_foundation_grant(self, title: str, description: str,
                              amount: float, duration_months: int,
                              milestones: List[str]) -> str:
        """Create a foundation grant proposal"""
        if not self.genesis_key_loaded:
            raise ValueError("Genesis key not loaded - cannot create foundation grants")

        grant_id = hashlib.sha256(f"grant_{title}_{time.time()}".encode()).hexdigest()[:16]

        grant = {
            'grant_id': grant_id,
            'title': title,
            'description': description,
            'amount': amount,
            'duration_months': duration_months,
            'milestones': milestones,
            'status': 'pending_review',
            'votes_yes': 0,
            'votes_no': 0,
            'voters': [],
            'created_at': time.time(),
            'voting_ends': time.time() + (7 * 24 * 60 * 60),  # 7 days voting
            'approved_at': None,
            'funded_at': None,
            'completed_milestones': [],
            'payments': []
        }

        self.foundation_grants.append(grant)
        self.stats['foundation_grants'] += 1

        logger.info(f"🎁 Created foundation grant proposal: {title} (${amount})")
        return grant_id

    def vote_on_grant(self, grant_id: str, voter_address: str, vote: bool) -> bool:
        """Vote on a foundation grant proposal"""
        grant = None
        for g in self.foundation_grants:
            if g['grant_id'] == grant_id:
                grant = g
                break

        if not grant or grant['status'] != 'pending_review':
            return False

        # Check if already voted
        if voter_address in grant['voters']:
            return False

        # Record vote
        grant['voters'].append(voter_address)
        if vote:
            grant['votes_yes'] += 1
        else:
            grant['votes_no'] += 1

        # Check if voting period ended
        if time.time() > grant['voting_ends']:
            self._finalize_grant_voting(grant)

        logger.info(f"🗳️ Vote recorded for grant {grant_id}: {'Yes' if vote else 'No'} by {voter_address}")
        return True

    def _finalize_grant_voting(self, grant: Dict[str, Any]):
        """Finalize grant voting and approve/reject grant"""
        total_votes = grant['votes_yes'] + grant['votes_no']

        if total_votes == 0:
            grant['status'] = 'rejected'
            return

        approval_ratio = grant['votes_yes'] / total_votes

        if approval_ratio >= 0.6:  # 60% approval required
            grant['status'] = 'approved'
            grant['approved_at'] = time.time()
            logger.info(f"✅ Grant {grant['grant_id']} approved with {approval_ratio:.1%} approval")
        else:
            grant['status'] = 'rejected'
            logger.info(f"❌ Grant {grant['grant_id']} rejected with {approval_ratio:.1%} approval")

    def fund_approved_grant(self, grant_id: str) -> bool:
        """Fund an approved grant"""
        grant = None
        for g in self.foundation_grants:
            if g['grant_id'] == grant_id:
                grant = g
                break

        if not grant or grant['status'] != 'approved':
            return False

        # Check foundation balance
        if self.economic_metrics.foundation_balance < grant['amount']:
            return False

        # Fund the grant
        self.economic_metrics.foundation_balance -= grant['amount']
        grant['status'] = 'funded'
        grant['funded_at'] = time.time()

        # Record payment
        grant['payments'].append({
            'timestamp': time.time(),
            'amount': grant['amount'],
            'type': 'initial_funding'
        })

        logger.info(f"💰 Funded grant {grant_id} with {grant['amount']} tokens")
        return True

    def create_cross_exchange_settlement(self, from_exchange: str, to_exchange: str,
                                       amount: float, user_from: str, user_to: str) -> str:
        """Create a cross-exchange settlement"""
        settlement_id = hashlib.sha256(f"settlement_{from_exchange}_{to_exchange}_{time.time()}".encode()).hexdigest()[:16]

        settlement = {
            'settlement_id': settlement_id,
            'from_exchange': from_exchange,
            'to_exchange': to_exchange,
            'amount': amount,
            'user_from': user_from,
            'user_to': user_to,
            'status': 'pending',
            'created_at': time.time(),
            'secret_hash': None,
            'lock_time': None,
            'completion_time': None
        }

        self.pending_settlements[settlement_id] = settlement
        self.stats['cross_exchange_settlements'] += 1

        logger.info(f"🔄 Created cross-exchange settlement: {amount} tokens from {from_exchange} to {to_exchange}")
        return settlement_id

    def _update_economic_metrics(self):
        """Update economic metrics and statistics"""
        # Update monthly revenue calculation
        current_month = time.time() // (30 * 24 * 60 * 60)  # Monthly buckets

        for trust in self.trust_funds.values():
            # Reset monthly revenue for new month
            trust_month = trust.created_at // (30 * 24 * 60 * 60)
            if trust_month < current_month:
                trust.monthly_revenue = 0.0

        # Update global statistics
        self.stats.update({
            'total_trust_funds': len(self.trust_funds),
            'active_subscriptions': len([s for s in self.subscriptions.values() if s.status == 'active']),
            'monthly_revenue': sum(t.monthly_revenue for t in self.trust_funds.values()),
            'foundation_grants': len(self.foundation_grants),
            'burned_tokens': self.economic_metrics.burned_tokens,
            'cross_exchange_settlements': len(self.pending_settlements)
        })

    def _cleanup_expired_data(self):
        """Clean up expired data"""
        current_time = time.time()

        # Remove expired subscriptions
        expired_subs = []
        for sub_id, subscription in self.subscriptions.items():
            if (subscription.status == 'active' and
                current_time > subscription.next_billing + (30 * 24 * 60 * 60)):  # 30 days grace
                subscription.status = 'expired'
                expired_subs.append(sub_id)

        for sub_id in expired_subs:
            logger.info(f"⏰ Subscription {sub_id} expired")

        # Clean old economic data (keep 90 days)
        cutoff = current_time - (90 * 24 * 60 * 60)

        for trust in self.trust_funds.values():
            trust.revenue_history = [r for r in trust.revenue_history if r['timestamp'] > cutoff]

        self.economic_metrics.price_history = [p for p in self.economic_metrics.price_history if p['timestamp'] > cutoff]

    def get_economic_overview(self) -> Dict[str, Any]:
        """Get comprehensive economic overview"""
        return {
            'market_data': self.economic_metrics.get_market_data(),
            'trust_funds': {
                'total': len(self.trust_funds),
                'by_type': {
                    trust_type.value: len([t for t in self.trust_funds.values() if t.trust_type == trust_type])
                    for trust_type in TrustType
                },
                'total_balance': sum(t.balance for t in self.trust_funds.values()),
                'monthly_revenue': sum(t.monthly_revenue for t in self.trust_funds.values())
            },
            'subscriptions': {
                'total': len(self.subscriptions),
                'active': len([s for s in self.subscriptions.values() if s.status == 'active']),
                'monthly_revenue': sum(s.amount for s in self.subscriptions.values() if s.status == 'active')
            },
            'foundation': {
                'balance': self.economic_metrics.foundation_balance,
                'grants': len(self.foundation_grants),
                'active_grants': len([g for g in self.foundation_grants if g['status'] == 'funded']),
                'total_grants_value': sum(g['amount'] for g in self.foundation_grants if g['status'] in ['funded', 'approved'])
            },
            'fee_distribution': self.economic_metrics.fee_distribution,
            'fee_structure': self.economic_metrics.fee_structure,
            **self.stats
        }

    def get_trust_fund_details(self, trust_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed trust fund information"""
        trust = self.trust_funds.get(trust_id)
        if not trust:
            return None

        return {
            'trust': trust.to_dict(),
            'subscriptions': [
                {
                    'subscription_id': s.subscription_id,
                    'user_address': s.user_address,
                    'plan_id': s.plan_id,
                    'amount': s.amount,
                    'status': s.status,
                    'next_billing': s.next_billing
                }
                for s in self.subscriptions.values()
                if s.trust_id == trust_id and s.status == 'active'
            ],
            'revenue_trends': self._calculate_revenue_trends(trust)
        }

    def _calculate_revenue_trends(self, trust: TrustFund) -> Dict[str, Any]:
        """Calculate revenue trends for a trust fund"""
        if not trust.revenue_history:
            return {'daily': [], 'weekly': [], 'monthly': []}

        # Group by time periods (simplified)
        now = time.time()
        day_ago = now - (24 * 60 * 60)
        week_ago = now - (7 * 24 * 60 * 60)
        month_ago = now - (30 * 24 * 60 * 60)

        daily_revenue = sum(r['amount'] for r in trust.revenue_history if r['timestamp'] > day_ago)
        weekly_revenue = sum(r['amount'] for r in trust.revenue_history if r['timestamp'] > week_ago)
        monthly_revenue = sum(r['amount'] for r in trust.revenue_history if r['timestamp'] > month_ago)

        return {
            'daily': daily_revenue,
            'weekly': weekly_revenue,
            'monthly': monthly_revenue,
            'average_daily': monthly_revenue / 30 if monthly_revenue > 0 else 0
        }

# Global token economics instance
token_economics: Optional[TokenEconomicsEngine] = None

def get_token_economics(blockchain: Optional[SignChain] = None) -> TokenEconomicsEngine:
    """Get or create global token economics engine"""
    global token_economics
    if token_economics is None:
        token_economics = TokenEconomicsEngine(blockchain)
    return token_economics