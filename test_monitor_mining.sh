#!/bin/bash
# Quick test for mining dashboard
# This will run for 30 seconds then stop

echo "🧪 Testing PiSecure Mining Dashboard..."
echo "This will mine on testnet for 30 seconds"
echo ""

# Clean testnet
rm -rf /var/lib/pisecure/testnet

# Start monitoring with mining for 30 seconds
timeout 30 pisecure monitor --wallet pi_test --testnet --refresh-rate 1.0 2>&1 | tee /tmp/monitor_test.log

echo ""
echo "✅ Test complete. Check /tmp/monitor_test.log for output"
echo ""
echo "Check testnet blockchain:"
ls -lh /var/lib/pisecure/testnet/
