# PiSecure Bootstrap Node Registration & Communication Specification

## 1. Node Registration Endpoint

### POST /api/v1/nodes/register

**Purpose:** Register a PiSecure node with the bootstrap coordinator

**URLs:**
- Production: `https://bootstrap.pisecure.org/api/v1/nodes/register`
- Testnet: `https://bootstrap-testnet.pisecure.org/api/v1/nodes/register`

---

## 2. Request Specification

### Complete Schema

```json
{
  "node_id": "string (required, 8-64 chars)",
  "node_type": "string (required, one of: miner|validator|sentinel_ai|relay)",
  "services": ["string array (optional)"],
  "location": "string (optional, geographic hint)",
  "wallet_address": "string (optional, for rewards)",
  "capabilities": ["string array (optional)"],
  "sentinel_config": "object (optional, sentinel_ai nodes only)",
  "network": "string (optional, mainnet|testnet, default: mainnet)"
}
```

### Field Descriptions

| Field | Type | Required | Constraints | Example |
|-------|------|----------|-------------|---------|
| `node_id` | string | ✅ YES | 8-64 alphanumeric + hyphens | `miner-rpi5-001` |
| `node_type` | string | ✅ YES | miner, validator, sentinel_ai, relay | `miner` |
| `services` | string[] | ❌ NO | List of services offered | `["mining", "p2p_sync"]` |
| `location` | string | ❌ NO | Geographic region | `us-east`, `eu-west`, `ap-south` |
| `wallet_address` | string | ❌ NO | For validator/miner rewards | `0x1234...abcd` |
| `capabilities` | string[] | ❌ NO | Node capabilities | `["bootstrap_coordination", "peer_discovery"]` |
| `sentinel_config` | object | ❌ NO | Config for sentinel_ai nodes | See schema below |
| `network` | string | ❌ NO | Network selection | `mainnet`, `testnet` |

### Node Types

```
miner:
  - Actively mining blocks
  - Submits entropy samples
  - Can provide liquidity to DEX
  - Earns block rewards

validator:
  - Validates blocks
  - Participates in consensus
  - Earns validation rewards (0.1x block reward)
  - Should have high uptime

sentinel_ai:
  - Monitors network threats
  - Reports anomalies
  - Coordinates defense
  - Gets reputation bonuses for threat detection

relay:
  - Relays messages between nodes
  - No mining/validation
  - Provides network resilience
  - Minimal resource requirements
```

### Sentinel Configuration Schema

```json
{
  "sentinel_config": {
    "monitoring_enabled": true,
    "threat_detection_level": "high|medium|low",
    "defense_coordination": true,
    "blockchain_monitoring": true,
    "max_alert_rate": 100,
    "alert_channels": ["internal", "webhook"],
    "webhook_url": "https://your-infrastructure.com/alerts"
  }
}
```

### Example Request

```bash
curl -X POST https://bootstrap.pisecure.org/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "miner-rpi5-001",
    "node_type": "miner",
    "services": ["mining", "p2p_sync"],
    "location": "us-east",
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
    "capabilities": ["mining", "entropy_submission"],
    "network": "mainnet"
  }'
```

---

## 3. Response Specification

### Success Response (HTTP 200)

```json
{
  "registration_success": true,
  "node_id": "miner-rpi5-001",
  "assigned_role": "miner",
  "registration_time": 1737475200.0,
  "network_info": {
    "bootstrap_coordinator": "bootstrap.pisecure.org",
    "federation_enabled": true,
    "intelligence_sharing": true,
    "consensus_version": "1.0"
  },
  "capabilities_acknowledged": ["mining", "entropy_submission"],
  "services_enabled": ["mining", "p2p_sync"],
  "network_permissions": ["mine_blocks", "submit_entropy", "query_peers"],
  "initial_reputation": 50.0,
  "heartbeat_interval": 300,
  "entropy_submission_required": true,
  "entropy_submission_deadline": 1737478800.0
}
```

### Sentinel_AI Success Response (HTTP 200)

```json
{
  "registration_success": true,
  "node_id": "sentinel-node-001",
  "assigned_role": "sentinel_ai",
  "network_permissions": ["monitor", "alert", "coordinate"],
  "registration_time": 1737475200.0,
  "network_info": {
    "bootstrap_coordinator": "bootstrap.pisecure.org",
    "federation_enabled": true,
    "intelligence_sharing": true
  },
  "sentinel_capabilities": {
    "threat_detection": true,
    "defense_coordination": true,
    "reputation_management": true,
    "blockchain_monitoring": true,
    "max_threats_per_hour": 1000
  },
  "capabilities_acknowledged": [...],
  "services_enabled": [...]
}
```

### Error Responses

#### Missing Required Field (HTTP 400)
```json
{
  "error": "node_id required",
  "error_code": "MISSING_REQUIRED_FIELD",
  "required_fields": ["node_id", "node_type"]
}
```

#### Invalid Node Type (HTTP 400)
```json
{
  "error": "Invalid node_type",
  "error_code": "INVALID_NODE_TYPE",
  "valid_types": ["miner", "validator", "sentinel_ai", "relay"],
  "received": "invalid_type"
}
```

#### Node Already Registered (HTTP 409)
```json
{
  "error": "Node already registered",
  "error_code": "NODE_ALREADY_REGISTERED",
  "existing_node_id": "miner-rpi5-001",
  "registered_at": 1737400000.0,
  "update_endpoint": "/api/v1/nodes/status"
}
```

#### Invalid Location (HTTP 400)
```json
{
  "error": "Invalid location",
  "error_code": "INVALID_LOCATION",
  "valid_locations": ["us-east", "us-west", "eu-west", "eu-central", "ap-south", "ap-northeast"],
  "received": "invalid-region"
}
```

#### Server Error (HTTP 500)
```json
{
  "error": "Registration failed",
  "error_code": "INTERNAL_ERROR",
  "timestamp": 1737475200.0
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Node successfully registered |
| 400 | Bad Request | Invalid data, missing fields |
| 409 | Conflict | Node ID already registered |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server-side validation/DB error |

---

## 4. Request Headers

**Required:**
```http
Content-Type: application/json
```

**Recommended:**
```http
User-Agent: PiSecure-Node/1.0 (NodeType; Hardware; OS)
X-Network: mainnet|testnet
```

**Optional (Future):**
```http
X-Node-Signature: <ECDSA signature of request body>
X-Node-Public-Key: <Hex-encoded public key>
X-Request-ID: <UUID for tracking>
```

---

## 5. Validation Rules

### Node ID Validation

```
Requirements:
  - 8-64 characters
  - Alphanumeric + hyphens only
  - Must be unique per network
  - Lowercase recommended
  - Pattern: ^[a-zA-Z0-9]([a-zA-Z0-9-]{6,62}[a-zA-Z0-9])?$

Valid Examples:
  - miner-rpi5-001
  - validator-node-42
  - sentinel-ai-monitor-1
  - relay-us-east-01

Invalid Examples:
  - miner (too short)
  - MINER_RPI5_001 (underscores not allowed)
  - miner.rpi5.001 (dots not allowed)
```

### Wallet Address Validation

```
Requirements:
  - Valid blockchain address format
  - 42 characters (0x + 40 hex chars) for EVM chains
  - Optional if not claiming rewards

Pattern: ^0x[a-fA-F0-9]{40}$
```

### Service List Validation

```
Valid Services:
  - mining
  - validation
  - p2p_sync
  - relay
  - node_discovery
  - dex_coordination
  - intelligence_sharing

Invalid: Services must be from predefined list
```

### Capability List Validation

```
Valid Capabilities:
  - bootstrap_coordination
  - peer_discovery
  - network_health_monitoring
  - federation_management
  - mining
  - entropy_submission
  - threat_detection
  - defense_coordination

Custom capabilities allowed but logged
```

---

## 6. Registration Workflow

### Phase 1: Initial Registration
```
1. Node sends registration request
2. Bootstrap validates fields
3. Node is added to node_tracker
4. Temporary reputation assigned (50.0)
5. Node receives registration confirmation
```

### Phase 2: Entropy Validation (for miners)
```
1. Miner receives entropy_submission_deadline
2. Miner must submit entropy within 1 hour
3. If deadline missed: node flagged as "pending_entropy"
4. Miner can still mine but with reduced reputation
```

### Phase 3: Status Updates (ongoing)
```
1. Node sends heartbeat every 300 seconds
2. Updates status, metrics, capabilities
3. Maintains active registration
4. After 600 seconds of no heartbeat: marked offline
```

---

## 7. Client Implementation Examples

### Python Implementation

```python
#!/usr/bin/env python3
import requests
import time

class PiSecureNodeRegistrar:
    def __init__(self, node_id, node_type, bootstrap_url="https://bootstrap.pisecure.org"):
        self.node_id = node_id
        self.node_type = node_type
        self.bootstrap_url = bootstrap_url
        self.session = requests.Session()
    
    def register(self, location="us-east", wallet_address=None, network="mainnet"):
        """Register node with bootstrap"""
        
        payload = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "location": location,
            "network": network,
            "services": self._get_services(),
            "capabilities": self._get_capabilities()
        }
        
        if wallet_address:
            payload["wallet_address"] = wallet_address
        
        if self.node_type == "sentinel_ai":
            payload["sentinel_config"] = {
                "monitoring_enabled": True,
                "threat_detection_level": "high"
            }
        
        try:
            response = self.session.post(
                f"{self.bootstrap_url}/api/v1/nodes/register",
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Node registered successfully")
                print(f"  Initial reputation: {result['initial_reputation']}")
                print(f"  Heartbeat interval: {result['heartbeat_interval']}s")
                
                if result.get('entropy_submission_required'):
                    print(f"  ⚠️  Entropy submission required by {result['entropy_submission_deadline']}")
                
                return result
            
            elif response.status_code == 409:
                print(f"✗ Node {self.node_id} already registered")
                return None
            
            else:
                result = response.json()
                print(f"✗ Registration failed: {result.get('error')}")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"✗ Registration error: {e}")
            return None
    
    def _get_services(self):
        if self.node_type == "miner":
            return ["mining", "p2p_sync"]
        elif self.node_type == "validator":
            return ["validation", "p2p_sync"]
        elif self.node_type == "relay":
            return ["p2p_sync", "relay"]
        return []
    
    def _get_capabilities(self):
        if self.node_type == "miner":
            return ["mining", "entropy_submission"]
        elif self.node_type == "validator":
            return ["validation"]
        return []

# Usage
if __name__ == "__main__":
    registrar = PiSecureNodeRegistrar(
        node_id="miner-rpi5-001",
        node_type="miner",
        bootstrap_url="https://bootstrap.pisecure.org"
    )
    
    result = registrar.register(
        location="us-east",
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        network="mainnet"
    )
```

### Rust/Go Implementation Example

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type NodeRegistration struct {
    NodeID       string   `json:"node_id"`
    NodeType     string   `json:"node_type"`
    Services     []string `json:"services"`
    Location     string   `json:"location"`
    WalletAddr   string   `json:"wallet_address,omitempty"`
    Capabilities []string `json:"capabilities"`
    Network      string   `json:"network"`
}

func RegisterNode(nodeID, nodeType string) error {
    reg := NodeRegistration{
        NodeID:       nodeID,
        NodeType:     nodeType,
        Location:     "us-east",
        Services:     []string{"mining", "p2p_sync"},
        Capabilities: []string{"mining", "entropy_submission"},
        Network:      "mainnet",
    }
    
    payload, _ := json.Marshal(reg)
    
    resp, err := http.Post(
        "https://bootstrap.pisecure.org/api/v1/nodes/register",
        "application/json",
        bytes.NewBuffer(payload),
    )
    
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    if resp.StatusCode == 200 {
        fmt.Println("✓ Node registered successfully")
        return nil
    }
    
    return fmt.Errorf("registration failed: %d", resp.StatusCode)
}
```

---

## 8. WebSocket Support

### Current Status: ❌ NOT IMPLEMENTED (Future Enhancement)

**Planned for Phase 2+**

### Proposed WebSocket Specification

#### WebSocket Endpoint (Future)

```
wss://bootstrap.pisecure.org/api/v1/nodes/stream
wss://bootstrap-testnet.pisecure.org/api/v1/nodes/stream
```

#### Connection Flow (Proposed)

```
1. Client connects to WebSocket
2. Client sends authentication message
3. Server opens persistent bidirectional channel
4. Client/Server exchange events in real-time
```

#### Proposed Message Types

**Client → Server:**

```json
{
  "type": "subscribe",
  "channels": ["node_updates", "peer_discovery", "threat_alerts"]
}
```

```json
{
  "type": "heartbeat",
  "node_id": "miner-001",
  "metrics": {
    "cpu_usage": 45.2,
    "memory_mb": 512,
    "uptime_seconds": 86400
  }
}
```

```json
{
  "type": "report_threat",
  "threat_data": {...}
}
```

**Server → Client:**

```json
{
  "type": "peer_discovered",
  "peer": {
    "node_id": "validator-001",
    "address": "192.168.1.100",
    "port": 3142
  }
}
```

```json
{
  "type": "network_alert",
  "severity": "high",
  "alert": "DDoS attack detected from subnet 10.0.0.0/8"
}
```

### Benefits (Future)

✅ **Real-time peer discovery** instead of polling
✅ **Live threat alerts** for immediate response
✅ **Reduced latency** for time-sensitive operations
✅ **Lower bandwidth** than periodic status updates
✅ **Bi-directional communication** for interactive flows

### Current Workaround

**Use polling with status endpoints:**

```python
import time

while True:
    # Poll for node status
    response = requests.post(
        "https://bootstrap.pisecure.org/api/v1/nodes/status",
        json={
            "node_id": "miner-001",
            "status": "active",
            "metrics": {...}
        }
    )
    
    # Poll for peer list
    peers = requests.get(
        "https://bootstrap.pisecure.org/api/v1/nodes/list"
    )
    
    # Poll for network alerts (future endpoint)
    # alerts = requests.get("https://bootstrap.pisecure.org/api/v1/alerts")
    
    time.sleep(5)  # Poll every 5 seconds
```

### WebSocket Implementation Roadmap

**Phase 2 (Q2 2026):**
- ✅ Design WebSocket protocol specification
- ✅ Implement Flask-SocketIO or similar library
- ✅ Add subscription/channel management
- ✅ Beta testing with sentinel nodes

**Phase 3 (Q3 2026):**
- ✅ Production deployment
- ✅ Mobile client WebSocket support
- ✅ Fallback to polling for incompatible clients

**Phase 4 (Q4 2026):**
- ✅ Advanced features (multiplexing, compression)
- ✅ Performance optimization

---

## 9. Integration with Other Systems

### Node Tracker Integration

```python
# Internal: bootstrap/server.py
node_tracker.register_node({
    'node_id': node_id,
    'address': client_ip,
    'port': 3142,
    'capabilities': capabilities,
    'hashrate': 0,  # Updated via status endpoint
    'location': location,
    'is_mining': node_type == 'miner'
})
```

### Sentinel Integration

```python
# For sentinel_ai nodes
if node_type == 'sentinel_ai':
    sentinel_service.register_sentinel_node({
        'node_id': node_id,
        'sentinel_config': sentinel_config
    })
```

### DDoS Protection

```python
# Registered nodes bypass certain DDoS checks
# But still subject to rate limiting
ddos_protection.whitelist_endpoint(node_id)
```

### Network Intelligence

```python
# Record connection for analytics
network_intelligence.record_connection(client_ip)
```

---

## 10. Rate Limiting for Registration

| Limit Type | Value | Window |
|-----------|-------|--------|
| Per IP | 10 registrations | Per hour |
| Per Node ID | 1 registration | Global (re-register only via update) |
| Concurrent connections | 100 | Per bootstrap node |

---

## 11. Best Practices for Node Operators

1. **Use stable node IDs** - Don't change between restarts
2. **Register only once** - Use `/api/v1/nodes/status` for updates
3. **Set accurate location** - Helps with peer discovery
4. **Provide wallet address** - To receive mining rewards
5. **Implement heartbeat** - Send status every 5 minutes
6. **Submit entropy early** - Within 1 hour of registration (miners)
7. **Monitor registration deadline** - Don't miss entropy deadline

---

## 12. FAQ

**Q: Can I change my node_id after registration?**  
A: No, the node_id is permanent. To change, unregister and register with new ID.

**Q: How do I unregister?**  
A: Send status with `"status": "offline"` or node will auto-unregister after 1 hour of inactivity.

**Q: What if registration fails?**  
A: Check error message for specific issue. Most common: node already registered or invalid node_id format.

**Q: Do I need to re-register after restart?**  
A: No, same node_id will update existing registration. Just send status update.

**Q: When will WebSocket be available?**  
A: Planned for Phase 2 (Q2 2026). Currently use polling endpoints.

---

## 13. Version History

- **v1.0** (2026-01-21): Initial specification
  - HTTP-only endpoints
  - Node registration, status, list endpoints
  - Four node types (miner, validator, sentinel_ai, relay)
  
- **v1.1** (Planned Q2 2026): WebSocket support
  - Real-time peer discovery
  - Live threat alerts
  - Bi-directional communication

---

## Related Documentation

- [docs/api-entropy-validation.md](api-entropy-validation.md) - Entropy submission after registration
- [docs/PISECURE_TEAM_QA.md](PISECURE_TEAM_QA.md) - Q&A on all endpoints
- [ENTROPY_VALIDATION.md](../ENTROPY_VALIDATION.md) - Technical implementation
- [README.md](../README.md) - Quick start examples

---

## Summary for PiSecure Team

**Node Registration: ✅ Complete**
- Full HTTP/REST API specified
- Four node types supported (miner, validator, sentinel_ai, relay)
- Complete validation rules documented
- Error handling for all scenarios
- Python/Go implementation examples provided

**WebSocket Support: ❌ Not Implemented (Future Phase 2)**
- Design specification provided
- Benefits documented
- Roadmap outline given
- Current polling workaround documented
- Expected Q2 2026 implementation

Ready for team review and production deployment! 🚀
