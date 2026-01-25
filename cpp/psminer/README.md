# psminer - PiSecure Hardware-Verified Mining Client

High-performance C++ mining client exclusively for Raspberry Pi platforms.

## Overview

`psminer` is the official PiSecure mining client written in C++ for maximum performance. It features:

- **Hardware-Verified Mining**: Exclusive to Raspberry Pi with PiHash algorithm
- **Real-Time TUI Monitor**: Beautiful terminal interface showing live statistics
- **Multi-Threaded**: Efficient parallel mining across CPU cores
- **ARM Optimized**: NEON SIMD and architecture-specific optimizations
- **Low Overhead**: Minimal memory footprint and CPU efficiency

## Requirements

### Hardware
- **Raspberry Pi 3, 4, 5, or Zero 2 W** (required)
- Minimum 512MB RAM (1GB+ recommended for multi-threaded mining)
- Active cooling recommended for sustained mining

### Software
- Raspberry Pi OS (Bullseye or later)
- CMake 3.12+
- GCC 7+ or Clang 6+
- ncurses development library

## Installation

### Quick Install (from release binary)

```bash
# Download latest release
wget https://github.com/UnderhillForge/PiSecure/releases/latest/download/psminer-arm64
chmod +x psminer-arm64
sudo mv psminer-arm64 /usr/local/bin/psminer
```

### Build from Source

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y cmake g++ libncurses-dev

# Clone repository
cd /home/pi/PiSecure/cpp/psminer

# Build
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Install
sudo make install
```

## Usage

### Basic Mining

```bash
# Start mining (interactive TUI)
psminer -w YOUR_WALLET_ADDRESS

# Multi-threaded mining (4 cores)
psminer -w YOUR_WALLET_ADDRESS -t 4

# Testnet mining
psminer -w YOUR_WALLET_ADDRESS --testnet
```

### Advanced Options

```bash
# High-performance mining (Pi 5)
psminer -w YOUR_WALLET_ADDRESS \
    -t 4 \
    --rounds 8 \
    --memory 512

# Background daemon mode
psminer -w YOUR_WALLET_ADDRESS \
    -t 4 \
    --daemon

# Custom blockchain node
psminer -w YOUR_WALLET_ADDRESS \
    -u http://192.168.1.100:3142
```

### Command-Line Options

```
Required:
  -w, --wallet ADDRESS       Wallet address to receive mining rewards

Optional:
  -u, --url URL              Blockchain node URL (default: http://localhost:3142)
  -d, --data-dir PATH        Data directory (default: /var/lib/pisecure)
  -t, --threads N            Number of mining threads (default: 1)
      --difficulty N         Target difficulty (default: 146)
      --testnet              Use testnet instead of mainnet

Hardware Tuning:
      --rounds N             PiHash computation rounds (default: 8)
      --memory MB            PiHash memory buffer in MB (default: 256)
      --npu                  Enable NPU acceleration (Pi 6+)

Display:
      --no-tui               Disable TUI monitor (use plain output)
  -v, --verbose              Verbose output
      --daemon               Run as background daemon

Other:
  -h, --help                 Show this help message
      --version              Show version information
```

## TUI Monitor

The interactive TUI monitor provides real-time mining statistics:

- **Mining Statistics**: Hashrate, hashes computed, blocks found, difficulty
- **Hardware Status**: CPU/GPU temperature, frequency, throttle alerts
- **Network Status**: Peer connections, blockchain height
- **Activity Log**: Recent mining events and block discoveries

### Keyboard Controls

- `Q` - Quit miner
- `R` - Force refresh display
- `P` - Pause mining
- `H` - Show detailed help

## Performance Optimization

### Recommended Settings by Model

**Raspberry Pi 5 (High Performance)**
```bash
psminer -w WALLET -t 4 --rounds 8 --memory 512
```

**Raspberry Pi 4 (Balanced)**
```bash
psminer -w WALLET -t 2 --rounds 8 --memory 256
```

**Raspberry Pi 3B+ (Efficient)**
```bash
psminer -w WALLET -t 2 --rounds 4 --memory 128
```

**Pi Zero 2 W (Low Power)**
```bash
psminer -w WALLET -t 1 --rounds 4 --memory 64
```

### Tips

1. **Enable active cooling** - Sustained mining generates heat
2. **Monitor temperatures** - TUI shows real-time temps
3. **Tune thread count** - More threads ≠ better performance
4. **Watch for throttling** - TUI alerts if CPU throttles
5. **Optimize memory** - Balance memory usage with hashrate

## Systemd Service

Run as a system service for automatic startup:

```bash
# Create service file
sudo tee /etc/systemd/system/psminer.service << EOF
[Unit]
Description=PiSecure Mining Service
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/psminer -w YOUR_WALLET_ADDRESS -t 4 --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable psminer
sudo systemctl start psminer

# Check status
sudo systemctl status psminer
```

## Validation (Non-Pi Platforms)

For validation on Mac, Windows, or Linux (non-Pi):

```bash
# Use psvalid instead (coming soon)
psvalid -w YOUR_WALLET_ADDRESS
```

`psminer` will refuse to run on non-Raspberry Pi hardware. This is by design to ensure hardware-verified proof-of-work integrity.

## Troubleshooting

### "Hardware verification failed"

**Cause**: Not running on Raspberry Pi hardware  
**Solution**: Use `psvalid` for non-Pi validation

### Low hashrate

**Causes**: Thermal throttling, insufficient power, too many threads  
**Solutions**: 
- Check TUI for throttle warnings
- Reduce thread count
- Improve cooling
- Use quality power supply (3A+ for Pi 4/5)

### High temperature

**Causes**: No cooling, high ambient temperature, overclocking  
**Solutions**:
- Add heatsink/fan
- Reduce thread count or rounds
- Lower clock speed
- Improve ventilation

### TUI not displaying correctly

**Causes**: Terminal size too small, ncurses issues  
**Solutions**:
- Resize terminal (minimum 80x24)
- Update ncurses: `sudo apt-get install --reinstall libncurses6`
- Use `--no-tui` for plain text output

## Development

### Building

```bash
cd /home/pi/PiSecure/cpp/psminer
mkdir build && cd build

# Debug build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)

# Release build (optimized)
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### Testing

```bash
# Run unit tests (if BUILD_TESTS=ON)
cd build
ctest -V
```

### Project Structure

```
psminer/
├── include/           # Header files
│   ├── cli.hpp
│   ├── miner.hpp
│   ├── monitor_tui.hpp
│   └── hardware_verifier.hpp
├── src/               # Implementation
│   ├── main.cpp
│   ├── cli.cpp
│   ├── miner.cpp
│   ├── monitor_tui.cpp
│   └── hardware_verifier.cpp
├── CMakeLists.txt
└── README.md
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../../docs/contributing.md) for guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details

## Support

- **Documentation**: https://github.com/UnderhillForge/PiSecure/docs
- **Issues**: https://github.com/UnderhillForge/PiSecure/issues
- **Discord**: https://discord.gg/pisecure

---

**Built with ❤️ for the Raspberry Pi mining community**
