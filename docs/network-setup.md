# PiSecure Network Setup Guide

This guide explains how PiSecure nodes discover each other and synchronize the blockchain using a hybrid GitHub bootstrap + decentralized P2P approach.

## Network Architecture Overview

PiSecure uses a **hybrid bootstrapping strategy**:

1. **GitHub Bootstrap**: Initial trusted blockchain state from GitHub repository
2. **Decentralized P2P**: Ongoing peer discovery and network participation

```
New Node                    GitHub Repo                   P2P Network
    |                            |                            |
    |---- Download Genesis ----->|                            |
    |<--- Genesis Block ---------|                            |
    |                            |                            |
    |---- Download Config ------->|                            |
    |<--- Network Config ---------|                            |
    |                            |                            |
    |------- Initialize ----------|                            |
    |                            |                            |
    |------ Discover Peers ------┐                            |
    |                            |---- mDNS Local Network ---->|
    |                            |<--- Local Peers -----------|
    |                            |                            |
    |                            |----- DHT Global ----------┐ |
    |                            |<---- Global Peers --------┘ |
    |                            |                            |
    |----- Connect to Peers ---->|                            |
    |<---- Version Handshake ----|                            |
    |                            |                            |
    |--- Request Blockchain ----->|                            |
    |<--- Block Synchronization --|                            |
    |                            |                            |
    |------ Network Ready -------┘                            |
```

## Bootstrap Process

### Step 1: GitHub Bootstrap

New nodes start by downloading the canonical blockchain state from GitHub:

```bash
# Automatic bootstrap
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/network/bootstrap.sh | bash

# Or manual process
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure
cp blockchain/genesis.json /var/lib/pisecure/
cp network/config.json /etc/pisecure/
```

**What gets downloaded:**
- **Genesis block**: Official blockchain starting point
- **Network configuration**: Peer discovery settings, consensus rules
- **Integrity checksums**: Verification of downloaded files

### Step 2: Local Initialization

```bash
# Initialize node identity
pisecure init-identity --auto

# Create initial wallet
pisecure create-wallet "default_wallet"

# Load genesis blockchain
pisecure load-genesis /var/lib/pisecure/genesis.json
```

### Step 3: Decentralized Peer Discovery

Once bootstrapped, nodes discover peers through multiple methods:

#### mDNS Local Network Discovery
```python
# Automatic local network discovery
mdns = MDNSDiscovery()
local_peers = await mdns.discover_peers(timeout=30)

# Discovers peers on same LAN
# Example: ["192.168.1.100:3141", "192.168.1.101:3141"]
```

#### DHT Global Discovery
```python
# Distributed Hash Table discovery
dht = DHTDiscovery()
global_peers = await dht.discover_peers(timeout=30)

# Discovers peers worldwide via DHT network
# Uses BitTorrent DHT infrastructure
```

#### IPFS PubSub Channels
```python
# IPFS-based peer announcements
ipfs = IPFSPubSubDiscovery()
pubsub_peers = await ipfs.discover_peers(timeout=30)

# Subscribes to PiSecure peer announcement channels
# Decentralized via IPFS network
```

### Step 4: Network Connection

```bash
# Connect to discovered peers
pisecure connect-to-network

# Check connection status
pisecure network-status
```

### Step 5: Blockchain Synchronization

```bash
# Synchronize blockchain with network
pisecure sync-chain

# Monitor sync progress
pisecure sync-status
```

## Peer Discovery Methods

### 1. mDNS (Local Network)

**Best for:** Local network discovery, home/office setups

```bash
# Service announcement (automatic)
# Node advertises: _pisecure._tcp.local.

# Peer discovery (automatic)
# Browses for: _pisecure._tcp.local.
```

**Advantages:**
- Zero configuration
- Works on isolated networks
- Fast discovery (< 1 second)

**Limitations:**
- Local network only
- Requires multicast support

### 2. DHT (Global Network)

**Best for:** Internet-wide discovery, production deployments

```python
# Uses BitTorrent DHT infrastructure
infohash = generate_infohash("PiSecure Mainnet")
peers = dht.get_peers(infohash)
```

**Advantages:**
- Global peer discovery
- No central coordination
- Resistant to censorship

**Limitations:**
- Slower discovery (5-30 seconds)
- Dependent on DHT network health

### 3. IPFS PubSub (Decentralized)

**Best for:** Modern decentralized applications

```python
# Subscribe to peer channels
ipfs.pubsub.sub("pisecure/peers")

# Publish node announcements
ipfs.pubsub.pub("pisecure/peers", node_info)
```

**Advantages:**
- Fully decentralized
- Rich metadata support
- Works with IPFS ecosystem

**Limitations:**
- Requires IPFS node
- Higher resource usage

## Network Messages

### Version Handshake
```json
{
  "type": "version",
  "version": "0.1.0",
  "protocol_version": 1,
  "node_id": "abc123...",
  "capabilities": ["mining", "validation"],
  "best_height": 1234,
  "timestamp": 1735680000
}
```

### Block Synchronization
```json
{
  "type": "getblocks",
  "start_hash": "genesis_hash",
  "count": 500,
  "timestamp": 1735680000
}
```

### Transaction Propagation
```json
{
  "type": "tx",
  "transaction": {
    "type": "token_transfer",
    "sender_address": "wallet_addr",
    "recipient_address": "recipient_addr",
    "amount": 100,
    "signature": "sig..."
  },
  "timestamp": 1735680000
}
```

## Network Health Monitoring

### Connection Metrics
```bash
# View connected peers
pisecure list-peers

# Network statistics
pisecure network-stats

# Connection health
pisecure peer-health
```

### Sync Status
```bash
# Blockchain sync progress
pisecure sync-status

# Headers vs blocks
Headers: 12500/12500 (100%)
Blocks:  12480/12500 (99.8%)

# Estimated time to completion
ETA: 2 minutes
```

## Troubleshooting

### Bootstrap Issues

**Problem:** Genesis download fails
```
curl: (6) Could not resolve host: raw.githubusercontent.com
```

**Solution:**
```bash
# Check internet connectivity
ping -c 3 raw.githubusercontent.com

# Use alternative mirror
export PISECURE_BOOTSTRAP_MIRROR="https://github.com/UnderhillForge/PiSecure/archive/main.tar.gz"
```

### Peer Discovery Issues

**Problem:** No peers found
```
Discovered 0 peers
```

**Solutions:**
```bash
# Check local network
pisecure discover-mdns

# Check internet connectivity
pisecure test-connectivity

# Force specific peer
pisecure add-peer known-peer.example.com:3141
```

### Sync Issues

**Problem:** Blockchain sync stuck
```
Blocks: 100/12500 (0.8%)
No progress for 10 minutes
```

**Solutions:**
```bash
# Check peer connections
pisecure list-peers

# Try different peers
pisecure reconnect-peers

# Reset sync state
pisecure reset-sync
```

## Security Considerations

### Peer Authentication
- All connections use TLS 1.3
- Certificate verification required
- Node identity validation

### Sybil Attack Prevention
- Proof-of-work mining requirements
- Stake-based reputation system
- Geographic distribution validation

### Eclipse Attack Mitigation
- Multi-peer connections required
- Diverse peer selection algorithms
- Regular peer rotation

## Advanced Configuration

### Custom Bootstrap
```json
{
  "bootstrap": {
    "custom_genesis_url": "https://your-domain.com/genesis.json",
    "custom_config_url": "https://your-domain.com/config.json",
    "verify_signatures": true
  }
}
```

### Peer Preferences
```json
{
  "peers": {
    "preferred_regions": ["us-east", "eu-west"],
    "min_latency": 50,
    "max_hops": 3
  }
}
```

### Discovery Customization
```json
{
  "discovery": {
    "methods": ["mdns", "dht"],
    "mdns_timeout": 10,
    "dht_timeout": 20,
    "custom_bootstrap_peers": ["your-seed-node.com:3141"]
  }
}
```

## Network Evolution

### Phase 1: GitHub Bootstrap (Now)
- Trusted initial state
- Centralized bootstrap
- Decentralized operation

### Phase 2: DHT Dominant (Q1 2025)
- DHT as primary discovery
- GitHub as fallback
- Improved resilience

### Phase 3: Full Decentralization (Q2 2025)
- No external dependencies
- Pure P2P operation
- Maximum resilience

This hybrid approach ensures **trustworthy initialization** while enabling **fully decentralized operation** for the PiSecure network.