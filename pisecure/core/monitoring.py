"""
PiSecure Monitoring & Health Checks
====================================

System monitoring, health checks, and metrics collection.
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_connections: int
    blockchain_height: int
    active_peers: int
    pending_transactions: int
    uptime_seconds: float


@dataclass
class HealthStatus:
    """System health status"""
    overall: str  # 'healthy', 'warning', 'critical'
    checks: Dict[str, Dict[str, Any]]
    timestamp: float


class MetricsCollector:
    """Collect system and application metrics"""

    def __init__(self):
        self.start_time = time.time()
        self._lock = threading.Lock()
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = 100  # Keep last 100 measurements

    def collect_system_metrics(self, blockchain_height: int = 0,
                             active_peers: int = 0,
                             pending_transactions: int = 0) -> SystemMetrics:
        """Collect current system metrics"""
        metrics = SystemMetrics(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            disk_usage_percent=psutil.disk_usage('/').percent,
            network_connections=len(psutil.net_connections()),
            blockchain_height=blockchain_height,
            active_peers=active_peers,
            pending_transactions=pending_transactions,
            uptime_seconds=time.time() - self.start_time
        )

        with self._lock:
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_history:
                self._metrics_history.pop(0)

        return metrics

    def get_recent_metrics(self, hours: int = 1) -> List[SystemMetrics]:
        """Get metrics from the last N hours"""
        cutoff = time.time() - (hours * 3600)
        with self._lock:
            return [m for m in self._metrics_history if m.timestamp >= cutoff]

    def get_average_metrics(self, hours: int = 1) -> Optional[Dict[str, float]]:
        """Get average metrics over the last N hours"""
        recent = self.get_recent_metrics(hours)
        if not recent:
            return None

        # Calculate averages
        totals = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage_percent': 0,
            'network_connections': 0,
            'blockchain_height': 0,
            'active_peers': 0,
            'pending_transactions': 0
        }

        for metric in recent:
            for key in totals:
                totals[key] += getattr(metric, key)

        count = len(recent)
        averages = {key: total / count for key, total in totals.items()}
        averages['uptime_seconds'] = recent[-1].uptime_seconds
        averages['samples'] = count

        return averages


class HealthChecker:
    """System health monitoring"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._thresholds = {
            'cpu_percent': {'warning': 80, 'critical': 95},
            'memory_percent': {'warning': 85, 'critical': 95},
            'disk_usage_percent': {'warning': 90, 'critical': 95},
            'network_connections': {'warning': 1000, 'critical': 2000},
            'active_peers': {'warning': 1, 'critical': 0},  # Minimum peers
            'pending_transactions': {'warning': 1000, 'critical': 5000}
        }

    def check_system_health(self) -> HealthStatus:
        """Perform comprehensive health check"""
        checks = {}
        overall_status = 'healthy'

        # Get latest metrics
        recent_metrics = self.metrics.get_recent_metrics(hours=1)
        if not recent_metrics:
            return HealthStatus(
                overall='unknown',
                checks={'error': {'status': 'error', 'message': 'No metrics available'}},
                timestamp=time.time()
            )

        latest = recent_metrics[-1]

        # Check each metric against thresholds
        for metric_name, thresholds in self._thresholds.items():
            value = getattr(latest, metric_name)
            status = 'healthy'

            if value >= thresholds['critical']:
                status = 'critical'
            elif value >= thresholds['warning']:
                status = 'warning'

            checks[metric_name] = {
                'status': status,
                'value': value,
                'thresholds': thresholds
            }

            if status == 'critical':
                overall_status = 'critical'
            elif status == 'warning' and overall_status == 'healthy':
                overall_status = 'warning'

        # Additional checks
        checks.update(self._check_blockchain_health(latest))
        checks.update(self._check_network_health(latest))

        # Update overall status based on additional checks
        for check in checks.values():
            if check['status'] == 'critical':
                overall_status = 'critical'
                break
            elif check['status'] == 'warning' and overall_status == 'healthy':
                overall_status = 'warning'

        return HealthStatus(
            overall=overall_status,
            checks=checks,
            timestamp=time.time()
        )

    def _check_blockchain_health(self, metrics: SystemMetrics) -> Dict[str, Dict[str, Any]]:
        """Check blockchain-specific health"""
        checks = {}

        # Blockchain growth check (should be increasing)
        recent = self.metrics.get_recent_metrics(hours=1)
        if len(recent) >= 2:
            height_increase = recent[-1].blockchain_height - recent[0].blockchain_height
            if height_increase < 0:
                checks['blockchain_growth'] = {
                    'status': 'critical',
                    'message': 'Blockchain height decreased',
                    'value': height_increase
                }
            elif height_increase == 0:
                checks['blockchain_growth'] = {
                    'status': 'warning',
                    'message': 'No blockchain growth in last hour',
                    'value': height_increase
                }
            else:
                checks['blockchain_growth'] = {
                    'status': 'healthy',
                    'message': f'Blockchain growing normally (+{height_increase})',
                    'value': height_increase
                }
        else:
            checks['blockchain_growth'] = {
                'status': 'unknown',
                'message': 'Insufficient data for growth check'
            }

        return checks

    def _check_network_health(self, metrics: SystemMetrics) -> Dict[str, Dict[str, Any]]:
        """Check network-specific health"""
        checks = {}

        # Peer connectivity
        if metrics.active_peers == 0:
            checks['peer_connectivity'] = {
                'status': 'critical',
                'message': 'No active peers connected'
            }
        elif metrics.active_peers < 3:
            checks['peer_connectivity'] = {
                'status': 'warning',
                'message': f'Low peer count: {metrics.active_peers}',
                'value': metrics.active_peers
            }
        else:
            checks['peer_connectivity'] = {
                'status': 'healthy',
                'message': f'Good peer connectivity: {metrics.active_peers}',
                'value': metrics.active_peers
            }

        # Transaction backlog
        if metrics.pending_transactions > 1000:
            checks['transaction_backlog'] = {
                'status': 'warning',
                'message': f'High pending transaction count: {metrics.pending_transactions}',
                'value': metrics.pending_transactions
            }
        else:
            checks['transaction_backlog'] = {
                'status': 'healthy',
                'message': f'Normal pending transactions: {metrics.pending_transactions}',
                'value': metrics.pending_transactions
            }

        return checks


class AlertManager:
    """Manage alerts and notifications"""

    def __init__(self):
        self._alerts: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def check_and_alert(self, health_status: HealthStatus) -> List[Dict[str, Any]]:
        """Check health status and generate alerts"""
        alerts = []

        for check_name, check_data in health_status.checks.items():
            if check_data['status'] in ['warning', 'critical']:
                alert = {
                    'timestamp': health_status.timestamp,
                    'level': check_data['status'],
                    'component': check_name,
                    'message': check_data.get('message', f'{check_name} is {check_data["status"]}'),
                    'value': check_data.get('value'),
                    'thresholds': check_data.get('thresholds')
                }
                alerts.append(alert)

        # Store alerts
        with self._lock:
            self._alerts.extend(alerts)
            # Keep only recent alerts (last 1000)
            if len(self._alerts) > 1000:
                self._alerts = self._alerts[-1000:]

        return alerts

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the last N hours"""
        cutoff = time.time() - (hours * 3600)
        with self._lock:
            return [a for a in self._alerts if a['timestamp'] >= cutoff]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts (not resolved)"""
        # For now, return recent alerts (in production, track resolution)
        return self.get_recent_alerts(hours=1)


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)
alert_manager = AlertManager()