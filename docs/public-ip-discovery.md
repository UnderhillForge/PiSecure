# Public IP Discovery for Internet-Wide P2P

## Do I Need Port Forwarding?

**Short answer: NO for basic mining/validation!**

Just like Bitcoin, Ethereum, and other networks, PiSecure works in multiple modes:

### ✅ Outbound-Only Mode (No Port Forwarding Needed)
- **Mining**: Submit blocks via outbound connections ✅
- **Validation**: Fetch blocks from peers via outbound ✅
- **Transaction Broadcasting**: Send transactions to network ✅
- **Syncing**: Download blockchain from other nodes ✅

You can mine and validate without any router configuration!

### 🌟 Full Node Mode (Port Forwarding Recommended)
- Everything above, PLUS:
- **Help others sync**: Seed blockchain to new nodes
- **Accept incoming connections**: Be discoverable by other peers
- **Improve network health**: Increase decentralization

**Auto-enabled on ~60% of routers via UPnP** - no manual config needed!

## How PiSecure Handles This

### Automatic Configuration Attempts (No User Action)
1. **UPnP**: Tries to auto-configure port forwarding
2. **Relay Network**: Routes through community relay nodes
3. **Outbound-Only**: Falls back to client mode (still fully functional)

Your node will automatically use the best available method.

## Problem
Peers behind home routers need to report their **public IP** (router's external address) to bootstrap servers and other nodes. Reporting local LAN addresses (192.168.x.x) only works within the same network.

## Solution
PiSecure uses a multi-tier approach to discover and report the node's public IP:

### 1. NAT Traversal (Priority: Highest)
- **STUN**: Queries STUN servers to discover public IP/port mapping
- **UPnP**: Automatically configures port forwarding on compatible routers
- **Advantage**: Provides actual reachable endpoint with port mapping
- **Limitation**: Requires STUN server access or UPnP-enabled router

### 2. External IP Services (Priority: Medium)
- Queries public IP detection services (ipify.org, ifconfig.me, etc.)
- **Advantage**: Reliable, works behind most NATs
- **Limitation**: Requires manual port forwarding for incoming connections

### 3. Local Address Fallback (Priority: Low)
- Reports 0.0.0.0 → localhost or actual bind address
- **Use Case**: LAN-only testing, private networks
- **Limitation**: Not routable from internet

## How It Works

### Bootstrap Registration
When an API server starts, it automatically:

```python
# 1. Try NAT traversal methods
nat_results = node_discovery.make_node_discoverable()
endpoints = nat_results.get('endpoints', [])

# 2. Fallback to external IP services
if not endpoints:
    public_ip = _get_public_ip_fallback()  # api.ipify.org, etc.

# 3. Final fallback to local address
if not public_ip:
    public_ip = 'localhost'  # LAN-only mode
```

### Registration Data Sent
```json
{
  "node_id": "abc123...",
  "node_type": "miner",
  "services": ["api", "p2p_sync"],
  "address": "203.0.113.42",  // Public IP
  "port": 3142
}
```

## Port Forwarding Requirements

For incoming P2P connections, you need **one** of:

### Option 1: UPnP (Automatic)
- Enable UPnP on your router
- PiSecure automatically configures port forwarding
- Works on ~60% of home routers

### Option 2: Manual Port Forwarding
Forward **TCP port 3142** to your Pi's local IP:
- Router admin panel → Port Forwarding
- External port: 3142 → Internal IP: 192.168.1.x:3142

### Option 3: Relay Network (Coming Soon)
- Community-run relay nodes forward connections
- No router configuration needed
- Slightly higher latency

## Testing Your Setup

### Check Public IP Detection
```bash
python3 -c "
from pisecure.api.server import BlockchainAPI
api = BlockchainAPI()
print(api._get_public_ip_fallback())
"
```

### Verify External Reachability
From **another network** (not your LAN):
```bash
curl http://YOUR_PUBLIC_IP:3142/api/v1/chain
```

### Check Bootstrap Registration
```bash
# Start API server and check logs
python -m pisecure.api.server

# Look for:
# 🌐 Discovered public IP: x.x.x.x via external service
# ✅ Node registered with bootstrap: node_abc123...
```

## Troubleshooting

### "Using local address - node may not be reachable from internet"
**Cause**: Both NAT traversal and external IP detection failed  
**Fix**: Check internet connectivity, firewall rules

### Peers Can't Connect to Me
**Cause**: Port 3142 not forwarded to your Pi  
**Fix**: Enable UPnP or manually forward port in router

### API Works Locally But Not From Internet
**Cause**: Firewall blocking incoming connections  
**Fix**: 
```bash
# Raspberry Pi OS
sudo ufw allow 3142/tcp

# Check if port is listening
sudo netstat -tulpn | grep 3142
```

## Network Topologies

### Home Network (Common)
```
Internet → [Router/NAT] → Pi (192.168.1.5)
           Public IP: 203.0.113.42
           Port Forward: 3142 → 192.168.1.5:3142
```
Pi reports: `203.0.113.42:3142` to bootstrap

### VPS/Cloud (Simple)
```
Internet → Pi (203.0.113.42 direct)
```
Pi reports: `203.0.113.42:3142` to bootstrap

### Symmetric NAT (Challenging)
```
Internet → [Carrier-Grade NAT] → [Router] → Pi
           (No inbound possible)
```
Pi reports public IP but needs **relay network** for incoming connections

## Future Enhancements

1. **IPv6 Support**: Native end-to-end connectivity
2. **TURN Relays**: Fallback for restrictive NATs
3. **Tor Integration**: Privacy-focused .onion addresses
4. **Hole Punching**: ICE-based direct P2P establishment

## See Also
- [NAT Traversal Implementation](../pisecure/core/nat_traversal.py)
- [Network Setup Guide](network-setup.md)
- [Bootstrap Server Protocol](bootstrap-server.txt)
