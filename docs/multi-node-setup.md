# Multi-Node Setup Guide

Complete guide for running multiple PiSecure nodes on the same network with automatic startup.

## Quick Start

### Single Node (Default Setup)
```bash
# Install API service (starts at boot)
sudo bash scripts/setup-api-service.sh

# That's it! API server runs 24/7, seeding to network
```

### Multiple Nodes - Option 2: Different Ports
Each node gets its own port and runs 24/7:

**Node 1 (Pi #1 - 192.168.68.64):**
```bash
sudo bash scripts/setup-api-service.sh 3142
# Forward router: 3142 → 192.168.68.64:3142
```

**Node 2 (Pi #2 - 192.168.68.65):**
```bash
sudo bash scripts/setup-api-service.sh 3143
# Forward router: 3143 → 192.168.68.65:3142 (internal still 3142, external 3143)
```

**Node 3 (Pi #3 - 192.168.68.66):**
```bash
sudo bash scripts/setup-api-service.sh 3144
# Forward router: 3144 → 192.168.68.66:3142
```

### Multiple Nodes - Option 3: Hybrid (Recommended)
One full node + others mine-only:

**Node 1 (Full Seeding Node - always on):**
```bash
sudo bash scripts/setup-api-service.sh 3142
# Forward router: 3142 → 192.168.68.64:3142
```

**Nodes 2-5 (Mining Only - run when mining):**
```bash
# No service needed - just mine when you want
pisecure mine --wallet my-wallet
# OR monitor mode
pisecure monitor --wallet my-wallet
```

## Service Management

### Start/Stop Services
```bash
# Start
sudo systemctl start pisecure-api

# Stop
sudo systemctl stop pisecure-api

# Restart
sudo systemctl restart pisecure-api

# Status
sudo systemctl status pisecure-api
```

### View Logs
```bash
# Live logs (tail -f style)
sudo journalctl -u pisecure-api -f

# Last 100 lines
sudo journalctl -u pisecure-api -n 100

# Since boot
sudo journalctl -u pisecure-api -b
```

### Disable Auto-Start
```bash
sudo systemctl disable pisecure-api
sudo systemctl stop pisecure-api
```

## Router Port Forwarding

### Single Node
```
External Port: 3142 → Internal IP: 192.168.68.64:3142
Protocol: TCP
```

### Multiple Nodes (Different External Ports)
```
3142 → 192.168.68.64:3142  (Node 1)
3143 → 192.168.68.65:3142  (Node 2) 
3144 → 192.168.68.66:3142  (Node 3)
```

**Note:** Internal port stays 3142, external ports differ!

### Finding Your Router Settings
Common router admin URLs:
- `http://192.168.1.1` or `http://192.168.0.1`
- Look for: "Port Forwarding", "Virtual Servers", "NAT", or "Applications"

## Mining While API Runs

The API service **doesn't mine** - it just seeds blocks. To mine:

### Option A: Separate Mining Process
```bash
# API service running in background (seeding)
# Start mining separately
pisecure mine --wallet my-wallet
```

### Option B: Combined Service (Future Enhancement)
Create a separate mining service:
```bash
sudo bash scripts/setup-mining-service.sh my-wallet
```

## Verification

### Check API is Running
```bash
# Local check
curl http://localhost:3142/api/v1/chain

# From another Pi on same network
curl http://192.168.68.64:3142/api/v1/chain

# From internet (after port forwarding)
curl http://YOUR_PUBLIC_IP:3142/api/v1/chain
```

### Check Service Status
```bash
sudo systemctl status pisecure-api
```

Look for:
- `Active: active (running)` ✅
- `Enabled: enabled` ✅ (starts at boot)

### Test Auto-Restart
```bash
# Kill the process
sudo pkill -f "pisecure.api.server"

# Service should restart automatically (check after 10 seconds)
sleep 10 && sudo systemctl status pisecure-api
```

## Resource Usage

### Check Resource Consumption
```bash
# Memory usage
ps aux | grep pisecure.api.server

# Service resource stats
systemd-cgtop -1 | grep pisecure
```

### Adjust Resource Limits
Edit service file:
```bash
sudo nano /etc/systemd/system/pisecure-api.service

# Change these lines:
MemoryMax=512M      # Increase if needed
CPUQuota=50%        # Percentage of one CPU core

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart pisecure-api
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs for errors
sudo journalctl -u pisecure-api -n 50

# Common issues:
# - Port already in use (another process on 3142)
# - Virtual environment missing (run make install)
# - Permissions (should run as 'pi' user)
```

### Port Already in Use
```bash
# Find what's using port 3142
sudo lsof -i :3142
# or
sudo netstat -tlnp | grep 3142

# Kill the process
sudo kill <PID>
```

### Service Disabled Accidentally
```bash
sudo systemctl enable pisecure-api
sudo systemctl start pisecure-api
```

### Logs Not Appearing
```bash
# Force log output
sudo systemctl restart pisecure-api
sleep 2
sudo journalctl -u pisecure-api -n 20
```

## Network Architecture Examples

### Example 1: Home Mining Farm (4 Pis)
```
Internet → Router (129.222.3.32) → LAN
                ↓
   ┌────────────┼────────────┬─────────────┐
   │            │            │             │
Pi #1 (Full)  Pi #2       Pi #3        Pi #4
.64:3142      .65         .66          .67
API 24/7      Mine only   Mine only    Mine only
Seeding       Outbound    Outbound     Outbound
```

**Setup:**
- Pi #1: API service + port forward 3142
- Pi #2-4: No service, run miner when active

### Example 2: Always-On Network (3 Pis)
```
Internet → Router → LAN
             ↓
   ┌─────────┼─────────┐
   │         │         │
Pi #1      Pi #2     Pi #3
.64:3142   .65:3143  .66:3144
ALL ports forwarded
ALL running API 24/7
```

**Setup:**
- All Pis: API service on different ports
- Router: Forward 3142, 3143, 3144

### Example 3: Hybrid (Best of Both)
```
Internet → Router → LAN
             ↓
   ┌─────────┴──────────┬──────────┐
   │                    │          │
Pi #1 (Full)      Pi #2 (Mine)  Pi #3 (Validate)
.64:3142          .65           .66
API 24/7          No service    No service
Seeding           Mine daily    Validate daily
```

**Setup:**
- Pi #1: API service + port forward (always on)
- Pi #2: Run miner manually when needed
- Pi #3: Run validator manually when needed

## Benefits of 24/7 API Service

✅ **Network Health:**
- Always available for peers to sync from
- Improves network decentralization
- Helps new nodes bootstrap faster

✅ **Your Benefits:**
- Node stays synced even when not mining
- Faster mining startup (already synced)
- Build reputation as reliable peer

✅ **Low Resource Usage:**
- Idle API server uses ~50MB RAM
- Minimal CPU when not serving blocks
- Total power: ~3-5W for Pi Zero, ~5-10W for Pi 4

## Security Considerations

### Firewall (Recommended)
```bash
# Install firewall
sudo apt install ufw

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow PiSecure API
sudo ufw allow 3142/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Additional Security
- Change default SSH port
- Use SSH keys instead of passwords
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Monitor logs regularly: `sudo journalctl -u pisecure-api`

## Performance Tips

### Optimize for Pi Zero/1
```bash
# Reduce resource limits in service file
MemoryMax=256M
CPUQuota=40%
```

### Optimize for Pi 4/5
```bash
# Increase limits for better performance
MemoryMax=1G
CPUQuota=100%
```

### SSD vs SD Card
- **SSD/USB boot**: Much faster, more reliable
- **SD Card**: Works but slower sync, wear concerns

## Automated Setup Script

For easy deployment across multiple Pis:

```bash
#!/bin/bash
# deploy-node.sh - Run on each Pi

# Get node number as argument
NODE_NUM="${1:-1}"
BASE_PORT=3142
PORT=$((BASE_PORT + NODE_NUM - 1))

# Install PiSecure
cd ~
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure
make install

# Setup API service
sudo bash scripts/setup-api-service.sh $PORT

echo "✅ Node $NODE_NUM configured on port $PORT"
echo "Remember to forward router port $PORT → $(hostname -I | awk '{print $1}'):$PORT"
```

Run on each Pi:
```bash
# Pi #1
bash deploy-node.sh 1  # Port 3142

# Pi #2
bash deploy-node.sh 2  # Port 3143

# Pi #3
bash deploy-node.sh 3  # Port 3144
```

## Monitoring Dashboard

View all nodes from one place:

```bash
# On your main Pi or laptop
watch -n 5 '
  echo "=== Node Status ==="
  for ip in 192.168.68.64 192.168.68.65 192.168.68.66; do
    echo -n "$ip: "
    curl -s --max-time 2 http://$ip:3142/api/v1/chain 2>&1 | 
      grep -o "blocks\":[0-9]*" | cut -d: -f2 || echo "offline"
  done
'
```

## Next Steps

1. ✅ Install API service on at least one node
2. ✅ Configure router port forwarding
3. ✅ Test external connectivity
4. ✅ Set up additional nodes as needed
5. ✅ Monitor logs for any issues

Your node now contributes to network health 24/7! 🎉
