#!/usr/bin/env python3
"""
Debug bootstrap connectivity and mempool endpoint.
"""

import sys
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 70)
print("🔍 Bootstrap Connectivity Debug")
print("=" * 70)

bootstrap_url = "https://bootstrap.pisecure.org"

# Test 1: Direct HTTPS connection
print("\n1️⃣  Testing direct HTTPS connection to bootstrap...")
try:
    response = requests.get(f"{bootstrap_url}/api/v1/mempool?network=testnet", timeout=10)
    print(f"✅ Status: {response.status_code}")
    data = response.json()
    print(f"✅ Response:")
    print(f"   - Network: {data.get('network')}")
    print(f"   - Pending: {len(data.get('pending', []))} transactions")
    print(f"   - Timestamp: {data.get('timestamp')}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Check peers endpoint
print("\n2️⃣  Testing bootstrap peers endpoint...")
try:
    response = requests.get(f"{bootstrap_url}/api/v1/bootstrap/peers", timeout=10)
    print(f"✅ Status: {response.status_code}")
    data = response.json()
    peers = data.get('peers', [])
    print(f"✅ Response has {len(peers)} peers:")
    for peer in peers[:3]:
        print(f"   - {peer.get('address')}:{peer.get('port')} (status: {peer.get('status')})")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 3: Python client discovery
print("\n3️⃣  Testing PiSecureClient peer discovery...")
try:
    from pisecure.api.client import PiSecureClient
    client = PiSecureClient()
    print(f"✅ Client created")
    print(f"   - Bootstrap URLs: {client.bootstrap_endpoints}")
    print(f"   - Discovered API endpoints: {client.api_endpoints}")
    
    if "bootstrap.pisecure.org" in str(client.bootstrap_endpoints):
        print("✅ Bootstrap is in endpoints list")
    else:
        print("⚠️  Bootstrap is NOT in discovered endpoints")
        
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Try calling mempool via bootstrap directly with requests
print("\n4️⃣  Testing mempool fetch with direct requests...")
try:
    response = requests.get(
        "https://bootstrap.pisecure.org/api/v1/mempool",
        params={"network": "testnet"},
        timeout=10
    )
    data = response.json()
    print(f"✅ Got mempool: {len(data.get('pending', []))} pending txs")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "=" * 70)
