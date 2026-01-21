"""
PiSecure Test Suite
===================

Comprehensive test suite for PiSecure components.
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, patch

from pisecure.core.validation import InputValidator, SecurityUtils


class TestInputValidator:

    def test_validate_wallet_address_valid(self):
        """Test valid wallet addresses"""
        valid_addresses = [
            "a" * 32,  # 32 chars
            "A" * 64,  # 64 chars
            "1234567890abcdef" * 4,  # mixed case
        ]
        for addr in valid_addresses:
            assert InputValidator.validate_wallet_address(addr)

    def test_validate_wallet_address_invalid(self):
        """Test invalid wallet addresses"""
        invalid_addresses = [
            "",  # empty
            "a" * 31,  # too short
            "a" * 65,  # too long
            "ggggggggggggggggggggggggggggggg",  # 31 chars
            "ggggggggggggggggggggggggggggggggg",  # 33 chars
            "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",  # way too long
            "ggggggggggggggggggggggggggggggg!",  # invalid char
            "ggggggggggggggggggggggggggggggg ",  # trailing space
            None,  # not string
            12345,  # not string
        ]
        for addr in invalid_addresses:
            assert not InputValidator.validate_wallet_address(addr)

    def test_validate_amount_valid(self):
        """Test valid amounts"""
        valid_amounts = [
            ("1.0", Decimal("1.0")),
            ("0.00000001", Decimal("0.00000001")),
            ("1000000", Decimal("1000000")),
            ("123.45678901", Decimal("123.45678901")),
            (Decimal("500.5"), Decimal("500.5")),
            (1000, Decimal("1000")),
        ]
        for input_val, expected in valid_amounts:
            result = InputValidator.validate_amount(input_val)
            assert result == expected

    def test_validate_amount_invalid(self):
        """Test invalid amounts"""
        invalid_amounts = [
            0,  # zero
            -1,  # negative
            "0",  # zero string
            "-1.5",  # negative string
            1000001,  # too large
            "1000001",  # too large string
            "1.000000001",  # too many decimals
            "abc",  # not numeric
            "",  # empty
            None,  # none
            [],  # list
        ]
        for amount in invalid_amounts:
            assert InputValidator.validate_amount(amount) is None

    def test_validate_transaction_type(self):
        """Test transaction type validation"""
        valid_types = [
            'genesis', 'token_transfer', 'batch_transfer',
            'name_registration', 'mining_reward', 'test_transaction',
            'sensor_reading'
        ]
        for tx_type in valid_types:
            assert InputValidator.validate_transaction_type(tx_type)

        invalid_types = [
            'invalid_type', '', 'GENESIS', 'token transfer', None
        ]
        for tx_type in invalid_types:
            assert not InputValidator.validate_transaction_type(tx_type)

    def test_validate_token_transfer_valid(self):
        """Test valid token transfer validation"""
        tx_data = {
            'type': 'token_transfer',
            'timestamp': time.time(),
            'sender_address': 'a' * 32,
            'recipient_address': 'b' * 32,
            'amount': '100.5',
            'signature': 'sig123'
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert result['valid']
        assert len(result['errors']) == 0

    def test_validate_token_transfer_invalid(self):
        """Test invalid token transfer validation"""
        # Missing required fields
        tx_data = {
            'type': 'token_transfer',
            'timestamp': time.time(),
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert not result['valid']
        assert len(result['errors']) > 0

        # Invalid addresses
        tx_data = {
            'type': 'token_transfer',
            'timestamp': time.time(),
            'sender_address': 'invalid',
            'recipient_address': 'b' * 32,
            'amount': '100.5',
            'signature': 'sig123'
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert not result['valid']
        assert 'sender address' in ' '.join(result['errors']).lower()

    def test_validate_batch_transfer_valid(self):
        """Test valid batch transfer validation"""
        tx_data = {
            'type': 'batch_transfer',
            'timestamp': time.time(),
            'sender_address': 'a' * 32,
            'total_amount': '200.0',
            'transfers': [
                {'recipient': 'b' * 32, 'amount': '100.0'},
                {'recipient': 'c' * 32, 'amount': '100.0'}
            ],
            'signature': 'sig123'
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert result['valid']
        assert len(result['errors']) == 0

    def test_validate_batch_transfer_invalid_total(self):
        """Test batch transfer with mismatched total"""
        tx_data = {
            'type': 'batch_transfer',
            'timestamp': time.time(),
            'sender_address': 'a' * 32,
            'total_amount': '150.0',  # Should be 200.0
            'transfers': [
                {'recipient': 'b' * 32, 'amount': '100.0'},
                {'recipient': 'c' * 32, 'amount': '100.0'}
            ],
            'signature': 'sig123'
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert not result['valid']
        assert 'mismatch' in ' '.join(result['errors']).lower()

    def test_validate_name_registration_valid(self):
        """Test valid name registration validation"""
        tx_data = {
            'type': 'name_registration',
            'timestamp': time.time(),
            'wallet_address': 'a' * 32,
            'name': 'myname',
            'registration_fee': '10.0'
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert result['valid']
        assert len(result['errors']) == 0

    def test_validate_name_registration_invalid_fee(self):
        """Test name registration with invalid fee"""
        tx_data = {
            'type': 'name_registration',
            'timestamp': time.time(),
            'wallet_address': 'a' * 32,
            'name': 'myname',
            'registration_fee': '1.0'  # Too low
        }
        result = InputValidator.validate_transaction_data(tx_data)
        assert not result['valid']
        assert 'fee' in ' '.join(result['errors']).lower()

    def test_sanitize_string(self):
        """Test string sanitization"""
        # Normal string
        assert InputValidator.sanitize_string("hello world") == "hello world"

        # String with control characters
        dirty = "hello\x00world\x01test"
        assert InputValidator.sanitize_string(dirty) == "helloworldtest"

        # Empty and None
        assert InputValidator.sanitize_string("") == ""
        assert InputValidator.sanitize_string(None) == ""

        # Length limit
        long_string = "a" * 2000
        assert len(InputValidator.sanitize_string(long_string)) == 1000


class TestSecurityUtils:

    def test_generate_request_id(self):
        """Test request ID generation"""
        id1 = SecurityUtils.generate_request_id()
        id2 = SecurityUtils.generate_request_id()

        assert len(id1) == 16  # 8 bytes * 2 chars per byte
        assert id1 != id2
        assert all(c in '0123456789abcdef' for c in id1)

    def test_hash_sensitive_data(self):
        """Test sensitive data hashing"""
        data = "secret_password_123"
        hashed = SecurityUtils.hash_sensitive_data(data)

        assert len(hashed) == 20  # 16 chars + "..."
        assert hashed.endswith("...")
        assert hashed != data

        # Same input should produce same hash
        hashed2 = SecurityUtils.hash_sensitive_data(data)
        assert hashed == hashed2

    def test_validate_request_rate(self):
        """Test rate limiting"""
        SecurityUtils.reset_rate_limits()  # Clear any prior test state
        client_id = "test_client"

        # Use a fixed time to track requests
        with patch('pisecure.core.validation.time.time') as mock_time:
            base_time = 1000000.0
            mock_time.return_value = base_time
            
            # Should allow initial requests
            for i in range(10):
                assert SecurityUtils.validate_request_rate(client_id, max_requests=10)

            # Should deny 11th request
            assert not SecurityUtils.validate_request_rate(client_id, max_requests=10)

            # Should allow after time window passes (simulate time passing)
            mock_time.return_value = base_time + 61  # 61 seconds later
            assert SecurityUtils.validate_request_rate(client_id, max_requests=10)


if __name__ == "__main__":
    pytest.main([__file__])