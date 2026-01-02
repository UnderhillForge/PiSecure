# PiSecure JavaScript/TypeScript Client

A JavaScript/TypeScript SDK for interacting with the PiSecure blockchain network.

## Installation

```bash
npm install pisecure-client
# or
yarn add pisecure-client
```

## Quick Start

### JavaScript (CommonJS)

```javascript
const { PiSecureClient } = require('pisecure-client');

async function main() {
    // Initialize client
    const client = new PiSecureClient();

    try {
        // Get blockchain info
        const info = await client.getBlockchainInfo();
        console.log(`Blockchain has ${info.blocks} blocks`);

        // Get wallet balance
        const balance = await client.getWalletBalance('your_wallet_address');
        console.log(`Balance: ${balance} tokens`);

        // Create and submit transaction
        const tx = client.createTransferTransaction(
            'from_wallet_id',
            'to_address',
            100.0,
            'Payment memo'
        );
        const txHash = await client.submitTransaction(tx);
        console.log(`Transaction submitted: ${txHash}`);

    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
```

### TypeScript

```typescript
import { PiSecureClient, BlockchainInfo, Transaction } from 'pisecure-client';

async function main() {
    const client = new PiSecureClient();

    try {
        // Get blockchain info with type safety
        const info: BlockchainInfo = await client.getBlockchainInfo();
        console.log(`Blocks: ${info.blocks}`);

        // Get balance
        const balance: number = await client.getWalletBalance('address');
        console.log(`Balance: ${balance}`);

    } catch (error) {
        console.error('Error:', error);
    }
}

main();
```

### Browser Usage

```html
<!DOCTYPE html>
<html>
<head>
    <title>PiSecure Web App</title>
    <script src="https://cdn.jsdelivr.net/npm/pisecure-client@latest/dist/pisecure-client.min.js"></script>
</head>
<body>
    <div id="app"></div>

    <script>
        const client = new PiSecureClient();

        async function loadBlockchainInfo() {
            try {
                const info = await client.getBlockchainInfo();
                document.getElementById('app').innerHTML = `
                    <h1>PiSecure Blockchain</h1>
                    <p>Blocks: ${info.blocks}</p>
                    <p>Pending TX: ${info.pending_transactions}</p>
                `;
            } catch (error) {
                console.error('Failed to load blockchain info:', error);
            }
        }

        loadBlockchainInfo();
    </script>
</body>
</html>
```

## Features

- 🌐 **Universal**: Works in Node.js and browsers
- 📝 **TypeScript Support**: Full type definitions included
- 🔄 **Promise-based**: Modern async/await API
- 🔍 **Auto-discovery**: Finds PiSecure nodes automatically
- ⚖️ **Load Balancing**: Distributes requests across nodes
- 🔄 **Retry Logic**: Handles network failures
- 🔒 **Secure**: HTTPS/TLS support
- 💰 **314ST Token Economics**: Built-in token-powered access control
- 🏦 **Developer Trust Funds**: Subscription and funding models
- 🏛️ **Foundation Governance**: Community-controlled development
- 👥 **End User Abstraction**: Blockchain invisible to users

## API Reference

### PiSecureClient

#### Constructor
```typescript
const client = new PiSecureClient(options?: {
    bootstrapPeers?: string[];
    apiVersion?: string;
    timeout?: number;
    maxRetries?: number;
});
```

#### Blockchain Operations
```typescript
// Get blockchain status
const info: BlockchainInfo = await client.getBlockchainInfo();

// Get specific block
const block: Block = await client.getBlock(42);

// Get recent blocks
const blocks: Block[] = await client.getBlocks({ limit: 10, offset: 0 });

// Get transaction
const tx: Transaction = await client.getTransaction('hash');
```

#### Wallet Operations
```typescript
// Get balance
const balance: number = await client.getWalletBalance('address');

// Get transaction history
const txs: Transaction[] = await client.getWalletTransactions('address', 20);

// Create wallet
const wallet: Wallet = await client.createWallet({
    name: 'my_wallet',
    displayName: 'My Wallet'
});

// List wallets
const wallets: Wallet[] = await client.listWallets();
```

#### Transaction Operations
```typescript
// Submit transaction
const txHash: string = await client.submitTransaction(txData);

// Create transfer (helper)
const tx: Transaction = client.createTransferTransaction(
    'from_wallet',
    'to_address',
    100.0,
    'memo'
);
```

#### Network Operations
```typescript
// Network status
const status: NetworkStatus = await client.getNetworkStatus();

// Known peers
const peers: string[] = await client.getNetworkPeers();

// Health check
const health: HealthStatus = await client.healthCheck();
```

#### 314ST Economics Operations
```typescript
// Trust fund management
const trust = await client.createDeveloperTrust(
    'developer_address',
    'public',  // 'public', 'subscriber_all', 'subscriber_individual', 'hybrid'
    1000.0    // Initial funding in 314ST
);

const trustStatus = await client.getTrust(trust.trust_id);
await client.fundTrust(trust.trust_id, 500.0);

// Subscription management
const plan = await client.createSubscriptionPlan(trust.trust_id, {
    name: 'Premium Plan',
    monthly_cost: 50.0,
    features: ['unlimited_access', 'priority_support'],
    limits: { daily_calls: 10000 }
});

await client.addSubscriber(trust.trust_id, 'user_123', plan.plan_id);
await client.grantFreeAccess(trust.trust_id, 'free_user_456');

// Access control
const accessResult = await client.checkUserAccess(
    trust.trust_id,
    'user_123',
    'submit_data',
    { data_size: 100 }
);

// Foundation governance
const foundation = await client.getFoundationStatus();
const grant = await client.createGrant({
    project_name: 'PiSecure Mobile SDK',
    developer: 'mobile_team',
    funding_requested: 15000,
    milestones: ['Design', 'Development', 'Testing', 'Release']
});

await client.voteOnGrant(
    grant.grant_id,
    'voter_wallet',
    true,   // approve
    100.0   // voting power based on token balance
);
```

## Type Definitions

```typescript
interface BlockchainInfo {
    blocks: number;
    pending_transactions: number;
    difficulty: number;
    is_valid: boolean;
    network_health: string;
    latest_block?: Block;
}

interface Block {
    index: number;
    timestamp: number;
    transactions: Transaction[];
    previous_hash: string;
    hash: string;
    nonce: number;
}

interface Transaction {
    type: string;
    data: any;
    signature: string;
    timestamp: number;
    hash?: string;
}

interface Wallet {
    id: string;
    name: string;
    address: string;
    balance: number;
}

interface NetworkStatus {
    connected_peers: number;
    known_peers: number;
    node_id: string;
    listening_port: number;
}
```

## Error Handling

```javascript
const client = new PiSecureClient();

try {
    const balance = await client.getWalletBalance('address');
    console.log(`Balance: ${balance}`);
} catch (error) {
    if (error.code === 'CONNECTION_ERROR') {
        console.log('No PiSecure nodes available');
    } else if (error.code === 'API_ERROR') {
        console.log(`API error: ${error.message}`);
    } else {
        console.log(`Unknown error: ${error.message}`);
    }
}
```

## Advanced Usage

### Custom Bootstrap Peers

```javascript
const client = new PiSecureClient({
    bootstrapPeers: [
        'https://my-node.com/peers.json',
        'http://trusted-peer.local:3142'
    ]
});
```

### React Integration

```jsx
import React, { useState, useEffect } from 'react';
import { PiSecureClient } from 'pisecure-client';

function BlockchainInfo() {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const client = new PiSecureClient();

        client.getBlockchainInfo()
            .then(setInfo)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div>Loading...</div>;

    return (
        <div>
            <h1>PiSecure Blockchain</h1>
            <p>Blocks: {info?.blocks}</p>
            <p>Pending TX: {info?.pending_transactions}</p>
        </div>
    );
}
```

### WebSocket Real-time Updates (Future)

```javascript
// Planned real-time updates
const client = new PiSecureClient();
const ws = client.subscribeToUpdates();

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('New block:', update);
};
```

## Dependencies

- Runtime: None (pure JavaScript)
- Development: TypeScript, Jest, Webpack

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Node.js Support

- Node.js 14+
- ESM and CommonJS modules

## Building from Source

```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd clients/javascript
npm install
npm run build
```

## Contributing

See the main PiSecure repository for contribution guidelines.

## License

MIT License