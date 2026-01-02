# PiSecure Installation Guide

This guide covers the complete installation process for PiSecure on Raspberry Pi devices.

## System Requirements

### Hardware Requirements

- **Raspberry Pi**: Any model (Zero W, 3, 4, 5, etc.)
- **Storage**: Minimum 8GB SD card (16GB+ recommended)
- **RAM**: 512MB minimum (1GB+ recommended)
- **Network**: Ethernet or WiFi connectivity

### Software Requirements

- **OS**: Raspberry Pi OS (32-bit or 64-bit)
- **Python**: 3.7+ (pre-installed on Raspberry Pi OS)
- **Internet**: Required for initial installation and updates

### Verified Hardware

PiSecure includes hardware verification to ensure only authorized Raspberry Pi devices can participate in mining:

```bash
pisecure verify-hardware
# ✅ Hardware verification PASSED!
# 📱 Device: Raspberry Pi 4 Model B
# 🎯 Confidence: 95.2%
# 🔒 Anti-spoofing: ✅
```

## Installation Methods

### Method 1: One-Command Installation (Recommended)

```bash
# Fresh Raspberry Pi installation
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash
```

This automated installer will:
- ✅ Install all system dependencies
- ✅ Create PiSecure service user
- ✅ Clone and install PiSecure
- ✅ Configure firewall and security
- ✅ Generate unique hostname
- ✅ Create default mining wallet
- ✅ Install system-wide commands
- ✅ Configure automatic services
- ✅ Set up update monitoring

### Method 2: Manual Installation

For custom installations or development:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3 python3-pip python3-venv git curl jq nginx ufw fail2ban avahi-daemon unattended-upgrades

# 3. Clone repository
git clone https://github.com/UnderhillForge/PiSecure.git /opt/pisecure
cd /opt/pisecure

# 4. Install PiSecure
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 5. Run setup scripts
sudo ./install.sh
```

## Post-Installation Setup

### Verify Installation

```bash
# Check system status
pisecure status

# Verify wallet creation
pisecure wallet

# Check dashboard
curl http://localhost:5000
```

### Access Points

After successful installation:

- **Web Dashboard**: http://pisecure-node-xxxxx.local
- **Direct Access**: http://[your-pi-ip]:5000
- **Wallet Management**: http://pisecure-node-xxxxx.local/wallet
- **SSH Access**: ssh pi@pisecure-node-xxxxx.local

### Default Credentials

- **SSH**: pi / raspberry (change immediately)
- **Web Interface**: No authentication required (local network only)

## Configuration

### Basic Configuration

PiSecure is configured via `/etc/pisecure/config.json`:

```json
{
  "network": {
    "listen_port": 3141,
    "max_connections": 10
  },
  "mining": {
    "enabled": true,
    "max_temperature": 70
  },
  "dashboard": {
    "enabled": true,
    "port": 5000
  }
}
```

### Advanced Configuration

```bash
# Edit configuration
sudo nano /etc/pisecure/config.json

# Restart services
sudo systemctl restart pisecure-mining pisecure-dashboard
```

## Security Setup

### Initial Security Configuration

**CRITICAL**: Complete these steps to secure your installation:

```bash
# 1. Change default password
passwd

# 2. Generate update signing keys (on secure system)
pisecure generate-signing-key

# 3. Register your public key
pisecure register-update-key developer_key /path/to/public_key.pem

# 4. Set signature threshold
pisecure set-update-threshold 1

# 5. Verify setup
pisecure list-update-keys
```

### Firewall Configuration

PiSecure automatically configures UFW firewall:

```bash
# Check firewall status
sudo ufw status

# Should show:
# Status: active
# 22/tcp                     ALLOW       Anywhere    # SSH
# 5000/tcp                   ALLOW       Anywhere    # Dashboard
# 3141/tcp                   ALLOW       Anywhere    # PiSecure P2P
```

### Service Management

```bash
# Check service status
sudo systemctl status pisecure-mining
sudo systemctl status pisecure-dashboard

# View service logs
sudo journalctl -u pisecure-mining -f
sudo journalctl -u pisecure-dashboard -f

# Restart services
sudo systemctl restart pisecure-mining
```

## Wallet Setup

### Automatic Wallet Creation

The installer automatically creates a unique wallet:

```bash
pisecure wallet

# Output:
# 🏦 node-406f0f (PiSecure Node Wallet)
# Address: 0daf50d046f42f591d296b773c7d1155
# Balance: 0.000000 tokens
```

### Manual Wallet Creation

```bash
# Create additional wallets
pisecure create-wallet my_wallet "My Personal Wallet"

# List all wallets
pisecure wallet
```

## Network Configuration

### Hostname Configuration

PiSecure automatically sets unique hostnames:

```bash
hostname
# Output: pisecure-node-406f0f

# Access via:
# http://pisecure-node-406f0f.local
```

### Peer Discovery

PiSecure automatically discovers peers:

```bash
# Check connected peers
pisecure status

# Bootstrap peers from GitHub
# Automatic peer exchange via blockchain
```

## Update Configuration

### Automatic Updates

PiSecure includes automatic update monitoring:

```bash
# Check for updates
pisecure check-updates

# View update status
pisecure update-status

# Manual update application
pisecure check-updates --apply
```

### Update Security

Updates require cryptographic authorization:

```bash
# Only authorized developers can create updates
# Updates must be signed with registered keys
# Multi-signature support available
```

## Troubleshooting Installation

### Common Issues

#### Installation Fails

```bash
# Check system requirements
python3 --version
pip3 --version

# Verify internet connectivity
ping -c 3 google.com

# Check disk space
df -h
```

#### Services Won't Start

```bash
# Check service status
sudo systemctl status pisecure-mining
sudo systemctl status pisecure-dashboard

# View detailed logs
sudo journalctl -u pisecure-mining --no-pager -n 50
sudo journalctl -u pisecure-dashboard --no-pager -n 50

# Restart services
sudo systemctl restart pisecure-mining pisecure-dashboard
```

#### Dashboard Not Accessible

```bash
# Check if service is running
sudo systemctl status pisecure-dashboard

# Check firewall
sudo ufw status

# Test local access
curl http://localhost:5000

# Check hostname resolution
avahi-resolve-host-name pisecure-node-xxxxx.local
```

#### Mining Not Working

```bash
# Verify hardware
pisecure verify-hardware

# Check mining service
sudo systemctl status pisecure-mining

# View mining logs
sudo journalctl -u pisecure-mining -f
```

### Recovery Procedures

#### Reinstall PiSecure

```bash
# Stop services
sudo systemctl stop pisecure-mining pisecure-dashboard

# Remove installation
sudo rm -rf /opt/pisecure
sudo rm -rf /var/lib/pisecure
sudo rm -rf /etc/pisecure

# Reinstall
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash
```

#### Reset Configuration

```bash
# Backup wallet data
sudo cp -r /var/lib/pisecure /var/lib/pisecure.backup

# Reset configuration
sudo rm /etc/pisecure/config.json
sudo ./install.sh
```

## Performance Optimization

### For Raspberry Pi Zero W

```bash
# Reduce mining intensity
sudo nano /etc/pisecure/config.json
# Set: "max_temperature": 60

# Disable unnecessary services
sudo systemctl disable avahi-daemon
```

### For Raspberry Pi 4/5

```bash
# Enable full mining capacity
sudo nano /etc/pisecure/config.json
# Set: "max_temperature": 75

# Optimize network settings
sudo nano /etc/sysctl.conf
# Add: net.core.somaxconn=1024
```

## Verification Checklist

After installation, verify:

- [ ] PiSecure services are running
- [ ] Web dashboard is accessible
- [ ] Wallet was created automatically
- [ ] Firewall is configured
- [ ] Hostname is set correctly
- [ ] Update keys are configured (if applicable)
- [ ] Mining is active
- [ ] Peer connections established

## Getting Help

### Documentation
- Main documentation: `/path/to/PiSecure_Docs/README.md`
- CLI help: `pisecure --help`
- Command help: `pisecure <command> --help`

### Logs and Diagnostics

```bash
# System logs
sudo journalctl -u pisecure-mining
sudo journalctl -u pisecure-dashboard

# PiSecure logs
tail -f /var/log/pisecure/pisecure.log

# Generate diagnostic report
pisecure status > diagnostic.txt
pisecure update-status >> diagnostic.txt
```

---

**Installation Complete**: Your PiSecure node is now ready for decentralized blockchain operations!