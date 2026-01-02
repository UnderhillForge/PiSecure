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
- 💰 **314ST Token Economics**: Built-in token-powered access control
- 🏦 **Developer Trust Funds**: Subscription and funding models
- 🏛️ **Foundation Governance**: Community-controlled development
- 👥 **End User Abstraction**: Blockchain invisible to users

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

#### 314ST Economics Operations
- `create_developer_trust(developer_address, trust_type, initial_funding)` - Create trust fund
- `get_trust(trust_id)` - Get trust status
- `fund_trust(trust_id, amount)` - Add tokens to trust
- `create_subscription_plan(trust_id, plan_data)` - Create subscription plan
- `add_subscriber(trust_id, user_id, plan_id)` - Subscribe user to plan
- `grant_free_access(trust_id, user_id)` - Grant free access to user
- `check_user_access(trust_id, user_id, operation_cost)` - Check access permissions
- `get_foundation_status()` - Get foundation information
- `create_grant(project_data)` - Submit grant proposal
- `vote_on_grant(grant_id, voter_address, vote, voting_power)` - Vote on grants
- `calculate_api_cost(operation, params)` - Calculate operation costs

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

### 314ST Token Economics

#### Developer Trust Funds

```python
# Create a public trust (free access, developer pays)
trust = client.create_developer_trust(
    developer_address="dev_wallet_123",
    trust_type="public",
    initial_funding=1000.0  # 1000 314ST
)
print(f"Trust created: {trust['trust_id']}")

# Fund the trust
client.fund_trust(trust['trust_id'], 500.0)

# Check trust status
status = client.get_trust(trust['trust_id'])
print(f"Trust balance: {status['balance']} 314ST")
```

#### Subscription Models

```python
# Create subscription plan
plan = client.create_subscription_plan(trust['trust_id'], {
    'name': 'Premium Access',
    'monthly_cost': 50.0,  # 50 314ST/month
    'features': ['unlimited_api', 'priority_support'],
    'limits': {'daily_calls': 10000}
})

# Subscribe a user
client.add_subscriber(trust['trust_id'], 'user_456', plan['plan_id'])

# Grant free access to specific user
client.grant_free_access(trust['trust_id'], 'free_user_789')
```

#### End User API Access

```python
# Check if user can access (invisible to end user)
access_result = client.check_user_access(
    trust_id=trust['trust_id'],
    user_id='end_user_123',
    operation='submit_sensor_data',
    params={'data_size': 100}
)

if access_result['can_access']:
    # User can proceed with operation
    result = submit_sensor_data(sensor_data)
    print(f"Data submitted: {result}")
else:
    print(f"Access denied: {access_result['message']}")
```

#### Foundation Governance

```python
# Get foundation status
foundation = client.get_foundation_status()
print(f"Foundation balance: {foundation['balance']} 314ST")

# Submit grant proposal
grant = client.create_grant({
    'project_name': 'PiSecure Mobile App',
    'developer': 'mobile_dev_team',
    'funding_requested': 10000,
    'milestones': ['MVP', 'Beta Release', 'Launch'],
    'description': 'Native mobile wallet for PiSecure'
})

# Vote on grants (requires token holding)
client.vote_on_grant(
    grant_id=grant['grant_id'],
    voter_address='your_wallet',
    vote=True,  # True = approve, False = reject
    voting_power=100.0  # Based on token balance
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