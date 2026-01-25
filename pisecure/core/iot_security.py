"""
PiSecure IoT Device Integration for Enhanced Security
====================================================

Leverages IoT device network for enhanced transaction security through
device trust scores, hardware verification, and decentralized oracles.
"""

import hashlib
import json
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class IoTEnhancedSecurity:
    """IoT device integration for enhanced blockchain security"""

    def __init__(self, blockchain=None):
        self.blockchain = blockchain
        self.device_oracle = DeviceOracle()
        self.hardware_verification = HardwareVerifier()
        self.trust_scores = {}
        self.device_network = DeviceNetwork()

    async def enhance_transaction_security(self, transaction: Dict) -> Dict:
        """Enhance transaction security using IoT device data"""
        device_fingerprint = transaction.get('device_fingerprint', '')
        hardware_signature = transaction.get('hardware_signature', '')

        # Get device trust score
        device_trust_score = await self.device_oracle.get_device_trust_score(device_fingerprint)

        # Verify hardware authenticity
        hardware_verification = await self.hardware_verification.verify(hardware_signature)

        # Calculate risk multiplier based on trust factors
        risk_multiplier = self.calculate_risk_multiplier(
            device_trust_score,
            hardware_verification
        )

        # Adjust transaction fee based on risk
        base_fee = transaction.get('fee', 0.001)
        adjusted_fee = base_fee * risk_multiplier

        enhanced_transaction = {
            **transaction,
            'device_trust_score': device_trust_score,
            'hardware_verified': hardware_verification.verified,
            'risk_multiplier': risk_multiplier,
            'adjusted_fee': adjusted_fee,
            'security_level': self.get_security_level(risk_multiplier),
            'iot_enhanced': True,
            'enhancement_timestamp': time.time()
        }

        # Log security enhancement
        await self._log_security_enhancement(enhanced_transaction)

        return enhanced_transaction

    def calculate_risk_multiplier(self, trust_score: float,
                                hardware_verification: Dict) -> float:
        """Calculate risk multiplier based on security factors"""
        base_multiplier = 1.0

        # Trust score adjustment (lower trust = higher fee)
        if trust_score < 0.3:
            base_multiplier *= 3.0  # 3x fee for low trust
        elif trust_score < 0.6:
            base_multiplier *= 1.5  # 1.5x fee for medium trust
        else:
            base_multiplier *= 0.8  # 20% discount for high trust

        # Hardware verification adjustment
        if not hardware_verification.get('verified', False):
            base_multiplier *= 2.0  # 2x fee for unverified hardware
        else:
            # Bonus for verified hardware
            hardware_trust = hardware_verification.get('trust_level', 0.5)
            base_multiplier *= (1.0 - hardware_trust * 0.2)  # Up to 20% discount

        # Network health adjustment
        network_health = self.device_network.get_network_health()
        if network_health < 0.5:
            base_multiplier *= 1.2  # 20% penalty for poor network health

        return max(0.1, min(base_multiplier, 10.0))  # Clamp between 0.1x and 10x

    def get_security_level(self, risk_multiplier: float) -> str:
        """Get security level description based on risk multiplier"""
        if risk_multiplier <= 0.8:
            return 'elite'  # High trust, low risk
        elif risk_multiplier <= 1.2:
            return 'standard'  # Normal risk
        elif risk_multiplier <= 2.0:
            return 'enhanced'  # Medium risk
        elif risk_multiplier <= 5.0:
            return 'high_security'  # High risk
        else:
            return 'maximum_security'  # Very high risk

    async def create_trust_oracle(self, device_network: List[Dict]) -> Dict:
        """Create decentralized oracle from IoT device network"""
        # Filter verified devices
        verified_devices = await self.filter_verified_devices(device_network)

        # Calculate consensus data
        consensus_data = await self.calculate_device_consensus(verified_devices)

        # Deploy oracle contract
        oracle_contract = {
            'oracle_id': f"oracle_{int(time.time())}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}",
            'device_count': len(verified_devices),
            'consensus_threshold': 0.67,  # 2/3 majority
            'update_frequency': 'every_10_blocks',
            'trust_score': consensus_data['average_trust'],
            'created_at': time.time(),
            'active': True
        }

        # Create blockchain transaction for oracle deployment
        oracle_tx = {
            "type": "trust_oracle_created",
            "oracle_id": oracle_contract['oracle_id'],
            "device_count": oracle_contract['device_count'],
            "consensus_threshold": oracle_contract['consensus_threshold'],
            "trust_score": oracle_contract['trust_score'],
            "timestamp": time.time(),
            "signature": f"oracle-create-{oracle_contract['oracle_id']}"
        }

        if self.blockchain:
            self.blockchain.pending_transactions.append(oracle_tx)

        print(f"🔮 Created trust oracle with {len(verified_devices)} devices")
        return oracle_contract

    async def filter_verified_devices(self, device_network: List[Dict]) -> List[Dict]:
        """Filter network for verified, trustworthy devices"""
        verified_devices = []

        for device in device_network:
            fingerprint = device.get('fingerprint', '')
            trust_score = await self.device_oracle.get_device_trust_score(fingerprint)

            # Only include devices with sufficient trust and uptime
            if (trust_score >= 0.6 and
                device.get('uptime_percentage', 0) >= 95 and
                device.get('hardware_verified', False)):

                verified_devices.append({
                    **device,
                    'trust_score': trust_score,
                    'verified_at': time.time()
                })

        return verified_devices

    async def calculate_device_consensus(self, devices: List[Dict]) -> Dict:
        """Calculate consensus data from device network"""
        if not devices:
            return {'average_trust': 0.0, 'consensus_reached': False}

        trust_scores = [d['trust_score'] for d in devices]

        consensus_data = {
            'average_trust': statistics.mean(trust_scores),
            'median_trust': statistics.median(trust_scores),
            'min_trust': min(trust_scores),
            'max_trust': max(trust_scores),
            'consensus_reached': len([t for t in trust_scores if t >= 0.7]) >= len(devices) * 0.67,
            'device_count': len(devices),
            'timestamp': time.time()
        }

        return consensus_data

    async def get_network_security_score(self) -> Dict:
        """Get overall network security score from IoT devices"""
        network_status = await self.device_network.get_status()

        security_score = {
            'overall_score': 0.0,
            'device_count': network_status.get('active_devices', 0),
            'average_trust': 0.0,
            'hardware_verification_rate': 0.0,
            'network_uptime': network_status.get('average_uptime', 0),
            'threat_detection_active': network_status.get('threat_detection', False),
            'last_updated': time.time()
        }

        if security_score['device_count'] > 0:
            # Calculate weighted security score
            trust_weight = 0.4
            hardware_weight = 0.3
            uptime_weight = 0.2
            threat_weight = 0.1

            devices = network_status.get('devices', [])
            if devices:
                trust_scores = []
                hardware_verified = 0

                for device in devices:
                    trust_scores.append(device.get('trust_score', 0))
                    if device.get('hardware_verified', False):
                        hardware_verified += 1

                security_score['average_trust'] = statistics.mean(trust_scores) if trust_scores else 0
                security_score['hardware_verification_rate'] = hardware_verified / len(devices)

                security_score['overall_score'] = (
                    security_score['average_trust'] * trust_weight +
                    security_score['hardware_verification_rate'] * hardware_weight +
                    (security_score['network_uptime'] / 100) * uptime_weight +
                    (1.0 if security_score['threat_detection_active'] else 0.0) * threat_weight
                )

        return security_score

    async def detect_security_threats(self, transaction: Dict) -> List[Dict]:
        """Use IoT network to detect potential security threats"""
        threats = []

        # Check for unusual patterns
        anomaly_score = await self._calculate_anomaly_score(transaction)
        if anomaly_score > 0.8:
            threats.append({
                'type': 'anomalous_transaction',
                'severity': 'high',
                'confidence': anomaly_score,
                'description': 'Transaction pattern deviates significantly from normal behavior'
            })

        # Check device reputation
        device_reputation = await self._check_device_reputation(transaction)
        if device_reputation['risk_level'] == 'high':
            threats.append({
                'type': 'device_reputation_risk',
                'severity': 'medium',
                'confidence': device_reputation['confidence'],
                'description': f'Device has {device_reputation["risk_level"]} risk reputation'
            })

        # Network-based threat detection
        network_threats = await self.device_network.detect_threats(transaction)
        threats.extend(network_threats)

        return threats

    async def _calculate_anomaly_score(self, transaction: Dict) -> float:
        """Calculate anomaly score for transaction"""
        # Simplified anomaly detection
        amount = transaction.get('amount', 0)
        sender = transaction.get('sender', '')

        # Check against historical patterns
        historical_avg = await self._get_historical_average(sender)
        historical_std = await self._get_historical_std(sender)

        if historical_std == 0:
            return 0.0

        z_score = abs(amount - historical_avg) / historical_std

        # Convert z-score to anomaly score (0-1)
        return min(z_score / 3.0, 1.0)  # 3-sigma rule

    async def _get_historical_average(self, address: str) -> float:
        """Get historical average transaction amount for address"""
        if not self.blockchain:
            return 0.0

        amounts = []
        for block in self.blockchain.chain[-10:]:  # Last 10 blocks
            for tx in block.transactions:
                if tx.get('sender') == address or tx.get('recipient') == address:
                    amounts.append(tx.get('amount', 0))

        return statistics.mean(amounts) if amounts else 0.0

    async def _get_historical_std(self, address: str) -> float:
        """Get historical standard deviation for address"""
        if not self.blockchain:
            return 1.0

        amounts = []
        for block in self.blockchain.chain[-10:]:
            for tx in block.transactions:
                if tx.get('sender') == address or tx.get('recipient') == address:
                    amounts.append(tx.get('amount', 0))

        return statistics.stdev(amounts) if len(amounts) > 1 else 1.0

    async def _check_device_reputation(self, transaction: Dict) -> Dict:
        """Check device reputation for risk assessment"""
        device_fingerprint = transaction.get('device_fingerprint', '')

        if not device_fingerprint:
            return {'risk_level': 'unknown', 'confidence': 0.0}

        trust_score = await self.device_oracle.get_device_trust_score(device_fingerprint)

        if trust_score >= 0.8:
            return {'risk_level': 'low', 'confidence': 0.9}
        elif trust_score >= 0.6:
            return {'risk_level': 'medium', 'confidence': 0.7}
        else:
            return {'risk_level': 'high', 'confidence': 0.8}

    async def _log_security_enhancement(self, transaction: Dict):
        """Log security enhancement to blockchain"""
        if not self.blockchain:
            return

        security_tx = {
            "type": "security_enhancement",
            "transaction_id": transaction.get('id', 'unknown'),
            "device_trust_score": transaction['device_trust_score'],
            "hardware_verified": transaction['hardware_verified'],
            "risk_multiplier": transaction['risk_multiplier'],
            "security_level": transaction['security_level'],
            "threats_detected": len(await self.detect_security_threats(transaction)),
            "timestamp": time.time(),
            "signature": f"security-enhance-{transaction.get('id', 'unknown')}"
        }

        self.blockchain.pending_transactions.append(security_tx)


class DeviceOracle:
    """Decentralized oracle for device trust scoring"""

    def __init__(self):
        self.device_registry = {}
        self.trust_history = {}

    async def get_device_trust_score(self, fingerprint: str) -> float:
        """Get trust score for a device (0.0 = untrusted, 1.0 = fully trusted)"""
        if not fingerprint:
            return 0.0

        # Check device registry
        if fingerprint in self.device_registry:
            device_data = self.device_registry[fingerprint]

            # Calculate trust score based on multiple factors
            uptime_score = min(device_data.get('uptime_percentage', 0) / 100, 1.0)
            verification_score = 1.0 if device_data.get('hardware_verified', False) else 0.0
            reputation_score = device_data.get('reputation_score', 0.5)
            age_score = min((time.time() - device_data.get('first_seen', time.time())) / (30 * 24 * 3600), 1.0)  # 30 days max

            # Weighted average
            trust_score = (
                uptime_score * 0.3 +
                verification_score * 0.3 +
                reputation_score * 0.25 +
                age_score * 0.15
            )

            return trust_score

        # Unknown device - low trust
        return 0.2

    async def register_device(self, fingerprint: str, device_info: Dict):
        """Register a new device in the oracle"""
        self.device_registry[fingerprint] = {
            **device_info,
            'first_seen': time.time(),
            'last_seen': time.time(),
            'trust_score': 0.5,  # Start with neutral trust
            'reputation_score': 0.5
        }

    async def update_device_reputation(self, fingerprint: str, behavior_score: float):
        """Update device reputation based on behavior"""
        if fingerprint in self.device_registry:
            device = self.device_registry[fingerprint]

            # Update reputation with exponential moving average
            alpha = 0.1  # Smoothing factor
            device['reputation_score'] = (alpha * behavior_score +
                                        (1 - alpha) * device['reputation_score'])

            device['last_seen'] = time.time()


class HardwareVerifier:
    """Hardware verification for device authenticity"""

    def __init__(self):
        self.verification_cache = {}
        self.trusted_manufacturers = ['Raspberry Pi', 'Arduino', 'ESP32']

    async def verify(self, hardware_signature: str) -> Dict:
        """Verify hardware authenticity"""
        if not hardware_signature:
            return {
                'verified': False,
                'trust_level': 0.0,
                'manufacturer': 'unknown',
                'model': 'unknown'
            }

        # Check cache first
        if hardware_signature in self.verification_cache:
            cached_result = self.verification_cache[hardware_signature]
            if time.time() - cached_result['timestamp'] < 3600:  # 1 hour cache
                return cached_result

        # Perform hardware verification (simplified)
        verification_result = await self._perform_hardware_verification(hardware_signature)

        # Cache result
        self.verification_cache[hardware_signature] = {
            **verification_result,
            'timestamp': time.time()
        }

        return verification_result

    async def _perform_hardware_verification(self, signature: str) -> Dict:
        """Perform actual hardware verification"""
        # In production, this would verify against hardware certificates,
        # TPM measurements, or secure boot signatures

        # Simplified verification based on signature format
        if len(signature) < 20:
            return {
                'verified': False,
                'trust_level': 0.0,
                'manufacturer': 'unknown',
                'model': 'unknown'
            }

        # Check for known manufacturer signatures
        manufacturer = 'unknown'
        for mf in self.trusted_manufacturers:
            if mf.lower().replace(' ', '') in signature.lower():
                manufacturer = mf
                break

        # Calculate trust level based on signature strength
        trust_level = min(len(signature) / 64, 1.0)  # Normalize to 0-1

        return {
            'verified': trust_level > 0.5,
            'trust_level': trust_level,
            'manufacturer': manufacturer,
            'model': f"{manufacturer} Device",
            'serial_verified': True,  # Assume serial verification passed
            'secure_boot': trust_level > 0.7
        }


class DeviceNetwork:
    """IoT device network management"""

    def __init__(self):
        self.devices = {}
        self.network_health = 0.8  # Default health score

    async def get_status(self) -> Dict:
        """Get current network status"""
        active_devices = len([d for d in self.devices.values() if d.get('active', False)])

        return {
            'active_devices': active_devices,
            'total_devices': len(self.devices),
            'average_uptime': self._calculate_average_uptime(),
            'threat_detection': True,
            'last_scan': time.time(),
            'devices': list(self.devices.values())
        }

    def _calculate_average_uptime(self) -> float:
        """Calculate average uptime across network"""
        uptimes = [d.get('uptime_percentage', 0) for d in self.devices.values()]
        return statistics.mean(uptimes) if uptimes else 0.0

    def get_network_health(self) -> float:
        """Get overall network health score"""
        return self.network_health

    async def detect_threats(self, transaction: Dict) -> List[Dict]:
        """Detect network-based threats"""
        threats = []

        # Check for DDoS patterns
        if await self._detect_ddos_pattern(transaction):
            threats.append({
                'type': 'ddos_attempt',
                'severity': 'high',
                'description': 'Potential DDoS attack pattern detected'
            })

        # Check for sybil attacks
        if await self._detect_sybil_attack(transaction):
            threats.append({
                'type': 'sybil_attack',
                'severity': 'medium',
                'description': 'Possible sybil attack detected'
            })

        return threats

    async def _detect_ddos_pattern(self, transaction: Dict) -> bool:
        """Detect potential DDoS attack patterns"""
        # Simplified detection - check for rapid repeated transactions
        return False  # Placeholder

    async def _detect_sybil_attack(self, transaction: Dict) -> bool:
        """Detect potential sybil attacks"""
        # Simplified detection - check for suspicious account patterns
        return False  # Placeholder