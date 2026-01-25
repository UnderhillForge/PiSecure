"""
PiSecure Input Validation and Sanitization
==========================================

Comprehensive input validation and sanitization utilities for API security.

Features:
- JSON schema validation for request bodies
- Type checking and bounds validation
- Input sanitization (removing dangerous characters)
- Request size limits and structure validation
- Security-focused validation for blockchain operations

Security measures:
- SQL injection prevention
- XSS protection
- Path traversal prevention
- Command injection protection
- Buffer overflow prevention
"""

import re
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Union
from flask import request, abort

# Dangerous patterns to filter out
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',                # JavaScript URLs
    r'data:',                      # Data URLs (potential XSS)
    r'vbscript:',                  # VBScript
    r'on\w+\s*=',                  # Event handlers
    r'<\w+[^>]*>',                 # HTML tags
    r'\.\./',                      # Path traversal
    r'\.\.\\',                     # Windows path traversal
    r';\s*rm\s',                   # Command injection
    r';\s*del\s',                  # Windows command injection
    r';\s*format\s',               # Disk formatting
    r'union\s+select',             # SQL injection
    r'--',                         # SQL comments
    r'/\*.*?\*/',                  # SQL comments
    r'drop\s+table',               # SQL injection
    r'alter\s+table',              # SQL injection
]

# Safe character whitelist for various inputs
SAFE_CHARS = re.compile(r'^[a-zA-Z0-9_\-\.\s@]+$')
SAFE_NAME_CHARS = re.compile(r'^[a-zA-Z0-9_\-\s]+$')
SAFE_ADDRESS_CHARS = re.compile(r'^[a-fA-F0-9]{40,}$')  # Hex addresses
SAFE_TX_HASH_CHARS = re.compile(r'^[a-fA-F0-9]{64}$')   # 64 char hex

# Request size limits
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
MAX_URL_LENGTH = 2048
MAX_QUERY_PARAMS = 50
MAX_ARRAY_LENGTH = 1000

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)

def sanitize_string(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing dangerous patterns and limiting length.

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        ValidationError: If input is invalid or too long
    """
    if not isinstance(input_str, str):
        raise ValidationError("Input must be a string")

    # Check length
    if len(input_str) > max_length:
        raise ValidationError(f"Input too long (max {max_length} characters)")

    # Remove null bytes and other control characters
    sanitized = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')

    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

    # Trim whitespace
    sanitized = sanitized.strip()

    return sanitized

def validate_wallet_address(address: str) -> str:
    """
    Validate and sanitize wallet address.

    Args:
        address: Wallet address to validate

    Returns:
        Validated address

    Raises:
        ValidationError: If address is invalid
    """
    if not isinstance(address, str):
        raise ValidationError("Wallet address must be a string", "address")

    # Remove whitespace
    address = address.strip()

    # Check format (should be 40+ hex characters for Ethereum-style addresses)
    if not SAFE_ADDRESS_CHARS.match(address):
        raise ValidationError("Invalid wallet address format", "address")

    # Check length (typical blockchain addresses)
    if len(address) < 20 or len(address) > 100:
        raise ValidationError("Wallet address length invalid", "address")

    return address

def validate_transaction_hash(tx_hash: str) -> str:
    """
    Validate transaction hash.

    Args:
        tx_hash: Transaction hash to validate

    Returns:
        Validated hash

    Raises:
        ValidationError: If hash is invalid
    """
    if not isinstance(tx_hash, str):
        raise ValidationError("Transaction hash must be a string", "tx_hash")

    tx_hash = tx_hash.strip().lower()

    if not SAFE_TX_HASH_CHARS.match(tx_hash):
        raise ValidationError("Invalid transaction hash format", "tx_hash")

    return tx_hash

def validate_node_id(node_id: str) -> str:
    """
    Validate node identifier.

    Args:
        node_id: Node ID to validate

    Returns:
        Validated node ID

    Raises:
        ValidationError: If node ID is invalid
    """
    if not isinstance(node_id, str):
        raise ValidationError("Node ID must be a string", "node_id")

    node_id = sanitize_string(node_id, max_length=100)

    # Node IDs should be alphanumeric with safe characters
    if not SAFE_NAME_CHARS.match(node_id):
        raise ValidationError("Invalid node ID format", "node_id")

    return node_id

def validate_name(name: str) -> str:
    """
    Validate and sanitize name input.

    Args:
        name: Name to validate

    Returns:
        Validated name

    Raises:
        ValidationError: If name is invalid
    """
    name = sanitize_string(name, max_length=50)

    if len(name) < 1:
        raise ValidationError("Name cannot be empty", "name")

    if len(name) > 50:
        raise ValidationError("Name too long (max 50 characters)", "name")

    return name

def validate_amount(amount: Union[int, float, str]) -> float:
    """
    Validate monetary amount.

    Args:
        amount: Amount to validate

    Returns:
        Validated amount as float

    Raises:
        ValidationError: If amount is invalid
    """
    try:
        if isinstance(amount, str):
            # Remove commas and spaces
            amount = amount.replace(',', '').replace(' ', '')

        amount_float = float(amount)

        # Check bounds
        if amount_float < 0:
            raise ValidationError("Amount cannot be negative", "amount")

        if amount_float > 1e12:  # Reasonable upper bound
            raise ValidationError("Amount too large", "amount")

        # Check for precision issues
        if abs(amount_float) > 0 and abs(amount_float) < 1e-8:
            raise ValidationError("Amount too small", "amount")

        return amount_float

    except (ValueError, TypeError):
        raise ValidationError("Invalid amount format", "amount")

def validate_port(port: Union[int, str]) -> int:
    """
    Validate network port number.

    Args:
        port: Port to validate

    Returns:
        Validated port as integer

    Raises:
        ValidationError: If port is invalid
    """
    try:
        port_int = int(port)

        if port_int < 1 or port_int > 65535:
            raise ValidationError("Port must be between 1 and 65535", "port")

        # Reserve common ports that shouldn't be used
        reserved_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        if port_int in reserved_ports:
            raise ValidationError("Port number is reserved", "port")

        return port_int

    except (ValueError, TypeError):
        raise ValidationError("Invalid port number", "port")

def validate_capabilities(capabilities: List[str]) -> List[str]:
    """
    Validate node capabilities list.

    Args:
        capabilities: List of capabilities

    Returns:
        Validated capabilities list

    Raises:
        ValidationError: If capabilities are invalid
    """
    if not isinstance(capabilities, list):
        raise ValidationError("Capabilities must be a list", "capabilities")

    if len(capabilities) > 20:  # Reasonable limit
        raise ValidationError("Too many capabilities", "capabilities")

    validated = []
    allowed_caps = {
        'api', 'p2p_sync', 'mining', 'block_validation', 'bootstrap_coordination',
        'peer_discovery', 'network_health', 'intelligence_sharing'
    }

    for cap in capabilities:
        if not isinstance(cap, str):
            raise ValidationError("Capability must be a string", "capabilities")

        cap_clean = sanitize_string(cap, max_length=50)

        if cap_clean not in allowed_caps:
            raise ValidationError(f"Unknown capability: {cap_clean}", "capabilities")

        validated.append(cap_clean)

    return validated

def validate_json_data(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate JSON data against a schema.

    Args:
        data: JSON data to validate
        schema: Validation schema

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a JSON object")

    # Check required fields
    required = schema.get('required', [])
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}", field)

    # Validate field types and constraints
    properties = schema.get('properties', {})
    for field, constraints in properties.items():
        if field in data:
            value = data[field]
            field_type = constraints.get('type')

            # Type validation
            if field_type == 'string' and not isinstance(value, str):
                raise ValidationError(f"Field {field} must be a string", field)
            elif field_type == 'number' and not isinstance(value, (int, float)):
                raise ValidationError(f"Field {field} must be a number", field)
            elif field_type == 'integer' and not isinstance(value, int):
                raise ValidationError(f"Field {field} must be an integer", field)
            elif field_type == 'boolean' and not isinstance(value, bool):
                raise ValidationError(f"Field {field} must be a boolean", field)
            elif field_type == 'array' and not isinstance(value, list):
                raise ValidationError(f"Field {field} must be an array", field)

            # Length/size constraints
            if 'maxLength' in constraints and isinstance(value, str):
                if len(value) > constraints['maxLength']:
                    raise ValidationError(f"Field {field} too long", field)

            if 'minLength' in constraints and isinstance(value, str):
                if len(value) < constraints['minLength']:
                    raise ValidationError(f"Field {field} too short", field)

            if 'maximum' in constraints and isinstance(value, (int, float)):
                if value > constraints['maximum']:
                    raise ValidationError(f"Field {field} too large", field)

            if 'minimum' in constraints and isinstance(value, (int, float)):
                if value < constraints['minimum']:
                    raise ValidationError(f"Field {field} too small", field)

            # Custom validation functions
            if 'validator' in constraints:
                validator_func = constraints['validator']
                try:
                    validated_value = validator_func(value)
                    data[field] = validated_value  # Update with validated value
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(f"Validation failed for {field}: {str(e)}", field)

    return data

# Validation schemas for different API endpoints
VALIDATION_SCHEMAS = {
    'transaction': {
        'required': ['type', 'data', 'signature', 'timestamp'],
        'properties': {
            'type': {'type': 'string', 'maxLength': 50},
            'data': {'type': 'object'},
            'signature': {'type': 'string', 'minLength': 64, 'maxLength': 200},
            'timestamp': {'type': 'number', 'minimum': 1609459200},  # 2021-01-01
            'memo': {'type': 'string', 'maxLength': 500}
        }
    },

    'wallet_create': {
        'properties': {
            'name': {'type': 'string', 'maxLength': 50, 'validator': validate_name},
            'display_name': {'type': 'string', 'maxLength': 100}
        }
    },

    'trust_create': {
        'required': ['developer_address'],
        'properties': {
            'developer_address': {'type': 'string', 'validator': validate_wallet_address},
            'trust_type': {'type': 'string', 'maxLength': 20},
            'initial_funding': {'type': 'number', 'minimum': 0, 'maximum': 1000000}
        }
    },

    'node_register': {
        'required': ['node_id', 'address', 'port'],
        'properties': {
            'node_id': {'type': 'string', 'validator': validate_node_id},
            'address': {'type': 'string', 'maxLength': 100},
            'port': {'type': 'integer', 'validator': validate_port},
            'capabilities': {'type': 'array', 'validator': validate_capabilities},
            'hashrate': {'type': 'number', 'minimum': 0},
            'location': {'type': 'string', 'maxLength': 50}
        }
    },

    'names_register': {
        'required': ['name', 'wallet_address'],
        'properties': {
            'name': {'type': 'string', 'validator': validate_name},
            'wallet_address': {'type': 'string', 'validator': validate_wallet_address}
        }
    },

    'bootstrap_register': {
        'required': ['operator_id'],
        'properties': {
            'operator_id': {'type': 'string', 'validator': validate_node_id}
        }
    }
}

def validate_request(endpoint: str) -> Dict[str, Any]:
    """
    Validate incoming request for a specific endpoint.

    Args:
        endpoint: API endpoint name

    Returns:
        Validated request data

    Raises:
        ValidationError: If validation fails
    """
    # Check request size
    content_length = request.content_length or 0
    if content_length > MAX_REQUEST_SIZE:
        abort(413, "Request too large")

    # Check URL length
    if len(request.url) > MAX_URL_LENGTH:
        abort(414, "URL too long")

    # Check query parameters count
    if len(request.args) > MAX_QUERY_PARAMS:
        abort(400, "Too many query parameters")

    # Validate JSON data if present
    if request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
        try:
            data = request.get_json()
        except Exception:
            abort(400, "Invalid JSON")

        if endpoint in VALIDATION_SCHEMAS:
            schema = VALIDATION_SCHEMAS[endpoint]
            data = validate_json_data(data, schema)

        return data

    return {}

def safe_error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """
    Create a safe error response that doesn't leak sensitive information.

    Args:
        message: Error message
        status_code: HTTP status code

    Returns:
        Safe error response dict
    """
    # Remove any potentially sensitive information from message
    safe_message = re.sub(r'[a-fA-F0-9]{32,}', '[REDACTED]', message)  # Hide long hex strings
    safe_message = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]', safe_message)  # Hide IPs

    return {
        'error': safe_message,
        'status_code': status_code,
        'timestamp': int(time.time())
    }

def validate_and_sanitize_input(input_data: Any, input_type: str = 'general') -> Any:
    """
    General input validation and sanitization function.

    Args:
        input_data: Input data to validate
        input_type: Type of input ('string', 'number', 'address', etc.)

    Returns:
        Validated and sanitized input

    Raises:
        ValidationError: If validation fails
    """
    if input_type == 'string':
        return sanitize_string(input_data)
    elif input_type == 'address':
        return validate_wallet_address(input_data)
    elif input_type == 'tx_hash':
        return validate_transaction_hash(input_data)
    elif input_type == 'node_id':
        return validate_node_id(input_data)
    elif input_type == 'name':
        return validate_name(input_data)
    elif input_type == 'amount':
        return validate_amount(input_data)
    elif input_type == 'port':
        return validate_port(input_data)
    elif input_type == 'capabilities':
        return validate_capabilities(input_data)
    else:
        # General sanitization
        if isinstance(input_data, str):
            return sanitize_string(input_data)
        elif isinstance(input_data, (int, float)):
            return input_data
        elif isinstance(input_data, list):
            return [validate_and_sanitize_input(item) for item in input_data[:MAX_ARRAY_LENGTH]]
        elif isinstance(input_data, dict):
            return {k: validate_and_sanitize_input(v) for k, v in input_data.items() if len(k) < 100}
        else:
            return input_data

# Security monitoring functions
def log_security_event(event_type: str, details: Dict[str, Any], severity: str = 'info'):
    """
    Log security-related events for monitoring.

    Args:
        event_type: Type of security event
        details: Event details
        severity: Event severity level
    """
    import logging
    logger = logging.getLogger('security')

    # Sanitize details for logging
    safe_details = {}
    for k, v in details.items():
        if isinstance(v, str):
            safe_details[k] = re.sub(r'[a-fA-F0-9]{32,}', '[REDACTED]', v)
        else:
            safe_details[k] = v

    message = f"SECURITY_EVENT: {event_type} - {safe_details}"

    if severity == 'error':
        logger.error(message)
    elif severity == 'warning':
        logger.warning(message)
    else:
        logger.info(message)

def check_rate_limit_exceeded(request_info: Dict[str, Any]) -> bool:
    """
    Check if request should be blocked due to rate limiting.

    Args:
        request_info: Request information

    Returns:
        True if request should be blocked
    """
    # This would integrate with the rate limiting system
    # For now, return False (allow all)
    return False

def validate_file_upload(file_data: bytes, filename: str) -> bool:
    """
    Validate uploaded file for security.

    Args:
        file_data: File content bytes
        filename: Original filename

    Returns:
        True if file is safe

    Raises:
        ValidationError: If file is unsafe
    """
    # Check file size
    if len(file_data) > 10 * 1024 * 1024:  # 10MB limit
        raise ValidationError("File too large")

    # Check filename for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError("Invalid filename")

    # Check for executable content (basic check)
    if file_data.startswith(b'\x7fELF'):  # ELF executable
        raise ValidationError("Executable files not allowed")

    if file_data.startswith(b'MZ'):  # Windows executable
        raise ValidationError("Executable files not allowed")

    return True