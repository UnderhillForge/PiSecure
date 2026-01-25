# WebSocket P2P Quick Reference

## Quick Start

### Enable WebSocket P2P
```bash
# Via environment variable
export PISECURE_WEBSOCKET_P2P=1
pisecure mine

# Via CLI
pisecure network --enable
# (Requires restart)
```

### Check Status
```bash
# View P2P statistics
pisecure status --p2p

# Shows:
# - Connected peers: 25/30
# - WebSocket enabled: yes
# - Block propagation time: 145ms avg
# - Duplicates dropped: 456
# - HTTP fallback rate: 0.5%
```

## For Developers

### Using WebSocket P2P in Code

```python
from pisecure.core import SignChain
from pisecure.network.discovery import PeerDiscovery
from pisecure.core.p2p_sync import P2PSyncManager

# Initialize blockchain and discovery
blockchain = SignChain()
discovery = PeerDiscovery()

# Create P2P sync manager (WebSocket auto-enabled if env var set)
sync_manager = P2PSyncManager(blockchain, discovery)

# Start synchronization
sync_manager.start_sync()

# Get statistics
stats = sync_manager.get_p2p_statistics()
print(f"Connected peers: {stats['websocket_stats']['connected_peers']}")
print(f"Messages received: {stats['websocket_stats']['messages_received']}")
print(f"Avg propagation time: {stats['propagation_stats']['propagation_time_avg']:.1f}ms")

# Stop sync when done
sync_manager.stop_sync()
```

### Directly Using WebSocket P2P Client

```python
from pisecure.core.websocket_p2p_client import WebSocketP2PClient

# Create client
client = WebSocketP2PClient(
    node_id='my-node-1',
    listen_port=3142,
    max_peers=30
)

# Register message handler
def handle_block(message):
    print(f"Received block: {message['data']['hash']}")

client.register_handler('block_announcement', handle_block)

# Send message (tries WebSocket, falls back to HTTP)
sync_manager._send_to_peer(
    peer_id='peer-2',
    message={
        'type': 'block_announcement',
        'data': {'hash': 'abc123', 'height': 100}
    }
)

# Get statistics
stats = client.get_statistics()
print(f"Connected: {stats['connected_peers']}/{stats['total_peers']}")
```

## Configuration Options

### Environment Variables
```bash
# Enable/disable WebSocket P2P
PISECURE_WEBSOCKET_P2P=1

# Maximum peers to connect to
PISECURE_WS_MAX_PEERS=30

# WebSocket listen port
PISECURE_WS_PORT=3142

# Enable HTTP fallback (always 1)
PISECURE_WS_FALLBACK_HTTP=1

# Bloom filter size for deduplication
PISECURE_WS_BLOOM_SIZE=1000

# Message TTL in deduplication (seconds)
PISECURE_WS_MESSAGE_TTL=300

# Rate limit (messages per second per peer)
PISECURE_WS_RATE_LIMIT=100

# Connection recycle interval (seconds)
PISECURE_WS_RECYCLE_INTERVAL=86400  # 24 hours

# Enable debug logging
PISECURE_LOG_LEVEL=DEBUG
```

## Monitoring

### Real-Time Statistics
```python
from pisecure.core.p2p_sync import P2PSyncManager

stats = sync_manager.get_p2p_statistics()

# WebSocket stats
ws_stats = stats['websocket_stats']
print(f"Connected peers: {ws_stats['connected_peers']}")
print(f"Total peers: {ws_stats['total_peers']}")
print(f"Messages sent: {ws_stats['messages_sent']}")
print(f"Messages received: {ws_stats['messages_received']}")
print(f"Duplicates dropped: {ws_stats['duplicates_dropped']}")
print(f"Rate limited drops: {ws_stats['rate_limited_drops']}")
print(f"Connection errors: {ws_stats['connection_errors']}")

# Propagation stats
prop_stats = stats['propagation_stats']
print(f"Blocks propagated: {prop_stats['blocks_propagated']}")
print(f"Avg propagation time: {prop_stats['propagation_time_avg']:.1f}ms")
print(f"Failed propagations: {prop_stats['failed_propagations']}")

# Sync stats
sync_stats = stats['sync_stats']
print(f"Blocks synced: {sync_stats['blocks_synced']}")
print(f"Sync errors: {sync_stats['sync_errors']}")
```

### Log Analysis
```bash
# Enable debug logging
export PISECURE_LOG_LEVEL=DEBUG
pisecure mine

# View logs
tail -f ~/.pisecure/logs/pisecure.log | grep WebSocket

# Monitor specific events
tail -f ~/.pisecure/logs/pisecure.log | grep -E "Sending to|WebSocket|HTTP send"
```

## Troubleshooting

### Check if WebSocket P2P is Enabled
```bash
# Method 1: Check environment
echo $PISECURE_WEBSOCKET_P2P
# Output: 1 (enabled) or 0 (disabled)

# Method 2: Check via CLI
pisecure network
# Output: WebSocket P2P: enabled

# Method 3: Check statistics
pisecure status --p2p | grep "WebSocket enabled"
```

### Test Connection to Peer
```python
from pisecure.core.websocket_p2p_client import WebSocketP2PClient

client = WebSocketP2PClient(node_id='test-node')

# Try to connect to a peer
try:
    client.connect_to_peer(
        peer_id='peer-1',
        address='192.168.1.100',
        port=3142
    )
    print("Connected successfully")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Monitor Bandwidth Usage
```bash
# Watch network interface
watch -n 1 'ifstat -i eth0 1 1'

# Or use nethogs
sudo nethogs -p

# Expected: ~2GB/month per node (about 100 bytes/sec)
```

### Check Deduplication
```bash
# View deduplication statistics
pisecure status --p2p | grep -i duplicate

# Expected: <1% of messages are duplicates
# If higher: Check bloom filter size
```

## Common Issues & Solutions

### Issue: "WebSocket connections not working"
**Solution**:
```bash
# 1. Check if enabled
echo $PISECURE_WEBSOCKET_P2P

# 2. Check port is open
sudo netstat -tlnp | grep 3142

# 3. Check firewall
sudo ufw allow 3142

# 4. Enable debug logging
export PISECURE_LOG_LEVEL=DEBUG
pisecure mine
```

### Issue: "High CPU usage"
**Solution**:
```bash
# 1. Check if WebSocket P2P is causing it
export PISECURE_WEBSOCKET_P2P=0
pisecure mine  # Compare CPU

# 2. If still high: Reduce peer count
export PISECURE_WS_MAX_PEERS=10

# 3. Check for stuck connections
pisecure status --p2p | grep "Connected peers"
```

### Issue: "Connection errors in logs"
**Solution**:
```bash
# 1. Check if peers are reachable
ping peer-address

# 2. Check if ports are open
nc -zv peer-address 3142

# 3. Try disabling WebSocket (use HTTP fallback)
export PISECURE_WEBSOCKET_P2P=0

# 4. Check logs for specific error
grep "Connection error" ~/.pisecure/logs/pisecure.log
```

### Issue: "Memory usage growing"
**Solution**:
```bash
# 1. Check if connections are recycled
# Should recycle every 24 hours

# 2. Check deduplication cache size
export PISECURE_WS_BLOOM_SIZE=500  # Reduce from 1000

# 3. Monitor memory
watch -n 1 'free -h'

# 4. Check connection count
lsof -p $(pgrep -f "pisecure mine") | grep TCP | wc -l
# Expected: ~30-60 connections
```

## Performance Baseline

### Expected Performance (Single Node)
- Connected peers: 20-30
- Block propagation: 50-150ms
- Bandwidth: 2-5 MB/day (2-5 GB/month)
- CPU overhead: +5%
- Memory overhead: +50MB

### Network-Wide Performance (10,000 nodes)
- Avg propagation time: 150-200ms
- Total bandwidth: 20-50 TB/month network-wide
- Per-node bandwidth: 2-5 GB/month
- Total connections: ~250,000
- Total RAM: 3.75 GB network-wide

## Advanced Configuration

### Custom Bloom Filter Size
```python
from pisecure.core.websocket_p2p_client import MessageDeduplicator

# Larger filter = fewer duplicates, more memory
dedup = MessageDeduplicator(max_size=2000)  # Default 1000
```

### Custom Rate Limits
```python
from pisecure.core.websocket_p2p_client import PeerConnection

peer = PeerConnection(peer_id='peer-1', address='192.168.1.10', port=3142)

# Check rate limiting
if peer.is_rate_limited(max_per_second=50):  # Custom limit
    print("Peer rate limited")
```

### Enable Message Compression (Future)
```bash
# Not yet implemented, placeholder for Phase 2
export PISECURE_WS_COMPRESSION=gzip
```

## Resources

- [Full Documentation](./PHASE1_WEBSOCKET_P2P_IMPLEMENTATION.md)
- [WebSocket P2P Client Code](./pisecure/core/websocket_p2p_client.py)
- [P2P Sync Manager Code](./pisecure/core/p2p_sync.py)
- [CLI Commands](./pisecure/cli.py)

## Support

For issues:
1. Check this troubleshooting guide
2. Enable debug logging: `export PISECURE_LOG_LEVEL=DEBUG`
3. Collect statistics: `pisecure status --p2p`
4. File issue with logs and configuration

---

**Last Updated**: 2024  
**Phase**: 1 (Hybrid WebSocket + HTTP Fallback)  
**Status**: Production Ready (Testnet first)
