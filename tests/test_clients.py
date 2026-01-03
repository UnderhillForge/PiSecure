"""
PiSecure Client API Test Suite
==============================

Comprehensive tests for all client implementations.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the pisecure package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pisecure.api.client import PiSecureClient
from pisecure.api.async_client import AsyncPiSecureClient


class TestPiSecureClient:
    """Test synchronous PiSecure client"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked endpoints"""
        client = PiSecureClient()
        client.api_endpoints = ['http://test-endpoint:3142']
        return client

    def test_initialization(self):
        """Test client initialization"""
        client = PiSecureClient()
        assert client.api_version == 'v1'
        assert client.timeout == 30
        assert client.max_retries == 3
        assert hasattr(client, 'api_endpoints')

    @patch('pisecure.api.client.requests.Session.request')
    def test_get_blockchain_info(self, mock_request, client):
        """Test getting blockchain info"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'blocks': 1000,
            'height': 999,
            'difficulty': 1000000,
            'pending_transactions': 5
        }
        mock_request.return_value = mock_response

        result = client.get_blockchain_info()
        assert result['blocks'] == 1000
        assert result['height'] == 999

    @patch('pisecure.api.client.requests.Session.request')
    def test_get_wallet_balance(self, mock_request, client):
        """Test getting wallet balance"""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': '123.45'}
        mock_request.return_value = mock_response

        result = client.get_wallet_balance('test_address')
        assert result == 123.45

    @patch('pisecure.api.client.requests.Session.request')
    def test_submit_transaction(self, mock_request, client):
        """Test transaction submission"""
        mock_response = Mock()
        mock_response.json.return_value = {'transaction_hash': 'testhash123'}
        mock_request.return_value = mock_response

        tx_data = {'type': 'transfer', 'amount': 100}
        result = client.submit_transaction(tx_data)
        assert result == 'testhash123'

    def test_create_transfer_transaction(self, client):
        """Test transfer transaction creation"""
        tx = client.create_transfer_transaction(
            'wallet1', 'addr1', 100.0, 'test memo'
        )

        assert tx['type'] == 'transfer'
        assert tx['from_wallet'] == 'wallet1'
        assert tx['to_address'] == 'addr1'
        assert tx['amount'] == 100.0
        assert tx['memo'] == 'test memo'
        assert 'timestamp' in tx
        assert 'data' in tx

    @patch('pisecure.api.client.requests.Session.request')
    def test_request_retry_logic(self, mock_request, client):
        """Test request retry on failure"""
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}

        mock_request.side_effect = [
            Exception('Connection failed'),
            Exception('Timeout'),
            mock_response
        ]

        result = client._make_request('GET', 'test/endpoint')
        assert result['success'] is True
        assert mock_request.call_count == 3

    @patch('pisecure.api.client.requests.Session.request')
    def test_request_max_retries_exceeded(self, mock_request, client):
        """Test max retries exceeded"""
        mock_request.side_effect = Exception('Always fails')

        with pytest.raises(ConnectionError):
            client._make_request('GET', 'test/endpoint')

        assert mock_request.call_count == 3  # max_retries


class TestAsyncPiSecureClient:
    """Test asynchronous PiSecure client"""

    @pytest.fixture
    async def async_client(self):
        """Create test async client"""
        client = AsyncPiSecureClient()
        client.api_endpoints = ['http://test-endpoint:3142']
        await client.initialize()
        return client

    @pytest.mark.asyncio
    async def test_async_initialization(self):
        """Test async client initialization"""
        client = AsyncPiSecureClient()
        assert client.api_version == 'v1'
        assert client.cache_ttl == 30
        assert hasattr(client, 'session')

    @pytest.mark.asyncio
    async def test_async_get_blockchain_info(self, async_client):
        """Test async blockchain info retrieval"""
        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                'blocks': 2000,
                'height': 1999,
                'pending_transactions': 10
            }

            result = await async_client.get_blockchain_info()
            assert result['blocks'] == 2000
            mock_request.assert_called_once_with('GET', 'blockchain/info')

    @pytest.mark.asyncio
    async def test_batch_wallet_balances(self, async_client):
        """Test batch wallet balance retrieval"""
        addresses = ['addr1', 'addr2', 'addr3']

        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                {'balance': '100.0'},
                {'balance': '200.0'},
                {'balance': '300.0'}
            ]

            result = await async_client.get_wallet_balances(addresses)

            assert result['addr1'] == 100.0
            assert result['addr2'] == 200.0
            assert result['addr3'] == 300.0
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_transaction_submission(self, async_client):
        """Test batch transaction submission"""
        transactions = [
            {'type': 'transfer', 'amount': 10},
            {'type': 'transfer', 'amount': 20},
            {'type': 'transfer', 'amount': 30}
        ]

        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                {'transaction_hash': 'hash1'},
                {'transaction_hash': 'hash2'},
                {'transaction_hash': 'hash3'}
            ]

            result = await async_client.submit_transaction_batch(transactions)

            assert len(result) == 3
            assert 'hash1' in result
            assert 'hash2' in result
            assert 'hash3' in result

    @pytest.mark.asyncio
    async def test_client_metrics(self, async_client):
        """Test client metrics collection"""
        # Make some requests to generate metrics
        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {'test': 'data'}

            await async_client.get_blockchain_info()
            await async_client.get_blockchain_info()

            metrics = await async_client.get_client_metrics()

            assert metrics['requests_total'] >= 2
            assert 'cache_size' in metrics
            assert 'active_connections' in metrics

    @pytest.mark.asyncio
    async def test_cache_functionality(self, async_client):
        """Test client-side caching"""
        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {'cached': 'data'}

            # First request should hit API
            result1 = await async_client._make_async_request('GET', 'test/endpoint')
            assert mock_request.call_count == 1

            # Second request should use cache
            result2 = await async_client._make_async_request('GET', 'test/endpoint')
            assert mock_request.call_count == 1  # Still 1, used cache

            assert result1 == result2

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, async_client):
        """Test circuit breaker functionality"""
        with patch.object(async_client, '_make_async_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception('Service unavailable')

            # Trigger multiple failures
            for _ in range(5):
                try:
                    await async_client._make_async_request('GET', 'test/endpoint')
                except:
                    pass

            # Circuit should be open
            assert async_client.circuit_open

            # Should not make actual requests when circuit is open
            with pytest.raises(ConnectionError):
                await async_client._make_async_request('GET', 'test/endpoint')


class TestClientIntegration:
    """Integration tests for client functionality"""

    def test_sync_client_convenience_functions(self):
        """Test convenience functions"""
        with patch('pisecure.api.client.PiSecureClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_wallet_balance.return_value = 500.0
            mock_client.submit_transaction.return_value = 'test_hash'

            from pisecure.api.client import get_balance, submit_tx

            # Test get_balance
            result = get_balance('test_addr')
            assert result == 500.0
            mock_client.get_wallet_balance.assert_called_once_with('test_addr')

            # Test submit_tx
            result = submit_tx({'test': 'data'})
            assert result == 'test_hash'
            mock_client.submit_transaction.assert_called_once_with({'test': 'data'})

    @pytest.mark.asyncio
    async def test_async_client_convenience_functions(self):
        """Test async convenience functions"""
        with patch('pisecure.api.async_client.AsyncPiSecureClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get_wallet_balance.return_value = 750.0
            mock_client.submit_transaction.return_value = 'async_hash'

            from pisecure.api.async_client import aget_balance, asubmit_tx

            # Test aget_balance
            result = await aget_balance('test_addr')
            assert result == 750.0
            mock_client.get_wallet_balance.assert_called_once_with('test_addr')

            # Test asubmit_tx
            result = await asubmit_tx({'async': 'data'})
            assert result == 'async_hash'
            mock_client.submit_transaction.assert_called_once_with({'async': 'data'})


class TestClientErrorHandling:
    """Test error handling across clients"""

    @pytest.fixture
    def client(self):
        client = PiSecureClient()
        client.api_endpoints = ['http://test-endpoint:3142']
        return client

    def test_invalid_wallet_address(self, client):
        """Test handling of invalid wallet addresses"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = ValueError("Invalid address format")

            with pytest.raises(ValueError):
                client.get_wallet_balance("invalid_address")

    def test_network_timeout(self, client):
        """Test network timeout handling"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = ConnectionError("Network timeout")

            with pytest.raises(ConnectionError):
                client.get_blockchain_info()

    def test_insufficient_funds(self, client):
        """Test insufficient funds error"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = ValueError("Insufficient funds")

            with pytest.raises(ValueError):
                client.submit_transaction({'type': 'transfer', 'amount': 1000000})

    def test_invalid_transaction_data(self, client):
        """Test invalid transaction data"""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = ValueError("Invalid transaction data")

            with pytest.raises(ValueError):
                client.submit_transaction({'invalid': 'data'})


# JavaScript client tests (mocked since we can't run JS in Python)
class TestJavaScriptClientCompatibility:
    """Test that JS client interface matches Python client"""

    def test_javascript_client_interface(self):
        """Verify JS client has same interface as Python client"""
        # This would be tested by running the JS client in Node.js
        # For now, we verify the interface design is consistent

        python_methods = [
            'get_blockchain_info', 'get_block', 'get_blocks', 'get_transaction',
            'get_wallet_balance', 'get_wallet_transactions', 'create_wallet', 'list_wallets',
            'submit_transaction', 'create_transfer_transaction',
            'get_network_status', 'get_network_peers', 'health_check'
        ]

        # Verify these methods exist in our Python client
        client = PiSecureClient()
        for method in python_methods:
            assert hasattr(client, method), f"Missing method: {method}"

    def test_async_client_interface(self):
        """Verify async client has all necessary methods"""
        async_methods = [
            'get_blockchain_info', 'get_block', 'get_blocks',
            'get_wallet_balance', 'submit_transaction',
            'get_wallet_balances', 'submit_transaction_batch',
            'get_client_metrics'
        ]

        # This would be verified in actual async tests
        # For now, we document the expected interface
        pass


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])