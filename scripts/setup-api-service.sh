#!/bin/bash
# Setup PiSecure API Server as systemd service
# Run with: sudo bash scripts/setup-api-service.sh [port]

set -e

PORT="${1:-3142}"
SERVICE_NAME="pisecure-api"

# If port is not 3142, create a custom service for this node
if [ "$PORT" != "3142" ]; then
    SERVICE_NAME="pisecure-api-${PORT}"
fi

echo "Setting up PiSecure API service: $SERVICE_NAME"
echo "Port: $PORT"

# Create service file with correct port
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > /tmp/pisecure-service.tmp << EOF
[Unit]
Description=PiSecure API Server (Port $PORT)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/PiSecure
Environment="PATH=/home/pi/PiSecure/pisecure_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PISECURE_DATA_DIR=/var/lib/pisecure"

# Start API server
ExecStart=/home/pi/PiSecure/pisecure_env/bin/python -m pisecure.api.server --host 0.0.0.0 --port $PORT

# Restart on failure
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Resource limits
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

# Install service file
sudo mv /tmp/pisecure-service.tmp "$SERVICE_FILE"
sudo chmod 644 "$SERVICE_FILE"

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start at boot
sudo systemctl enable "$SERVICE_NAME"

echo "✅ Service installed: $SERVICE_NAME"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Disable: sudo systemctl disable $SERVICE_NAME"
echo ""
echo "Start now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo systemctl start "$SERVICE_NAME"
    sleep 2
    sudo systemctl status "$SERVICE_NAME" --no-pager
fi
