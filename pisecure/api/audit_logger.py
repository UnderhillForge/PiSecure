"""
PiSecure Security Audit Logging System
======================================

Comprehensive security audit logging system for PiSecure blockchain nodes.
Tracks all security events, API calls, authentication attempts, and system activities
with proper log rotation, integrity verification, and secure storage.

Features:
- Structured JSON logging with correlation IDs
- Automatic log rotation and retention
- Log integrity verification with HMAC
- Encrypted log storage options
- Real-time log analysis and alerting
- GDPR-compliant log management
"""

import os
import json
import time
import hashlib
import hmac
import threading
import gzip
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import secrets
import base64


class AuditEventType(Enum):
    """Security audit event types"""
    API_ACCESS = "api_access"
    API_ERROR = "api_error"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_ATTEMPT = "auth_attempt"
    BLOCKCHAIN_ACCESS = "blockchain_access"
    WALLET_ACCESS = "wallet_access"
    TRANSACTION_SUBMIT = "transaction_submit"
    MINING_START = "mining_start"
    MINING_STOP = "mining_stop"
    NODE_REGISTER = "node_register"
    PEER_CONNECT = "peer_connect"
    PEER_DISCONNECT = "peer_disconnect"
    SECURITY_VIOLATION = "security_violation"
    DDoS_ATTACK = "ddos_attack"
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    PATH_TRAVERSAL = "path_traversal"
    CONFIG_CHANGE = "config_change"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    LOG_ROTATION = "log_rotation"
    INTEGRITY_CHECK = "integrity_check"


class AuditLogger:
    """
    Thread-safe security audit logging system with integrity verification.

    Features:
    - Structured JSON logging with correlation IDs
    - HMAC-based integrity verification
    - Automatic log rotation and compression
    - Encrypted log storage (optional)
    - Real-time alerting for security events
    - GDPR-compliant data retention
    """

    def __init__(self, log_dir: str = "/var/log/pisecure/audit",
                 max_log_size: int = 10 * 1024 * 1024,  # 10MB
                 retention_days: int = 90,
                 enable_encryption: bool = False,
                 enable_alerts: bool = True):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for audit logs
            max_log_size: Maximum log file size before rotation (bytes)
            retention_days: Days to retain audit logs
            enable_encryption: Enable encrypted log storage
            enable_alerts: Enable real-time security alerts
        """
        self.log_dir = Path(log_dir)
        self.max_log_size = max_log_size
        self.retention_days = retention_days
        self.enable_encryption = enable_encryption
        self.enable_alerts = enable_alerts

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Current log file
        self.current_log_file = None
        self.current_log_path = None

        # Thread safety
        self.lock = threading.RLock()

        # HMAC key for integrity verification
        self.hmac_key = self._generate_hmac_key()

        # Encryption key (if enabled)
        self.encryption_key = None
        if enable_encryption:
            self.encryption_key = self._generate_encryption_key()

        # Alert callbacks
        self.alert_callbacks = []

        # Initialize logger
        self._setup_logger()

        # Start background maintenance
        self._start_maintenance_thread()

        # Log system startup
        self.log_event(AuditEventType.SYSTEM_STARTUP, {
            'message': 'Security audit logging system initialized',
            'version': '1.0.0',
            'log_dir': str(log_dir),
            'encryption_enabled': enable_encryption
        })

    def _generate_hmac_key(self) -> bytes:
        """Generate HMAC key for log integrity verification"""
        key_file = self.log_dir / '.hmac_key'
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = secrets.token_bytes(32)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure key file permissions
            os.chmod(key_file, 0o600)
            return key

    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key for log files"""
        key_file = self.log_dir / '.encryption_key'
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = secrets.token_bytes(32)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure key file permissions
            os.chmod(key_file, 0o600)
            return key

    def _setup_logger(self):
        """Setup Python logging for audit events"""
        self.logger = logging.getLogger('pisecure.audit')
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add file handler for audit logs
        log_path = self.log_dir / 'audit.log'
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)

    def _start_maintenance_thread(self):
        """Start background maintenance thread for log rotation and cleanup"""
        maintenance_thread = threading.Thread(
            target=self._maintenance_worker,
            daemon=True,
            name="AuditLogMaintenance"
        )
        maintenance_thread.start()

    def _maintenance_worker(self):
        """Background worker for log maintenance"""
        while True:
            try:
                # Check for rotation every 5 minutes
                time.sleep(300)

                with self.lock:
                    self._check_rotation()
                    self._cleanup_old_logs()

            except Exception as e:
                print(f"Audit log maintenance error: {e}")

    def _check_rotation(self):
        """Check if log rotation is needed"""
        if not self.current_log_path or not self.current_log_path.exists():
            self._open_new_log_file()
            return

        # Check file size
        if self.current_log_path.stat().st_size >= self.max_log_size:
            self._rotate_log()

    def _rotate_log(self):
        """Rotate current log file"""
        if not self.current_log_path:
            return

        # Generate new filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rotated_path = self.log_dir / f'audit_{timestamp}.log'

        # Move current log file
        self.current_log_path.rename(rotated_path)

        # Compress rotated log
        self._compress_log(rotated_path)

        # Log rotation event
        self.log_event(AuditEventType.LOG_ROTATION, {
            'rotated_file': str(rotated_path),
            'compressed': True,
            'reason': 'size_limit'
        })

        # Open new log file
        self._open_new_log_file()

    def _compress_log(self, log_path: Path):
        """Compress log file using gzip"""
        compressed_path = log_path.with_suffix('.log.gz')

        try:
            with open(log_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Remove uncompressed file
            log_path.unlink()

        except Exception as e:
            print(f"Failed to compress log {log_path}: {e}")

    def _cleanup_old_logs(self):
        """Clean up old log files based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob('audit_*.log.gz'):
            try:
                # Extract timestamp from filename
                timestamp_str = log_file.stem.split('_', 1)[1]
                file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                if file_date < cutoff_date:
                    log_file.unlink()
                    print(f"Cleaned up old audit log: {log_file}")

            except (ValueError, IndexError):
                # Skip files with invalid timestamp format
                continue

    def _open_new_log_file(self):
        """Open new log file for writing"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_log_path = self.log_dir / f'current_{timestamp}.log'
        self.current_log_file = open(self.current_log_path, 'a', encoding='utf-8')

    def log_event(self, event_type: Union[AuditEventType, str],
                  data: Dict[str, Any],
                  client_ip: str = None,
                  user_id: str = None,
                  session_id: str = None,
                  severity: str = 'info') -> str:
        """
        Log security audit event.

        Args:
            event_type: Type of audit event
            data: Event data dictionary
            client_ip: Client IP address
            user_id: User identifier (if applicable)
            session_id: Session identifier
            severity: Event severity (debug, info, warning, error, critical)

        Returns:
            Correlation ID for the logged event
        """
        with self.lock:
            # Generate correlation ID
            correlation_id = secrets.token_hex(16)

            # Build audit record
            audit_record = {
                'timestamp': datetime.now().isoformat(),
                'correlation_id': correlation_id,
                'event_type': event_type.value if isinstance(event_type, AuditEventType) else str(event_type),
                'severity': severity,
                'client_ip': client_ip,
                'user_id': user_id,
                'session_id': session_id,
                'data': data
            }

            # Convert to JSON
            json_record = json.dumps(audit_record, ensure_ascii=False)

            # Generate HMAC for integrity verification
            hmac_digest = hmac.new(self.hmac_key, json_record.encode('utf-8'), hashlib.sha256)
            integrity_hash = hmac_digest.hexdigest()

            # Add integrity hash to record
            audit_record['integrity_hash'] = integrity_hash
            final_record = json.dumps(audit_record, ensure_ascii=False)

            # Encrypt if enabled
            if self.enable_encryption:
                final_record = self._encrypt_record(final_record)

            # Write to log file
            if self.current_log_file:
                try:
                    self.current_log_file.write(final_record + '\n')
                    self.current_log_file.flush()
                except Exception as e:
                    print(f"Failed to write audit log: {e}")
                    # Try to reopen log file
                    self._open_new_log_file()

            # Also log via Python logging
            self.logger.info(f"AUDIT: {correlation_id} - {event_type.value if isinstance(event_type, AuditEventType) else str(event_type)}")

            # Check for alerts
            if self.enable_alerts:
                self._check_alerts(audit_record)

            return correlation_id

    def _encrypt_record(self, record: str) -> str:
        """Encrypt audit record (simple XOR for demonstration)"""
        if not self.encryption_key:
            return record

        # Simple XOR encryption (replace with proper encryption in production)
        encrypted = bytearray()
        key_len = len(self.encryption_key)
        record_bytes = record.encode('utf-8')

        for i, byte in enumerate(record_bytes):
            encrypted.append(byte ^ self.encryption_key[i % key_len])

        return base64.b64encode(encrypted).decode('ascii')

    def _check_alerts(self, audit_record: Dict[str, Any]):
        """Check if audit record should trigger alerts"""
        event_type = audit_record['event_type']
        severity = audit_record['severity']

        # Alert conditions
        alert_conditions = [
            severity in ['error', 'critical'],
            event_type in ['ddos_attack', 'brute_force', 'security_violation'],
            event_type == 'auth_failure' and self._check_brute_force(audit_record),
        ]

        if any(alert_conditions):
            self._trigger_alert(audit_record)

    def _check_brute_force(self, audit_record: Dict[str, Any]) -> bool:
        """Check for brute force attack patterns"""
        # Simple check: multiple auth failures from same IP in short time
        # In production, this would query recent logs
        return False  # Placeholder

    def _trigger_alert(self, audit_record: Dict[str, Any]):
        """Trigger security alerts"""
        for callback in self.alert_callbacks:
            try:
                callback(audit_record)
            except Exception as e:
                print(f"Alert callback error: {e}")

    def add_alert_callback(self, callback):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)

    def verify_log_integrity(self, log_file: Path = None) -> bool:
        """
        Verify integrity of audit log file.

        Args:
            log_file: Log file to verify (current if None)

        Returns:
            True if integrity check passes
        """
        if log_file is None:
            log_file = self.current_log_path

        if not log_file or not log_file.exists():
            return False

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse JSON record
                        if self.enable_encryption:
                            # Decrypt first
                            line = self._decrypt_record(line)

                        record = json.loads(line)

                        # Verify HMAC
                        integrity_hash = record.pop('integrity_hash', '')
                        json_record = json.dumps(record, ensure_ascii=False, sort_keys=True)

                        expected_hmac = hmac.new(self.hmac_key, json_record.encode('utf-8'), hashlib.sha256)
                        expected_hash = expected_hmac.hexdigest()

                        if not hmac.compare_digest(integrity_hash, expected_hash):
                            print(f"Integrity check failed at line {line_num}")
                            return False

                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Invalid record at line {line_num}: {e}")
                        return False

            return True

        except Exception as e:
            print(f"Integrity verification error: {e}")
            return False

    def _decrypt_record(self, encrypted_record: str) -> str:
        """Decrypt audit record"""
        if not self.encryption_key:
            return encrypted_record

        try:
            encrypted_bytes = base64.b64decode(encrypted_record)
            decrypted = bytearray()
            key_len = len(self.encryption_key)

            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ self.encryption_key[i % key_len])

            return decrypted.decode('utf-8')

        except Exception:
            return encrypted_record  # Return as-is if decryption fails

    def search_logs(self, query: Dict[str, Any],
                   start_time: datetime = None,
                   end_time: datetime = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search audit logs with filtering.

        Args:
            query: Search criteria dictionary
            start_time: Start time for search
            end_time: End time for search
            limit: Maximum results to return

        Returns:
            List of matching audit records
        """
        results = []

        # Search all log files
        for log_file in self.log_dir.glob('*.log*'):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            if self.enable_encryption:
                                line = self._decrypt_record(line)

                            record = json.loads(line)

                            # Apply time filters
                            record_time = datetime.fromisoformat(record['timestamp'])
                            if start_time and record_time < start_time:
                                continue
                            if end_time and record_time > end_time:
                                continue

                            # Apply query filters
                            if self._matches_query(record, query):
                                results.append(record)

                                if len(results) >= limit:
                                    break

                        except (json.JSONDecodeError, ValueError):
                            continue

            except Exception:
                continue

            if len(results) >= limit:
                break

        return results

    def _matches_query(self, record: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if record matches search query"""
        for key, value in query.items():
            if key not in record:
                return False

            record_value = record[key]
            if isinstance(value, dict):
                # Nested query
                if not self._matches_query(record_value, value):
                    return False
            elif record_value != value:
                return False

        return True

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Args:
            hours: Hours to analyze

        Returns:
            Statistics dictionary
        """
        start_time = datetime.now() - timedelta(hours=hours)

        # Count events by type
        event_counts = {}
        severity_counts = {}
        ip_counts = {}

        logs = self.search_logs({}, start_time=start_time, limit=10000)

        for record in logs:
            # Event type counts
            event_type = record.get('event_type', 'unknown')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # Severity counts
            severity = record.get('severity', 'info')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # IP counts
            client_ip = record.get('client_ip')
            if client_ip:
                ip_counts[client_ip] = ip_counts.get(client_ip, 0) + 1

        return {
            'total_events': len(logs),
            'event_counts': event_counts,
            'severity_counts': severity_counts,
            'unique_ips': len(ip_counts),
            'top_ips': sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'time_range_hours': hours
        }


# Global audit logger instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

def log_security_event(event_type: Union[AuditEventType, str],
                      data: Dict[str, Any],
                      client_ip: str = None,
                      user_id: str = None,
                      session_id: str = None,
                      severity: str = 'info') -> str:
    """
    Convenience function to log security events.

    Args:
        event_type: Type of security event
        data: Event data
        client_ip: Client IP address
        user_id: User identifier
        session_id: Session identifier
        severity: Event severity

    Returns:
        Correlation ID
    """
    logger = get_audit_logger()
    return logger.log_event(event_type, data, client_ip, user_id, session_id, severity)

# Flask middleware for automatic audit logging
class AuditLogMiddleware:
    """Flask middleware for automatic audit logging of API requests"""

    def __init__(self, app, exclude_paths: List[str] = None):
        """
        Initialize audit log middleware.

        Args:
            app: Flask application
            exclude_paths: Paths to exclude from audit logging
        """
        self.app = app
        self.exclude_paths = exclude_paths or ['/health', '/favicon.ico']

        # Register middleware
        self.app.before_request(self.log_request)
        self.app.after_request(self.log_response)

    def log_request(self):
        """Log incoming API request"""
        from flask import request

        if request.path in self.exclude_paths:
            return

        # Get client IP (handle proxies)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Log API access
        log_security_event(
            AuditEventType.API_ACCESS,
            {
                'method': request.method,
                'path': request.path,
                'query_string': request.query_string.decode('utf-8') if request.query_string else '',
                'user_agent': request.headers.get('User-Agent', ''),
                'content_length': request.content_length,
                'content_type': request.content_type
            },
            client_ip=client_ip,
            severity='info'
        )

    def log_response(self, response):
        """Log API response"""
        from flask import request

        if request.path in self.exclude_paths:
            return response

        # Log API errors
        if response.status_code >= 400:
            log_security_event(
                AuditEventType.API_ERROR,
                {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'content_length': response.content_length,
                    'error_response': response.get_data(as_text=True)[:500]  # First 500 chars
                },
                client_ip=request.headers.get('X-Forwarded-For', request.remote_addr),
                severity='warning' if response.status_code < 500 else 'error'
            )

        return response


# Example usage and testing
if __name__ == '__main__':
    # Initialize audit logger
    audit = AuditLogger()

    # Log some test events
    audit.log_event(AuditEventType.SYSTEM_STARTUP, {'version': '1.0.0'})
    audit.log_event(AuditEventType.API_ACCESS, {'method': 'GET', 'path': '/api/health'})
    audit.log_event(AuditEventType.SECURITY_VIOLATION, {'type': 'xss_attempt', 'blocked': True}, severity='warning')

    # Verify integrity
    print(f"Log integrity check: {audit.verify_log_integrity()}")

    # Get statistics
    stats = audit.get_statistics(hours=1)
    print(f"Audit statistics: {stats}")

    # Search logs
    results = audit.search_logs({'event_type': 'api_access'})
    print(f"Found {len(results)} API access events")