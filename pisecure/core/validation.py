"""
PiSecure Input Validation & Security
====================================

Comprehensive input validation and security utilities.
"""

import re
import hashlib
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation


class InputValidator:
    """Input validation utilities for PiSecure"""

    # Wallet address pattern (hexadecimal, 32-64 chars)
    WALLET_ADDRESS_PATTERN = re.compile(r'^[a-fA-F0-9]{32,64}$')

    # Transaction types
    VALID_TX_TYPES = {
        'genesis', 'token_transfer', 'batch_transfer',
        'name_registration', 'mining_reward', 'test_transaction',
        'sensor_reading'
    }

    @staticmethod
    def validate_wallet_address(address: str) -> bool:
        """Validate wallet address format"""
        if not isinstance(address, str):
            return False
        return bool(InputValidator.WALLET_ADDRESS_PATTERN.match(address.strip()))

    @staticmethod
    def validate_amount(amount: Any) -> Optional[Decimal]:
        """Validate and normalize amount"""
        try:
            if isinstance(amount, str):
                amount = amount.strip()
            decimal_amount = Decimal(str(amount))

            # Check bounds (0 < amount <= 1,000,000)
            if decimal_amount <= 0 or decimal_amount > 1_000_000:
                return None

            # Check decimal places (max 8)
            if decimal_amount.as_tuple().exponent < -8:
                return None

            return decimal_amount

        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def validate_transaction_type(tx_type: str) -> bool:
        """Validate transaction type"""
        return tx_type in InputValidator.VALID_TX_TYPES

    @staticmethod
    def validate_transaction_data(tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete transaction data"""
        errors = []

        # Required fields
        required_fields = ['type', 'timestamp']
        for field in required_fields:
            if field not in tx_data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {'valid': False, 'errors': errors}

        # Validate transaction type
        tx_type = tx_data.get('type')
        if not InputValidator.validate_transaction_type(tx_type):
            errors.append(f"Invalid transaction type: {tx_type}")

        # Type-specific validation
        if tx_type == 'token_transfer':
            errors.extend(InputValidator._validate_token_transfer(tx_data))
        elif tx_type == 'batch_transfer':
            errors.extend(InputValidator._validate_batch_transfer(tx_data))
        elif tx_type == 'name_registration':
            errors.extend(InputValidator._validate_name_registration(tx_data))

        # Validate timestamp
        timestamp = tx_data.get('timestamp')
        if not isinstance(timestamp, (int, float)) or timestamp < 0:
            errors.append("Invalid timestamp")
        elif timestamp > time.time() + 300:  # Max 5 minutes in future
            errors.append("Timestamp too far in future")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []  # Could add warnings for best practices
        }

    @staticmethod
    def _validate_token_transfer(tx_data: Dict[str, Any]) -> List[str]:
        """Validate token transfer transaction"""
        errors = []

        required = ['sender_address', 'recipient_address', 'amount', 'signature']
        for field in required:
            if field not in tx_data:
                errors.append(f"Missing field: {field}")
                continue

        if 'sender_address' in tx_data:
            if not InputValidator.validate_wallet_address(tx_data['sender_address']):
                errors.append("Invalid sender address format")

        if 'recipient_address' in tx_data:
            if not InputValidator.validate_wallet_address(tx_data['recipient_address']):
                errors.append("Invalid recipient address format")

        if 'amount' in tx_data:
            amount = InputValidator.validate_amount(tx_data['amount'])
            if amount is None:
                errors.append("Invalid amount")

        return errors

    @staticmethod
    def _validate_batch_transfer(tx_data: Dict[str, Any]) -> List[str]:
        """Validate batch transfer transaction"""
        errors = []

        required = ['sender_address', 'transfers', 'total_amount', 'signature']
        for field in required:
            if field not in tx_data:
                errors.append(f"Missing field: {field}")
                continue

        if 'transfers' in tx_data:
            transfers = tx_data['transfers']
            if not isinstance(transfers, list) or len(transfers) == 0:
                errors.append("Invalid transfers list")
            else:
                total_calculated = Decimal('0')
                for i, transfer in enumerate(transfers):
                    if not isinstance(transfer, dict):
                        errors.append(f"Transfer {i} is not a valid object")
                        continue

                    recipient = transfer.get('recipient')
                    amount = transfer.get('amount')

                    if not recipient or not InputValidator.validate_wallet_address(recipient):
                        errors.append(f"Transfer {i}: invalid recipient address")

                    amount_decimal = InputValidator.validate_amount(amount)
                    if amount_decimal is None:
                        errors.append(f"Transfer {i}: invalid amount")
                    else:
                        total_calculated += amount_decimal

                # Check total matches
                total_expected = InputValidator.validate_amount(tx_data.get('total_amount'))
                if total_expected is not None and total_calculated != total_expected:
                    errors.append(f"Total amount mismatch: {total_calculated} vs {total_expected}")

        return errors

    @staticmethod
    def _validate_name_registration(tx_data: Dict[str, Any]) -> List[str]:
        """Validate name registration transaction"""
        errors = []

        required = ['wallet_address', 'name', 'registration_fee']
        for field in required:
            if field not in tx_data:
                errors.append(f"Missing field: {field}")

        if 'name' in tx_data:
            name = tx_data['name']
            if not isinstance(name, str) or len(name.strip()) == 0:
                errors.append("Invalid name")
            elif len(name) > 64:  # Reasonable name length limit
                errors.append("Name too long (max 64 characters)")

        if 'registration_fee' in tx_data:
            fee = InputValidator.validate_amount(tx_data['registration_fee'])
            if fee is None or fee < 5:  # Minimum registration fee
                errors.append("Invalid registration fee (minimum 5 tokens)")

        return errors

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            return ""
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
        return sanitized[:max_length].strip()


class SecurityUtils:
    """Security utilities for PiSecure"""

    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID for tracking"""
        import secrets
        return secrets.token_hex(8)

    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:16] + "..."

    @staticmethod
    def validate_request_rate(client_id: str, max_requests: int = 100,
                            time_window: int = 60) -> bool:
        """Simple rate limiting (in production, use Redis or similar)"""
        # This is a basic in-memory implementation
        # In production, you'd use Redis or a database
        current_time = time.time()

        # Simple in-memory tracking (resets on restart)
        if not hasattr(SecurityUtils, '_rate_limits'):
            SecurityUtils._rate_limits = {}

        if client_id not in SecurityUtils._rate_limits:
            SecurityUtils._rate_limits[client_id] = []

        # Clean old requests
        SecurityUtils._rate_limits[client_id] = [
            req_time for req_time in SecurityUtils._rate_limits[client_id]
            if current_time - req_time < time_window
        ]

        # Check rate limit
        if len(SecurityUtils._rate_limits[client_id]) >= max_requests:
            return False

        # Add current request
        SecurityUtils._rate_limits[client_id].append(current_time)
        return True