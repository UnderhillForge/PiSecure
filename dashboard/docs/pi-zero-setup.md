# PiSecure Pi Zero 2 W Setup Guide

This guide walks through setting up a Raspberry Pi Zero 2 W as the initial PiSecure network node with full web dashboard and remote management capabilities.

## Hardware Requirements

- **Raspberry Pi Zero 2 W** (512MB RAM, 1GHz quad-core)
- **MicroSD Card** (32GB or larger, Class 10)
- **Power Supply** (official Raspberry Pi PSU recommended)
- **Ethernet or WiFi** (for network connectivity)

## OS Installation

### 1. Download Raspberry Pi OS Lite (32-bit)

```bash
# Download the latest 32-bit Lite image
wget https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2023-12-11/2023-12-11-raspios-bullseye-armhf-lite.img.xz

# Verify download integrity
sha256sum 2023-12-11-raspios-bullseye-armhf-lite.img.xz
```

### 2. Flash to MicroSD Card

```bash
# Find your SD card device
lsblk

# Flash the image (replace /dev/sdX with your device)
xzcat 2023-12-11-raspios-bullseye-armhf-lite.img.xz | sudo dd of=/dev/sdX bs=4M status=progress

# Flush writes
sync
```

### 3. Initial Configuration

Mount the boot partition and configure SSH and WiFi:

```bash
# Mount boot partition
sudo mount /dev/sdX1 /mnt

# Enable SSH
sudo touch /mnt/ssh

# Configure WiFi (if using wireless)
sudo tee /mnt/wpa_supplicant.conf > /dev/null << EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiSSID"
    psk="YourWiFiPassword"
    key_mgmt=WPA-PSK
}
EOF

# Unmount
sudo umount /mnt
```

### 4. First Boot

Insert the SD card, connect power, and wait for boot. The Pi will connect to your WiFi network.

Find the IP address:
```bash
# On your router admin panel, or use:
nmap -sn 192.168.1.0/24  # Adjust subnet as needed
```

SSH into the Pi:
```bash
ssh pi@192.168.1.xxx  # Default password: raspberry
```

## PiSecure Installation

### 1. System Update

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required tools
sudo apt install -y git curl wget htop
```

### 2. PiSecure Dashboard Installation

```bash
# Download and run the installation script
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/dashboard/scripts/install.sh | bash
```

This script will:
- ✅ Check hardware compatibility
- ✅ Install system dependencies (Python, Nginx, etc.)
- ✅ Create Python virtual environment
- ✅ Install PiSecure and dashboard components
- ✅ Configure systemd services
- ✅ Setup Nginx reverse proxy
- ✅ Optimize for Pi Zero 2 W hardware

### 3. Post-Installation Setup

The installation script will display completion information. The dashboard will be available at:
- **Local**: http://localhost
- **Network**: http://[pi-ip-address]

## Initial Configuration

### 1. Access the Dashboard

Open your browser and navigate to `http://[pi-ip-address]`

### 2. Bootstrap the Network

```bash
# Initialize PiSecure with genesis block
sudo systemctl start pisecure-dashboard

# Check dashboard is running
sudo systemctl status pisecure-dashboard

# Bootstrap blockchain from GitHub
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/network/bootstrap.sh | bash
```

### 3. Create Your First Wallet

```bash
# Access PiSecure CLI
source /opt/pisecure/venv/bin/activate
cd /opt/pisecure

# Create wallet
pisecure create-wallet "primary_wallet" --name "Pi Zero Primary"

# List wallets
pisecure show-wallet
```

### 4. Start Mining

```bash
# Start mining service
sudo systemctl enable pisecure-mining
sudo systemctl start pisecure-mining

# Check mining status
sudo systemctl status pisecure-mining
```

## Dashboard Features

### System Monitoring
- **CPU Usage**: Real-time CPU utilization with temperature
- **Memory**: RAM usage and swap statistics
- **Disk**: Storage usage and I/O statistics
- **Network**: Bandwidth usage and connection status

### Blockchain Explorer
- **Block Browser**: View recent blocks and transactions
- **Network Stats**: Difficulty, hashrate, peer count
- **Transaction History**: Recent transfers and mining rewards
- **Chain Validation**: Blockchain integrity status

### Mining Dashboard
- **Hashrate**: Current mining performance (MH/s)
- **Blocks Found**: Successful mining statistics
- **Mining Uptime**: Service availability
- **Temperature**: Hardware thermal monitoring

### Network Status
- **Connected Peers**: Active network connections
- **Sync Progress**: Blockchain download status
- **Network Health**: Overall network performance
- **Geographic Distribution**: Peer location diversity

### Wallet Management
- **Balance Tracking**: Token balances across wallets
- **Transaction History**: Transfer records and mining rewards
- **Address Management**: Wallet addresses and labels
- **Security Status**: Wallet encryption and backup status

## Remote Management

### SSH Access

```bash
# Direct SSH access
ssh pi@pisecure-node.local

# Key-based authentication (recommended)
ssh-copy-id pi@pisecure-node.local
```

### Web Dashboard Access

```bash
# Local access
curl http://localhost

# Remote access (if exposed)
curl http://pisecure-node.duckdns.org
```

### Service Management

```bash
# Check all PiSecure services
sudo systemctl status 'pisecure-*'

# Restart dashboard
sudo systemctl restart pisecure-dashboard

# View logs
journalctl -u pisecure-dashboard -f
```

## Auto-Update Configuration

### 1. GitHub Webhook Setup

1. Go to your GitHub repository settings
2. Navigate to "Webhooks" → "Add webhook"
3. Configure webhook:
   - **Payload URL**: `http://your-pi-ip:5001/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Generate a secure random string
   - **Events**: Select "Pushes" only

### 2. Configure Webhook Secret

```bash
# Edit webhook handler
sudo nano /opt/pisecure/dashboard/web/webhook.py

# Update WEBHOOK_SECRET with your GitHub secret
WEBHOOK_SECRET = "your-actual-webhook-secret"
```

### 3. Enable Webhook Service

```bash
# Enable and start webhook service
sudo systemctl enable pisecure-webhook
sudo systemctl start pisecure-webhook

# Test webhook (should respond with 'ignored' for test payload)
curl -X POST http://localhost:5001/webhook/github \
  -H "Content-Type: application/json" \
  -d '{"test": "payload"}'
```

## Performance Optimization

### Memory Management
The dashboard is optimized for the Pi Zero's 512MB RAM:

```bash
# Check memory usage
htop

# Monitor PiSecure processes
ps aux | grep pisecure

# Memory limits are set in systemd services:
# - Dashboard: 256MB limit
# - Mining: 128MB limit
```

### CPU Optimization
```bash
# Check CPU frequency
vcgencmd measure_clock arm

# Monitor temperatures
vcgencmd measure_temp

# CPU governor is set to 'performance' for mining
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

### Storage Management
```bash
# Monitor disk usage
df -h

# Blockchain data location
du -sh /var/lib/pisecure/blockchain/

# Log rotation is configured for small storage
ls -la /var/log/pisecure/
```

## Networking

### Local Network Access

```bash
# Find Pi on local network
avahi-browse -a | grep pisecure

# Or use nmap
nmap -sn 192.168.1.0/24
```

### Remote Access (Optional)

#### DuckDNS Setup
```bash
# Install DuckDNS client
echo "yourdomain.duckdns.org" > /opt/pisecure/dashboard/duckdns-domain

# Create update script
cat > /opt/pisecure/dashboard/update-duckdns.sh << 'EOF'
#!/bin/bash
DOMAIN=$(cat /opt/pisecure/dashboard/duckdns-domain)
TOKEN="your-duckdns-token"
curl "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip="
EOF

# Make executable and add to cron
chmod +x /opt/pisecure/dashboard/update-duckdns.sh
(crontab -l ; echo "*/5 * * * * /opt/pisecure/dashboard/update-duckdns.sh") | crontab -
```

#### WireGuard VPN (Advanced)
```bash
# Install WireGuard
sudo apt install -y wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure VPN (consult WireGuard documentation)
```

## Monitoring & Alerts

### Log Monitoring

```bash
# View all PiSecure logs
journalctl -u pisecure-dashboard -u pisecure-mining --since today

# Follow logs in real-time
journalctl -f -u pisecure-dashboard
```

### Health Checks

```bash
# Check service health
sudo systemctl is-active pisecure-dashboard

# Test dashboard response
curl -f http://localhost/api/system/stats

# Check mining process
pgrep -f "pisecure mine"
```

### Automated Alerts (Optional)

```bash
# Install monitoring tools
sudo apt install -y monit

# Configure alerts for:
# - Service failures
# - High temperature
# - Low disk space
# - Network disconnection
```

## Backup & Recovery

### System Backup

```bash
# Create system backup
sudo tar -czf /var/lib/pisecure/backups/system-$(date +%Y%m%d).tar.gz \
    /opt/pisecure \
    /etc/pisecure \
    /var/lib/pisecure

# Backup blockchain data
cp /var/lib/pisecure/blockchain/chain.json /var/lib/pisecure/backups/
```

### Wallet Backup

```bash
# Export wallets
pisecure export-wallet /var/lib/pisecure/backups/wallets-$(date +%Y%m%d).json

# Secure the backup (encrypt with GPG, etc.)
```

## Troubleshooting

### Dashboard Won't Start

```bash
# Check service status
sudo systemctl status pisecure-dashboard

# Check logs
journalctl -u pisecure-dashboard -n 50

# Manual start for debugging
sudo -u pi /opt/pisecure/venv/bin/python /opt/pisecure/dashboard/web/app.py
```

### High Memory Usage

```bash
# Check memory usage
ps aux --sort=-%mem | head -10

# Restart services if needed
sudo systemctl restart pisecure-dashboard

# Check for memory leaks in logs
grep -i memory /var/log/pisecure/dashboard.log
```

### Mining Issues

```bash
# Check hardware verification
pisecure verify-hardware

# Check mining service
sudo systemctl status pisecure-mining

# Monitor hashrate
tail -f /var/log/pisecure/mining.log
```

### Network Issues

```bash
# Check connectivity
ping 8.8.8.8

# Test peer discovery
pisecure network-status

# Check firewall
sudo ufw status
```

## Next Steps

Once your Pi Zero 2 W is set up and running:

1. **Monitor Performance**: Use the dashboard to track system health
2. **Expand Network**: Help other users join the PiSecure network
3. **Contribute**: Submit issues and improvements to the project
4. **Scale Up**: Consider adding more nodes as the network grows

Your Pi Zero 2 W is now a fully functional PiSecure network node with comprehensive monitoring, remote management, and automatic updates!