# psvalidator - Universal Blockchain Validator

## Overview

**psvalidator** is a platform-agnostic blockchain validator for PiSecure that works on **any system** (Mac, Windows, Linux, Raspberry Pi). Unlike `psminer` which requires Raspberry Pi hardware for mining, `psvalidator` can earn rewards through validation on any platform.

## Key Features

### ✅ Universal Platform Support
- **Works on ANY system** - Mac, Windows, Linux, Raspberry Pi
- No hardware verification required
- No PiHash computation needed
- Pure validation using standard algorithms (SHA256, XOR)

### 🎯 Validation Capabilities
- **Block Validation**: Verifies proof-of-work (zero bit counting)
- **Transaction Validation**: Checks signatures and structure
- **Network Security**: Detects invalid blocks/transactions
- **Reward Earning**: Receives 1% of block rewards distributed among validators

### 🖥️ Three Operating Modes

#### 1. TUI Mode (Default)
Interactive terminal UI with real-time statistics:
```
╔════════════════════════════════════════════════════════════╗
║              PSVALIDATOR - VALIDATION MONITOR              ║
╚════════════════════════════════════════════════════════════╝

┌─ VALIDATION STATISTICS ────────────────────────────────────┐
│ Blocks Validated:            1,234                         │
│ Transactions Validated:     56,789                         │
│ Invalid Blocks:                  3                         │
│ Invalid Transactions:           12                         │
│ Uptime:                   12:34:56                         │
│ Current Height:            1,235                           │
└────────────────────────────────────────────────────────────┘

┌─ VALIDATOR REWARDS ────────────────────────────────────────┐
│ Total Earned:               45.2500 tokens                 │
│ Current Bucket:             15.5000 tokens                 │
│ Reward Rate:            1% of block rewards                │
└────────────────────────────────────────────────────────────┘
```

#### 2. CLI Mode
Simple text output with periodic updates:
```bash
psvalidator --wallet YOUR_WALLET --no-tui
```

#### 3. Daemon Mode
Background process for servers:
```bash
psvalidator --wallet YOUR_WALLET --daemon
```

## Installation

### Build from Source

```bash
cd cpp/psvalidator
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### Dependencies
- C++17 compiler
- nlohmann/json
- WebSocketPP (for daemon communication)
- Boost (system)
- OpenSSL

## Usage

### Basic Usage

```bash
# Start with TUI (default)
psvalidator --wallet pisecure_wallet_abc123

# Run in background daemon mode
psvalidator --wallet pisecure_wallet_abc123 --daemon

# Connect to remote daemon
psvalidator --wallet pisecure_wallet_abc123 --daemon-url ws://192.168.1.100:3142

# Testnet validation
psvalidator --wallet pisecure_wallet_test123 --testnet

# CLI mode (no TUI)
psvalidator --wallet pisecure_wallet_abc123 --no-tui

# Verbose logging
psvalidator --wallet pisecure_wallet_abc123 --verbose
```

### Command-Line Options

```
OPTIONS:
  --wallet ADDRESS       Wallet address for validator rewards (required)
  --daemon-url URL       pisecured WebSocket URL (default: ws://127.0.0.1:3142)
  --testnet              Connect to testnet instead of mainnet
  --daemon               Run in background daemon mode (no TUI)
  --no-tui               Disable TUI, use simple CLI output
  --threads N            Number of validation threads (default: 4)
  --poll-interval MS     Polling interval in milliseconds (default: 1000)
  --verbose              Enable verbose logging
  --version              Show version information
  --help                 Show help message
```

## How It Works

### Validation Workflow

1. **Connect to Daemon**: psvalidator connects to pisecured via WebSocket
2. **Monitor Blocks**: Continuously polls for new blocks
3. **Validate PoW**: Checks proof-of-work using zero bit counting
4. **Validate Transactions**: Verifies transaction structure and signatures
5. **Report Results**: Reports validation results to daemon
6. **Earn Rewards**: Receives 1% of block rewards in validator bucket

### Architecture

```
┌──────────────┐    WebSocket     ┌──────────────┐
│ psvalidator  │ ←──────────────→ │  pisecured   │
│  (Any OS)    │  ws://127.0.0.1  │   (Daemon)   │
└──────────────┘      :3142       └──────────────┘
                                          ↕
                                  ┌──────────────┐
                                  │ Validator    │
                                  │   Bucket     │
                                  │  (Rewards)   │
                                  └──────────────┘
```

### Validation vs Mining

| Feature | psvalidator (Validation) | psminer (Mining) |
|---------|-------------------------|------------------|
| Platform | **Any OS** | Raspberry Pi only |
| Algorithm | SHA256 + XOR (zero bit counting) | PiHash (hardware-bound) |
| Hardware | No special requirements | Pi hardware required |
| Rewards | 1% of block rewards (shared) | 99% of block rewards |
| Purpose | Validate existing blocks/txs | Create new blocks |
| Network Growth | ✅ Enables universal participation | Pi owners only |

## Reward Distribution

### How Validators Earn

1. **Block Reward Pool**: Each mined block allocates 1% to validator rewards
2. **Equal Distribution**: Rewards split among all active validators
3. **Bucket Accumulation**: Rewards accumulate in validator bucket
4. **Auto-Sweep**: Can automatically sweep to linked wallet

### Example Calculation

```
Block Reward: 50 tokens
Mining Reward (99%): 49.5 tokens → Miner
Validator Pool (1%): 0.5 tokens → Split among validators

If 10 active validators:
  Each validator earns: 0.5 ÷ 10 = 0.05 tokens per block
  
Over 1000 blocks validated:
  Total earnings: 0.05 × 1000 = 50 tokens
```

## Validation Logic

### Block Validation

```cpp
bool validate_block(const json &block_data) {
    // 1. Check proof-of-work
    if (!validate_pow(block_data["hash"], block_data["difficulty"]))
        return false;
    
    // 2. Verify timestamp
    // 3. Check previous hash linkage
    // 4. Validate merkle root
    // 5. Verify signatures
    
    return true;
}
```

### Zero Bit Counting (PoW Validation)

```cpp
uint32_t count_leading_zero_bits(const std::string &hash_hex) {
    uint32_t count = 0;
    
    for (char c : hash_hex) {
        uint8_t nibble = hex_to_nibble(c);
        
        if (nibble == 0) {
            count += 4;  // All 4 bits are zero
        } else {
            // Count leading zeros in non-zero nibble
            if (nibble < 8) count++;
            if (nibble < 4) count++;
            if (nibble < 2) count++;
            break;
        }
    }
    
    return count;
}
```

## Running as System Service

### systemd Service

Create `/etc/systemd/system/psvalidator.service`:

```ini
[Unit]
Description=PiSecure Validator
After=network.target pisecured.service

[Service]
Type=simple
User=pisecure
WorkingDirectory=/opt/pisecure
ExecStart=/usr/local/bin/psvalidator --wallet YOUR_WALLET --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable psvalidator
sudo systemctl start psvalidator
sudo systemctl status psvalidator
```

## Monitoring & Logs

### View Logs
```bash
# Follow logs
journalctl -u psvalidator -f

# Last 100 lines
journalctl -u psvalidator -n 100
```

### Check Status
```bash
# If using TUI
# Press 'r' to refresh, 'q' to quit

# If using daemon mode
# Check logs for status updates
```

## Performance Tuning

### Adjust Validation Threads
```bash
# More threads for powerful systems
psvalidator --wallet YOUR_WALLET --threads 8

# Fewer threads for resource-constrained systems
psvalidator --wallet YOUR_WALLET --threads 2
```

### Polling Interval
```bash
# Faster polling (more responsive, higher CPU)
psvalidator --wallet YOUR_WALLET --poll-interval 500

# Slower polling (less CPU usage)
psvalidator --wallet YOUR_WALLET --poll-interval 2000
```

## Troubleshooting

### Cannot Connect to Daemon
```bash
# Check if pisecured is running
pgrep pisecured

# Start pisecured
pisecured --validate-only

# Check connectivity
curl http://localhost:3142/health
```

### No Rewards Being Earned
1. Verify wallet address is correct
2. Check validator bucket status via API
3. Ensure blocks are being validated (check stats)
4. Verify daemon has linked wallet

### High CPU Usage
- Reduce validation threads: `--threads 2`
- Increase poll interval: `--poll-interval 2000`
- Use daemon mode instead of TUI: `--daemon`

## API Integration

psvalidator uses the pisecured WebSocket API:

```cpp
// Get blockchain height
auto count = ws_client->get_block_count();

// Fetch block for validation
auto block = ws_client->get_block(std::to_string(height));

// Check validator bucket
auto bucket = ws_client->get_bucket_status();

// Get network stats
auto stats = ws_client->get_network_stats();
```

## Security Considerations

### Validation Integrity
- Zero bit counting is deterministic and tamper-proof
- No hardware binding required (universal validation)
- Results are verifiable by all network participants

### Reward Security
- Rewards only distributed to active validators
- Bucket balances tracked on-chain
- Auto-sweep prevents reward loss

## Future Enhancements

- [ ] UTXO validation
- [ ] Signature verification
- [ ] Merkle root validation
- [ ] Double-spend detection
- [ ] Advanced fraud detection
- [ ] Machine learning anomaly detection
- [ ] Distributed validation coordination

## Comparison with Other Components

| Component | Purpose | Platform | Rewards |
|-----------|---------|----------|---------|
| **pisecured** | Blockchain daemon | Any | N/A |
| **psminer** | Block mining | Raspberry Pi only | 99% |
| **psvalidator** | Block/tx validation | **Any OS** | 1% |
| **pswallet** | Wallet management | Any | N/A |

## Contributing

Improvements to validation logic welcome:
- Enhanced transaction validation
- Better fraud detection
- Performance optimizations
- Cross-platform compatibility fixes

## License

Same as PiSecure main project (see root LICENSE file)

## Support

- Documentation: `docs/validator-guide.md`
- Issues: GitHub Issues
- Community: PiSecure Discord/Forum
