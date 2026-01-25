"""
PiSecure DDoS Protection and Abuse Detection
=============================================

Advanced DDoS protection and abuse detection system with ML-powered analysis.

Features:
- IP reputation checking with dynamic blacklisting
- Request fingerprinting and pattern analysis
- Suspicious behavior detection
- Progressive rate limiting escalation
- Geographic attack pattern recognition
- Automated threat response coordination

Integration:
- Works with bootstrap server intelligence
- Leverages existing rate limiting system
- Integrates with validation framework
- Provides real-time threat intelligence
"""

import time
import hashlib
import ipaddress
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Set
import logging
import re

logger = logging.getLogger(__name__)

class DDoSProtection:
    """
    Advanced DDoS protection and abuse detection system.

    Monitors traffic patterns, detects suspicious behavior, and implements
    automated defense mechanisms.
    """

    def __init__(self, max_requests_per_window: int = 1000,
                 window_size_seconds: int = 60,
                 blacklist_threshold: int = 10,
                 suspicious_score_threshold: float = 0.7):
        """
        Initialize DDoS protection system.

        Args:
            max_requests_per_window: Maximum requests per time window per IP
            window_size_seconds: Size of monitoring window in seconds
            blacklist_threshold: Number of violations before blacklisting
            suspicious_score_threshold: Threshold for suspicious behavior detection
        """
        self.max_requests_per_window = max_requests_per_window
        self.window_size_seconds = window_size_seconds
        self.blacklist_threshold = blacklist_threshold
        self.suspicious_score_threshold = suspicious_score_threshold

        # IP tracking data structures
        self.ip_requests = defaultdict(lambda: deque(maxlen=max_requests_per_window))
        self.ip_violations = defaultdict(int)
        self.blacklisted_ips = set()
        self.suspicious_ips = set()

        # Request pattern analysis
        self.request_patterns = defaultdict(list)
        self.endpoint_access_patterns = defaultdict(lambda: defaultdict(int))

        # Geographic analysis
        self.ip_geographic_data = {}
        self.geographic_threat_levels = defaultdict(float)

        # Automated response tracking
        self.blocked_requests = 0
        self.suspicious_requests = 0
        self.last_bootstrap_check = 0

        # Progressive delay system
        self.progressive_delays = {}  # IP -> delay_seconds

    def check_request(self, ip_address: str, endpoint: str,
                     user_agent: str = "", request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check incoming request for DDoS/abuse patterns.

        Args:
            ip_address: Client IP address
            endpoint: Requested API endpoint
            user_agent: User agent string
            request_data: Request payload data

        Returns:
            Dict with 'allowed': bool and optional 'delay': seconds
        """
        # Clean IP address
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            clean_ip = str(ip_obj)
        except ValueError:
            return {'allowed': False, 'reason': 'Invalid IP address'}

        # Check if IP is blacklisted
        if clean_ip in self.blacklisted_ips:
            self.blocked_requests += 1
            logger.warning(f"🚫 Blocked request from blacklisted IP: {clean_ip}")
            return {'allowed': False, 'reason': 'IP blacklisted'}

        # Record request
        current_time = time.time()
        self.ip_requests[clean_ip].append(current_time)

        # Clean old requests from sliding window
        self._clean_old_requests(clean_ip, current_time)

        # Check rate limiting
        request_count = len(self.ip_requests[clean_ip])
        if request_count > self.max_requests_per_window:
            self._handle_rate_limit_violation(clean_ip)
            return {'allowed': False, 'reason': 'Rate limit exceeded'}

        # Analyze request patterns
        suspicious_score = self._analyze_request_patterns(
            clean_ip, endpoint, user_agent, request_data, current_time
        )

        # Check geographic threats
        geo_threat = self._check_geographic_threats(clean_ip)

        # Combined threat assessment
        total_threat_score = (suspicious_score * 0.6) + (geo_threat * 0.4)

        if total_threat_score > self.suspicious_score_threshold:
            self._handle_suspicious_request(clean_ip, total_threat_score)
            self.suspicious_requests += 1

        # Apply progressive delays
        delay = self.progressive_delays.get(clean_ip, 0)
        if delay > 0:
            return {'allowed': True, 'delay': delay}

        return {'allowed': True}

    def _clean_old_requests(self, ip: str, current_time: float):
        """Remove requests outside the sliding window."""
        window_start = current_time - self.window_size_seconds

        # Remove old requests
        while self.ip_requests[ip] and self.ip_requests[ip][0] < window_start:
            self.ip_requests[ip].popleft()

    def _handle_rate_limit_violation(self, ip: str):
        """Handle rate limit violations with progressive responses."""
        self.ip_violations[ip] += 1

        if self.ip_violations[ip] >= self.blacklist_threshold:
            self._blacklist_ip(ip)
        else:
            # Apply progressive delay
            delay = min(self.ip_violations[ip] * 0.1, 5.0)  # Max 5 second delay
            self.progressive_delays[ip] = delay

        logger.warning(f"⚠️ Rate limit violation from {ip} (violations: {self.ip_violations[ip]})")

    def _blacklist_ip(self, ip: str):
        """Add IP to blacklist."""
        self.blacklisted_ips.add(ip)
        self.progressive_delays[ip] = 30  # 30 second delay for blacklisted IPs

        # Clean up tracking data
        if ip in self.ip_requests:
            del self.ip_requests[ip]

        logger.warning(f"🚫 Blacklisted IP: {ip}")

    def _analyze_request_patterns(self, ip: str, endpoint: str,
                                user_agent: str, request_data: Dict[str, Any],
                                timestamp: float) -> float:
        """
        Analyze request patterns for suspicious behavior.

        Returns:
            Suspicious score (0.0 to 1.0)
        """
        suspicious_score = 0.0

        # Track endpoint access patterns
        self.endpoint_access_patterns[ip][endpoint] += 1

        # Check for unusual endpoint access patterns
        total_requests = sum(self.endpoint_access_patterns[ip].values())
        endpoint_ratio = self.endpoint_access_patterns[ip][endpoint] / total_requests

        # High concentration on single endpoint (possible enumeration/scanning)
        if total_requests > 10 and endpoint_ratio > 0.8:
            suspicious_score += 0.3

        # Check user agent patterns
        if self._is_suspicious_user_agent(user_agent):
            suspicious_score += 0.4

        # Analyze request data patterns
        if request_data:
            data_score = self._analyze_request_data(request_data)
            suspicious_score += data_score * 0.3

        # Check request timing patterns (bursty traffic)
        timing_score = self._analyze_timing_patterns(ip, timestamp)
        suspicious_score += timing_score * 0.2

        return min(suspicious_score, 1.0)

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent indicates suspicious activity."""
        if not user_agent:
            return True  # Empty user agent is suspicious

        suspicious_patterns = [
            r'curl|wget|python-requests|go-http-client',  # Automation tools
            r'scanner|bot|crawler',  # Known bots
            r'sqlmap|nikto|dirbuster',  # Security tools
            r'^-$',  # Empty or dash user agent
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True

        return False

    def _analyze_request_data(self, request_data: Dict[str, Any]) -> float:
        """Analyze request data for suspicious patterns."""
        suspicious_score = 0.0

        # Check for common attack patterns
        data_str = str(request_data).lower()

        attack_patterns = [
            'union select', 'drop table', 'script', 'javascript:',
            '../../../', '..\\', '<script>', 'eval(', 'base64',
            'sleep(', 'benchmark(', 'script>', 'iframe', 'object'
        ]

        for pattern in attack_patterns:
            if pattern in data_str:
                suspicious_score += 0.2

        # Check for unusually large data
        if len(str(request_data)) > 10000:  # 10KB threshold
            suspicious_score += 0.1

        # Check for repetitive patterns (possible fuzzing)
        if self._has_repetitive_patterns(request_data):
            suspicious_score += 0.2

        return min(suspicious_score, 1.0)

    def _has_repetitive_patterns(self, data: Any, threshold: int = 5) -> bool:
        """Check for repetitive patterns that indicate fuzzing."""
        data_str = str(data)

        # Look for repeated characters or sequences
        for char in set(data_str):
            if data_str.count(char * 3) > threshold:
                return True

        # Look for repeated words
        words = re.findall(r'\b\w+\b', data_str.lower())
        for word in set(words):
            if words.count(word) > 10:  # Same word repeated many times
                return True

        return False

    def _analyze_timing_patterns(self, ip: str, timestamp: float) -> float:
        """Analyze request timing patterns for bursty traffic."""
        if len(self.ip_requests[ip]) < 5:
            return 0.0

        # Calculate inter-request intervals
        requests = list(self.ip_requests[ip])
        intervals = []

        for i in range(1, len(requests)):
            intervals.append(requests[i] - requests[i-1])

        if not intervals:
            return 0.0

        # Check for very regular intervals (bot-like behavior)
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        regularity_score = 1.0 / (1.0 + variance)  # Higher score = more regular

        # Check for very fast requests (flooding)
        fast_requests = sum(1 for i in intervals if i < 0.1)  # Less than 100ms apart
        flood_score = min(fast_requests / 10.0, 1.0)

        return (regularity_score * 0.6) + (flood_score * 0.4)

    def _check_geographic_threats(self, ip: str) -> float:
        """Check geographic threat levels for IP."""
        # Get geographic data (simplified - would use GeoIP in production)
        geo_data = self._get_geographic_data(ip)
        if not geo_data:
            return 0.0

        country = geo_data.get('country', 'unknown')
        threat_level = self.geographic_threat_levels.get(country, 0.0)

        return threat_level

    def _get_geographic_data(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get geographic data for IP address."""
        # Check cache first
        if ip in self.ip_geographic_data:
            return self.ip_geographic_data[ip]

        # Simplified geographic lookup (would use GeoIP2 in production)
        try:
            # Basic IP classification
            ip_obj = ipaddress.ip_address(ip)

            # Very basic geographic hints based on IP ranges
            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                geo_data = {'country': 'private', 'region': 'local'}
            elif ip_obj.is_private:
                geo_data = {'country': 'private', 'region': 'local'}
            else:
                # Would query GeoIP database here
                geo_data = {'country': 'unknown', 'region': 'unknown'}

            self.ip_geographic_data[ip] = geo_data
            return geo_data

        except Exception:
            return None

    def _handle_suspicious_request(self, ip: str, threat_score: float):
        """Handle suspicious requests with appropriate responses."""
        logger.warning(f"🚨 Suspicious request from {ip} (threat score: {threat_score:.2f})")

        # Add to suspicious IPs list
        self.suspicious_ips.add(ip)

        # Apply progressive delay
        current_delay = self.progressive_delays.get(ip, 0)
        new_delay = min(current_delay + 1.0, 10.0)  # Max 10 second delay
        self.progressive_delays[ip] = new_delay

        # If very suspicious, consider blacklisting
        if threat_score > 0.9:
            self.ip_violations[ip] += 2  # Double violation for high threat
            if self.ip_violations[ip] >= self.blacklist_threshold:
                self._blacklist_ip(ip)

    def update_geographic_threats(self, threat_data: Dict[str, Any]):
        """Update geographic threat levels from external intelligence."""
        if 'geographic_threats' in threat_data:
            for country, threat_level in threat_data['geographic_threats'].items():
                self.geographic_threat_levels[country] = threat_level

    def get_protection_stats(self) -> Dict[str, Any]:
        """Get comprehensive protection statistics."""
        return {
            'blacklisted_ips': len(self.blacklisted_ips),
            'suspicious_ips': len(self.suspicious_ips),
            'blocked_requests': self.blocked_requests,
            'suspicious_requests': self.suspicious_requests,
            'active_delays': len(self.progressive_delays),
            'monitored_ips': len(self.ip_requests),
            'total_violations': sum(self.ip_violations.values())
        }

    def cleanup_expired_data(self, max_age_seconds: int = 3600):
        """Clean up old tracking data."""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        # Clean old progressive delays
        expired_delays = [
            ip for ip, delay_time in self.progressive_delays.items()
            if delay_time < cutoff_time
        ]
        for ip in expired_delays:
            del self.progressive_delays[ip]

        # Clean old geographic data (keep longer)
        geo_cutoff = current_time - (24 * 3600)  # 24 hours
        # Note: In production, you'd track access times for geo data

    def reset_violations(self, ip: str):
        """Reset violations for an IP (admin function)."""
        if ip in self.ip_violations:
            del self.ip_violations[ip]
        if ip in self.progressive_delays:
            del self.progressive_delays[ip]
        if ip in self.suspicious_ips:
            self.suspicious_ips.remove(ip)

    def get_ip_status(self, ip: str) -> Dict[str, Any]:
        """Get status information for a specific IP."""
        return {
            'ip': ip,
            'blacklisted': ip in self.blacklisted_ips,
            'suspicious': ip in self.suspicious_ips,
            'violations': self.ip_violations.get(ip, 0),
            'delay': self.progressive_delays.get(ip, 0),
            'requests_in_window': len(self.ip_requests.get(ip, [])),
            'geographic_data': self.ip_geographic_data.get(ip, {})
        }


class RequestFingerprinting:
    """
    Advanced request fingerprinting for abuse detection.

    Creates unique fingerprints for request patterns to identify
    coordinated attacks and bot behavior.
    """

    def __init__(self):
        self.fingerprints = defaultdict(list)
        self.fingerprint_scores = defaultdict(float)

    def fingerprint_request(self, ip: str, method: str, endpoint: str,
                          user_agent: str, headers: Dict[str, str]) -> str:
        """
        Create a fingerprint for the request.

        Returns:
            Fingerprint string
        """
        # Create fingerprint from key characteristics
        fingerprint_data = {
            'method': method,
            'endpoint': endpoint,
            'user_agent_family': self._normalize_user_agent(user_agent),
            'accept_language': headers.get('Accept-Language', ''),
            'accept_encoding': headers.get('Accept-Encoding', ''),
            'connection': headers.get('Connection', ''),
        }

        # Create hash
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint = hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]

        # Track fingerprint usage
        self.fingerprints[fingerprint].append({
            'ip': ip,
            'timestamp': time.time(),
            'endpoint': endpoint
        })

        # Clean old entries (keep last 100 per fingerprint)
        if len(self.fingerprints[fingerprint]) > 100:
            self.fingerprints[fingerprint] = self.fingerprints[fingerprint][-100:]

        return fingerprint

    def _normalize_user_agent(self, user_agent: str) -> str:
        """Normalize user agent to family level."""
        if not user_agent:
            return 'unknown'

        ua_lower = user_agent.lower()

        if 'chrome' in ua_lower and 'safari' in ua_lower:
            return 'chrome'
        elif 'firefox' in ua_lower:
            return 'firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            return 'safari'
        elif 'edge' in ua_lower or 'edg' in ua_lower:
            return 'edge'
        elif 'curl' in ua_lower:
            return 'curl'
        elif 'python' in ua_lower:
            return 'python'
        elif 'go-http' in ua_lower:
            return 'golang'
        elif 'postman' in ua_lower:
            return 'postman'
        else:
            return 'other'

    def analyze_fingerprint_patterns(self, fingerprint: str) -> Dict[str, Any]:
        """Analyze usage patterns for a fingerprint."""
        if fingerprint not in self.fingerprints:
            return {'score': 0.0, 'analysis': 'unknown'}

        entries = self.fingerprints[fingerprint]
        if len(entries) < 2:
            return {'score': 0.0, 'analysis': 'insufficient_data'}

        # Analyze IP diversity
        unique_ips = len(set(entry['ip'] for entry in entries))
        ip_diversity = unique_ips / len(entries)

        # Analyze timing patterns
        timestamps = [entry['timestamp'] for entry in entries]
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i-1])

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            regularity = 1.0 / (1.0 + sum((i - avg_interval) ** 2 for i in intervals) / len(intervals))
        else:
            regularity = 0.0

        # Calculate suspicious score
        suspicious_score = 0.0

        # Low IP diversity (same fingerprint from many IPs = botnet)
        if ip_diversity < 0.3:
            suspicious_score += 0.5

        # High regularity (bot-like timing)
        if regularity > 0.8:
            suspicious_score += 0.3

        # Many requests in short time
        recent_entries = [e for e in entries if e['timestamp'] > time.time() - 300]  # Last 5 minutes
        if len(recent_entries) > 20:
            suspicious_score += 0.2

        analysis = 'normal'
        if suspicious_score > 0.7:
            analysis = 'highly_suspicious'
        elif suspicious_score > 0.4:
            analysis = 'suspicious'

        return {
            'score': suspicious_score,
            'analysis': analysis,
            'unique_ips': unique_ips,
            'total_requests': len(entries),
            'ip_diversity': ip_diversity,
            'timing_regularity': regularity
        }


# Global instances
ddos_protection = DDoSProtection()
request_fingerprinting = RequestFingerprinting()