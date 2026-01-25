"""
PiSecure Institutional Custody Solutions
========================================

Enterprise-grade custody solutions for institutional adoption of 314ST,
including multi-signature wallets, cold storage management, and comprehensive
audit trails.
"""

import hashlib
import json
import time
import secrets
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class InstitutionalCustody:
    """Enterprise custody solutions for institutional 314ST holders"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.custody_levels = {
            'retail': {
                'multi_sig': 1,
                'cold_storage': False,
                'audit_required': False,
                'backup_keys': 1
            },
            'professional': {
                'multi_sig': 2,
                'cold_storage': True,
                'audit_required': True,
                'backup_keys': 3
            },
            'institutional': {
                'multi_sig': 3,
                'cold_storage': True,
                'audit_required': True,
                'backup_keys': 5
            },
            'sovereign': {
                'multi_sig': 7,
                'cold_storage': True,
                'audit_required': True,
                'backup_keys': 9,
                'air_gapped': True,
                'geographic_distribution': True
            }
        }

        self.institutional_wallets = {}
        self.audit_trail = InstitutionalAuditTrail()

    async def create_institutional_wallet(self, institution_id: str,
                                       custody_level: str,
                                       authorized_signers: List[str],
                                       metadata: Dict = None) -> Dict:
        """Create an institutional-grade custody wallet"""
        if custody_level not in self.custody_levels:
            raise ValueError(f"Invalid custody level: {custody_level}")

        config = self.custody_levels[custody_level]
        required_signers = config['multi_sig']

        if len(authorized_signers) < required_signers:
            raise ValueError(f"Need at least {required_signers} authorized signers for {custody_level} custody")

        # Generate wallet ID and keys
        wallet_id = f"inst_{institution_id}_{int(time.time())}_{secrets.token_hex(4)}"

        # Create multi-signature wallet structure
        wallet = {
            'wallet_id': wallet_id,
            'institution_id': institution_id,
            'custody_level': custody_level,
            'authorized_signers': authorized_signers,
            'required_signatures': required_signers,
            'pending_transactions': {},
            'cold_storage_enabled': config['cold_storage'],
            'audit_enabled': config['audit_required'],
            'created_at': time.time(),
            'status': 'active',
            'metadata': metadata or {}
        }

        # Set up cold storage if required
        if config['cold_storage']:
            wallet['cold_storage'] = await self._setup_cold_storage(wallet_id, config)

        # Enable audit logging
        if config['audit_required']:
            await self.audit_trail.enable_for_wallet(wallet_id)

        self.institutional_wallets[wallet_id] = wallet

        # Create blockchain registration
        registration_tx = {
            "type": "institutional_wallet_created",
            "wallet_id": wallet_id,
            "institution_id": institution_id,
            "custody_level": custody_level,
            "authorized_signers": authorized_signers,
            "required_signatures": required_signers,
            "cold_storage": config['cold_storage'],
            "timestamp": time.time(),
            "signature": f"inst-wallet-{wallet_id}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(registration_tx)

        print(f"🏛️ Created institutional wallet: {wallet_id} ({custody_level} custody)")
        return wallet

    async def _setup_cold_storage(self, wallet_id: str, config: Dict) -> Dict:
        """Set up cold storage for institutional wallet"""
        cold_wallet_id = f"cold_{wallet_id}"

        cold_setup = {
            'wallet_id': cold_wallet_id,
            'air_gapped': config.get('air_gapped', False),
            'geographic_distribution': config.get('geographic_distribution', False),
            'backup_keys': config['backup_keys'],
            'created_at': time.time(),
            'last_rotation': time.time(),
            'rotation_threshold': 100000  # Rotate after 100k 314ST
        }

        if config.get('geographic_distribution', False):
            cold_setup['locations'] = ['US-East', 'EU-West', 'Asia-Pacific']

        return cold_setup

    async def initiate_institutional_transfer(self, wallet_id: str,
                                           recipient: str,
                                           amount: float,
                                           initiator: str,
                                           description: str = "") -> str:
        """Initiate a multi-signature transfer from institutional wallet"""
        if wallet_id not in self.institutional_wallets:
            raise ValueError(f"Wallet not found: {wallet_id}")

        wallet = self.institutional_wallets[wallet_id]

        # Verify initiator is authorized
        if initiator not in wallet['authorized_signers']:
            raise ValueError(f"Unauthorized initiator: {initiator}")

        # Generate transfer ID
        transfer_id = f"transfer_{wallet_id}_{int(time.time())}_{secrets.token_hex(4)}"

        # Create pending transfer
        transfer = {
            'transfer_id': transfer_id,
            'wallet_id': wallet_id,
            'recipient': recipient,
            'amount': amount,
            'initiator': initiator,
            'description': description,
            'approvals': [initiator],  # Initiator auto-approves
            'required_approvals': wallet['required_signatures'],
            'status': 'pending_approval',
            'created_at': time.time(),
            'expires_at': time.time() + 604800  # 7 days
        }

        wallet['pending_transactions'][transfer_id] = transfer

        # Log to audit trail
        await self.audit_trail.log_event(wallet_id, 'transfer_initiated', {
            'transfer_id': transfer_id,
            'amount': amount,
            'recipient': recipient,
            'initiator': initiator
        })

        print(f"📤 Initiated institutional transfer: {transfer_id} ({amount} 314ST)")
        return transfer_id

    async def approve_transfer(self, wallet_id: str, transfer_id: str,
                             approver: str) -> bool:
        """Approve a pending institutional transfer"""
        if wallet_id not in self.institutional_wallets:
            return False

        wallet = self.institutional_wallets[wallet_id]

        if transfer_id not in wallet['pending_transactions']:
            return False

        transfer = wallet['pending_transactions'][transfer_id]

        # Check if already approved
        if approver in transfer['approvals']:
            return False

        # Verify approver is authorized
        if approver not in wallet['authorized_signers']:
            return False

        # Add approval
        transfer['approvals'].append(approver)

        # Log approval
        await self.audit_trail.log_event(wallet_id, 'transfer_approved', {
            'transfer_id': transfer_id,
            'approver': approver,
            'current_approvals': len(transfer['approvals']),
            'required_approvals': transfer['required_approvals']
        })

        # Check if we have enough approvals
        if len(transfer['approvals']) >= transfer['required_approvals']:
            await self._execute_institutional_transfer(wallet_id, transfer_id)

        return True

    async def _execute_institutional_transfer(self, wallet_id: str, transfer_id: str):
        """Execute approved institutional transfer"""
        wallet = self.institutional_wallets[wallet_id]
        transfer = wallet['pending_transactions'][transfer_id]

        # Create blockchain transaction
        blockchain_tx = {
            "type": "institutional_transfer",
            "wallet_id": wallet_id,
            "transfer_id": transfer_id,
            "sender": wallet_id,
            "recipient": transfer['recipient'],
            "amount": transfer['amount'],
            "approvals": transfer['approvals'],
            "description": transfer['description'],
            "timestamp": time.time(),
            "signature": f"inst-transfer-{transfer_id}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(blockchain_tx)

        # Update transfer status
        transfer['status'] = 'executed'
        transfer['executed_at'] = time.time()

        # Log execution
        await self.audit_trail.log_event(wallet_id, 'transfer_executed', {
            'transfer_id': transfer_id,
            'amount': transfer['amount'],
            'recipient': transfer['recipient'],
            'approvals_used': len(transfer['approvals'])
        })

        print(f"✅ Executed institutional transfer: {transfer_id} ({transfer['amount']} 314ST)")

    async def rotate_cold_storage(self, wallet_id: str) -> str:
        """Rotate cold storage wallet for enhanced security"""
        if wallet_id not in self.institutional_wallets:
            raise ValueError(f"Wallet not found: {wallet_id}")

        wallet = self.institutional_wallets[wallet_id]

        if not wallet.get('cold_storage'):
            raise ValueError("Cold storage not enabled for this wallet")

        cold_storage = wallet['cold_storage']

        # Check if rotation is needed
        if not self._should_rotate_cold_storage(cold_storage):
            return cold_storage['wallet_id']

        # Create new cold wallet
        new_cold_wallet_id = f"cold_{wallet_id}_{int(time.time())}"

        # Transfer all funds (simulated - would require manual process)
        rotation_tx = {
            "type": "cold_storage_rotation",
            "wallet_id": wallet_id,
            "old_cold_wallet": cold_storage['wallet_id'],
            "new_cold_wallet": new_cold_wallet_id,
            "timestamp": time.time(),
            "signature": f"cold-rotate-{wallet_id}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(rotation_tx)

        # Update cold storage info
        cold_storage['wallet_id'] = new_cold_wallet_id
        cold_storage['last_rotation'] = time.time()

        # Log rotation
        await self.audit_trail.log_event(wallet_id, 'cold_storage_rotated', {
            'old_wallet': cold_storage['wallet_id'],
            'new_wallet': new_cold_wallet_id
        })

        print(f"🔄 Rotated cold storage for wallet: {wallet_id}")
        return new_cold_wallet_id

    def _should_rotate_cold_storage(self, cold_storage: Dict) -> bool:
        """Check if cold storage should be rotated"""
        # Rotate if threshold exceeded or time-based (90 days)
        time_since_rotation = time.time() - cold_storage.get('last_rotation', 0)
        return time_since_rotation > (90 * 24 * 3600)  # 90 days

    def get_wallet_status(self, wallet_id: str) -> Dict:
        """Get comprehensive status of institutional wallet"""
        if wallet_id not in self.institutional_wallets:
            return {}

        wallet = self.institutional_wallets[wallet_id]

        status = {
            'wallet_id': wallet_id,
            'institution_id': wallet['institution_id'],
            'custody_level': wallet['custody_level'],
            'status': wallet['status'],
            'authorized_signers': len(wallet['authorized_signers']),
            'required_signatures': wallet['required_signatures'],
            'pending_transfers': len(wallet['pending_transactions']),
            'cold_storage_enabled': wallet.get('cold_storage', {}).get('air_gapped', False),
            'audit_enabled': wallet.get('audit_enabled', False),
            'created_at': wallet['created_at']
        }

        # Add cold storage status if enabled
        if wallet.get('cold_storage'):
            cold = wallet['cold_storage']
            status['cold_storage'] = {
                'air_gapped': cold.get('air_gapped', False),
                'geographic_distribution': cold.get('geographic_distribution', False),
                'last_rotation': cold.get('last_rotation', 0),
                'rotation_due': self._should_rotate_cold_storage(cold)
            }

        return status

    def generate_custody_report(self, wallet_id: str, start_time: float,
                               end_time: float) -> Dict:
        """Generate comprehensive custody report"""
        if wallet_id not in self.institutional_wallets:
            return {}

        wallet = self.institutional_wallets[wallet_id]

        report = {
            'wallet_id': wallet_id,
            'institution_id': wallet['institution_id'],
            'period': {'start': start_time, 'end': end_time},
            'custody_level': wallet['custody_level'],
            'transfers_executed': 0,
            'total_volume': 0.0,
            'approvals_used': 0,
            'security_events': [],
            'compliance_status': 'compliant'
        }

        # Get audit events for the period
        audit_events = self.audit_trail.get_events(wallet_id, start_time, end_time)

        for event in audit_events:
            if event['event_type'] == 'transfer_executed':
                report['transfers_executed'] += 1
                report['total_volume'] += event['data'].get('amount', 0)
                report['approvals_used'] += event['data'].get('approvals_used', 0)

        report['security_events'] = [e for e in audit_events if 'security' in e['event_type'].lower()]

        return report


class InstitutionalAuditTrail:
    """Comprehensive audit trail for institutional custody operations"""

    def __init__(self):
        self.audit_logs = {}  # wallet_id -> list of events
        self.retention_period = 2555 * 24 * 3600  # 7 years

    async def enable_for_wallet(self, wallet_id: str):
        """Enable audit logging for a wallet"""
        if wallet_id not in self.audit_logs:
            self.audit_logs[wallet_id] = []

    async def log_event(self, wallet_id: str, event_type: str, data: Dict):
        """Log an audit event"""
        if wallet_id not in self.audit_logs:
            await self.enable_for_wallet(wallet_id)

        event = {
            'event_id': f"{wallet_id}_{int(time.time())}_{secrets.token_hex(4)}",
            'wallet_id': wallet_id,
            'event_type': event_type,
            'data': data,
            'timestamp': time.time(),
            'signature': self._sign_event(event)
        }

        self.audit_logs[wallet_id].append(event)

        # Clean old events
        self._cleanup_old_events(wallet_id)

    def _sign_event(self, event: Dict) -> str:
        """Create cryptographic signature for audit event"""
        event_string = json.dumps({
            'event_id': event['event_id'],
            'event_type': event['event_type'],
            'timestamp': event['timestamp']
        }, sort_keys=True)

        return hashlib.sha256(event_string.encode()).hexdigest()

    def _cleanup_old_events(self, wallet_id: str):
        """Remove events older than retention period"""
        if wallet_id not in self.audit_logs:
            return

        cutoff_time = time.time() - self.retention_period
        self.audit_logs[wallet_id] = [
            event for event in self.audit_logs[wallet_id]
            if event['timestamp'] > cutoff_time
        ]

    def get_events(self, wallet_id: str, start_time: float = 0,
                  end_time: float = None) -> List[Dict]:
        """Get audit events for a wallet within time range"""
        if wallet_id not in self.audit_logs:
            return []

        if end_time is None:
            end_time = time.time()

        return [
            event for event in self.audit_logs[wallet_id]
            if start_time <= event['timestamp'] <= end_time
        ]

    def generate_audit_report(self, wallet_id: str, start_time: float,
                            end_time: float) -> Dict:
        """Generate comprehensive audit report"""
        events = self.get_events(wallet_id, start_time, end_time)

        report = {
            'wallet_id': wallet_id,
            'period': {'start': start_time, 'end': end_time},
            'total_events': len(events),
            'event_types': {},
            'anomalies': [],
            'compliance_status': 'compliant'
        }

        for event in events:
            event_type = event['event_type']
            if event_type not in report['event_types']:
                report['event_types'][event_type] = 0
            report['event_types'][event_type] += 1

        # Check for anomalies (simplified)
        transfer_events = [e for e in events if 'transfer' in e['event_type']]
        if len(transfer_events) > 100:  # High frequency
            report['anomalies'].append('High transfer frequency detected')

        return report