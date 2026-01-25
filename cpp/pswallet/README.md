# pswallet - PiSecure Wallet Manager & Smart Contract Engine

High-performance C++ wallet management and smart contract execution engine for PiSecure blockchain, providing:

- **Native Wallet Operations**: Create, manage, and secure cryptographic wallets
- **Transaction Management**: Send, batch transfer, and transaction history
- **Smart Contract Execution**: Run PiScript (.ps) smart contracts with sandbox security
- **Blockchain Integration**: Direct REST API integration with PiSecure nodes
- **Cross-Platform**: Works on Raspberry Pi, Linux, Mac, and Windows

## Features

### Wallet Management
- Create and manage multiple wallets
- RSA 4096-bit cryptographic keys (hardware-verified on Pi)
- Wallet export/import with optional encryption
- Cold storage support
- Transaction history tracking

### Transaction Operations
- Single and batch transfers
- Automatic fee calculation
- Transaction signing and verification
- Pending transaction tracking
- Real-time transaction streaming via WebSocket

### Smart Contracts
- **PiScript language**: Simple, sandboxed contract scripting
- **Script execution**: Run contracts from files with parameters
- **Sandbox security**: Prevent malicious operations (exec, fork, etc.)
- **Event emission**: Trigger and listen to contract events
- **State management**: Persistent contract state storage

### Blockchain Integration
- Query wallet balances from blockchain
- Submit transactions and monitor confirmation
- Real-time blockchain event streams
- Node health and status monitoring
- Peer discovery and network status

## Installation

### Prerequisites
- **CMake** 3.12+
- **C++17 compiler** (g++, clang)
- **libcurl-dev** for HTTP requests
- **libssl-dev** for cryptography
- **nlohmann_json** header library (nlohmann-json3-dev)

### Quick Install
```bash
# Automatic compilation during pip install
pip install -e /path/to/PiSecure

# Or build manually
cd cpp/pswallet
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
sudo make install
```

### Manual Build
```bash
cd cpp/pswallet
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
./pswallet --version
```

## Usage

### Wallet Management

```bash
# Create a new wallet
pswallet create my_wallet

# List all wallets
pswallet list

# Show wallet info
pswallet info my_wallet

# Export wallet (backup)
pswallet export my_wallet

# Import wallet from backup
pswallet import my_wallet.backup
```

### Transactions

```bash
# Check balance
pswallet balance 0x1234567890abcdef...

# Send tokens
pswallet send my_wallet 0x5678... 100.0 --memo "Payment"

# View transaction history
pswallet history 0x1234567890abcdef...

# Show pending transactions
pswallet pending

# Batch transfers from file
pswallet batch-send transfers.json
```

### Smart Contracts

```bash
# Run a script
pswallet run-script contract.ps

# Validate script syntax
pswallet validate contract.ps

# Deploy contract
pswallet deploy contract.ps

# Call contract function
pswallet call 0xcontract... function_name --params '{"key": "value"}'

# Dry-run (simulate without submitting)
pswallet send my_wallet 0x5678... 100.0 --dry-run
```

### Options

```bash
# Global options
--testnet              Use testnet blockchain (separate from mainnet)
-j, --json             Output as JSON
-q, --quiet            Suppress informational output
-v, --verbose          Verbose output with details
-u, --url URL          Blockchain node URL (default: http://localhost:3142)
-d, --wallet-dir DIR   Custom wallet directory
-p, --password PASS    Wallet encryption password

# Transaction options
-r, --recipient ADDR   Transfer recipient address
-a, --amount AMOUNT    Transfer amount
-m, --memo TEXT        Transaction memo
--limit N              Transaction history limit

# Script options
-s, --script FILE      Smart contract file
--dry-run              Simulate without submitting
```

## PiScript Smart Contract Language

PiScript is a simple, sandboxed scripting language for defining and executing smart contracts.

### Basic Syntax

```javascript
// Comments use //

// Contracts are defined as blocks
contract MyContract {
    // Constants (immutable)
    const recipient = "0x1234567890abcdef...";
    const amount = 100.0;
    
    // State variables (mutable, persisted)
    state balance = 0.0;
    state locked = false;
    
    // Functions
    function transfer() {
        if (!locked) {
            transaction transfer {
                to: recipient,
                amount: amount,
                type: "token_transfer"
            }
            balance += amount;
        }
    }
    
    function lock() {
        locked = true;
        return "Locked";
    }
}
```

### Built-in Functions

- `transfer(to, amount)` - Send tokens
- `get_balance(address)` - Query wallet balance
- `get_time()` - Get current Unix timestamp
- `call_contract(address, function, params)` - Call another contract
- `emit_event(name, data)` - Emit event
- `log(message)` - Write to log
- `require(condition, message)` - Assert condition
- `revert(message)` - Stop execution with error

### Example Contracts

**Simple Payment**
```javascript
contract Payment {
    const recipient = "0xBob";
    const amount = 50.0;
    
    function execute() {
        transaction transfer {
            to: recipient,
            amount: amount,
            memo: "Payment for services"
        }
        return "Payment sent";
    }
}
```

**Escrow Contract**
```javascript
contract Escrow {
    const buyer = "0xAlice";
    const seller = "0xBob";
    const amount = 1000.0;
    
    state locked = true;
    state completed = false;
    
    function confirm_delivery() {
        require(msg.sender == buyer, "Only buyer can confirm");
        completed = true;
        locked = false;
        
        transaction transfer {
            to: seller,
            amount: amount,
            memo: "Escrow release"
        }
        
        return "Escrow completed";
    }
    
    function cancel() {
        require(!completed, "Already completed");
        locked = false;
        
        transaction transfer {
            to: buyer,
            amount: amount,
            memo: "Escrow cancelled"
        }
        
        return "Escrow cancelled";
    }
}
```

## Architecture

### Components

```
pswallet (CLI)
  ├─ Wallet (wallet.hpp/cpp)
  │   ├─ Wallet creation and management
  │   ├─ Key generation (RSA 4096)
  │   ├─ Transaction creation
  │   └─ Export/Import
  │
  ├─ BlockchainClient (blockchain_client.hpp/cpp)
  │   ├─ HTTP REST API client
  │   ├─ Balance queries
  │   ├─ Transaction submission
  │   └─ Stream subscriptions
  │
  ├─ SmartContractEngine (smart_contract.hpp/cpp)
  │   ├─ PiScript parser
  │   ├─ Sandbox enforcer
  │   ├─ Script executor
  │   └─ Contract state manager
  │
  └─ CLI (cli.hpp/cpp)
      ├─ Argument parsing
      ├─ Command routing
      ├─ Output formatting
      └─ User interaction
```

### Data Flow

```
User Input
    ↓
CLI Parser
    ├─→ Wallet Commands → Wallet Manager
    ├─→ Transaction Commands → Wallet + BlockchainClient
    ├─→ Contract Commands → SmartContractEngine
    └─→ Blockchain Commands → BlockchainClient
    ↓
Output (JSON/Table/Text)
```

### Security Model

- **Wallet Keys**: RSA 4096-bit, stored with restrictive file permissions (0600)
- **Transaction Signing**: RSA PSS padding with SHA256
- **Script Sandbox**: Prevents access to system resources, file system, network (except blockchain API)
- **Address Validation**: Enforces 0x-prefixed hex format (20-byte Ethereum-style)
- **Transaction Verification**: Signature-based authentication

## Configuration

### Environment Variables

```bash
# Blockchain node URL
export PISECURE_NODE_URL=http://my-node:3142

# Use testnet
export PISECURE_TESTNET=1

# Custom wallet directory
export PISECURE_WALLET_DIR=/custom/path

# Verbose logging
export PISECURE_VERBOSE=1
```

### Wallet Directory

Default: `~/.pisecure/wallets/` (mainnet) or `~/.pisecure-testnet/wallets/` (testnet)

Structure:
```
wallets/
├─ wallet1.json
├─ wallet2.json
└─ wallet3.json
```

## API Reference

### Wallet Class
```cpp
// Create wallet
auto wallet = Wallet::create_wallet("my_wallet", "Display Name");

// Load wallet
auto wallet = Wallet::load_wallet("my_wallet");

// List wallets
auto wallets = Wallet::list_wallets();

// Create transaction
auto tx = Wallet::create_transfer(wallet_id, recipient, amount, memo);

// Sign transaction
auto signature = Wallet::sign_transaction(tx, private_key);
```

### BlockchainClient Class
```cpp
BlockchainClient client("http://localhost:3142");

// Get balance
auto balance = client.get_balance(address);

// Get transactions
auto txs = client.get_transactions(address, limit);

// Submit transaction
auto tx_hash = client.submit_transaction(tx_json);

// Get chain info
auto info = client.get_chain_info();
```

### SmartContractEngine Class
```cpp
auto context = std::make_shared<ScriptContext>(wallet_address, contract_address);

// Execute file
auto result = SmartContractEngine::execute_file("contract.ps", context);

// Execute inline
auto result = SmartContractEngine::execute(script_code, context);

// Validate
auto error = SmartContractEngine::validate_script(script_code);
```

## Performance

- **Binary Size**: ~240 KB (ARM64 optimized)
- **Memory**: <50 MB for typical operations
- **Transaction Processing**: <100ms per transaction
- **Script Execution**: <200ms for typical contracts
- **API Latency**: Depends on blockchain node

## Troubleshooting

### Build Issues

**CMake not found**
```bash
sudo apt install cmake build-essential
```

**libcurl not found**
```bash
sudo apt install libcurl4-openssl-dev
```

**OpenSSL headers missing**
```bash
sudo apt install libssl-dev
```

**nlohmann_json missing**
```bash
sudo apt install nlohmann-json3-dev
# Or download from https://github.com/nlohmann/json
```

### Runtime Issues

**Wallet not found**
- Check wallet directory: `~/.pisecure/wallets/`
- Ensure wallet was created with correct name

**Connection refused**
- Verify blockchain node is running on specified URL
- Check firewall rules: `sudo ufw allow 3142`
- Verify node is listening: `netstat -tlnp | grep 3142`

**Permission denied (wallet operations)**
- Check wallet file permissions: `ls -la ~/.pisecure/wallets/`
- Ensure user has read/write access to wallet directory

**Script execution errors**
- Validate syntax: `pswallet validate contract.ps`
- Check for forbidden operations (exec, fork, etc.)
- Review error message for line number

## Development

### Directory Structure
```
cpp/pswallet/
├─ include/          # Header files
│   ├─ wallet.hpp
│   ├─ blockchain_client.hpp
│   ├─ smart_contract.hpp
│   └─ cli.hpp
├─ src/              # Implementation
│   ├─ main.cpp
│   ├─ wallet.cpp
│   ├─ blockchain_client.cpp
│   ├─ smart_contract.cpp
│   └─ cli.cpp
├─ build/            # Build artifacts (generated)
├─ CMakeLists.txt    # Build configuration
└─ README.md         # This file
```

### Building from Source
```bash
cd cpp/pswallet
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON ..
make -j$(nproc)
./pswallet --version
```

### Code Style
- C++17 standard
- 4-space indentation
- snake_case for functions/variables
- CamelCase for classes/structs
- Comprehensive documentation

## Distribution

The pswallet binary is automatically compiled and installed when installing PiSecure:

```bash
# Install from PiSecure repository
pip install -e /path/to/PiSecure

# Binary will be installed to:
# - /usr/local/bin/pswallet (system-wide)
# - ~/.local/bin/pswallet (user install)
```

## License

PiSecure is licensed under the MIT License. See LICENSE file in the main repository.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md in the main PiSecure repository.

## Support

- **Issues**: https://github.com/UnderhillForge/PiSecure/issues
- **Documentation**: https://pisecure.readthedocs.io/
- **Community**: [PiSecure Discord/Forum]

## Changelog

### Version 1.0.0
- Initial release
- Wallet management (create, list, export, import)
- Transaction operations (send, batch, history)
- PiScript smart contract engine
- Blockchain API integration
- Cross-platform support (Pi, Linux, Mac, Windows)

---

Built with ❤️ for Raspberry Pi and the decentralized future.
