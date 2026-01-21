"""
Test Monitoring System
======================

Tests for the monitoring and health check system.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from pisecure.core.monitoring import (
    MetricsCollector, HealthChecker, AlertManager,
    SystemMetrics, HealthStatus
)


class TestMetricsCollector:

    def test_collect_system_metrics(self):
        """Test metrics collection"""
        collector = MetricsCollector()

        # Mock psutil functions
        with patch('pisecure.core.monitoring.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 45.5
            mock_psutil.virtual_memory.return_value.percent = 67.8
            mock_psutil.disk_usage.return_value.percent = 23.4
            mock_psutil.net_connections.return_value = ['conn1', 'conn2', 'conn3']

            metrics = collector.collect_system_metrics(
                blockchain_height=100,
                active_peers=5,
                pending_transactions=10
            )

            assert metrics.cpu_percent == 45.5
            assert metrics.memory_percent == 67.8
            assert metrics.disk_usage_percent == 23.4
            assert metrics.network_connections == 3
            assert metrics.blockchain_height == 100
            assert metrics.active_peers == 5
            assert metrics.pending_transactions == 10
            assert metrics.uptime_seconds >= 0

    def test_metrics_history_limit(self):
        """Test metrics history size limiting"""
        collector = MetricsCollector()
        collector._max_history = 3

        # Add 5 metrics
        for i in range(5):
            with patch('pisecure.core.monitoring.psutil'):
                collector.collect_system_metrics()

        assert len(collector._metrics_history) == 3

    def test_get_recent_metrics(self):
        """Test retrieving recent metrics"""
        collector = MetricsCollector()

        # Add metrics at different times
        base_time = time.time()
        times = [base_time - 7200, base_time - 3600, base_time - 1800, base_time]  # 2h, 1h, 30m, now

        for i, t in enumerate(times):
            with patch('pisecure.core.monitoring.time.time', return_value=t):
                with patch('pisecure.core.monitoring.psutil'):
                    collector.collect_system_metrics(blockchain_height=i*10)

        # Get metrics from last hour
        recent = collector.get_recent_metrics(hours=1)
        assert len(recent) == 2  # Last two metrics
        assert recent[0].blockchain_height == 20
        assert recent[1].blockchain_height == 30

    def test_get_average_metrics(self):
        """Test calculating average metrics"""
        collector = MetricsCollector()

        # Add some test metrics
        for i in range(3):
            with patch('pisecure.core.monitoring.psutil') as mock_psutil:
                mock_psutil.cpu_percent.return_value = 10 * (i + 1)  # 10, 20, 30
                mock_psutil.virtual_memory.return_value.percent = 20 * (i + 1)  # 20, 40, 60
                mock_psutil.disk_usage.return_value.percent = 5
                mock_psutil.net_connections.return_value = [1, 2, 3]
                collector.collect_system_metrics(
                    blockchain_height=100 + i,
                    active_peers=2 + i,
                    pending_transactions=5 + i
                )

        averages = collector.get_average_metrics(hours=1)
        assert averages is not None
        assert averages['cpu_percent'] == 20.0  # (10+20+30)/3
        assert averages['memory_percent'] == 40.0  # (20+40+60)/3
        assert averages['blockchain_height'] == 101.0  # (100+101+102)/3
        assert averages['samples'] == 3


class TestHealthChecker:

    def test_check_system_health_healthy(self):
        """Test health check with healthy system"""
        collector = MetricsCollector()
        checker = HealthChecker(collector)

        # Add healthy metrics
        with patch('pisecure.core.monitoring.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 50
            mock_psutil.virtual_memory.return_value.percent = 60
            mock_psutil.disk_usage.return_value.percent = 70
            mock_psutil.net_connections.return_value = 100

            collector.collect_system_metrics(
                blockchain_height=1000,
                active_peers=10,
                pending_transactions=100
            )

        health = checker.check_system_health()
        assert health.overall == 'healthy'
        assert all(check['status'] == 'healthy' for check in health.checks.values()
                  if check['status'] != 'unknown')

    def test_check_system_health_critical(self):
        """Test health check with critical issues"""
        collector = MetricsCollector()
        checker = HealthChecker(collector)

        # Add critical metrics
        with patch('pisecure.core.monitoring.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 98  # Critical
            mock_psutil.virtual_memory.return_value.percent = 60
            mock_psutil.disk_usage.return_value.percent = 70
            mock_psutil.net_connections.return_value = 100

            collector.collect_system_metrics(
                blockchain_height=1000,
                active_peers=0,  # Critical
                pending_transactions=100
            )

        health = checker.check_system_health()
        assert health.overall == 'critical'

        # Check specific critical checks
        assert health.checks['cpu_percent']['status'] == 'critical'
        assert health.checks['peer_connectivity']['status'] == 'critical'

    def test_check_blockchain_growth(self):
        """Test blockchain growth health check"""
        collector = MetricsCollector()
        checker = HealthChecker(collector)

        # Add metrics showing growth
        base_time = time.time()
        for i, offset in enumerate([-3600, -1800, 0]):  # 1 hour ago, 30 min ago, now
            with patch('pisecure.core.monitoring.time.time', return_value=base_time + offset):
                with patch('pisecure.core.monitoring.psutil'):
                    collector.collect_system_metrics(blockchain_height=100 + i*5)

        # Check health with mocked time set to "now" (base_time)
        with patch('pisecure.core.monitoring.time.time', return_value=base_time):
            health = checker.check_system_health()
        growth_check = health.checks.get('blockchain_growth')
        assert growth_check is not None
        assert growth_check['status'] == 'healthy'
        assert '+10' in growth_check['message']

    def test_check_blockchain_no_growth(self):
        """Test blockchain no growth warning"""
        collector = MetricsCollector()
        checker = HealthChecker(collector)

        # Add metrics showing no growth
        base_time = time.time()
        for offset in [-3600, 0]:  # 1 hour ago, now
            with patch('pisecure.core.monitoring.time.time', return_value=base_time + offset):
                with patch('pisecure.core.monitoring.psutil'):
                    collector.collect_system_metrics(blockchain_height=100)

        health = checker.check_system_health()
        growth_check = health.checks.get('blockchain_growth')
        assert growth_check is not None
        assert growth_check['status'] == 'warning'
        assert 'No blockchain growth' in growth_check['message']


class TestAlertManager:

    def test_check_and_alert(self):
        """Test alert generation"""
        manager = AlertManager()

        # Create a health status with warnings/criticals
        health = HealthStatus(
            overall='warning',
            checks={
                'cpu_percent': {
                    'status': 'warning',
                    'value': 85,
                    'thresholds': {'warning': 80, 'critical': 95}
                },
                'memory_percent': {
                    'status': 'healthy',
                    'value': 60
                },
                'peer_connectivity': {
                    'status': 'critical',
                    'message': 'No active peers connected',
                    'value': 0
                }
            },
            timestamp=time.time()
        )

        alerts = manager.check_and_alert(health)
        assert len(alerts) == 2  # cpu warning + peer critical

        # Check alert structure
        cpu_alert = next(a for a in alerts if a['component'] == 'cpu_percent')
        assert cpu_alert['level'] == 'warning'
        assert cpu_alert['value'] == 85

        peer_alert = next(a for a in alerts if a['component'] == 'peer_connectivity')
        assert peer_alert['level'] == 'critical'
        assert 'No active peers' in peer_alert['message']

    def test_get_recent_alerts(self):
        """Test retrieving recent alerts"""
        manager = AlertManager()

        base_time = time.time()

        # Add alerts at different times
        old_alert = {
            'timestamp': base_time - 7200,  # 2 hours ago
            'level': 'warning',
            'component': 'cpu_percent',
            'message': 'High CPU'
        }
        recent_alert = {
            'timestamp': base_time - 1800,  # 30 min ago
            'level': 'critical',
            'component': 'memory_percent',
            'message': 'High memory'
        }

        manager._alerts = [old_alert, recent_alert]

        # Get alerts from last hour
        recent = manager.get_recent_alerts(hours=1)
        assert len(recent) == 1
        assert recent[0]['component'] == 'memory_percent'

    def test_alert_history_limit(self):
        """Test alert history size limiting"""
        manager = AlertManager()

        # Add more than limit
        for i in range(1005):
            alert = {
                'timestamp': time.time(),
                'level': 'warning',
                'component': f'component_{i}',
                'message': f'Alert {i}'
            }
            manager._alerts.append(alert)

        # Should only keep last 1000
        assert len(manager._alerts) == 1000
        assert manager._alerts[0]['component'] == 'component_5'
        assert manager._alerts[-1]['component'] == 'component_1004'


if __name__ == "__main__":
    pytest.main([__file__])