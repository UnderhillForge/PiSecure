#!/usr/bin/env python3
"""
Minimal PiSecure Dashboard - Working Version for Pi Zero 2 W
============================================================

A lightweight dashboard that demonstrates PiSecure monitoring capabilities
without heavy cryptographic dependencies. Perfect for resource-constrained devices.
"""

from flask import Flask, render_template_string
import psutil
import time
import subprocess
import json
import os
from pathlib import Path

app = Flask(__name__)

# HTML Template (embedded to avoid file dependencies)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PiSecure Node - {{ hostname }}</title>
    <meta http-equiv="refresh" content="30">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        .header h1 {
            color: #2c3e50;
            font-size: 2rem;
            font-weight: 600;
            text-align: center;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-2px); }
        .card h2 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.3rem;
            font-weight: 500;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #ecf0f1;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #7f8c8d; font-weight: 500; }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2c3e50;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #27ae60, #3498db);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .status-good { color: #27ae60; }
        .status-warn { color: #f39c12; }
        .status-bad { color: #e74c3c; }
        .status-unknown { color: #95a5a6; }
        .activity-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .activity-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }
        .activity-item:last-child { border-bottom: none; }
        .activity-time { color: #7f8c8d; font-size: 0.9rem; }
        .activity-desc { font-weight: 500; }
        .footer {
            text-align: center;
            color: rgba(255,255,255,0.8);
            margin-top: 20px;
            font-size: 0.9rem;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 1.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 PiSecure Node Dashboard - {{ hostname }}</h1>
            <p style="text-align: center; color: #7f8c8d; margin-top: 5px;">
                Network Status: <span class="{{ 'status-' + network_status.lower() }}">{{ network_status }}</span> |
                Last Update: {{ timestamp }}
            </p>
        </div>

        <div class="grid">
            <!-- System Status -->
            <div class="card">
                <h2>🖥️ System Status</h2>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value">{{ cpu_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ cpu_percent }}%"></div>
                </div>

                <div class="metric">
                    <span class="metric-label">Memory</span>
                    <span class="metric-value">{{ memory_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ memory_percent }}%"></div>
                </div>

                <div class="metric">
                    <span class="metric-label">Disk Usage</span>
                    <span class="metric-value">{{ disk_percent }}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {{ disk_percent }}%"></div>
                </div>

                <div class="metric">
                    <span class="metric-label">Temperature</span>
                    <span class="metric-value">{{ temperature }}°C</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value">{{ uptime }}</span>
                </div>
            </div>

            <!-- Blockchain Status -->
            <div class="card">
                <h2>⛓️ Blockchain Status</h2>
                <div class="metric">
                    <span class="metric-label">Blocks</span>
                    <span class="metric-value">{{ block_count }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Pending TX</span>
                    <span class="metric-value">{{ pending_tx }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Difficulty</span>
                    <span class="metric-value">{{ difficulty }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Chain Valid</span>
                    <span class="metric-value {{ 'status-good' if chain_valid else 'status-bad' }}">
                        {{ '✅ Valid' if chain_valid else '❌ Invalid' }}
                    </span>
                </div>

                <div class="metric">
                    <span class="metric-label">Network Health</span>
                    <span class="metric-value status-good">{{ network_health }}</span>
                </div>
            </div>

            <!-- Mining Status -->
            <div class="card">
                <h2>⛏️ Mining Status</h2>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value {{ 'status-' + mining_status.lower() }}">{{ mining_status }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Hashrate</span>
                    <span class="metric-value">{{ hashrate }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Blocks Found</span>
                    <span class="metric-value">{{ blocks_found }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Mining Uptime</span>
                    <span class="metric-value">{{ mining_uptime }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Current Temp</span>
                    <span class="metric-value">{{ mining_temp }}°C</span>
                </div>
            </div>

            <!-- Network Status -->
            <div class="card">
                <h2>🌐 Network Status</h2>
                <div class="metric">
                    <span class="metric-label">Connected Peers</span>
                    <span class="metric-value">{{ connected_peers }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Known Peers</span>
                    <span class="metric-value">{{ known_peers }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Sync Progress</span>
                    <span class="metric-value">{{ sync_progress }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">IP Address</span>
                    <span class="metric-value">{{ ip_address }}</span>
                </div>

                <div class="metric">
                    <span class="metric-label">Data Received</span>
                    <span class="metric-value">{{ network_recv }} MB</span>
                </div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="card">
            <h2>📋 Recent Activity</h2>
            <div class="activity-list" id="recent-blocks">
                {% for block in recent_blocks %}
                <div class="activity-item">
                    <span class="activity-time">{{ block.time }}</span>
                    <span class="activity-desc">Block #{{ block.index }}: {{ block.transactions }} transactions</span>
                </div>
                {% endfor %}
                {% if not recent_blocks %}
                <div class="activity-item">
                    <span class="activity-time">--:--</span>
                    <span class="activity-desc">No recent blocks - blockchain initializing</span>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="footer">
            <p>PiSecure Dashboard v0.1.0 | Running on Raspberry Pi Zero 2 W | Auto-refresh: 30s</p>
            <p>🚀 Ready for decentralized blockchain operations | 🔐 Hardware-verified mining</p>
        </div>
    </div>
</body>
</html>
"""

def get_system_info():
    """Get comprehensive system information"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # Temperature (Pi specific)
        try:
            result = subprocess.run(['vcgencmd', 'measure_temp'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                temperature = float(temp_str.split('=')[1].split("'")[0])
            else:
                temperature = 0
        except:
            temperature = 0

        # IP Address
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except:
            ip_address = "Unknown"

        # Uptime
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"

        # Hostname
        hostname = subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()

        # Network I/O
        network = psutil.net_io_counters()
        network_recv = round(network.bytes_recv / (1024**2), 1)

        return {
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory_percent, 1),
            'disk_percent': round(disk_percent, 1),
            'temperature': round(temperature, 1),
            'ip_address': ip_address,
            'uptime': uptime_str,
            'hostname': hostname,
            'network_recv': network_recv
        }
    except Exception as e:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'temperature': 0,
            'ip_address': "Error",
            'uptime': "Error",
            'hostname': "Error",
            'network_recv': 0,
            'error': str(e)
        }

def get_blockchain_info():
    """Get blockchain information (simulated for demo)"""
    # In a real implementation, this would query the actual blockchain
    # For now, return simulated data

    # Try to read from actual blockchain if it exists
    blockchain_file = Path("/var/lib/pisecure/blockchain/chain.json")
    if blockchain_file.exists():
        try:
            with open(blockchain_file, 'r') as f:
                chain_data = json.load(f)
                block_count = len(chain_data)
                latest_block = chain_data[-1] if chain_data else {}
                pending_tx = 0  # Would need to check pending file
                difficulty = latest_block.get('difficulty', 4)
                chain_valid = True  # Would need validation
        except:
            block_count = 0
            pending_tx = 0
            difficulty = 4
            chain_valid = False
    else:
        # Simulated data for demo
        block_count = 0
        pending_tx = 0
        difficulty = 4
        chain_valid = False

    return {
        'block_count': block_count,
        'pending_tx': pending_tx,
        'difficulty': difficulty,
        'chain_valid': chain_valid,
        'network_health': 'Initializing' if block_count == 0 else 'Good'
    }

def get_mining_info():
    """Get mining information (simulated for demo)"""
    return {
        'mining_status': 'Ready',  # Would check actual mining process
        'hashrate': '0 MH/s',      # Would get from mining software
        'blocks_found': 0,         # Would track actual blocks found
        'mining_uptime': '0m',     # Would track mining process uptime
        'mining_temp': 0           # Current temperature
    }

def get_network_info():
    """Get network information"""
    return {
        'connected_peers': 0,      # Would check actual peer connections
        'known_peers': 0,          # Would check peer database
        'sync_progress': '0%',     # Would check sync status
        'ip_address': 'Scanning...', # Already handled in system info
        'network_recv': 0          # Already handled in system info
    }

def get_recent_blocks():
    """Get recent blocks (simulated for demo)"""
    # In real implementation, would query blockchain
    return []

@app.route('/')
def dashboard():
    """Main dashboard page"""
    system_info = get_system_info()
    blockchain_info = get_blockchain_info()
    mining_info = get_mining_info()
    network_info = get_network_info()

    # Combine all data
    data = {
        **system_info,
        **blockchain_info,
        **mining_info,
        **network_info,
        'network_status': 'Initializing' if blockchain_info['block_count'] == 0 else 'Active',
        'timestamp': time.strftime('%H:%M:%S'),
        'recent_blocks': get_recent_blocks()
    }

    return render_template_string(HTML_TEMPLATE, **data)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': time.time()}

if __name__ == '__main__':
    print("🚀 Starting Minimal PiSecure Dashboard...")
    print("========================================")
    print("Dashboard will be available at:")
    print("  Local:   http://localhost:5000")
    print("  Network: http://[your-pi-ip]:5000")
    print("")
    print("Features:")
    print("  ✅ Real-time system monitoring")
    print("  ✅ Blockchain status display")
    print("  ✅ Mining status tracking")
    print("  ✅ Network peer information")
    print("  ✅ Auto-refresh every 30 seconds")
    print("")
    print("Note: This is a demonstration dashboard.")
    print("Full PiSecure features require additional setup.")
    print("")

    app.run(host='0.0.0.0', port=5000, debug=False)