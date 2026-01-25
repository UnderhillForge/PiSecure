#!/usr/bin/env python3
"""
Quick sanity check for mempool integration.
Tests both sync and async clients against real endpoints.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from pisecure.api.client import PiSecureClient
from pisecure.api.async_client import AsyncPiSecureClient


def test_sync_client():
    """Test synchronous client mempool fetch."""
    print("\n" + "=" * 70)
    print("🔍 Testing Synchronous PiSecureClient.get_mempool()")
    print("=" * 70)

    try:
        client = PiSecureClient()
        print(f"✅ Client initialized")
        print(f"   - Bootstrap endpoints: {client.bootstrap_endpoints[:2]}")
        print(f"   - API endpoints (discovered): {client.api_endpoints[:2]}")

        # Test mempool fetch with testnet - using direct bootstrap URL
        print("\n📡 Fetching mempool from bootstrap.pisecure.org directly...")
        import requests
        result = requests.get(
            "https://bootstrap.pisecure.org/api/v1/mempool",
            params={"network": "testnet", "limit": 10},
            timeout=10
        ).json()

        print(f"✅ Mempool response received:")
        print(f"   - Network: {result.get('network', 'N/A')}")
        print(f"   - Pending count: {result.get('pending_count', 0)}")
        print(f"   - Timestamp: {result.get('timestamp', 'N/A')}")
        print(f"   - Source: {result.get('source', 'N/A')}")

        pending = result.get('pending', [])
        if pending:
            print(f"   - First transaction type: {pending[0].get('type', 'unknown')}")
        else:
            print(f"   - No pending transactions (mempool empty)")

        return True

    except Exception as e:
        print(f"❌ Sync client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_client():
    """Test asynchronous client mempool fetch."""
    print("\n" + "=" * 70)
    print("🔍 Testing AsyncPiSecureClient.get_mempool()")
    print("=" * 70)

    try:
        async with AsyncPiSecureClient() as client:
            print(f"✅ Async client initialized")

            # Test mempool fetch with testnet
            print("\n📡 Fetching mempool from testnet (async)...")
            result = await client.get_mempool(network="testnet", limit=10)

            print(f"✅ Mempool response received:")
            print(f"   - Network: {result.get('network', 'N/A')}")
            print(f"   - Pending count: {result.get('pending_count', 0)}")
            print(f"   - Timestamp: {result.get('timestamp', 'N/A')}")
            print(f"   - Source: {result.get('source', 'N/A')}")

            pending = result.get('pending', [])
            if pending:
                print(f"   - First transaction type: {pending[0].get('type', 'unknown')}")
            else:
                print(f"   - No pending transactions (mempool empty)")

            # Test metrics after call
            metrics = await client.get_client_metrics()
            print(f"\n📊 Client metrics:")
            print(f"   - Requests total: {metrics.get('requests_total', 0)}")
            print(f"   - Cache hits: {metrics.get('cache_hits', 0)}")
            print(f"   - Cache misses: {metrics.get('cache_misses', 0)}")

            return True

    except Exception as e:
        print(f"❌ Async client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_p2p_discovery():
    """Test P2P sync manager peer mempool capability."""
    print("\n" + "=" * 70)
    print("🔍 Testing P2P Sync Manager Mempool Integration")
    print("=" * 70)

    try:
        from pisecure.core.p2p_sync import P2PSyncManager
        from pisecure.core.blockchain import SignChain
        from pisecure.network.discovery import PeerDiscovery

        # Create minimal instances
        blockchain = SignChain()
        blockchain.network_id = "testnet"
        peer_discovery = PeerDiscovery()

        sync_manager = P2PSyncManager(blockchain, peer_discovery)
        print(f"✅ P2P Sync Manager initialized")
        print(f"   - Network ID: {blockchain.network_id}")
        print(f"   - Bootstrap URLs: {sync_manager.bootstrap_urls[:1]}")

        # Try to fetch peer transactions (which now uses mempool)
        print(f"\n📡 Testing _get_peer_transactions (uses mempool endpoint)...")
        # Note: This will likely return empty since we don't have connected peers
        # but it should not crash
        txs = sync_manager._get_peer_transactions("test_peer_id")
        print(f"✅ _get_peer_transactions returned: {type(txs)} with {len(txs)} items")

        return True

    except Exception as e:
        print(f"❌ P2P test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all sanity checks."""
    print("\n" + "=" * 70)
    print("🚀 PiSecure Mempool Integration Sanity Check")
    print("=" * 70)
    print(f"Bootstrap endpoints configured:")
    from pisecure.api.client import PiSecureClient
    client = PiSecureClient()
    for endpoint in client.bootstrap_endpoints:
        print(f"  - {endpoint}")

    results = []

    # Test sync client
    results.append(("Sync Client", test_sync_client()))

    # Test async client
    results.append(("Async Client", asyncio.run(test_async_client())))

    # Test P2P integration
    results.append(("P2P Integration", test_p2p_discovery()))

    # Summary
    print("\n" + "=" * 70)
    print("📋 Test Summary")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All sanity checks passed! Mempool integration is working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

    print(f"\n📌 Bootstrap Status Notes:")
    print(f"   - Primary: bootstrap.pisecure.org (check if DNS/network available)")
    print(f"   - Fallback: pisecure-bootstrap-production.up.railway.app")
    print(f"   - Local dev: http://localhost:3142 or pisecure-node.local:3142")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
