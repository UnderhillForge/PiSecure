# WebSocket Integration - Quick Start

The bootstrap team has implemented WebSocket support for real-time communication. PiSecure now includes full WebSocket client integration via CLI commands.

## Installation

WebSocket support requires the `python-socketio` package:

```bash
pip install python-socketio
```

If not installed, WebSocket will automatically fall back to HTTP polling with no errors.

## Available Commands

### 1. Listen to Real-Time Events

```bash
# Listen to node registration events
pisecure ws listen --node-id my-node-001 --subscribe nodes

# Listen to multiple channels
pisecure ws listen --node-id my-node-001 --subscribe nodes --subscribe threats --subscribe health

# Available channels: nodes, threats, health, dex, rates
pisecure ws listen --help
```

**Events you'll receive:**
- `node_registered` - New node joined network
- `node_offline` - Node went offline
- `node_heartbeat` - Node heartbeat with metrics
- `threat_detected` - Security threat alert
- `health_update` - Network health metrics
- `pool_updated` - DEX pool changes
- `quota_reset` - Rate limit quota reset

### 2. Send Heartbeat

```bash
# Send heartbeat with default metrics
pisecure ws heartbeat --node-id my-node-001

# Send heartbeat with custom metrics
pisecure ws heartbeat \
  --node-id my-node-001 \
  --cpu 45.2 \
  --memory 512 \
  --uptime 86400 \
  --hashrate 500.5
```

### 3. Report Threat

```bash
# Report DDoS attack
pisecure ws threat \
  --node-id my-node-001 \
  --threat-type ddos_attack \
  --severity high \
  --source "10.0.0.0/8" \
  --details "50k requests/sec detected"

# Report suspicious node
pisecure ws threat \
  --node-id my-node-001 \
  --threat-type suspicious_node \
  --severity medium
```

### 4. Check Connection Status

```bash
# Show WebSocket statistics
pisecure ws stats --node-id my-node-001
```

## Architecture

### Namespaces

| Namespace | Purpose | Key Events |
|-----------|---------|-----------|
| `/nodes` | Node management | node_registered, node_offline, node_heartbeat |
| `/threats` | Security alerts | threat_detected, threat_escalated, defense_activated |
| `/health` | Network metrics | health_update, consensus_status |
| `/dex` | Trading updates | pool_updated, trade_executed |
| `/rates` | Rate limits | rate_limit_status, quota_reset |

### Benefits Over HTTP Polling

| Metric | HTTP Polling | WebSocket |
|--------|------------|-----------|
| Latency | 2.5-5 seconds | 50ms |
| Bandwidth per node | 86.4 MB/day | 21.9 KB/day |
| Server processes | 4 workers | 1 worker |
| Response time | 5 seconds | 100ms |

### Automatic Fallback

If `python-socketio` is not installed or WebSocket connection fails:
1. Client automatically falls back to HTTP polling (5-second intervals)
2. No user intervention required
3. All commands work transparently with HTTP

## Features

✅ **5 Real-Time Namespaces** - Nodes, threats, health, DEX, rates  
✅ **Authentication** - Node ID-based with reputation checks  
✅ **Automatic Reconnection** - Exponential backoff on disconnect  
✅ **HTTP Fallback** - Works without WebSocket library  
✅ **Rate Limiting** - Built-in quota management  
✅ **Error Handling** - Graceful error recovery  

## Example: Monitor Network in Real-Time

```bash
# Terminal 1: Listen for threats
pisecure --testnet ws listen --node-id monitor-001 --subscribe threats

# Terminal 2: Send a test threat
pisecure --testnet ws threat \
  --node-id test-node \
  --threat-type ddos_attack \
  --severity critical
```

## Integration with Mining

The WebSocket client will automatically:
1. Send heartbeats every 30 seconds during mining
2. Report threats detected during operation
3. Subscribe to rate limit updates
4. Monitor network health

For future integration, the bootstrap server provides:
- Real-time peer discovery
- Immediate threat response coordination
- Network consensus status
- DEX liquidity updates
- 314ST token metrics

## API Reference

See [WEBSOCKET_SPECIFICATION.md](WEBSOCKET_SPECIFICATION.md) for complete API details including:
- Message schemas
- Authentication protocols
- Error codes
- Rate limiting
- JavaScript/Python examples
