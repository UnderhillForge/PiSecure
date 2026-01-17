# PiSecure Developer API

The PiSecure Developer API provides platform-independent access to the PiSecure blockchain network, which uses the custom PiHash mining algorithm exclusive to Raspberry Pi hardware. Developers can integrate blockchain functionality into their applications without running mining nodes or PiSecure servers locally.

## 🚀 Quick Start

### Python Client

```python
from pisecure.api.client import PiSecureClient

# Initialize client (automatically discovers nodes)
client = PiSecureClient()

# Get wallet balance
balance = client.get_wallet_balance('your_wallet_address')
print(f"Balance: {balance} tokens")

# Get blockchain information
info = client.get_blockchain_info()
print(f"Blockchain has {info['blocks']} blocks")
```

### JavaScript/TypeScript

```javascript
import { PiSecureClient } from 'pisecure-client';

const client = new PiSecureClient();

// Get balance
const balance = await client.getWalletBalance('your_address');
console.log(`Balance: ${balance} tokens`);
```

## 📚 Architecture

### API Server
PiSecure nodes expose a REST API on port 3142 that provides:
- Blockchain queries and exploration
- Transaction submission and tracking
- Wallet operations
- Network status and peer information

### Client Libraries
- **Automatic peer discovery**: Finds available PiSecure nodes
- **Load balancing**: Distributes requests across healthy nodes
- **Retry logic**: Handles network failures gracefully
- **Type safety**: Full TypeScript support

### Peer Discovery
- **Bootstrap peers**: Initial node discovery
- **Health monitoring**: Automatic failover to healthy nodes
- **Local network scanning**: Finds nodes on same network
- **Peer exchange**: Nodes share known peers

## 🔧 Installation

### Python

```bash
pip install pisecure-client
# or
pip install git+https://github.com/UnderhillForge/PiSecure.git#subdirectory=clients/python
```

### JavaScript/TypeScript

```bash
npm install pisecure-client
# or
yarn add pisecure-client
```

### Node.js

```bash
npm install pisecure-client
```

## 📖 API Reference

### Core Classes

#### PiSecureClient

Main client class for interacting with the PiSecure network.

```python
class PiSecureClient:
    def __init__(self, bootstrap_peers=None, api_version="v1", timeout=30, max_retries=3)
```

### Blockchain Operations

#### Get Blockchain Info
```python
info = client.get_blockchain_info()
# Returns: {'blocks': 123, 'pending_transactions': 5, 'difficulty': 4, ...}
```

#### Get Specific Block
```python
block = client.get_block(42)
# Returns: Block data dictionary
```

#### Get Recent Blocks
```python
blocks = client.get_blocks(limit=10, offset=0)
# Returns: List of block dictionaries
```

#### Get Transaction
```python
tx = client.get_transaction('tx_hash_here')
# Returns: Transaction data dictionary
```

### Wallet Operations

#### Get Balance
```python
balance = client.get_wallet_balance('wallet_address')
# Returns: float (token balance)
```

#### Get Transaction History
```python
transactions = client.get_wallet_transactions('address', limit=20)
# Returns: List of transaction dictionaries
```

#### Create Wallet
```python
wallet = client.create_wallet(name='my_wallet', display_name='My Wallet')
# Returns: {'success': True, 'wallet_id': '...', 'address': '...'}
```

#### List Wallets
```python
wallets = client.list_wallets()
# Returns: List of wallet dictionaries
```

### Transaction Operations

#### Submit Transaction
```python
tx_hash = client.submit_transaction(transaction_data)
# Returns: Transaction hash string
```

#### Create Transfer Transaction
```python
tx = client.create_transfer_transaction(
    from_wallet='wallet_id',
    to_address='recipient_address',
    amount=100.0,
    memo='Payment for services'
)
# Returns: Unsigned transaction dictionary
```

### Network Operations

#### Get Network Status
```python
status = client.get_network_status()
# Returns: {'connected_peers': 5, 'known_peers': 25, ...}
```

#### Get Network Peers
```python
peers = client.get_network_peers()
# Returns: List of peer addresses
```

## 🎯 Use Cases

### 1. **E-commerce Payment Integration**

```python
# Merchant payment processing
def process_payment(amount, customer_wallet):
    # Check customer balance
    balance = client.get_wallet_balance(customer_wallet)
    if balance >= amount:
        # Create transfer transaction
        tx = client.create_transfer_transaction(
            from_wallet=customer_wallet,
            to_address=merchant_wallet,
            amount=amount,
            memo=f'Payment for order #{order_id}'
        )
        # Submit transaction
        tx_hash = client.submit_transaction(tx)
        return {'success': True, 'tx_hash': tx_hash}
    else:
        return {'success': False, 'error': 'Insufficient balance'}
```

### 2. **Blockchain Explorer**

```python
# Build a block explorer
def get_blockchain_summary():
    info = client.get_blockchain_info()
    recent_blocks = client.get_blocks(limit=10)

    return {
        'total_blocks': info['blocks'],
        'difficulty': info['difficulty'],
        'pending_txs': info['pending_transactions'],
        'recent_blocks': recent_blocks
    }
```

### 3. **Wallet Application**

```python
# Wallet management app
class WalletApp:
    def __init__(self):
        self.client = PiSecureClient()

    def create_new_wallet(self, name):
        return self.client.create_wallet(name=name)

    def get_balance(self, address):
        return self.client.get_wallet_balance(address)

    def send_payment(self, from_addr, to_addr, amount):
        # In real app, this would include proper signing
        tx = self.client.create_transfer_transaction(from_addr, to_addr, amount)
        return self.client.submit_transaction(tx)
```

### 4. **IoT Device Integration**

```python
# Raspberry Pi IoT device
import time
from pisecure.api.client import PiSecureClient

def iot_monitoring_loop():
    client = PiSecureClient()

    while True:
        # Read sensor data
        temperature = read_temperature_sensor()
        humidity = read_humidity_sensor()

        # Create transaction with sensor data
        tx_data = {
            'type': 'sensor_reading',
            'device_id': 'raspberry_pi_001',
            'timestamp': time.time(),
            'data': {
                'temperature': temperature,
                'humidity': humidity,
                'location': 'warehouse_a'
            }
        }

        # Submit to blockchain
        tx_hash = client.submit_transaction(tx_data)
        print(f"Submitted sensor data: {tx_hash}")

        time.sleep(300)  # Every 5 minutes
```

### 5. **Supply Chain Tracking**

```python
# Supply chain management system
def record_shipment_movement(shipment_id, from_location, to_location):
    tx_data = {
        'type': 'shipment_movement',
        'shipment_id': shipment_id,
        'timestamp': time.time(),
        'data': {
            'from_location': from_location,
            'to_location': to_location,
            'moved_by': 'logistics_company_xyz',
            'vehicle_id': 'TRUCK_001'
        }
    }

    client = PiSecureClient()
    tx_hash = client.submit_transaction(tx_data)

    return {
        'success': True,
        'tx_hash': tx_hash,
        'blockchain_record': f"https://explorer.pisecure.net/tx/{tx_hash}"
    }
```

## 🌐 Client Libraries

### Python Library Features
- ✅ Synchronous and asynchronous support
- ✅ Automatic retry and load balancing
- ✅ Type hints for IDE support
- ✅ Comprehensive error handling
- ✅ Connection pooling

### JavaScript/TypeScript Features
- ✅ Promise-based API
- ✅ Browser and Node.js support
- ✅ TypeScript definitions
- ✅ WebSocket real-time updates
- ✅ React/Vue.js integration helpers

### Additional Platforms (Planned)
- **Go**: `go get github.com/UnderhillForge/PiSecure/clients/go`
- **Rust**: `cargo add pisecure-client`
- **Java**: Maven/Gradle packages
- **C#**: NuGet package

## 🔒 Security Considerations

### API Security
- Rate limiting prevents abuse
- Request validation and sanitization
- CORS protection for web applications
- Optional authentication for private deployments

### Client Security
- Secure connection handling
- Input validation before submission
- Private key never sent over network (sign locally)
- Certificate pinning support

### Network Security
- Peer health verification
- Automatic failover to healthy nodes
- Encrypted communication (TLS)
- DDoS protection through rate limiting

## 🚀 Advanced Usage

### Custom Bootstrap Peers

```python
# Use custom bootstrap peers
client = PiSecureClient(
    bootstrap_peers=[
        'https://my-private-node.com/peers.json',
        'http://trusted-node.local:3142'
    ]
)
```

### High Availability Setup

```python
# Multiple client instances for redundancy
clients = [
    PiSecureClient(bootstrap_peers=['https://node1.com/peers.json']),
    PiSecureClient(bootstrap_peers=['https://node2.com/peers.json']),
    PiSecureClient(bootstrap_peers=['https://node3.com/peers.json'])
]

def get_balance_redundant(address):
    for client in clients:
        try:
            return client.get_wallet_balance(address)
        except:
            continue
    raise Exception("All clients failed")
```

### Monitoring and Health Checks

```python
# Health monitoring
def monitor_network_health():
    client = PiSecureClient()

    while True:
        try:
            health = client.health_check()
            network = client.get_network_status()

            print(f"API Health: {health['status']}")
            print(f"Connected Peers: {network['connected_peers']}")

        except Exception as e:
            print(f"Health check failed: {e}")

        time.sleep(60)
```

## 📋 API Endpoints

### Core Endpoints
- `GET /api/v1/health` - Health check
- `GET /api/v1/blockchain/info` - Blockchain status
- `GET /api/v1/blockchain/block/<index>` - Get block
- `GET /api/v1/blockchain/blocks` - Get blocks
- `GET /api/v1/wallet/<address>/balance` - Get balance
- `POST /api/v1/transaction` - Submit transaction
- `GET /api/v1/network/status` - Network status

### Full API Documentation
Available at: `http://your-node:3142/api/v1/docs`

## 🤝 Contributing

We welcome contributions to the PiSecure Developer API:

1. **Client Libraries**: Add support for new platforms
2. **Documentation**: Improve examples and guides
3. **Features**: Add new API endpoints or capabilities
4. **Testing**: Add comprehensive test coverage

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: https://docs.pisecure.net/api
- **Issues**: https://github.com/UnderhillForge/PiSecure/issues
- **Discussions**: https://github.com/UnderhillForge/PiSecure/discussions

---

**PiSecure**: Decentralized Security Framework for the IoT Era 🚀