"""
PiSecure Regulatory Compliance Engine
=====================================

Automated KYC/AML compliance system for cryptocurrency exchanges
integrating with PiSecure's 314ST token.
"""

import hashlib
import json
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class RegulatoryComplianceEngine:
    """Automated regulatory compliance system for exchanges"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.kyc_providers = ['Chainalysis', 'Elliptic', 'ScoreChain']
        self.regulatory_zones = {
            'US': {
                'aml_threshold': 10000,
                'kyc_required': True,
                'reporting_required': True,
                'sanctions_screening': True
            },
            'EU': {
                'aml_threshold': 15000,
                'kyc_required': True,
                'reporting_required': True,
                'sanctions_screening': True
            },
            'Asia': {
                'aml_threshold': 5000,
                'kyc_required': False,
                'reporting_required': False,
                'sanctions_screening': True
            },
            'Global': {
                'aml_threshold': 3000,
                'kyc_required': False,
                'reporting_required': False,
                'sanctions_screening': True
            }
        }

        # Load sanctions lists
        self.sanctions_lists = self._load_sanctions_lists()

    def _load_sanctions_lists(self) -> Dict[str, List[str]]:
        """Load international sanctions lists"""
        # In production, this would load from external APIs
        return {
            'OFAC': ['blocked_address_1', 'blocked_address_2'],
            'EU': ['eu_sanctioned_1', 'eu_sanctioned_2'],
            'UN': ['un_sanctioned_1', 'un_sanctioned_2']
        }

    async def automated_compliance_check(self, transaction: Dict,
                                       jurisdiction: str = 'Global') -> Dict:
        """Perform automated compliance check on a transaction"""
        rules = self.regulatory_zones.get(jurisdiction, self.regulatory_zones['Global'])

        # Calculate risk score
        risk_score = await self.calculate_risk_score(transaction)

        # Check sanctions
        sanctions_check = await self.check_sanctions(transaction)

        # Check AML thresholds
        aml_check = self.check_aml_threshold(transaction, rules)

        # Determine compliance status
        compliance_result = {
            'transaction_id': transaction.get('id', 'unknown'),
            'risk_score': risk_score,
            'sanctions_check': sanctions_check,
            'aml_check': aml_check,
            'jurisdiction': jurisdiction,
            'timestamp': time.time()
        }

        # Make compliance decision
        if risk_score > 0.8 or sanctions_check['flagged']:
            compliance_result.update({
                'approved': False,
                'reason': 'High risk transaction',
                'required_actions': ['Enhanced KYC', 'Manual review'],
                'escalation_level': 'high'
            })
        elif aml_check['threshold_exceeded']:
            compliance_result.update({
                'approved': False,
                'reason': f'AML threshold exceeded ({aml_check["amount"]} > {rules["aml_threshold"]})',
                'required_actions': ['KYC verification', 'Source of funds check'],
                'escalation_level': 'medium'
            })
        else:
            compliance_result.update({
                'approved': True,
                'compliance_level': 'auto_approved',
                'monitoring_required': rules.get('reporting_required', False)
            })

        # Log compliance decision to blockchain
        await self._log_compliance_decision(compliance_result)

        return compliance_result

    async def calculate_risk_score(self, transaction: Dict) -> float:
        """Calculate risk score for transaction (0.0 = low risk, 1.0 = high risk)"""
        risk_score = 0.0

        # Amount-based risk
        amount = transaction.get('amount', 0)
        if amount > 50000:
            risk_score += 0.3
        elif amount > 10000:
            risk_score += 0.2
        elif amount > 1000:
            risk_score += 0.1

        # Transaction frequency risk
        sender = transaction.get('sender', '')
        recent_txs = await self._get_recent_transactions(sender, hours=24)
        if len(recent_txs) > 10:
            risk_score += 0.2

        # New user risk
        if await self._is_new_user(sender):
            risk_score += 0.1

        # Cross-border risk
        if self._is_cross_border(transaction):
            risk_score += 0.1

        # Unusual timing risk (odd hours)
        if self._is_unusual_timing(transaction):
            risk_score += 0.1

        # Velocity risk (rapid transactions)
        velocity_score = await self._calculate_velocity_risk(sender)
        risk_score += velocity_score

        return min(risk_score, 1.0)

    async def check_sanctions(self, transaction: Dict) -> Dict:
        """Check transaction parties against sanctions lists"""
        parties = [
            transaction.get('sender', ''),
            transaction.get('recipient', ''),
            transaction.get('user_from', ''),
            transaction.get('user_to', '')
        ]

        flagged_parties = []
        sanction_sources = []

        for party in parties:
            if not party:
                continue

            for list_name, sanctioned_addresses in self.sanctions_lists.items():
                if party in sanctioned_addresses:
                    flagged_parties.append(party)
                    sanction_sources.append(list_name)

        return {
            'flagged': len(flagged_parties) > 0,
            'flagged_parties': flagged_parties,
            'sanction_sources': sanction_sources,
            'checked_lists': list(self.sanctions_lists.keys())
        }

    def check_aml_threshold(self, transaction: Dict, rules: Dict) -> Dict:
        """Check if transaction exceeds AML reporting thresholds"""
        amount = transaction.get('amount', 0)
        threshold = rules.get('aml_threshold', 10000)

        return {
            'threshold_exceeded': amount > threshold,
            'amount': amount,
            'threshold': threshold,
            'reporting_required': rules.get('reporting_required', False)
        }

    async def _get_recent_transactions(self, address: str, hours: int) -> List[Dict]:
        """Get recent transactions for an address"""
        if not self.blockchain:
            return []

        # In production, this would query the blockchain efficiently
        recent_txs = []
        cutoff_time = time.time() - (hours * 3600)

        for block in reversed(self.blockchain.chain):
            if block.timestamp < cutoff_time:
                break

            for tx in block.transactions:
                if (tx.get('sender') == address or tx.get('recipient') == address) and tx.get('timestamp', 0) > cutoff_time:
                    recent_txs.append(tx)

        return recent_txs

    async def _is_new_user(self, address: str) -> bool:
        """Check if address is a new user (limited transaction history)"""
        if not self.blockchain:
            return True

        total_txs = 0
        for block in self.blockchain.chain[-10:]:  # Last 10 blocks
            for tx in block.transactions:
                if tx.get('sender') == address or tx.get('recipient') == address:
                    total_txs += 1

        return total_txs < 3

    def _is_cross_border(self, transaction: Dict) -> bool:
        """Check if transaction crosses jurisdictional boundaries"""
        # Simplified - in production would use IP geolocation, user profiles, etc.
        sender_country = transaction.get('sender_country', 'unknown')
        recipient_country = transaction.get('recipient_country', 'unknown')

        return sender_country != recipient_country and sender_country != 'unknown'

    def _is_unusual_timing(self, transaction: Dict) -> bool:
        """Check if transaction occurs at unusual times"""
        timestamp = transaction.get('timestamp', time.time())
        hour = time.gmtime(timestamp).tm_hour

        # Flag transactions between 2 AM and 6 AM
        return 2 <= hour <= 6

    async def _calculate_velocity_risk(self, address: str) -> float:
        """Calculate velocity risk based on transaction frequency"""
        recent_txs = await self._get_recent_transactions(address, hours=1)

        # High velocity = high risk
        if len(recent_txs) > 5:
            return 0.3
        elif len(recent_txs) > 2:
            return 0.1

        return 0.0

    async def _log_compliance_decision(self, decision: Dict):
        """Log compliance decision to blockchain"""
        if not self.blockchain:
            return

        compliance_tx = {
            "type": "compliance_decision",
            "transaction_id": decision['transaction_id'],
            "approved": decision['approved'],
            "risk_score": decision['risk_score'],
            "reason": decision.get('reason', ''),
            "jurisdiction": decision['jurisdiction'],
            "timestamp": time.time(),
            "signature": f"compliance-{decision['transaction_id']}"
        }

        self.blockchain.pending_transactions.append(compliance_tx)

    def generate_compliance_report(self, start_time: float, end_time: float) -> Dict:
        """Generate compliance report for regulatory authorities"""
        if not self.blockchain:
            return {}

        report = {
            'period': {'start': start_time, 'end': end_time},
            'transactions_analyzed': 0,
            'high_risk_flagged': 0,
            'sanctions_hits': 0,
            'aml_threshold_exceeded': 0,
            'jurisdictions': {},
            'summary': {}
        }

        for block in self.blockchain.chain:
            if not (start_time <= block.timestamp <= end_time):
                continue

            for tx in block.transactions:
                if tx.get('type') == 'compliance_decision':
                    report['transactions_analyzed'] += 1

                    if tx.get('risk_score', 0) > 0.8:
                        report['high_risk_flagged'] += 1

                    jurisdiction = tx.get('jurisdiction', 'unknown')
                    if jurisdiction not in report['jurisdictions']:
                        report['jurisdictions'][jurisdiction] = 0
                    report['jurisdictions'][jurisdiction] += 1

        return report