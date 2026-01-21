# MetaMask Integration for PiSecure

This document describes the MetaMask wallet integration feature for PiSecure blockchain.

## Overview

The MetaMask integration allows users to connect their MetaMask browser extension wallet to the PiSecure blockchain platform. This provides a seamless way for Ethereum wallet users to interact with PiSecure nodes and track their wallet activities.

## Features

- **MetaMask Detection**: Automatically detects if MetaMask browser extension is installed
- **Wallet Connection**: One-click connection to MetaMask wallet
- **Account Display**: Shows connected account address, balance, and network
- **Signature Verification**: Verifies wallet ownership through message signing
- **Wallet Linking**: Links MetaMask addresses to PiSecure wallet system
- **Multi-Network Support**: Works with Ethereum Mainnet, testnets, and compatible networks

## Components

### Frontend (JavaScript)

Located in: `dashboard/web/static/js/metamask.js`

The `MetamaskIntegration` class handles all MetaMask interactions:

```javascript
// Initialize MetaMask integration
const metamask = new MetamaskIntegration();

// Connect to MetaMask
await metamask.connect();

// Get account info
const account = metamask.getAccount();
const balance = await metamask.getBalance();
const chainId = metamask.getChainId();
```

Key features:
- Automatic MetaMask detection
- Event listeners for account/network changes
- Signature generation for wallet verification
- Automatic wallet registration with PiSecure backend

### Backend (Python)

Located in: `dashboard/web/app.py`

The API endpoint `/api/wallets/metamask/link` handles wallet linking:

```python
POST /api/wallets/metamask/link
Content-Type: application/json

{
  "address": "0x1234...",
  "chain_id": "0x1",
  "signature": "0xabcd...",
  "message": "PiSecure Wallet Link: ...",
  "timestamp": 1234567890
}
```

Response:
```json
{
  "success": true,
  "wallet_id": "metamask_12345678",
  "address": "0x1234...",
  "chain_id": "0x1",
  "message": "MetaMask wallet linked successfully"
}
```

### User Interface

Located in: `dashboard/web/templates/wallets.html`

The wallet page includes a dedicated MetaMask section with:
- Connection button
- Status indicator
- Account address display
- Network/chain display
- Balance display (in ETH)

## Usage

### For Users

1. **Install MetaMask**
   - Visit [metamask.io](https://metamask.io)
   - Install the browser extension
   - Create or import a wallet

2. **Connect to PiSecure**
   - Navigate to the PiSecure wallet page (`/wallets`)
   - Find the "MetaMask Wallet" section
   - Click "Connect MetaMask" button
   - Approve the connection in MetaMask popup
   - Sign the verification message when prompted

3. **View Wallet Info**
   - Once connected, your account address, network, and balance are displayed
   - The connection persists across page reloads
   - Your MetaMask wallet is now linked to PiSecure

### For Developers

#### Adding MetaMask Support to Other Pages

```html
<!-- Include the MetaMask script -->
<script src="{{ url_for('static', filename='js/metamask.js') }}"></script>

<script>
// Initialize on page load
window.addEventListener('load', () => {
    const metamask = new MetamaskIntegration();
    
    // Check if connected
    if (metamask.isConnected()) {
        console.log('Connected to:', metamask.getAccount());
    }
});
</script>
```

#### Creating Custom MetaMask Interactions

```javascript
// Sign a custom message
const signature = await metamask.signMessage('Custom message');

// Get wallet balance
const balance = await metamask.getBalance();

// Listen for account changes
window.ethereum.on('accountsChanged', (accounts) => {
    console.log('Account changed:', accounts[0]);
});
```

## Security Features

1. **Message Signing**: Requires signature verification to prove wallet ownership
2. **Address Validation**: Validates Ethereum address format (0x + 40 hex chars)
3. **Timestamp Verification**: Includes timestamp in signed message to prevent replay attacks
4. **Secure Storage**: MetaMask wallet links stored separately from PiSecure private keys

## Storage

MetaMask wallet links are stored in:
```
/var/lib/pisecure/wallets/metamask/<wallet_id>.json
```

Example wallet file:
```json
{
  "wallet_id": "metamask_12345678",
  "name": "MetaMask 0x1234...5678",
  "metamask_address": "0x1234567890123456789012345678901234567890",
  "chain_id": "0x1",
  "linked_at": 1234567890,
  "signature": "0xabcdef...",
  "message": "PiSecure Wallet Link: ...",
  "wallet_type": "metamask"
}
```

## Supported Networks

The integration supports all Ethereum-compatible networks:

- Ethereum Mainnet (0x1)
- Ropsten Testnet (0x3)
- Rinkeby Testnet (0x4)
- Goerli Testnet (0x5)
- Polygon Mainnet (0x89)
- Binance Smart Chain (0x38)
- Arbitrum One (0xa4b1)
- Optimism (0xa)
- And more...

## Troubleshooting

### MetaMask Not Detected

**Problem**: "MetaMask is not installed!" message appears

**Solution**:
- Ensure MetaMask browser extension is installed
- Refresh the page
- Check browser console for errors

### Connection Rejected

**Problem**: Connection request is rejected

**Solution**:
- Try connecting again
- Check if MetaMask is locked
- Ensure you have approved the connection in MetaMask popup

### Wrong Network

**Problem**: Connected to wrong network

**Solution**:
- Open MetaMask
- Switch to desired network
- Page will reload automatically

### Signature Failed

**Problem**: Signature request fails

**Solution**:
- Ensure MetaMask is unlocked
- Approve the signature request in MetaMask popup
- Check that the wallet has enough gas (not required for signing, but good to check)

## API Reference

### MetamaskIntegration Class

#### Constructor
```javascript
new MetamaskIntegration()
```
Initializes MetaMask integration and sets up event listeners.

#### Methods

**connect()**
- Returns: `Promise<boolean>`
- Connects to MetaMask and requests account access

**isInstalled()**
- Returns: `boolean`
- Checks if MetaMask extension is installed

**isConnected()**
- Returns: `boolean`
- Checks if wallet is currently connected

**getAccount()**
- Returns: `string | null`
- Gets current connected account address

**getChainId()**
- Returns: `string | null`
- Gets current network chain ID

**getBalance()**
- Returns: `Promise<string>`
- Gets ETH balance for connected account

**signMessage(message)**
- Parameters: `message` (string)
- Returns: `Promise<string>`
- Signs a message with the connected wallet

## Testing

Run the integration tests:

```bash
python3 test_metamask_integration.py
```

Tests include:
- JavaScript module existence and structure
- HTML template integration
- API endpoint functionality
- Storage directory operations

## Future Enhancements

Possible future improvements:
- Support for MetaMask Mobile
- EIP-1559 transaction support
- Token balance display (ERC-20)
- NFT integration (ERC-721)
- Cross-chain bridge functionality
- Multi-account management
- Hardware wallet support through MetaMask

## License

This MetaMask integration is part of the PiSecure project and follows the same license.

## Support

For issues or questions:
- GitHub Issues: [UnderhillForge/PiSecure](https://github.com/UnderhillForge/PiSecure/issues)
- MetaMask Documentation: [docs.metamask.io](https://docs.metamask.io)
