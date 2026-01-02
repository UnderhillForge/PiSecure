# 🚀 PiSecure Launch Instructions - First Pi Setup

**Complete step-by-step guide to launch PiSecure on your first Raspberry Pi**

## 📋 Pre-Launch Checklist

### ✅ Hardware Requirements
- [ ] **Raspberry Pi 5** (4GB+ RAM recommended)
- [ ] **MicroSD Card** (32GB+ Class 10)
- [ ] **Power Supply** (Official Raspberry Pi PSU)
- [ ] **Cooling** (Case with fan or heatsinks)
- [ ] **Network** (Ethernet or WiFi connection)
- [ ] **Storage** (External SSD/USB drive optional)

### ✅ Software Prerequisites
- [ ] **Raspberry Pi OS** (64-bit Lite or Desktop)
- [ ] **Python 3.9+** installed
- [ ] **Git** installed
- [ ] **OpenSSL** and development libraries
- [ ] **PiSecure repository** cloned

## 🛠️ Step-by-Step Launch Process

### **Step 1: Hardware Setup**

```bash
# 1. Flash Raspberry Pi OS to microSD card
# Use Raspberry Pi Imager: https://www.raspberrypi.com/software/

# 2. Enable SSH and WiFi (optional)
# Create ssh file and wpa_supplicant.conf on boot partition

# 3. Insert SD card and power on Pi
# Wait for boot completion
```

### **Step 2: System Configuration**

```bash
# SSH into your Pi (or use terminal if desktop)
ssh pi@raspberrypi.local
# Password: raspberry (change immediately)

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-dev git \
                   libssl-dev libffi-dev build-essential \
                   libcurl4-openssl-dev libjansson-dev \
                   sqlite3 redis-server

# Install Python dependencies
pip3 install flask flask-cors flask-limiter cryptography requests psutil

# Clone PiSecure repository
git clone https://github.com/UnderhillForge/PiSecure.git
cd PiSecure

# Install PiSecure
pip3 install -e .
```

### **Step 3: Genesis Key Verification**

```bash
# Verify genesis keys are present
ls -la pisecure/updates/
# Should show:
# -rw------- 1 pi pi genesis_auth_priv.key
# -rw-r--r-- 1 pi pi genesis_auth_pub.key

# Test key loading
python3 -c "
from pisecure.api.economics import foundation_trust
print('Genesis key loaded:', foundation_trust.genesis_private_key is not None)
print('Public key loaded:', foundation_trust.genesis_public_key is not None)
print('Foundation address:', foundation_trust.address)
"
```

### **Step 4: Genesis Mining Setup**

```bash
# Create mining configuration
mkdir -p /etc/pisecure
cat > /etc/pisecure/config.json << EOF
{
    "node_id": "genesis-node-01",
    "mining": {
        "enabled": true,
        "wallet_address": "genesis_miner_wallet",
        "threads": 4,
        "difficulty_adjustment": true
    },
    "network": {
        "listen_port": 3142,
        "bootstrap_peers": [],
        "max_peers": 50
    },
    "api": {
        "enabled": true,
        "host": "0.0.0.0",
        "port": 3142,
        "rate_limit": "100 per minute"
    },
    "storage": {
        "blockchain_path": "/var/lib/pisecure/blockchain.json",
        "database_path": "/var/lib/pisecure/pisecure.db"
    }
}
EOF

# Create data directories
sudo mkdir -p /var/lib/pisecure
sudo chown pi:pi /var/lib/pisecure
```

### **Step 5: Launch PiSecure Node**

```bash
# Start the PiSecure node (includes mining and API)
pisecure node start --config /etc/pisecure/config.json

# Verify it's running
ps aux | grep pisecure

# Check logs
tail -f /var/log/pisecure/node.log
```

### **Step 6: Verify Genesis Mining**

```bash
# Check mining status
pisecure mining status

# Should show:
# Status: Active
# Hashrate: ~XX H/s
# Blocks mined: Starting from 0
# Current block: Mining genesis/empty blocks

# Check blockchain status
curl http://localhost:3142/api/v1/blockchain/info

# Should show initial blockchain:
{
  "blocks": 1,
  "pending_transactions": 0,
  "difficulty": 4,
  "is_valid": true,
  "latest_block": {
    "index": 0,
    "transactions": [{"type": "genesis", ...}],
    "hash": "..."
  }
}
```

### **Step 7: Foundation Trust Initialization**

```bash
# Start API server if not running
pisecure api start

# Check foundation status
curl http://localhost:3142/api/v1/foundation/status

# Should show foundation initialized with genesis key

# Create initial donation transaction (automated script will handle this)
# For manual testing:
curl -X POST http://localhost:3142/api/v1/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "type": "token_transfer",
    "sender_address": "genesis_miner_wallet",
    "recipient_address": "foundation_314st",
    "amount": 1000,
    "memo": "Initial foundation funding",
    "signature": "genesis_signature_placeholder"
  }'
```

### **Step 8: Web Dashboard Setup**

```bash
# Install dashboard dependencies
pip3 install flask-socketio python-socketio

# Start dashboard (optional - for monitoring)
cd dashboard/web
python3 app.py --host 0.0.0.0 --port 5000

# Access dashboard at: http://your-pi-ip:5000
```

### **Step 9: Automated Foundation Donations**

```bash
# Create automated donation script
cat > /home/pi/foundation_donation.py << 'EOF'
#!/usr/bin/env python3
import time
import requests
from pisecure_client import PiSecureClient

DONATION_RATE = 0.50  # Donate 50% of mining rewards

def donate_to_foundation():
    try:
        client = PiSecureClient()

        # Get current wallet balance
        balance_response = client.get_wallet_balance('genesis_miner_wallet')
        if 'error' in balance_response:
            print(f"Balance check failed: {balance_response['error']}")
            return False

        balance = balance_response.get('balance', 0)
        donation_amount = balance * DONATION_RATE

        if donation_amount < 100:  # Minimum donation
            print(f"Balance too low: {balance} (min donation: 100)")
            return False

        # Create donation transaction
        tx = client.create_transfer_transaction(
            'genesis_miner_wallet',
            'foundation_314st',
            donation_amount,
            f'Foundation donation - {donation_amount} 314ST'
        )

        # Submit transaction
        result = client.submit_transaction(tx)
        if 'transaction_hash' in result:
            print(f"✅ Donated {donation_amount} 314ST to foundation")
            print(f"   TX Hash: {result['transaction_hash']}")

            # Check foundation balance
            foundation_status = client.get_foundation_status()
            if 'balance' in foundation_status:
                print(f"   Foundation balance: {foundation_status['balance']} 314ST")

            return True
        else:
            print(f"❌ Donation failed: {result}")
            return False

    except Exception as e:
        print(f"❌ Donation error: {e}")
        return False

if __name__ == '__main__':
    print("🚀 PiSecure Foundation Donation Script")
    print("   Donating 50% of mining rewards to foundation")
    print("   Press Ctrl+C to stop")
    print()

    while True:
        donate_to_foundation()
        time.sleep(3600)  # Check every hour

EOF

# Make executable and run
chmod +x /home/pi/foundation_donation.py

# Test donation script
python3 /home/pi/foundation_donation.py &
# (Will run in background, check every hour)
```

### **Step 10: Monitoring & Health Checks**

```bash
# Create monitoring script
cat > /home/pi/monitor_pisecure.sh << 'EOF'
#!/bin/bash

echo "🔍 PiSecure Health Check - $(date)"
echo "================================="

# Check PiSecure processes
echo "📊 Process Status:"
ps aux | grep -E "(pisecure|python.*pisecure)" | grep -v grep || echo "❌ No PiSecure processes found"

# Check mining status
echo -e "\n⛏️  Mining Status:"
curl -s http://localhost:3142/api/v1/mining/stats | jq . || echo "❌ Mining API unavailable"

# Check blockchain status
echo -e "\n⛓️  Blockchain Status:"
curl -s http://localhost:3142/api/v1/blockchain/info | jq . || echo "❌ Blockchain API unavailable"

# Check foundation status
echo -e "\n🏛️  Foundation Status:"
curl -s http://localhost:3142/api/v1/foundation/status | jq . || echo "❌ Foundation API unavailable"

# System resources
echo -e "\n🖥️  System Resources:"
echo "CPU: $(uptime | awk '{print $8,$9,$10}')"
echo "Memory: $(free -h | awk 'NR==2{printf "%.1fG/%.1fG (%.0f%%)", $3/1024, $2/1024, $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5" used)"}')"
echo "Temperature: $(vcgencmd measure_temp 2>/dev/null || echo "N/A")"

echo -e "\n✅ Health check complete"
EOF

# Make executable
chmod +x /home/pi/monitor_pisecure.sh

# Run health check
/home/pi/monitor_pisecure.sh
```

## 📊 **Launch Success Metrics**

### **Immediate Success (First Hour)**
- [ ] ✅ Genesis block mined
- [ ] ✅ Mining active (~100+ H/s)
- [ ] ✅ API server responding
- [ ] ✅ Foundation trust initialized
- [ ] ✅ Web dashboard accessible

### **Short-term Success (First Day)**
- [ ] ✅ 10+ blocks mined
- [ ] ✅ 5000+ 314ST mined
- [ ] ✅ Foundation balance growing
- [ ] ✅ System stable (<50°C temperature)
- [ ] ✅ Network connections healthy

### **Launch Success (First Week)**
- [ ] ✅ 100+ blocks mined
- [ ] ✅ 50,000+ 314ST mined
- [ ] ✅ Foundation funded (10,000+ 314ST)
- [ ] ✅ All APIs functional
- [ ] ✅ Monitoring systems working

## 🔧 **Troubleshooting Guide**

### **Mining Not Starting**
```bash
# Check logs
tail -f /var/log/pisecure/mining.log

# Verify hardware
vcgencmd get_throttled  # Should return 0x0

# Check CPU temperature
vcgencmd measure_temp   # Should be <70°C

# Restart mining
pisecure mining restart
```

### **API Server Not Responding**
```bash
# Check if port is in use
netstat -tlnp | grep 3142

# Restart API server
pisecure api restart

# Check logs
tail -f /var/log/pisecure/api.log
```

### **Foundation Transactions Failing**
```bash
# Verify genesis keys
python3 -c "from pisecure.api.economics import foundation_trust; print('Keys OK' if foundation_trust.genesis_private_key else 'Keys missing')"

# Check foundation API
curl http://localhost:3142/api/v1/foundation/status

# Test transaction signing
curl -X POST http://localhost:3142/api/v1/foundation/sign-transaction \
  -H "Content-Type: application/json" \
  -d '{"type": "test", "data": "test"}'
```

### **High CPU/Memory Usage**
```bash
# Check resource usage
top -p $(pgrep -f pisecure)

# Adjust mining threads
# Edit /etc/pisecure/config.json
# Reduce "threads" from 4 to 2
pisecure node restart
```

## 🚨 **Emergency Procedures**

### **If System Becomes Unresponsive**
```bash
# Hard reboot (last resort)
sudo reboot

# After reboot, check logs
journalctl -u pisecure --since "1 hour ago"

# Restart services
pisecure node restart
```

### **If Keys Are Compromised**
```bash
# Immediately stop all services
pisecure node stop

# Generate new keys (requires protocol update)
# Contact community for emergency governance

# Backup all data first
cp -r /var/lib/pisecure /var/lib/pisecure.backup
```

### **If Mining Performance Is Poor**
```bash
# Check system performance
/home/pi/monitor_pisecure.sh

# Adjust difficulty if needed
# Edit config to reduce difficulty temporarily
# difficulty: 2  # Instead of 4

pisecure node restart
```

## 📞 **Support Resources**

### **Documentation**
- **Main README**: `https://github.com/UnderhillForge/PiSecure/blob/main/README.md`
- **API Documentation**: `http://localhost:3142/api/v1/docs`
- **Launch Checklist**: `LAUNCH_CHECKLIST.md`
- **Foundation Setup**: `FOUNDATION_SETUP.md`

### **Community Support**
- **GitHub Issues**: Report bugs and request features
- **Web Dashboard**: `http://localhost:5000` (if running)
- **API Health**: `http://localhost:3142/api/v1/health`

### **Monitoring Tools**
- **System Dashboard**: `http://localhost:5000`
- **API Explorer**: `http://localhost:3142/api/v1/docs`
- **Health Script**: `/home/pi/monitor_pisecure.sh`
- **Donation Script**: `/home/pi/foundation_donation.py`

## 🎯 **Next Steps After Launch**

### **Immediate (Day 1-3)**
1. Monitor mining performance and stability
2. Verify foundation funding is accumulating
3. Test API endpoints with sample transactions
4. Set up automated monitoring alerts

### **Short-term (Week 1)**
1. Optimize mining performance (threads, cooling)
2. Set up backup and recovery procedures
3. Test foundation transaction signing
4. Begin ecosystem development (trusts, grants)

### **Medium-term (Month 1)**
1. Add second Pi node for redundancy
2. Implement advanced monitoring and alerting
3. Launch developer onboarding program
4. Begin community governance processes

---

## 🎊 **Launch Success Checklist**

- [ ] ✅ **Genesis block mined** - Blockchain initialized
- [ ] ✅ **Mining active** - Generating new blocks continuously
- [ ] ✅ **API functional** - All endpoints responding
- [ ] ✅ **Foundation operational** - Trust created and fundable
- [ ] ✅ **Web dashboard working** - Monitoring interface accessible
- [ ] ✅ **Automated systems running** - Donations and monitoring active
- [ ] ✅ **System stable** - Temperatures normal, resources adequate
- [ ] ✅ **Documentation accessible** - All guides and references available

**🎉 Congratulations! PiSecure is now live on your first Raspberry Pi! The foundation of a decentralized future is being built, one block at a time.**