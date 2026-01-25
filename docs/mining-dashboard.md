# PiSecure Mining Dashboard

Interactive real-time mining dashboard inspired by HandyMiner-CLI, optimized for Raspberry Pi hardware monitoring.

## Features

### 📊 Real-Time Metrics
- **Mining Status**: Current hashrate, nonce attempts, best zero count progress
- **Hardware Health**: CPU temperature with sparklines, thermal throttle status, memory usage
- **Session Stats**: Blocks found, rewards earned, uptime, average block time
- **Blockchain State**: Total blocks, pending transactions, chain validity

### 📈 Sparkline Charts
- **Hashrate History**: Last 60 samples of mining speed (H/s)
- **Temperature History**: CPU temp trends over time
- **Zero Count Progress**: Visual progress toward difficulty target

### 🔗 Syndicate (Pool) Mode
- **Pool Statistics**: Total members, combined hashrate, blocks found
- **Your Contribution**: Share percentage, rank by hashpower, rewards earned
- **Member List**: Active syndicate members with Pi models and performance
- **Graceful Fallback**: Dashboard works even when syndicate unavailable

### 🎨 Rich Terminal UI
- Color-coded temperature alerts (green < 70°C, yellow 70-75°C, red > 75°C)
- Live updating panels with 1-second refresh (configurable)
- Throttle status indicators (NORMAL, LIGHT, HEAVY, PAUSED, EMERGENCY)
- Clean layout with header, mining status, hardware, session, and blockchain panels

## Usage

### Basic Usage
```bash
# Watch existing mining activity (dashboard only)
pisecure monitor

# Mine and display dashboard in one command
pisecure monitor --wallet pi_test --testnet

# Mine with balance limit
pisecure monitor --wallet pi_miner --limit 100

# Enable safe mode (thermal throttling)
pisecure monitor --wallet pi_test --safe-mode --testnet

# Custom refresh rate (2 seconds)
pisecure monitor --refresh-rate 2.0
```

### Command Options
```
--mode [solo|syndicate|auto]     Mining mode (default: auto)
--refresh-rate FLOAT              Dashboard refresh in seconds (default: 1.0)
--member-id TEXT                  Syndicate member ID for pool mode
--testnet                         Connect to testnet blockchain
--wallet TEXT                     Start mining with this wallet (enables auto-mining)
--limit INTEGER                   Stop when wallet reaches this balance
--safe-mode                       Enable thermal throttling and memory management
```

### Mining + Dashboard
The most powerful feature is combining mining and monitoring in one command:

```bash
# Start mining in background, show live dashboard
pisecure monitor --wallet pi_test --testnet

# Mine until wallet has 500 314ST tokens
pisecure monitor --wallet pi_miner --limit 500

# Safe mode for long mining sessions (prevents overheating)
pisecure monitor --wallet pi_test --safe-mode
```

### Dashboard Only (Watch Mode)
If you're already mining in another terminal, launch dashboard without `--wallet`:

```bash
# Terminal 1: Start mining
pisecure mine --wallet pi_miner --testnet

# Terminal 2: Watch dashboard
pisecure monitor --testnet
```

## Dashboard Layout

```
┌──────────────────────────────────────────────────────────┐
│ πSecure Mining Dashboard | MAINNET | ⛏️  Solo Mining     │
└──────────────────────────────────────────────────────────┘
┌─────────────────────────┬───────────────────────────────┐
│ ⛏️  Mining Status        │ 🖥️  Hardware Health           │
│                         │                               │
│ 🟢 Status  ACTIVE       │ 🌡️  CPU Temp  63.7°C ▁▂▃▄▅   │
│ ⚡ Hashrate 1.2 H/s ▂▃▄│ 🚦 Throttle  NORMAL           │
│ 🎯 Progress 142/146 (97%)│ 💾 Memory   46.5%            │
│ 🔢 Nonce   12,345       │ 🔧 Hardware Raspberry Pi 5   │
│ 🔨 Hashes  12,345       │                               │
│ ⏱️  Est. Time 45s       │                               │
├─────────────────────────┼───────────────────────────────┤
│ 📊 Session Stats        │ ⛓️  Blockchain                │
│                         │                               │
│ ⏰ Uptime  5m 23s       │ ⛓️  Total Blocks  1,234       │
│ 📦 Blocks Found  3      │ 📨 Pending TXs  5             │
│ 💰 Rewards  150.00 314ST│ 🔐 Chain Valid  ✅ VALID      │
│ ⏱️  Avg Block  60s      │ 🕐 Last Block  14:23:45       │
│ 🎯 Difficulty  146 zeros│                               │
└─────────────────────────┴───────────────────────────────┘
Press Ctrl+C to exit  |  Refresh: 1.0s  |  Mode: SOLO
```

## Syndicate Mode Layout

When connected to a mining pool, additional panel shows:

```
┌─────────────────────────────────┐
│ 🔗 Syndicate Pool               │
│                                 │
│ 🏊 Pool      Pi-Edu-Farm        │
│ 👥 Members   127                │
│ ⚡ Pool Rate  127.4 H/s          │
│ 📊 Your Share  0.94%            │
│ 📦 Pool Blocks  456             │
│ 💰 Your Rewards  42.50 314ST    │
└─────────────────────────────────┘
```

## Testing

### Test Script
A test script is provided to verify dashboard functionality:

```bash
# Run dashboard with simulated mining
python test_dashboard.py
```

This will:
1. Load or create a test blockchain
2. Start simulated mining in background thread
3. Launch dashboard with live updates
4. Run for 5 minutes (or until Ctrl+C)

### Manual Testing
```bash
# Test system monitor
python pisecure/core/system_monitor.py

# Test dashboard import
python -c "from pisecure.monitor import MiningDashboard; print('OK')"

# Show help
pisecure monitor --help
```

## Architecture

### Components
- **monitor.py**: Main dashboard with Rich UI
- **system_monitor.py**: Hardware monitoring (CPU temp, memory, throttle)
- **blockchain.py**: Mining session tracking methods
  - `get_live_mining_stats()`: Current mining metrics
  - `get_mining_session_state()`: Session progress
- **cli.py**: `pisecure monitor` command integration

### Mining Session Tracking
The blockchain maintains a `mining_session` dictionary with:
- `active`: Mining in progress
- `start_time`: Session start timestamp
- `hashes_tried`: Total hash attempts
- `blocks_found`: Blocks mined this session
- `current_nonce`: Current nonce being tried
- `best_zeros`: Best zero count achieved
- `target_zeros`: Difficulty target
- `hashrate`: Current hashes per second

### Update Flow
1. Mine operation updates `blockchain.mining_session` every 1000 hashes
2. Dashboard calls `get_live_mining_stats()` every refresh interval
3. System monitor reads CPU temp, memory via `/proc` and `vcgencmd`
4. Rich Live() context updates all panels in place

## Performance

- **CPU Usage**: ~1-2% for dashboard display (Rich library)
- **Memory**: ~20MB additional (deque history buffers)
- **Refresh Rate**: Default 1.0s (configurable 0.5s - 5.0s)
- **History Buffer**: Last 60 samples for sparklines (~60 bytes per metric)

## Troubleshooting

### Dashboard Not Showing Mining Progress
- Ensure mining is active in another terminal
- Check that blockchain path matches (testnet vs mainnet)
- Verify mining_session is being updated in mine_block()

### Temperature Shows 0.0°C
- Ensure `vcgencmd` is accessible: `vcgencmd measure_temp`
- Check `/sys/class/thermal/thermal_zone0/temp` exists
- May need to add user to `video` group: `sudo usermod -a -G video pi`

### Syndicate Panel Shows "Not connected"
- Syndicate mode requires coordinator setup (not fully implemented)
- Use `--mode solo` until syndicate coordination is deployed
- Graceful fallback ensures dashboard still works

### Import Error: No module named 'pisecure.monitor'
- Install PiSecure: `pip install -e .`
- Or add to PYTHONPATH: `export PYTHONPATH=/home/pi/PiSecure:$PYTHONPATH`

## Future Enhancements

### Short-term
- [ ] Historical charts (hashrate over hours/days)
- [ ] Alert notifications (temperature, blocks found)
- [ ] Multi-wallet tracking in one dashboard
- [ ] Export session statistics to CSV

### Long-term
- [ ] Web dashboard version (accessible from phone/browser)
- [ ] Syndicate coordinator integration (full pool features)
- [ ] Comparison mode (solo vs syndicate earnings)
- [ ] Remote monitoring (dashboard connects to remote Pi)
- [ ] Sound notifications for block finds

## Related Documentation
- [HandyMiner-CLI](https://github.com/HandyOSS/HandyMiner-CLI) - Inspiration for dashboard design
- [Rich Library](https://github.com/Textualize/rich) - Terminal UI framework
- [PiSecure Mining](../README.md#mining) - Mining setup and configuration
- [Syndicate System](pisecure/core/syndicate.py) - Mining pool architecture
