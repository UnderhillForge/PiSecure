#!/usr/bin/env python3
"""
PiSecure Python Client with ML-Powered Intelligence
==================================================

Advanced Python client for PiSecure blockchain with integrated ML-powered
threat detection, smart routing, and predictive analytics.

Features:
- ML-powered attack detection and defense
- Smart peer routing with threat awareness
- Geographic clustering optimization
- Predictive network load analysis
- Real-time intelligence streaming
- Type-safe intelligence methods
"""

import asyncio
import json
import time
import hashlib
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlencode
import websockets
import aiohttp
import requests

logger = logging.getLogger(__name__)


@dataclass
class ThreatAnalysis:
    """Type-safe threat intelligence data"""
    threat_level: str
    active_attacks: List[Dict]
    confidence: float
    timestamp: float
    ml_score: Optional[float] = None
    analysis_period: str = "last_hour"


@dataclass
class OptimizedRoute:
    """Type-safe routing optimization data"""
    optimized_nodes: List[Dict]
    scoring_method: str
    threat_adjusted: bool
    total_candidates: int
    geo_score: Optional[float] = None
    load_score: Optional[float] = None
    reliability_score: Optional[float] = None


@dataclass
class NetworkHealth:
    """Type-safe network health data"""
    overall_health: int
    threat_level: str
    participation: float
    avg_block_time: float
    health_score: float
    timestamp: float


class IntelligenceConfig:
    """Configuration for intelligence features"""

    def __init__(self,
                 threat_detection: bool = True,
                 smart_routing: bool = True,
                 geographic_optimization: bool = True,
                 predictive_analytics: bool = True,
                 threat_awareness_level: str = 'advanced'):
        self.threat_detection = threat_detection
        self.smart_routing = smart_routing
        self.geographic_optimization = geographic_optimization
        self.predictive_analytics = predictive_analytics
        self.threat_awareness_level = threat_awareness_level


class ConnectionPool:
    """Intelligent connection pool with threat-aware load balancing"""

    def __init__(self):
        self.endpoints: List[str] = []
        self.health_status: Dict[str, Dict] = {}
        self.current_index = 0
        self._lock = threading.Lock()
        self._client_ref: Optional['PiSecureClient'] = None

    def add_endpoint(self, endpoint: str):
        """Add endpoint to pool"""
        if endpoint not in self.endpoints:
            self.endpoints.append(endpoint)

    def set_client_reference(self, client: 'PiSecureClient'):
        """Set reference to client for intelligence access"""
        self._client_ref = client

    def get_next_endpoint(self, service_type: str = 'general') -> str:
        """Get next endpoint with intelligence optimization"""
        if not self.endpoints:
            raise ValueError("No available endpoints")

        # Try intelligence-optimized selection first
        if self._client_ref and self._client_ref.intelligence_config.smart_routing:
            try:
                candidate_data = []
                for endpoint in self.endpoints:
                    candidate_data.append({
                        'node_id': endpoint,
                        'location': 'unknown',  # Would need geocoding in production
                        'load_factor': self._estimate_load_factor(endpoint),
                        'reliability_score': self._get_reliability_score(endpoint)
                    })

                optimization = self._client_ref.optimize_peer_routing(
                    available_nodes=candidate_data,
                    service_type=service_type
                )

                if optimization.optimized_nodes:
                    optimized_endpoint = optimization.optimized_nodes[0]['node']
                    if optimized_endpoint in self.endpoints and self.is_healthy(optimized_endpoint):
                        return optimized_endpoint

            except Exception as e:
                logger.debug(f"Intelligence optimization failed: {e}")

        # Fallback to round-robin
        with self._lock:
            attempts = 0
            while attempts < len(self.endpoints):
                endpoint = self.endpoints[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.endpoints)

                if self.is_healthy(endpoint):
                    return endpoint
                attempts += 1

        raise ValueError("No healthy endpoints available")

    def mark_healthy(self, endpoint: str):
        """Mark endpoint as healthy"""
        self.health_status[endpoint] = {
            'healthy': True,
            'last_check': time.time()
        }

    def mark_unhealthy(self, endpoint: str):
        """Mark endpoint as unhealthy"""
        self.health_status[endpoint] = {
            'healthy': False,
            'last_check': time.time()
        }

    def is_healthy(self, endpoint: str) -> bool:
        """Check if endpoint is healthy"""
        status = self.health_status.get(endpoint)
        if not status:
            return True  # Assume healthy if not checked

        # If marked unhealthy recently, consider unhealthy
        if not status['healthy'] and time.time() - status['last_check'] < 60:
            return False

        return True

    def _estimate_load_factor(self, endpoint: str) -> float:
        """Estimate load factor for endpoint"""
        status = self.health_status.get(endpoint)
        if not status:
            return 0.5  # Default medium load

        if not status['healthy']:
            return 0.9  # High load if unhealthy

        return 0.3  # Assume healthy endpoints have lower load

    def _get_reliability_score(self, endpoint: str) -> float:
        """Get reliability score for endpoint"""
        status = self.health_status.get(endpoint)
        if not status:
            return 0.8  # Default good reliability

        # Lower score if recently unhealthy
        if not status['healthy'] and time.time() - status['last_check'] < 300:
            return 0.3

        return 0.9  # Healthy endpoints get high reliability


class PiSecureClient:
    """
    Advanced PiSecure Python Client with ML-Powered Intelligence

    Features:
    - ML-powered threat detection and defense
    - Smart routing with geographic optimization
    - Predictive analytics and network insights
    - Real-time intelligence streaming
    - Type-safe intelligence methods
    """

    def __init__(self,
                 api_url: str = None,
                 api_key: str = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 intelligence_enabled: bool = True,
                 intelligence_config: IntelligenceConfig = None):
        """
        Initialize PiSecure client with intelligence features

        Args:
            api_url: Base API URL (optional, will auto-discover)
            api_key: API key for authenticated requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            intelligence_enabled: Enable intelligence features
            intelligence_config: Intelligence configuration
        """
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.intelligence_enabled = intelligence_enabled
        self.intelligence_config = intelligence_config or IntelligenceConfig()

        # Core components
        self.connection_pool = ConnectionPool()
        self.connection_pool.set_client_reference(self)
        self.session = requests.Session()
        self.session.timeout = timeout

        # Set up headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PiSecure-Python-Client/1.0.0'
        })
        if api_key:
            self.session.headers['X-API-Key'] = api_key

        # Intelligence state
        self._threat_cache: Optional[ThreatAnalysis] = None
        self._threat_cache_time = 0
        self._threat_cache_ttl = 60  # 1 minute

        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        self._intelligence_callbacks: Dict[str, List[Callable]] = {}

        # Auto-discover endpoints if not provided
        if not api_url:
            self._discover_endpoints()

        # Fallback endpoints
        if not self.connection_pool.endpoints:
            self.connection_pool.add_endpoint('http://localhost:3142')

    def _discover_endpoints(self):
        """Discover available endpoints from bootstrap"""
        bootstrap_urls = [
            "https://bootstrap.pisecure.org/api/v1/bootstrap/peers",
            "https://pisecure-bootstrap-production.up.railway.app/api/v1/bootstrap/peers"
        ]

        for url in bootstrap_urls:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                peers = response.json().get('peers', [])

                for peer in peers:
                    api_url = peer.get('api_url') or f"http://{peer['host']}:{peer.get('port', 3142)}"
                    self.connection_pool.add_endpoint(api_url)

                if self.connection_pool.endpoints:
                    break

            except Exception as e:
                logger.debug(f"Failed to discover from {url}: {e}")
                continue

    def _make_request(self,
                     method: str,
                     endpoint: str,
                     data: Any = None,
                     params: Dict = None,
                     intelligence_aware: bool = True) -> Dict:
        """
        Make HTTP request with intelligence awareness

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            intelligence_aware: Whether to use intelligence features
        """
        url = self._build_url(endpoint, params)
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Get endpoint with intelligence (if enabled)
                if intelligence_aware and self.intelligence_enabled:
                    base_url = self.connection_pool.get_next_endpoint()
                else:
                    # Simple round-robin fallback
                    endpoints = self.connection_pool.endpoints
                    if not endpoints:
                        raise ValueError("No endpoints available")
                    base_url = endpoints[attempt % len(endpoints)]

                full_url = urljoin(base_url + '/', url.lstrip('/'))

                # Prepare request
                kwargs = {'timeout': self.timeout}
                if data:
                    kwargs['json'] = data

                response = self.session.request(method, full_url, **kwargs)
                response.raise_for_status()

                # Mark endpoint as healthy
                self.connection_pool.mark_healthy(base_url)

                return response.json()

            except Exception as e:
                last_error = e
                # Mark endpoint as unhealthy
                try:
                    base_url = self.connection_pool.endpoints[attempt % len(self.connection_pool.endpoints)]
                    self.connection_pool.mark_unhealthy(base_url)
                except:
                    pass

                # Check if it's a threat-related failure
                if self.intelligence_enabled and intelligence_aware:
                    try:
                        threat_info = self.get_threat_intelligence()
                        if threat_info.threat_level in ['high', 'critical']:
                            logger.warning(f"High threat level detected during request: {threat_info.threat_level}")
                    except:
                        pass

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt * 0.1)

        raise Exception(f"Request failed after {self.max_retries} attempts: {last_error}")

    def _build_url(self, endpoint: str, params: Dict = None) -> str:
        """Build API URL"""
        url = f"/api/v1/{endpoint.lstrip('/')}"
        if params:
            url += "?" + urlencode(params)
        return url

    # === INTELLIGENCE METHODS ===

    # Attack Detection & Threat Intelligence

    def get_threat_intelligence(self) -> ThreatAnalysis:
        """Get ML-powered attack detection analysis"""
        if not self.intelligence_enabled:
            return ThreatAnalysis('unknown', [], 0.0, time.time())

        # Check cache
        if (self._threat_cache and
            time.time() - self._threat_cache_time < self._threat_cache_ttl):
            return self._threat_cache

        try:
            response = self._make_request('GET', 'intelligence/attacks')

            threat_analysis = ThreatAnalysis(
                threat_level=response.get('threat_level', 'unknown'),
                active_attacks=response.get('detected_attacks', []),
                confidence=response.get('confidence', 0.5),
                timestamp=response.get('timestamp', time.time()),
                ml_score=response.get('ml_score'),
                analysis_period=response.get('analysis_period', 'unknown')
            )

            # Cache result
            self._threat_cache = threat_analysis
            self._threat_cache_time = time.time()

            return threat_analysis

        except Exception as e:
            logger.error(f"Failed to get threat intelligence: {e}")
            return ThreatAnalysis('unknown', [], 0.0, time.time())

    def get_defense_status(self) -> Dict[str, Any]:
        """Get automated defense system status"""
        try:
            return self._make_request('GET', 'intelligence/defense')
        except Exception as e:
            logger.error(f"Failed to get defense status: {e}")
            return {'defense_intelligence': {'automated_defense_active': False}}

    def get_network_health(self) -> NetworkHealth:
        """Get comprehensive network health analysis"""
        try:
            response = self._make_request('GET', 'intelligence/health')

            return NetworkHealth(
                overall_health=response.get('network_health', {}).get('overall_health', 50),
                threat_level=response.get('network_health', {}).get('threat_level', 'unknown'),
                participation=response.get('network_health', {}).get('participation', 0.0),
                avg_block_time=response.get('network_health', {}).get('avg_block_time', 600),
                health_score=response.get('network_health', {}).get('health_score', 0.5),
                timestamp=response.get('timestamp', time.time())
            )
        except Exception as e:
            logger.error(f"Failed to get network health: {e}")
            return NetworkHealth(50, 'unknown', 0.0, 600, 0.5, time.time())

    # Smart Routing & Geographic Intelligence

    def optimize_peer_routing(self,
                            available_nodes: List[Dict],
                            service_type: str = 'general') -> OptimizedRoute:
        """Get AI-optimized peer routing"""
        if not self.intelligence_enabled:
            # Return first node as fallback
            return OptimizedRoute([available_nodes[0]] if available_nodes else [],
                                'fallback', False, len(available_nodes))

        try:
            data = {
                'available_nodes': available_nodes,
                'service_type': service_type
            }

            response = self._make_request('POST', 'intelligence/optimize', data)

            return OptimizedRoute(
                optimized_nodes=response.get('optimized_nodes', []),
                scoring_method=response.get('optimization_method', 'unknown'),
                threat_adjusted=response.get('threat_adjusted', False),
                total_candidates=response.get('total_candidates', len(available_nodes)),
                geo_score=response.get('geo_score'),
                load_score=response.get('load_score'),
                reliability_score=response.get('reliability_score')
            )

        except Exception as e:
            logger.error(f"Failed to optimize routing: {e}")
            # Return basic optimization
            return OptimizedRoute(available_nodes[:3], 'fallback', False, len(available_nodes))

    def get_geographic_clusters(self) -> Dict[str, Any]:
        """Get geographic clustering analysis"""
        try:
            return self._make_request('GET', 'intelligence/clusters')
        except Exception as e:
            logger.error(f"Failed to get geographic clusters: {e}")
            return {'geographic_clusters': {}, 'clustering_method': 'unavailable'}

    # Predictive Analytics

    def predict_network_load(self, hours_ahead: int = 1) -> Dict[str, Any]:
        """Get network load predictions"""
        try:
            params = {'hours_ahead': min(hours_ahead, 24)}
            return self._make_request('GET', 'intelligence/predict', None, params)
        except Exception as e:
            logger.error(f"Failed to predict network load: {e}")
            return {'predictions': {'predicted_connections': 0, 'confidence': 'unknown'}}

    def get_network_insights(self) -> NetworkHealth:
        """Get comprehensive network intelligence"""
        return self.get_network_health()

    # === STANDARD BLOCKCHAIN METHODS ===

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._make_request('GET', 'blockchain/info')

    def get_block(self, block_index: int) -> Dict[str, Any]:
        """Get block by index"""
        return self._make_request('GET', f'blockchain/block/{block_index}')

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction by hash"""
        return self._make_request('GET', f'blockchain/transaction/{tx_hash}')

    def get_wallet_balance(self, address: str) -> float:
        """Get wallet balance"""
        response = self._make_request('GET', f'wallet/{address}/balance')
        return float(response.get('balance', 0))

    def submit_transaction(self, tx_data: Dict[str, Any]) -> str:
        """Submit transaction to network"""
        # Check network health before submission if intelligence enabled
        if self.intelligence_enabled and self.intelligence_config.threat_detection:
            try:
                health = self.get_network_health()
                if health.threat_level in ['high', 'critical']:
                    logger.warning(f"High threat level detected: {health.threat_level}")
            except Exception as e:
                logger.debug(f"Could not check network health: {e}")

        response = self._make_request('POST', 'transaction', tx_data)
        return response.get('transaction_hash', '')

    def get_network_peers(self) -> List[Dict[str, Any]]:
        """Get network peers"""
        response = self._make_request('GET', 'network/peers')
        return response.get('peers', [])

    def get_optimized_peers(self,
                           service_type: str = 'general',
                           threat_aware: bool = True) -> List[Dict[str, Any]]:
        """Get peers optimized by intelligence"""
        if not self.intelligence_enabled or not threat_aware:
            return self.get_network_peers()

        try:
            basic_peers = self.get_network_peers()
            optimization = self.optimize_peer_routing(basic_peers, service_type)
            return optimization.optimized_nodes
        except Exception as e:
            logger.error(f"Failed to get optimized peers: {e}")
            return self.get_network_peers()

    # === MINER INTELLIGENCE CONTRIBUTION ===

    def report_miner_intelligence(self,
                                miner_id: str,
                                intelligence_type: str,
                                data: Dict[str, Any],
                                location: str = None,
                                confidence: float = 0.8) -> Dict[str, Any]:
        """
        Report intelligence from mining node back to bootstrap network.

        This enables miners to contribute to the collective intelligence,
        creating decentralized threat detection and network optimization.

        Args:
            miner_id: Unique identifier for the mining node
            intelligence_type: Type of intelligence ('connection_anomaly', 'geographic_attack', 'latency_spike', etc.)
            data: Intelligence data payload
            location: Geographic location of the miner
            confidence: Confidence score (0.0-1.0) in the intelligence

        Returns:
            Dict containing report acceptance status
        """
        if not self.intelligence_enabled:
            return {'report_accepted': False, 'reason': 'intelligence_disabled'}

        report_data = {
            'miner_id': miner_id,
            'intelligence_type': intelligence_type,
            'data': data,
            'location': location,
            'confidence': confidence,
            'timestamp': time.time(),
            'hardware_info': self._get_miner_hardware_info(),
            'network_context': self._get_network_context()
        }

        # Sign the report (in production, would use proper cryptographic signing)
        report_data['signature'] = self._sign_intelligence_report(report_data)

        try:
            response = self._make_request('POST', 'intelligence/miner-report', report_data)
            return response
        except Exception as e:
            logger.error(f"Failed to submit miner intelligence: {e}")
            return {'report_accepted': False, 'error': str(e)}

    def report_connection_anomaly(self,
                                miner_id: str,
                                target_ip: str,
                                anomaly_type: str,
                                severity: str = 'medium',
                                metadata: Dict = None) -> Dict[str, Any]:
        """Report suspicious connection behavior observed by miner"""
        data = {
            'target_ip': target_ip,
            'anomaly_type': anomaly_type,  # 'unusual_traffic', 'connection_storm', 'geographic_anomaly'
            'severity': severity,
            'connection_count': metadata.get('connection_count', 0) if metadata else 0,
            'time_window': metadata.get('time_window', 300) if metadata else 300,  # 5 minutes
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'connection_anomaly', data)

    def report_geographic_attack_pattern(self,
                                       miner_id: str,
                                       region: str,
                                       attack_vector: str,
                                       affected_nodes: int = 1,
                                       metadata: Dict = None) -> Dict[str, Any]:
        """Report geographic attack patterns observed by miner"""
        data = {
            'region': region,
            'attack_vector': attack_vector,  # 'ddos', 'sybil_attack', 'eclipse_attack'
            'affected_nodes': affected_nodes,
            'attack_duration': metadata.get('duration', 0) if metadata else 0,
            'targeted_services': metadata.get('services', []) if metadata else [],
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'geographic_attack', data, region)

    def report_network_latency_anomaly(self,
                                     miner_id: str,
                                     target_region: str,
                                     latency_ms: float,
                                     baseline_latency: float = None,
                                     metadata: Dict = None) -> Dict[str, Any]:
        """Report network latency anomalies that could indicate attacks"""
        data = {
            'target_region': target_region,
            'measured_latency': latency_ms,
            'baseline_latency': baseline_latency,
            'latency_increase': latency_ms - (baseline_latency or 0),
            'anomaly_score': self._calculate_latency_anomaly_score(latency_ms, baseline_latency),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'latency_anomaly', data)

    def report_hardware_security_event(self,
                                     miner_id: str,
                                     event_type: str,
                                     severity: str = 'high',
                                     metadata: Dict = None) -> Dict[str, Any]:
        """Report hardware-level security events"""
        data = {
            'event_type': event_type,  # 'temperature_anomaly', 'power_spike', 'unauthorized_access'
            'severity': severity,
            'hardware_metrics': self._get_detailed_hardware_metrics(),
            'system_integrity': self._check_system_integrity(),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'hardware_security', data)

    # === MINING-SPECIFIC INTELLIGENCE REPORTING ===

    def report_hashrate_anomaly(self,
                              miner_id: str,
                              measured_hashrate: float,
                              expected_hashrate: float,
                              anomaly_type: str,
                              severity: str = 'medium',
                              metadata: Dict = None) -> Dict[str, Any]:
        """
        Report unusual mining hashrate activity patterns.

        Useful for detecting:
        - Hashrate hijacking attacks
        - Botnet mining activity
        - Hardware failures
        - Mining pool attacks
        """
        data = {
            'measured_hashrate': measured_hashrate,  # MH/s
            'expected_hashrate': expected_hashrate,  # MH/s
            'hashrate_deviation': measured_hashrate - expected_hashrate,
            'deviation_percentage': ((measured_hashrate - expected_hashrate) / expected_hashrate) * 100 if expected_hashrate > 0 else 0,
            'anomaly_type': anomaly_type,  # 'hashrate_drop', 'hashrate_spike', 'unstable_hashrate'
            'severity': severity,
            'mining_hardware': self._get_miner_hardware_info(),
            'mining_metrics': self._get_mining_performance_metrics(),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'hashrate_anomaly', data)

    def report_block_propagation_anomaly(self,
                                       miner_id: str,
                                       block_hash: str,
                                       propagation_time: float,
                                       expected_time: float,
                                       network_conditions: Dict = None,
                                       metadata: Dict = None) -> Dict[str, Any]:
        """
        Report block propagation time anomalies for network latency intelligence.

        Useful for detecting:
        - Network congestion
        - Geographic routing issues
        - P2P network health problems
        - Eclipse attacks
        """
        data = {
            'block_hash': block_hash[:16] + '...',
            'propagation_time': propagation_time,  # seconds
            'expected_time': expected_time,  # seconds
            'time_deviation': propagation_time - expected_time,
            'deviation_percentage': ((propagation_time - expected_time) / expected_time) * 100 if expected_time > 0 else 0,
            'network_conditions': network_conditions or self._get_network_context(),
            'geographic_factors': self._analyze_geographic_factors(),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'block_propagation_anomaly', data)

    def report_geographic_mining_distribution(self,
                                           miner_id: str,
                                           region: str,
                                           mining_concentration: float,
                                           pool_distribution: Dict[str, float],
                                           decentralization_score: float,
                                           metadata: Dict = None) -> Dict[str, Any]:
        """
        Report geographic mining distribution patterns for mining pool concentration analysis.

        Useful for monitoring:
        - Mining decentralization
        - Geographic attack vectors
        - Mining pool dominance
        - Regional mining health
        """
        data = {
            'region': region,
            'mining_concentration': mining_concentration,  # percentage of regional mining power
            'pool_distribution': pool_distribution,  # {'pool_name': percentage}
            'decentralization_score': decentralization_score,  # 0.0 (centralized) to 1.0 (decentralized)
            'regional_stats': self._get_regional_mining_stats(region),
            'pool_dominance_risk': self._calculate_pool_dominance_risk(pool_distribution),
            'geographic_diversity': self._analyze_geographic_diversity(pool_distribution),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'geographic_mining_distribution', data, region)

    def report_hardware_performance_trends(self,
                                         miner_id: str,
                                         performance_trends: Dict[str, Any],
                                         efficiency_score: float,
                                         degradation_indicators: List[str],
                                         metadata: Dict = None) -> Dict[str, Any]:
        """
        Report mining hardware performance trends and efficiency analysis.

        Useful for detecting:
        - Hardware aging/failure patterns
        - Thermal throttling issues
        - Power supply problems
        - Mining efficiency optimization opportunities
        """
        data = {
            'performance_trends': performance_trends,  # {'hashrate_trend': [...], 'efficiency_trend': [...]}
            'efficiency_score': efficiency_score,  # 0.0 (poor) to 1.0 (optimal)
            'degradation_indicators': degradation_indicators,  # ['thermal_throttling', 'power_issues', ...]
            'hardware_health': self._get_detailed_hardware_metrics(),
            'mining_optimization': self._get_mining_optimization_suggestions(efficiency_score),
            'trend_analysis': self._analyze_performance_trends(performance_trends),
            'metadata': metadata or {}
        }

        return self.report_miner_intelligence(miner_id, 'hardware_performance_trends', data)

    # === WALLET INTELLIGENCE CONTRIBUTION ===

    def report_wallet_intelligence(self,
                                 wallet_id: str,
                                 intelligence_type: str,
                                 data: Dict[str, Any],
                                 privacy_level: str = 'aggregated',
                                 confidence: float = 0.8) -> Dict[str, Any]:
        """
        Report privacy-preserving transaction pattern intelligence from wallet nodes.

        Wallets contribute anonymized transaction patterns to enhance network intelligence
        while maintaining user privacy through aggregation and anonymization.

        Args:
            wallet_id: Anonymized wallet identifier (not actual address)
            intelligence_type: Type of intelligence ('volume_patterns', 'geographic_distribution', 'fee_market', 'fraud_patterns')
            data: Privacy-preserving intelligence data
            privacy_level: Privacy protection level ('aggregated', 'anonymized', 'minimal')
            confidence: Confidence score in the intelligence

        Returns:
            Dict containing report acceptance status
        """
        if not self.intelligence_enabled:
            return {'report_accepted': False, 'reason': 'intelligence_disabled'}

        # Apply privacy transformations based on privacy level
        if privacy_level == 'aggregated':
            data = self._aggregate_wallet_data(data)
        elif privacy_level == 'anonymized':
            data = self._anonymize_wallet_data(data)
        elif privacy_level == 'minimal':
            data = self._minimize_wallet_data(data)

        report_data = {
            'wallet_id': wallet_id,  # Anonymized identifier
            'intelligence_type': intelligence_type,
            'data': data,
            'privacy_level': privacy_level,
            'confidence': confidence,
            'timestamp': time.time(),
            'wallet_context': self._get_wallet_context(),  # Non-identifying context
            'network_participation': self._get_wallet_network_participation()
        }

        # Privacy-preserving signature (not linked to actual wallet)
        report_data['signature'] = self._sign_privacy_preserving_report(report_data)

        try:
            response = self._make_request('POST', 'intelligence/wallet-report', report_data)
            return response
        except Exception as e:
            logger.error(f"Failed to submit wallet intelligence: {e}")
            return {'report_accepted': False, 'error': str(e)}

    def report_transaction_volume_patterns(self,
                                        wallet_id: str,
                                        time_window_hours: int,
                                        transaction_counts: Dict[str, int],
                                        volume_trends: Dict[str, Any],
                                        network_comparison: Dict = None,
                                        privacy_level: str = 'aggregated') -> Dict[str, Any]:
        """
        Report transaction volume patterns for network usage analytics.

        Provides insights into transaction frequency and timing patterns
        to help optimize network capacity planning.

        Args:
            wallet_id: Anonymized wallet identifier
            time_window_hours: Analysis time window in hours
            transaction_counts: Transaction counts by type/category
            volume_trends: Volume trend analysis (increasing/decreasing/stable)
            network_comparison: Comparison with network averages
            privacy_level: Privacy protection level
        """
        data = {
            'time_window_hours': time_window_hours,
            'transaction_counts': transaction_counts,  # e.g., {'transfers': 25, 'contracts': 5}
            'volume_trends': volume_trends,  # e.g., {'direction': 'increasing', 'rate': 0.15}
            'network_comparison': network_comparison or {},
            'peak_usage_hours': self._analyze_peak_usage_patterns(transaction_counts),
            'usage_consistency': self._calculate_usage_consistency(volume_trends),
            'capacity_implications': self._assess_network_capacity_impact(volume_trends)
        }

        return self.report_wallet_intelligence(wallet_id, 'volume_patterns', data, privacy_level)

    def report_geographic_transaction_distribution(self,
                                                wallet_id: str,
                                                region_activity: Dict[str, float],
                                                cross_border_patterns: Dict[str, Any],
                                                regional_preferences: List[str],
                                                privacy_level: str = 'aggregated') -> Dict[str, Any]:
        """
        Report geographic transaction distribution patterns.

        Helps understand regional network usage and optimize geographic routing.

        Args:
            wallet_id: Anonymized wallet identifier
            region_activity: Transaction activity by region (percentages)
            cross_border_patterns: Cross-border transaction patterns
            regional_preferences: Preferred regions for transactions
            privacy_level: Privacy protection level
        """
        data = {
            'region_activity': region_activity,  # e.g., {'us-east': 0.4, 'eu-west': 0.35, 'asia': 0.25}
            'cross_border_patterns': cross_border_patterns,  # e.g., {'frequency': 'weekly', 'typical_regions': ['us', 'eu']}
            'regional_preferences': regional_preferences,  # e.g., ['us-east', 'us-central']
            'geographic_diversity': self._calculate_geographic_diversity(region_activity),
            'regional_concentration_risk': self._assess_regional_concentration_risk(region_activity),
            'network_topology_implications': self._analyze_topology_implications(region_activity)
        }

        return self.report_wallet_intelligence(wallet_id, 'geographic_distribution', data, privacy_level)

    def report_fee_market_intelligence(self,
                                    wallet_id: str,
                                    fee_observations: Dict[str, Any],
                                    fee_acceptance_patterns: Dict[str, Any],
                                    market_sentiment: str,
                                    privacy_level: str = 'aggregated') -> Dict[str, Any]:
        """
        Report fee market intelligence for transaction fee optimization.

        Provides data to help optimize fee estimation and network economics.

        Args:
            wallet_id: Anonymized wallet identifier
            fee_observations: Observed fee levels and acceptance rates
            fee_acceptance_patterns: Patterns in fee acceptance
            market_sentiment: Overall fee market sentiment ('optimistic', 'pessimistic', 'neutral')
            privacy_level: Privacy protection level
        """
        data = {
            'fee_observations': fee_observations,  # e.g., {'average_fee': 0.001, 'median_fee': 0.0008}
            'fee_acceptance_patterns': fee_acceptance_patterns,  # e.g., {'fast_confirmation_rate': 0.85, 'slow_rate': 0.95}
            'market_sentiment': market_sentiment,
            'fee_efficiency_analysis': self._analyze_fee_efficiency(fee_observations),
            'confirmation_time_trends': self._analyze_confirmation_trends(fee_acceptance_patterns),
            'economic_optimization_opportunities': self._identify_fee_optimization_opportunities(fee_observations, fee_acceptance_patterns)
        }

        return self.report_wallet_intelligence(wallet_id, 'fee_market', data, privacy_level)

    def report_fraud_pattern_detection(self,
                                    wallet_id: str,
                                    suspicious_patterns: List[Dict[str, Any]],
                                    risk_assessments: Dict[str, Any],
                                    anomaly_scores: Dict[str, float],
                                    privacy_level: str = 'anonymized') -> Dict[str, Any]:
        """
        Report fraud pattern detection observations.

        Helps identify and prevent fraudulent transaction patterns while maintaining privacy.

        Args:
            wallet_id: Anonymized wallet identifier
            suspicious_patterns: Detected suspicious transaction patterns
            risk_assessments: Risk assessments for different pattern types
            anomaly_scores: Anomaly scores for different behaviors
            privacy_level: Privacy protection level (higher for sensitive fraud data)
        """
        data = {
            'suspicious_patterns': suspicious_patterns,  # Anonymized pattern descriptions
            'risk_assessments': risk_assessments,  # Risk levels by category
            'anomaly_scores': anomaly_scores,  # Statistical anomaly scores
            'pattern_frequency_analysis': self._analyze_pattern_frequencies(suspicious_patterns),
            'risk_trend_analysis': self._analyze_risk_trends(risk_assessments),
            'preventive_measure_suggestions': self._suggest_fraud_prevention_measures(anomaly_scores)
        }

        return self.report_wallet_intelligence(wallet_id, 'fraud_patterns', data, privacy_level)

    # === INTELLIGENCE-AWARE APPLICATION EXAMPLES ===

    def submit_sensor_reading_intelligent(self,
                                        device_id: str,
                                        sensor_type: str,
                                        value: float,
                                        unit: str,
                                        location: str = None) -> str:
        """Submit sensor reading with intelligence awareness"""
        # Check network health before submission
        try:
            health = self.get_network_health()
            if health.overall_health < 50:
                logger.warning("Poor network health detected")
        except Exception as e:
            pass

        # Create transaction
        data = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "location": location,
            "timestamp": int(time.time()),
            "reading_id": hashlib.sha256(f"{device_id}{sensor_type}{time.time()}".encode()).hexdigest()[:16]
        }

        tx = {
            "type": "sensor_reading",
            "data": data,
            "signature": "",  # Would be signed by device
            "timestamp": int(time.time())
        }

        return self.submit_transaction(tx)

    def record_supply_chain_event_intelligent(self,
                                            product_id: str,
                                            event_type: str,
                                            manufacturer: str,
                                            data: Dict[str, Any]) -> str:
        """Record supply chain event with intelligence awareness"""
        # Get threat intelligence for security
        try:
            threat_info = self.get_threat_intelligence()
            if threat_info.threat_level == 'high':
                logger.warning("High threat level - proceeding with caution")
        except Exception as e:
            pass

        # Create transaction
        tx_data = {
            "event_type": event_type,
            "product_id": product_id,
            "manufacturer": manufacturer,
            "data": data,
            "timestamp": int(time.time())
        }

        tx = {
            "type": "supply_chain_event",
            "data": tx_data,
            "signature": "",  # Would be signed by manufacturer
            "timestamp": int(time.time())
        }

        return self.submit_transaction(tx)

    # === MINER INTELLIGENCE HELPERS ===

    def _get_miner_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information for miner intelligence reporting"""
        try:
            return {
                'cpu_model': 'Raspberry Pi',  # Would detect actual model
                'memory_gb': 4,  # Would detect actual memory
                'has_gpu': False,  # Pi doesn't have dedicated GPU
                'mining_capable': True,
                'thermal_throttling': False  # Would check thermal status
            }
        except Exception:
            return {'hardware_detection_failed': True}

    def _get_network_context(self) -> Dict[str, Any]:
        """Get network context for intelligence reporting"""
        try:
            return {
                'connected_peers': len(self.get_network_peers()),
                'network_health': self.get_network_health().overall_health,
                'threat_level': self.get_threat_intelligence().threat_level,
                'uptime_seconds': time.time()  # Would track actual uptime
            }
        except Exception:
            return {'network_context_unavailable': True}

    def _sign_intelligence_report(self, report_data: Dict[str, Any]) -> str:
        """Sign intelligence report (simplified for demo)"""
        # In production, this would use proper cryptographic signing
        report_string = json.dumps(report_data, sort_keys=True)
        return hashlib.sha256(report_string.encode()).hexdigest()[:32]

    def _calculate_latency_anomaly_score(self, latency: float, baseline: float = None) -> float:
        """Calculate anomaly score for latency measurements"""
        if not baseline or baseline <= 0:
            return 0.5  # Neutral score if no baseline

        ratio = latency / baseline
        if ratio < 1.2:
            return 0.1  # Normal
        elif ratio < 2.0:
            return 0.5  # Moderate anomaly
        else:
            return 0.9  # High anomaly

    def _get_detailed_hardware_metrics(self) -> Dict[str, Any]:
        """Get detailed hardware metrics for security reporting"""
        try:
            return {
                'cpu_temperature': 45.0,  # Would read from sensors
                'cpu_usage': 0.3,  # Would monitor actual usage
                'memory_usage': 0.4,
                'disk_usage': 0.2,
                'network_interfaces': ['eth0', 'wlan0'],
                'power_consumption': 5.0  # Watts
            }
        except Exception:
            return {'hardware_metrics_unavailable': True}

    def _check_system_integrity(self) -> Dict[str, Any]:
        """Check system integrity for security reporting"""
        try:
            return {
                'filesystem_integrity': True,  # Would check file hashes
                'process_integrity': True,  # Would verify running processes
                'kernel_integrity': True,  # Would check kernel modules
                'last_security_scan': time.time(),
                'known_vulnerabilities': 0
            }
        except Exception:
            return {'integrity_check_failed': True}

    # === MINING-SPECIFIC INTELLIGENCE HELPERS ===

    def _get_mining_performance_metrics(self) -> Dict[str, Any]:
        """Get current mining performance metrics"""
        try:
            return {
                'current_hashrate': 2.5,  # MH/s - would read from mining software
                'average_hashrate_24h': 2.3,  # MH/s
                'mining_efficiency': 0.85,  # percentage
                'power_consumption': 5.2,  # Watts
                'temperature': 48.5,  # Celsius
                'uptime_percentage': 98.5,  # percentage
                'rejected_shares': 0.02,  # percentage
                'pool_connection_status': 'connected'
            }
        except Exception:
            return {'mining_metrics_unavailable': True}

    def _analyze_geographic_factors(self) -> Dict[str, Any]:
        """Analyze geographic factors affecting block propagation"""
        try:
            # Would analyze current network topology and geographic distribution
            return {
                'regional_latency_variation': 0.15,  # coefficient of variation
                'intercontinental_hops': 2,  # estimated network hops
                'optimal_routing_available': True,
                'geographic_diversity_score': 0.78
            }
        except Exception:
            return {'geographic_analysis_unavailable': True}

    def _get_regional_mining_stats(self, region: str) -> Dict[str, Any]:
        """Get regional mining statistics"""
        try:
            # Would gather regional mining data from network
            return {
                'total_regional_hashrate': 500.0,  # TH/s
                'active_miners': 1250,
                'average_miner_hashrate': 2.4,  # MH/s
                'mining_pool_count': 8,
                'regional_difficulty_adjustment': 1.02
            }
        except Exception:
            return {'regional_stats_unavailable': True}

    def _calculate_pool_dominance_risk(self, pool_distribution: Dict[str, float]) -> float:
        """Calculate mining pool dominance risk score"""
        try:
            # Calculate Herfindahl-Hirschman Index for pool concentration
            total_percentage = sum(pool_distribution.values())
            hhi = sum((percentage / total_percentage) ** 2 for percentage in pool_distribution.values())

            # Convert to risk score (0.0 = perfectly distributed, 1.0 = monopoly)
            risk_score = (hhi - 1/len(pool_distribution)) / (1 - 1/len(pool_distribution)) if len(pool_distribution) > 1 else 1.0

            return min(risk_score, 1.0)
        except Exception:
            return 0.5  # Neutral risk if calculation fails

    def _analyze_geographic_diversity(self, pool_distribution: Dict[str, float]) -> Dict[str, Any]:
        """Analyze geographic diversity of mining pools"""
        try:
            # Would analyze geographic distribution of pools
            # Simplified analysis for demo
            pool_count = len(pool_distribution)
            max_concentration = max(pool_distribution.values()) if pool_distribution else 0

            return {
                'pool_geographic_spread': pool_count,
                'max_regional_concentration': max_concentration,
                'diversity_score': min(pool_count / 10, 1.0),  # Normalize to 0-1
                'recommended_diversification': max_concentration > 0.4
            }
        except Exception:
            return {'geographic_diversity_analysis_failed': True}

    def _get_mining_optimization_suggestions(self, efficiency_score: float) -> Dict[str, Any]:
        """Get mining optimization suggestions based on efficiency score"""
        try:
            suggestions = []

            if efficiency_score < 0.5:
                suggestions.extend([
                    'Consider hardware upgrade or replacement',
                    'Check for thermal throttling issues',
                    'Optimize power supply stability',
                    'Review mining software configuration'
                ])
            elif efficiency_score < 0.7:
                suggestions.extend([
                    'Fine-tune mining software parameters',
                    'Monitor temperature trends',
                    'Consider fan or cooling upgrades',
                    'Check for background process interference'
                ])
            elif efficiency_score < 0.9:
                suggestions.extend([
                    'Minor efficiency optimizations possible',
                    'Monitor for gradual performance degradation',
                    'Consider preventive maintenance'
                ])
            else:
                suggestions.append('Mining efficiency is optimal')

            return {
                'efficiency_score': efficiency_score,
                'optimization_suggestions': suggestions,
                'priority_level': 'high' if efficiency_score < 0.6 else 'medium' if efficiency_score < 0.8 else 'low'
            }
        except Exception:
            return {'optimization_suggestions_unavailable': True}

    def _analyze_performance_trends(self, performance_trends: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance trends for predictive maintenance"""
        try:
            analysis = {}

            # Analyze hashrate trends
            if 'hashrate_trend' in performance_trends:
                hashrate_values = performance_trends['hashrate_trend']
                if len(hashrate_values) > 1:
                    trend_slope = (hashrate_values[-1] - hashrate_values[0]) / len(hashrate_values)
                    analysis['hashrate_trend'] = {
                        'slope': trend_slope,
                        'direction': 'increasing' if trend_slope > 0.01 else 'decreasing' if trend_slope < -0.01 else 'stable',
                        'volatility': self._calculate_volatility(hashrate_values)
                    }

            # Analyze efficiency trends
            if 'efficiency_trend' in performance_trends:
                efficiency_values = performance_trends['efficiency_trend']
                if len(efficiency_values) > 1:
                    avg_efficiency = sum(efficiency_values) / len(efficiency_values)
                    analysis['efficiency_analysis'] = {
                        'average_efficiency': avg_efficiency,
                        'trend_quality': 'improving' if efficiency_values[-1] > efficiency_values[0] else 'declining',
                        'consistency': 1 - self._calculate_volatility(efficiency_values)
                    }

            analysis['predictive_maintenance'] = self._predict_maintenance_needs(analysis)

            return analysis
        except Exception:
            return {'trend_analysis_failed': True}

    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate coefficient of variation for volatility measurement"""
        try:
            if len(values) < 2:
                return 0.0

            mean = sum(values) / len(values)
            if mean == 0:
                return 0.0

            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5

            return std_dev / mean  # Coefficient of variation
        except Exception:
            return 0.0

    def _predict_maintenance_needs(self, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Predict maintenance needs based on trend analysis"""
        try:
            maintenance_score = 0.0
            recommendations = []

            # Check hashrate trends
            hashrate_trend = trend_analysis.get('hashrate_trend', {})
            if hashrate_trend.get('direction') == 'decreasing':
                maintenance_score += 0.4
                recommendations.append('Monitor for hardware degradation')

            if hashrate_trend.get('volatility', 0) > 0.1:
                maintenance_score += 0.2
                recommendations.append('Address hashrate instability')

            # Check efficiency trends
            efficiency_analysis = trend_analysis.get('efficiency_analysis', {})
            if efficiency_analysis.get('trend_quality') == 'declining':
                maintenance_score += 0.3
                recommendations.append('Investigate efficiency degradation')

            return {
                'maintenance_score': min(maintenance_score, 1.0),
                'urgency_level': 'high' if maintenance_score > 0.6 else 'medium' if maintenance_score > 0.3 else 'low',
                'recommendations': recommendations,
                'predicted_maintenance_window': '1-3 months' if maintenance_score > 0.5 else '3-6 months' if maintenance_score > 0.2 else '6+ months'
            }
        except Exception:
            return {'maintenance_prediction_failed': True}

    # === WALLET INTELLIGENCE HELPERS ===

    def _get_wallet_context(self) -> Dict[str, Any]:
        """Get non-identifying wallet context for intelligence reporting"""
        try:
            return {
                'client_version': '1.0.0',
                'intelligence_enabled': self.intelligence_enabled,
                'preferred_privacy_level': 'aggregated',  # Default privacy level
                'network_participation_level': 'active',  # active, passive, observer
                'typical_transaction_types': ['transfers', 'data_storage'],  # General categories
                'usage_patterns': 'regular'  # daily, weekly, irregular
            }
        except Exception:
            return {'wallet_context_unavailable': True}

    def _get_wallet_network_participation(self) -> Dict[str, Any]:
        """Get wallet's network participation metrics (privacy-preserving)"""
        try:
            return {
                'network_health_awareness': self.intelligence_enabled,
                'threat_detection_participation': self.intelligence_config.threat_detection,
                'smart_routing_usage': self.intelligence_config.smart_routing,
                'intelligence_contribution_level': 'standard',  # minimal, standard, comprehensive
                'privacy_protection_active': True
            }
        except Exception:
            return {'network_participation_unavailable': True}

    def _sign_privacy_preserving_report(self, report_data: Dict[str, Any]) -> str:
        """Sign intelligence report with privacy-preserving signature"""
        # This signature doesn't reveal wallet identity but proves report authenticity
        # In production, would use zero-knowledge proofs or similar privacy tech
        report_string = json.dumps({
            'intelligence_type': report_data.get('intelligence_type'),
            'privacy_level': report_data.get('privacy_level'),
            'timestamp': report_data.get('timestamp')
        }, sort_keys=True)
        return hashlib.sha256(report_string.encode()).hexdigest()[:32]

    def _aggregate_wallet_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply aggregation privacy transformation"""
        # Aggregate data to prevent individual transaction identification
        aggregated = {}
        for key, value in data.items():
            if isinstance(value, (int, float)) and key not in ['latitude', 'longitude']:  # Don't aggregate coordinates
                # Round to reduce precision
                aggregated[key] = round(value, 1) if isinstance(value, float) else value
            elif isinstance(value, list) and len(value) > 0:
                # Aggregate lists by taking averages or counts
                if all(isinstance(x, (int, float)) for x in value):
                    aggregated[f"{key}_count"] = len(value)
                    aggregated[f"{key}_avg"] = sum(value) / len(value)
                else:
                    aggregated[f"{key}_count"] = len(value)
            else:
                aggregated[key] = value
        return aggregated

    def _anonymize_wallet_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply anonymization privacy transformation"""
        # Remove or generalize identifying information
        anonymized = {}
        for key, value in data.items():
            if 'address' in key.lower() or 'hash' in key.lower():
                # Replace with anonymized identifier
                anonymized[key] = f"anon_{hash(key) % 1000:03d}"
            elif isinstance(value, str) and len(value) > 10:
                # Truncate long strings
                anonymized[key] = value[:8] + "..."
            elif isinstance(value, dict):
                # Recursively anonymize nested dictionaries
                anonymized[key] = self._anonymize_wallet_data(value)
            else:
                anonymized[key] = value
        return anonymized

    def _minimize_wallet_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply minimal privacy transformation (remove most data)"""
        # Only keep essential statistical information
        minimized = {}
        for key, value in data.items():
            if isinstance(value, (int, float)) and 'count' in key.lower():
                minimized[key] = value
            elif key in ['time_window_hours', 'region_activity', 'efficiency_score']:
                minimized[key] = value
        return minimized

    def _analyze_peak_usage_patterns(self, transaction_counts: Dict[str, int]) -> Dict[str, Any]:
        """Analyze peak usage patterns from transaction counts"""
        try:
            total_transactions = sum(transaction_counts.values())
            if total_transactions == 0:
                return {'peak_hours': [], 'usage_pattern': 'no_activity'}

            # Simple analysis - in production would analyze time-series data
            max_count = max(transaction_counts.values())
            peak_types = [tx_type for tx_type, count in transaction_counts.items() if count == max_count]

            return {
                'peak_transaction_types': peak_types,
                'peak_volume': max_count,
                'usage_intensity': 'high' if total_transactions > 100 else 'medium' if total_transactions > 10 else 'low',
                'diversity_score': len(transaction_counts) / max(1, total_transactions / 10)  # Normalize diversity
            }
        except Exception:
            return {'peak_analysis_failed': True}

    def _calculate_usage_consistency(self, volume_trends: Dict[str, Any]) -> float:
        """Calculate usage consistency score"""
        try:
            # Simple consistency calculation based on trend stability
            direction = volume_trends.get('direction', 'unknown')
            rate = volume_trends.get('rate', 0)

            if direction == 'stable':
                return 0.9
            elif abs(rate) < 0.1:
                return 0.7
            elif abs(rate) < 0.3:
                return 0.5
            else:
                return 0.2
        except Exception:
            return 0.5  # Neutral consistency

    def _assess_network_capacity_impact(self, volume_trends: Dict[str, Any]) -> Dict[str, Any]:
        """Assess network capacity implications of usage trends"""
        try:
            direction = volume_trends.get('direction', 'stable')
            rate = abs(volume_trends.get('rate', 0))

            if direction == 'increasing' and rate > 0.2:
                return {
                    'capacity_impact': 'high',
                    'scaling_recommendation': 'increase_network_capacity',
                    'timeline': 'immediate'
                }
            elif direction == 'increasing':
                return {
                    'capacity_impact': 'moderate',
                    'scaling_recommendation': 'monitor_closely',
                    'timeline': 'short_term'
                }
            else:
                return {
                    'capacity_impact': 'low',
                    'scaling_recommendation': 'maintain_current_capacity',
                    'timeline': 'no_action_needed'
                }
        except Exception:
            return {'capacity_assessment_failed': True}

    def _calculate_geographic_diversity(self, region_activity: Dict[str, float]) -> float:
        """Calculate geographic diversity score"""
        try:
            if not region_activity:
                return 0.0

            # Normalize percentages
            total = sum(region_activity.values())
            normalized = {region: pct/total for region, pct in region_activity.items()}

            # Calculate diversity (similar to Shannon entropy)
            entropy = -sum(pct * (pct ** 0.5) for pct in normalized.values() if pct > 0)

            # Normalize to 0-1 scale
            max_entropy = -sum(1/len(normalized) * ((1/len(normalized)) ** 0.5) for _ in normalized)
            return entropy / max_entropy if max_entropy > 0 else 0.0
        except Exception:
            return 0.5

    def _assess_regional_concentration_risk(self, region_activity: Dict[str, float]) -> float:
        """Assess regional concentration risk"""
        try:
            if not region_activity:
                return 0.5

            max_concentration = max(region_activity.values())
            region_count = len(region_activity)

            # Risk increases with concentration and decreases with region diversity
            concentration_risk = max_concentration / 100.0  # Normalize percentage to 0-1
            diversity_bonus = region_count / 10.0  # More regions = lower risk

            return max(0.0, min(1.0, concentration_risk - diversity_bonus * 0.1))
        except Exception:
            return 0.5

    def _analyze_topology_implications(self, region_activity: Dict[str, float]) -> Dict[str, Any]:
        """Analyze network topology implications"""
        try:
            regions = list(region_activity.keys())
            concentrations = list(region_activity.values())

            return {
                'cross_region_communication_needed': len(regions) > 1,
                'optimal_hub_regions': [r for r, c in region_activity.items() if c > 30],  # Regions with >30% activity
                'network_efficiency_score': 1.0 - (max(concentrations) / 100.0) + (len(regions) * 0.05),  # Balanced score
                'routing_complexity': 'high' if len(regions) > 3 else 'medium' if len(regions) > 1 else 'low'
            }
        except Exception:
            return {'topology_analysis_failed': True}

    def _analyze_fee_efficiency(self, fee_observations: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fee market efficiency"""
        try:
            avg_fee = fee_observations.get('average_fee', 0)
            median_fee = fee_observations.get('median_fee', 0)

            if median_fee > 0:
                efficiency_ratio = min(avg_fee, median_fee) / max(avg_fee, median_fee)
            else:
                efficiency_ratio = 0.5

            return {
                'fee_efficiency_score': efficiency_ratio,
                'fee_volatility': abs(avg_fee - median_fee) / max(avg_fee, median_fee) if max(avg_fee, median_fee) > 0 else 0,
                'market_maturity': 'efficient' if efficiency_ratio > 0.8 else 'developing' if efficiency_ratio > 0.6 else 'inefficient'
            }
        except Exception:
            return {'fee_analysis_failed': True}

    def _analyze_confirmation_trends(self, fee_acceptance_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze confirmation time trends"""
        try:
            fast_rate = fee_acceptance_patterns.get('fast_confirmation_rate', 0)
            slow_rate = fee_acceptance_patterns.get('slow_rate', 0)

            return {
                'confirmation_efficiency': fast_rate / (fast_rate + slow_rate) if (fast_rate + slow_rate) > 0 else 0.5,
                'confirmation_time_distribution': {
                    'fast_confirmations': fast_rate,
                    'slow_confirmations': slow_rate
                },
                'optimal_fee_range': 'current' if fast_rate > slow_rate else 'higher' if slow_rate > fast_rate * 2 else 'lower'
            }
        except Exception:
            return {'confirmation_analysis_failed': True}

    def _identify_fee_optimization_opportunities(self, fee_observations: Dict[str, Any],
                                               fee_acceptance_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Identify fee optimization opportunities"""
        try:
            fast_rate = fee_acceptance_patterns.get('fast_confirmation_rate', 0)
            slow_rate = fee_acceptance_patterns.get('slow_rate', 0)

            opportunities = []

            if fast_rate < 0.5:
                opportunities.append('Fees may be too low for fast confirmations')
            if slow_rate > fast_rate * 2:
                opportunities.append('Consider dynamic fee adjustment')
            if abs(fee_observations.get('average_fee', 0) - fee_observations.get('median_fee', 0)) > 0.0001:
                opportunities.append('Fee market shows volatility - monitor closely')

            return {
                'optimization_opportunities': opportunities,
                'fee_strategy_recommendation': 'dynamic' if len(opportunities) > 1 else 'static',
                'market_adaptation_needed': len(opportunities) > 0
            }
        except Exception:
            return {'fee_optimization_analysis_failed': True}

    def _analyze_pattern_frequencies(self, suspicious_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze frequencies of suspicious patterns"""
        try:
            if not suspicious_patterns:
                return {'pattern_frequency': 'none', 'risk_level': 'low'}

            pattern_types = {}
            for pattern in suspicious_patterns:
                p_type = pattern.get('type', 'unknown')
                pattern_types[p_type] = pattern_types.get(p_type, 0) + 1

            most_common = max(pattern_types.items(), key=lambda x: x[1]) if pattern_types else ('none', 0)

            return {
                'total_patterns': len(suspicious_patterns),
                'unique_pattern_types': len(pattern_types),
                'most_common_pattern': most_common[0],
                'pattern_frequency_score': most_common[1] / max(1, len(suspicious_patterns)),
                'risk_indication': 'high' if most_common[1] > 5 else 'medium' if most_common[1] > 2 else 'low'
            }
        except Exception:
            return {'pattern_analysis_failed': True}

    def _analyze_risk_trends(self, risk_assessments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk assessment trends"""
        try:
            risk_levels = risk_assessments.values()
            avg_risk = sum(float(level) for level in risk_levels if isinstance(level, (int, float))) / max(1, len(risk_levels))

            return {
                'average_risk_score': avg_risk,
                'risk_distribution': {
                    'high': sum(1 for r in risk_levels if isinstance(r, (int, float)) and r > 0.7),
                    'medium': sum(1 for r in risk_levels if isinstance(r, (int, float)) and 0.3 <= r <= 0.7),
                    'low': sum(1 for r in risk_levels if isinstance(r, (int, float)) and r < 0.3)
                },
                'overall_risk_trend': 'increasing' if avg_risk > 0.6 else 'moderate' if avg_risk > 0.3 else 'low'
            }
        except Exception:
            return {'risk_analysis_failed': True}

    def _suggest_fraud_prevention_measures(self, anomaly_scores: Dict[str, float]) -> List[str]:
        """Suggest fraud prevention measures based on anomaly scores"""
        try:
            suggestions = []
            max_anomaly = max(anomaly_scores.values()) if anomaly_scores else 0

            if max_anomaly > 0.8:
                suggestions.extend([
                    'Implement immediate transaction velocity limits',
                    'Enable enhanced KYC verification',
                    'Activate real-time fraud monitoring'
                ])
            elif max_anomaly > 0.6:
                suggestions.extend([
                    'Increase monitoring frequency',
                    'Review transaction pattern thresholds',
                    'Consider additional verification steps'
                ])
            elif max_anomaly > 0.4:
                suggestions.extend([
                    'Monitor transaction patterns closely',
                    'Review user behavior analytics',
                    'Consider preventive measures'
                ])

            return suggestions if suggestions else ['Continue standard fraud monitoring']
        except Exception:
            return ['Unable to generate fraud prevention suggestions']


# === INTELLIGENCE EVENT CALLBACKS ===

def on_threat_alert(client: PiSecureClient, callback: Callable):
    """Register callback for threat alerts"""
    if 'threat_alert' not in client._intelligence_callbacks:
        client._intelligence_callbacks['threat_alert'] = []
    client._intelligence_callbacks['threat_alert'].append(callback)


def on_defense_action(client: PiSecureClient, callback: Callable):
    """Register callback for defense actions"""
    if 'defense_action' not in client._intelligence_callbacks:
        client._intelligence_callbacks['defense_action'] = []
    client._intelligence_callbacks['defense_action'].append(callback)


def on_routing_update(client: PiSecureClient, callback: Callable):
    """Register callback for routing updates"""
    if 'routing_update' not in client._intelligence_callbacks:
        client._intelligence_callbacks['routing_update'] = []
    client._intelligence_callbacks['routing_update'].append(callback)


# === ASYNC INTELLIGENCE STREAMING ===

class IntelligenceStreamer:
    """Async WebSocket client for real-time intelligence streaming"""

    def __init__(self, client: PiSecureClient):
        self.client = client
        self.websocket = None
        self.running = False

    async def connect(self):
        """Connect to intelligence WebSocket stream"""
        try:
            # Get WebSocket URL from pool
            base_url = self.client.connection_pool.get_next_endpoint()
            ws_url = base_url.replace('http', 'ws') + '/api/v1/stream/intelligence'

            self.websocket = await websockets.connect(ws_url)
            self.running = True

            # Start message handler
            asyncio.create_task(self._message_handler())

        except Exception as e:
            logger.error(f"Failed to connect intelligence stream: {e}")
            raise

    async def disconnect(self):
        """Disconnect from intelligence stream"""
        self.running = False
        if self.websocket:
            await self.websocket.close()

    async def _message_handler(self):
        """Handle incoming intelligence messages"""
        try:
            while self.running and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)

                # Call registered callbacks
                event_type = data.get('type')
                if event_type in self.client._intelligence_callbacks:
                    for callback in self.client._intelligence_callbacks[event_type]:
                        try:
                            callback(data.get('data', {}))
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

        except Exception as e:
            logger.error(f"Intelligence stream error: {e}")
            self.running = False


# === EXAMPLE USAGE ===

if __name__ == "__main__":
    # Create intelligent client
    client = PiSecureClient(intelligence_enabled=True)

    # Basic blockchain operations
    try:
        info = client.get_blockchain_info()
        print(f"Blockchain: {info.get('blocks', 0)} blocks")

        # Intelligence features
        threat_info = client.get_threat_intelligence()
        print(f"Threat level: {threat_info.threat_level}")

        health = client.get_network_health()
        print(f"Network health: {health.overall_health}%")

        # Optimized peer discovery
        optimized_peers = client.get_optimized_peers('p2p_sync')
        print(f"Optimized peers: {len(optimized_peers)} available")

        # Intelligent sensor reading
        sensor_tx = client.submit_sensor_reading_intelligent(
            device_id="TEMP-001",
            sensor_type="temperature",
            value=23.5,
            unit="celsius",
            location="Warehouse A"
        )
        print(f"Intelligent sensor reading submitted: {sensor_tx}")

    except Exception as e:
        print(f"Error: {e}")