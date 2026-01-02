# PiSecure Python Client

A Python SDK for interacting with the PiSecure blockchain network via REST API.

## Installation

```bash
pip install pisecure-client
# or from source
pip install git+https://github.com/UnderhillForge/PiSecure.git#subdirectory=clients/python
```

## Quick Start

```python
from pisecure_client import PiSecureClient

# Initialize client
client = PiSecureClient()

# Get blockchain info
info = client.get_blockchain_info()
print(f"Blockchain has {info['blocks']} blocks")

# Get wallet balance
balance = client.get_wallet_balance('your_wallet_address')
print(f"Balance: {balance} tokens")

# Create and submit transaction
tx = client.create_transfer_transaction(
    'from_wallet_id',
    'to_address',
    100.0,
    'Payment memo'
)
tx_hash = client.submit_transaction(tx)
print(f"Transaction submitted: {tx_hash}")
```

## Features

- 🔍 **Automatic Peer Discovery**: Finds available PiSecure nodes
- ⚖️ **Load Balancing**: Distributes requests across healthy nodes
- 🔄 **Retry Logic**: Handles network failures gracefully
- 📝 **Type Hints**: Full Python type annotations
- 🔒 **Secure**: TLS encryption, input validation

## API Reference

### PiSecureClient

#### Initialization
```python
client = PiSecureClient(
    bootstrap_peers=None,  # Custom bootstrap peer list
    api_version="v1",      # API version
    timeout=30,            # Request timeout
    max_retries=3          # Retry attempts
)
```

#### Blockchain Operations
- `get_blockchain_info()` - Get blockchain status
- `get_block(index)` - Get specific block
- `get_blocks(limit=10, offset=0)` - Get recent blocks
- `get_transaction(tx_hash)` - Get transaction details

#### Wallet Operations
- `get_wallet_balance(address)` - Get wallet balance
- `get_wallet_transactions(address, limit=20)` - Get transaction history
- `create_wallet(name=None, display_name=None)` - Create new wallet
- `list_wallets()` - List available wallets

#### Transaction Operations
- `submit_transaction(tx_data)` - Submit transaction
- `create_transfer_transaction(from_wallet, to_address, amount, memo="")` - Helper for transfers

#### Network Operations
- `get_network_status()` - Get network information
- `get_network_peers()` - Get known peers
- `health_check()` - API health check

## Error Handling

```python
from pisecure_client import PiSecureClient
import requests

client = PiSecureClient()

try:
    balance = client.get_wallet_balance('some_address')
    print(f"Balance: {balance}")
except requests.exceptions.ConnectionError:
    print("No PiSecure nodes available")
except ValueError as e:
    print(f"API error: {e}")
```

## Advanced Usage

### Custom Bootstrap Peers

```python
client = PiSecureClient(
    bootstrap_peers=[
        'https://my-node.com/peers.json',
        'http://trusted-peer.local:3142'
    ]
)
```

### Async Support (Future)

```python
# Planned async support
import asyncio
from pisecure_client import AsyncPiSecureClient

async def main():
    client = AsyncPiSecureClient()
    balance = await client.get_wallet_balance('address')
    print(f"Balance: {balance}")

asyncio.run(main())
```

## Dependencies

- requests>=2.25.0
- typing-extensions>=4.0.0 (Python < 3.9)

## Contributing

Contributions welcome! Please see the main PiSecure repository for contribution guidelines.

## License

MIT License