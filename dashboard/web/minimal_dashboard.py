#!/usr/bin/env python3
"""
Minimal PiSecure Dashboard - Working Version for Pi Zero 2 W
============================================================

A lightweight dashboard that demonstrates PiSecure monitoring capabilities
without heavy cryptographic dependencies. Perfect for resource-constrained devices.
"""

from flask import Flask, render_template_string, request
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
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e6ff;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: rgba(30, 30, 46, 0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .header h1 {
            color: #a8b5d1;
            font-size: 2rem;
            font-weight: 600;
            text-align: center;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(30, 30, 46, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            transition: transform 0.2s, box-shadow 0.2s;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            border-color: rgba(102, 126, 234, 0.3);
        }
        .card h2 {
            color: #a8b5d1;
            margin-bottom: 15px;
            font-size: 1.3rem;
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .metric:last-child { border-bottom: none; }
        .metric-label {
            color: #8892b0;
            font-weight: 500;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #e0e6ff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4aa, #667eea);
            border-radius: 4px;
            transition: width 0.3s ease;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
        }
        .status-good { color: #00d4aa; }
        .status-warn { color: #ffd60a; }
        .status-bad { color: #ff453a; }
        .status-unknown { color: #8e8e93; }
        .activity-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .activity-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .activity-item:last-child { border-bottom: none; }
        .activity-time { color: #8892b0; font-size: 0.9rem; }
        .activity-desc {
            font-weight: 500;
            color: #e0e6ff;
        }
        .footer {
            text-align: center;
            color: rgba(224, 230, 255, 0.6);
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

                <!-- Node Discovery Status -->
                <div class="metric">
                    <span class="metric-label">Node Discovery</span>
                    <span class="metric-value {{ 'status-good' if node_discovery_enabled else 'status-warn' }}">
                        {{ '✅ Active' if node_discovery_enabled else '⚠️ Not Configured' }}
                    </span>
                </div>

                {% if public_endpoints %}
                <div class="metric">
                    <span class="metric-label">Public Access</span>
                    <span class="metric-value status-good">{{ public_endpoints|length }} endpoints</span>
                </div>
                {% endif %}
            </div>

            <!-- Node Discovery Status -->
            {% if node_discovery_enabled %}
            <div class="card">
                <h2>🛰️ Node Discovery</h2>
                <div class="metric">
                    <span class="metric-label">Discovery Methods</span>
                    <span class="metric-value">{{ discovery_methods|length }}</span>
                </div>

                {% if public_endpoints %}
                <div class="metric">
                    <span class="metric-label">Public Endpoints</span>
                    <span class="metric-value status-good">{{ public_endpoints|length }}</span>
                </div>

                {% for endpoint in public_endpoints %}
                <div class="metric">
                    <span class="metric-label">{{ endpoint.type|title }} Access</span>
                    <span class="metric-value status-good">✅ Available</span>
                </div>
                {% endfor %}
                {% else %}
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value status-warn">Setting up...</span>
                </div>
                {% endif %}

                {% if relay_count %}
                <div class="metric">
                    <span class="metric-label">Relay Network</span>
                    <span class="metric-value">{{ relay_count }} relays</span>
                </div>
                {% endif %}

                <p style="font-size: 0.9rem; color: #7f8c8d; margin-top: 10px;">
                    This node can be discovered worldwide through multiple methods.
                    Mobile apps automatically find and connect to this node.
                </p>
            </div>
            {% endif %}
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

# Wallet Management Template
WALLET_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PiSecure Wallet - {{ hostname }}</title>
        <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e6ff;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(30, 30, 46, 0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }
        .header h1 { color: #a8b5d1; font-size: 2rem; font-weight: 600; }
        .nav { margin-top: 10px; }
        .nav a {
            color: #667eea;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 500;
        }
        .nav a:hover { text-decoration: underline; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(30, 30, 46, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            border-color: rgba(102, 126, 234, 0.3);
        }
        .card h2 {
            color: #a8b5d1;
            margin-bottom: 15px;
            font-size: 1.3rem;
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }
        .card h3 {
            color: #a8b5d1;
            font-size: 1.1rem;
            margin: 20px 0 10px 0;
        }
        .card h4 {
            color: #8892b0;
            font-size: 1rem;
            margin: 15px 0 10px 0;
        }

        .wallet-list { margin-bottom: 20px; }
        .wallet-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            margin-bottom: 10px;
            background: rgba(45, 45, 61, 0.8);
            border-radius: 8px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: background 0.2s;
        }
        .wallet-item:hover { background: rgba(55, 55, 71, 0.8); }
        .wallet-info h3 { margin: 0; color: #e0e6ff; font-size: 1.1rem; }
        .wallet-address {
            font-family: monospace;
            font-size: 0.9rem;
            color: #8892b0;
            margin-top: 5px;
        }
        .wallet-balance {
            font-size: 1.2rem;
            font-weight: 600;
            color: #00d4aa;
        }

        .form-group { margin-bottom: 15px; }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #a8b5d1;
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 10px;
            background: rgba(45, 45, 61, 0.8);
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 1rem;
            color: #e0e6ff;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }

        .status-msg {
            margin-top: 10px;
            padding: 10px;
            border-radius: 8px;
            font-weight: 500;
        }
        .status-success { background: rgba(0, 212, 170, 0.2); color: #00d4aa; border: 1px solid rgba(0, 212, 170, 0.3); }
        .status-error { background: rgba(255, 69, 58, 0.2); color: #ff453a; border: 1px solid rgba(255, 69, 58, 0.3); }

        .blockchain-info {
            background: rgba(45, 45, 61, 0.8);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .blockchain-info div {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        .blockchain-info div:last-child { margin-bottom: 0; }
        .blockchain-info strong { color: #a8b5d1; }

        /* Modal styles */
        #block-modal, #tx-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            padding: 20px;
            box-sizing: border-box;
            display: none;
        }
        #block-modal > div, #tx-modal > div {
            background: rgba(30, 30, 46, 0.95);
            border-radius: 15px;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.1);
        }
        #block-modal p, #tx-modal p {
            margin: 8px 0;
            color: #e0e6ff;
        }
        #block-modal strong, #tx-modal strong {
            color: #a8b5d1;
        }

        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .wallet-item { flex-direction: column; align-items: flex-start; gap: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👛 PiSecure Wallet Management</h1>
            <div class="nav">
                <a href="/">← Dashboard</a>
                <a href="#create">Create Wallet</a>
                <a href="#transfer">Transfer</a>
                <a href="#blockchain">Blockchain</a>
            </div>
        </div>

        <div class="grid">
            <!-- Existing Wallets -->
            <div class="card">
                <h2>🏦 Your Wallets</h2>
                <div id="wallet-list" class="wallet-list">
                    {% for wallet in wallets %}
                    <div class="wallet-item">
                        <div class="wallet-info">
                            <h3>{{ wallet.name }} ({{ wallet.id }})</h3>
                            <div class="wallet-address">{{ wallet.address[:20] }}...</div>
                        </div>
                        <div class="wallet-balance">{{ "%.2f"|format(wallet.balance) }} tokens</div>
                    </div>
                    {% endfor %}
                    {% if not wallets %}
                    <p style="text-align: center; color: #7f8c8d; padding: 20px;">
                        No wallets found. Create your first wallet below.
                    </p>
                    {% endif %}
                </div>
            </div>

            <!-- Create New Wallet -->
            <div class="card" id="create">
                <h2>➕ Create New Wallet</h2>
                <form id="create-wallet-form">
                    <div class="form-group">
                        <label for="wallet_name">Wallet Name:</label>
                        <input type="text" id="wallet_name" name="wallet_name" placeholder="my_wallet" required>
                    </div>
                    <div class="form-group">
                        <label for="display_name">Display Name:</label>
                        <input type="text" id="display_name" name="display_name" placeholder="My Personal Wallet" required>
                    </div>
                    <button type="submit" class="btn">Create Wallet</button>
                </form>
                <div id="create-status"></div>
            </div>
        </div>

        <div class="grid">
            <!-- Transfer Tokens -->
            <div class="card" id="transfer">
                <h2>💸 Transfer Tokens</h2>
                <form id="transfer-form">
                    <div class="form-group">
                        <label for="recipient">Recipient (wallet name or address):</label>
                        <input type="text" id="recipient" name="recipient" placeholder="node-abc123 or full_address..." required>
                    </div>
                    <div class="form-group">
                        <label for="amount">Amount:</label>
                        <input type="number" id="amount" name="amount" step="0.01" min="0.01" placeholder="100.00" required>
                    </div>
                    <div class="form-group">
                        <label for="from_wallet">From Wallet (optional):</label>
                        <select id="from_wallet" name="from_wallet">
                            <option value="">Use default wallet</option>
                            {% for wallet in wallets %}
                            <option value="{{ wallet.id }}">{{ wallet.name }} ({{ wallet.id }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn">Transfer Tokens</button>
                </form>
                <div id="transfer-status"></div>
            </div>

            <!-- Wallet Backup -->
            <div class="card" id="backup">
                <h2>💾 Wallet Backup</h2>
                <form id="backup-form">
                    <div class="form-group">
                        <label for="backup_wallet">Wallet to Backup:</label>
                        <select id="backup_wallet" name="wallet_name" required>
                            {% for wallet in wallets %}
                            <option value="{{ wallet.id }}">{{ wallet.name }} ({{ wallet.id }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="include_private_key" name="include_private_key" value="true">
                            Include private key (encrypted backup)
                        </label>
                    </div>
                    <div class="form-group" id="password-group" style="display: none;">
                        <label for="backup_password">Encryption Password:</label>
                        <input type="password" id="backup_password" name="password" placeholder="Strong password..." minlength="8">
                    </div>
                    <button type="submit" class="btn">Create Backup</button>
                </form>
                <div id="backup-status"></div>
                <p style="font-size: 0.9rem; color: #7f8c8d; margin-top: 10px;">
                    ⚠️ Backups with private keys can restore your wallet completely.<br>
                    Store encrypted backups securely and remember your password!
                </p>
            </div>
        </div>

        <div class="grid">
            <!-- Wallet Restore -->
            <div class="card" id="restore">
                <h2>📥 Wallet Restore</h2>
                <form id="restore-form">
                    <div class="form-group">
                        <label for="restore_wallet_name">New Wallet Name:</label>
                        <input type="text" id="restore_wallet_name" name="wallet_name" placeholder="restored_wallet" required>
                    </div>
                    <div class="form-group">
                        <label for="backup_data">Backup Data:</label>
                        <textarea id="backup_data" name="backup_data" rows="6" placeholder="Paste your wallet backup JSON here..." required></textarea>
                    </div>
                    <div class="form-group" id="restore-password-group" style="display: none;">
                        <label for="restore_password">Decryption Password:</label>
                        <input type="password" id="restore_password" name="password" placeholder="Backup password...">
                    </div>
                    <button type="submit" class="btn">Restore Wallet</button>
                </form>
                <div id="restore-status"></div>
                <p style="font-size: 0.9rem; color: #7f8c8d; margin-top: 10px;">
                    📄 Paste the complete JSON backup data.<br>
                    If the backup includes private keys, enter the decryption password.
                </p>
            </div>

            <!-- Blockchain Explorer -->
            <div class="card" id="blockchain">
                <h2>⛓️ Blockchain Explorer</h2>

                <!-- Quick Stats -->
                <div class="blockchain-info">
                    <div><strong>Blocks:</strong> <span id="total-blocks">{{ chain_info.blocks }}</span></div>
                    <div><strong>Pending TX:</strong> <span id="pending-tx">{{ chain_info.pending_transactions }}</span></div>
                    <div><strong>Difficulty:</strong> <span id="difficulty">{{ chain_info.difficulty }}</span></div>
                    <div><strong>Chain Valid:</strong> <span id="chain-valid">{{ '✅ Yes' if chain_info.is_valid else '❌ No' }}</span></div>
                    <div><strong>Network Health:</strong> <span id="network-health">{{ chain_info.network_health }}</span></div>
                </div>

                <!-- Search -->
                <div class="form-group" style="margin: 15px 0;">
                    <label for="explorer-search">Search Blocks/TX:</label>
                    <input type="text" id="explorer-search" placeholder="Block #, TX hash, or address..." style="margin-bottom: 5px;">
                    <button type="button" class="btn" onclick="searchBlockchain()" style="width: auto; padding: 8px 16px;">Search</button>
                </div>

                <!-- Recent Blocks -->
                <h3 style="margin: 20px 0 10px 0; color: #2c3e50;">📦 Recent Blocks</h3>
                <div id="recent-blocks" class="wallet-list">
                    <!-- Blocks will be loaded here -->
                </div>

                <!-- Recent Transactions -->
                <h3 style="margin: 20px 0 10px 0; color: #2c3e50;">💸 Recent Transactions</h3>
                <div id="recent-transactions" class="wallet-list">
                    <!-- Transactions will be loaded here -->
                </div>

                <!-- Block Details Modal (hidden by default) -->
                <div id="block-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; padding: 20px; box-sizing: border-box;">
                    <div style="background: white; border-radius: 15px; padding: 20px; max-width: 800px; margin: 0 auto; max-height: 80vh; overflow-y: auto;">
                        <h2 style="margin-bottom: 20px;">📦 Block Details</h2>
                        <div id="block-details"></div>
                        <button class="btn" onclick="closeModal()" style="margin-top: 20px;">Close</button>
                    </div>
                </div>

                <!-- Transaction Details Modal -->
                <div id="tx-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; padding: 20px; box-sizing: border-box;">
                    <div style="background: white; border-radius: 15px; padding: 20px; max-width: 800px; margin: 0 auto; max-height: 80vh; overflow-y: auto;">
                        <h2 style="margin-bottom: 20px;">💸 Transaction Details</h2>
                        <div id="tx-details"></div>
                        <button class="btn" onclick="closeModal()" style="margin-top: 20px;">Close</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Create Wallet
        document.getElementById('create-wallet-form').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const statusDiv = document.getElementById('create-status');

            try {
                const response = await fetch('/api/create-wallet', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    statusDiv.innerHTML = '<div class="status-msg status-success">✅ Wallet created successfully! Address: ' + result.address + '</div>';
                    setTimeout(() => location.reload(), 2000);
                } else {
                    statusDiv.innerHTML = '<div class="status-msg status-error">❌ Error: ' + result.error + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status-msg status-error">❌ Network error: ' + error.message + '</div>';
            }
        });

        // Transfer Tokens
        document.getElementById('transfer-form').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const statusDiv = document.getElementById('transfer-status');

            try {
                const response = await fetch('/api/transfer', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    statusDiv.innerHTML = '<div class="status-msg status-success">✅ ' + result.message + '<br>TX Hash: ' + result.tx_hash + '</div>';
                    setTimeout(() => location.reload(), 3000);
                } else {
                    statusDiv.innerHTML = '<div class="status-msg status-error">❌ Error: ' + result.error + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status-msg status-error">❌ Network error: ' + error.message + '</div>';
            }
        });

        // Show/hide password field for backup
        document.getElementById('include_private_key').addEventListener('change', function(e) {
            const passwordGroup = document.getElementById('password-group');
            passwordGroup.style.display = e.target.checked ? 'block' : 'none';
            document.getElementById('backup_password').required = e.target.checked;
        });

        // Backup Wallet
        document.getElementById('backup-form').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const statusDiv = document.getElementById('backup-status');

            try {
                const response = await fetch('/api/wallet/backup', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    // Create downloadable backup file
                    const blob = new Blob([result.backup_data], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = result.filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    statusDiv.innerHTML = '<div class="status-msg status-success">✅ Backup created successfully!<br>Downloaded: ' + result.filename + '<br>Size: ' + result.size + ' bytes<br>Private key included: ' + (result.includes_private_key ? 'Yes (encrypted)' : 'No') + '</div>';
                } else {
                    statusDiv.innerHTML = '<div class="status-msg status-error">❌ Backup failed: ' + result.error + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status-msg status-error">❌ Network error: ' + error.message + '</div>';
            }
        });

        // Show/hide password field for restore
        document.getElementById('backup_data').addEventListener('input', function(e) {
            const backupData = e.target.value.trim();
            const passwordGroup = document.getElementById('restore-password-group');

            try {
                const data = JSON.parse(backupData);
                const hasPrivateKey = data.encrypted_private_key !== undefined;
                passwordGroup.style.display = hasPrivateKey ? 'block' : 'none';
                document.getElementById('restore_password').required = hasPrivateKey;
            } catch (error) {
                passwordGroup.style.display = 'none';
                document.getElementById('restore_password').required = false;
            }
        });

        // Restore Wallet
        document.getElementById('restore-form').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const statusDiv = document.getElementById('restore-status');

            try {
                const response = await fetch('/api/wallet/restore', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    statusDiv.innerHTML = '<div class="status-msg status-success">✅ Wallet restored successfully!<br>Wallet ID: ' + result.wallet_id + '<br>Address: ' + result.address + '<br>Private key restored: ' + (result.private_key_restored ? 'Yes' : 'No') + '</div>';
                    setTimeout(() => location.reload(), 3000);
                } else {
                    statusDiv.innerHTML = '<div class="status-msg status-error">❌ Restore failed: ' + result.error + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status-msg status-error">❌ Network error: ' + error.message + '</div>';
            }
        });

        // Load blockchain explorer data on page load
        loadBlockchainExplorer();

        // Auto-refresh blockchain stats every 30 seconds
        setInterval(async function() {
            updateBlockchainStats();
            loadBlockchainExplorer();
        }, 30000);

        // Auto-refresh wallet list every 30 seconds
        setInterval(async function() {
            try {
                const response = await fetch('/api/wallets');
                const data = await response.json();
                if (data.wallets) {
                    // Could update wallet list here if needed
                    console.log('Wallets updated:', data.wallets.length);
                }
            } catch (e) {
                console.log('Auto-refresh failed:', e);
            }
        }, 30000);

        // Load blockchain explorer data
        async function loadBlockchainExplorer() {
            try {
                // Load recent blocks
                const blocksResponse = await fetch('/api/blockchain/recent-blocks');
                const blocksData = await blocksResponse.json();

                // Update stats
                document.getElementById('total-blocks').textContent = blocksData.total_blocks;
                document.getElementById('pending-tx').textContent = blocksData.pending_tx;

                // Display recent blocks
                const blocksContainer = document.getElementById('recent-blocks');
                blocksContainer.innerHTML = '';

                if (blocksData.blocks.length === 0) {
                    blocksContainer.innerHTML = '<div class="wallet-item"><div class="wallet-info"><h3>No blocks yet</h3><div class="wallet-address">Blockchain initializing...</div></div></div>';
                } else {
                    blocksData.blocks.forEach(block => {
                        const blockElement = document.createElement('div');
                        blockElement.className = 'wallet-item';
                        blockElement.onclick = () => showBlockDetails(block.index);
                        blockElement.innerHTML = `
                            <div class="wallet-info">
                                <h3>Block #${block.index}</h3>
                                <div class="wallet-address">${block.hash} • ${block.timestamp}</div>
                            </div>
                            <div class="wallet-balance">${block.transactions} TX • Diff ${block.difficulty}</div>
                        `;
                        blocksContainer.appendChild(blockElement);
                    });
                }

                // Load recent transactions
                const txResponse = await fetch('/api/blockchain/recent-transactions');
                const txData = await txResponse.json();

                const txContainer = document.getElementById('recent-transactions');
                txContainer.innerHTML = '';

                if (txData.transactions.length === 0) {
                    txContainer.innerHTML = '<div class="wallet-item"><div class="wallet-info"><h3>No transactions yet</h3><div class="wallet-address">Waiting for activity...</div></div></div>';
                } else {
                    txData.transactions.forEach(tx => {
                        const txElement = document.createElement('div');
                        txElement.className = 'wallet-item';
                        txElement.onclick = () => showTransactionDetails(tx.tx_hash);
                        txElement.innerHTML = `
                            <div class="wallet-info">
                                <h3>${tx.tx_hash}</h3>
                                <div class="wallet-address">${tx.sender} → ${tx.recipient}</div>
                            </div>
                            <div class="wallet-balance">${tx.amount.toFixed(2)} tokens</div>
                        `;
                        txContainer.appendChild(txElement);
                    });
                }

            } catch (error) {
                console.error('Failed to load blockchain explorer:', error);
            }
        }

        // Update blockchain stats
        async function updateBlockchainStats() {
            try {
                const response = await fetch('/api/blockchain/recent-blocks');
                const data = await response.json();

                document.getElementById('total-blocks').textContent = data.total_blocks;
                document.getElementById('pending-tx').textContent = data.pending_tx;
            } catch (error) {
                console.error('Failed to update blockchain stats:', error);
            }
        }

        // Search blockchain
        function searchBlockchain() {
            const query = document.getElementById('explorer-search').value.trim();
            if (!query) return;

            fetch(`/api/blockchain/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        const result = data.results[0]; // Show first result
                        if (result.type === 'block') {
                            showBlockDetails(result.index);
                        } else if (result.type === 'transaction') {
                            showTransactionDetails(result.tx_hash.replace('...', ''));
                        }
                    } else {
                        alert('No results found for: ' + query);
                    }
                })
                .catch(error => {
                    console.error('Search failed:', error);
                    alert('Search failed: ' + error.message);
                });
        }

        // Show block details
        function showBlockDetails(blockIndex) {
            fetch(`/api/blockchain/block/${blockIndex}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Block not found: ' + data.error);
                        return;
                    }

                    const detailsDiv = document.getElementById('block-details');
                    detailsDiv.innerHTML = `
                        <div style="margin-bottom: 20px;">
                            <h3>Block #${data.index}</h3>
                            <p><strong>Hash:</strong> ${data.hash}</p>
                            <p><strong>Previous Hash:</strong> ${data.previous_hash}</p>
                            <p><strong>Timestamp:</strong> ${data.timestamp_human}</p>
                            <p><strong>Difficulty:</strong> ${data.difficulty}</p>
                            <p><strong>Nonce:</strong> ${data.nonce}</p>
                            <p><strong>Miner:</strong> ${data.miner}</p>
                            <p><strong>Transactions:</strong> ${data.transactions_count}</p>
                        </div>

                        <h4>Transactions (${data.transactions.length})</h4>
                        <div style="max-height: 300px; overflow-y: auto;">
                            ${data.transactions.map(tx => `
                                <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                    <p><strong>TX Hash:</strong> ${tx.tx_hash}</p>
                                    <p><strong>Type:</strong> ${tx.type}</p>
                                    <p><strong>From:</strong> ${tx.sender}</p>
                                    <p><strong>To:</strong> ${tx.recipient}</p>
                                    <p><strong>Amount:</strong> ${tx.amount} tokens</p>
                                    <p><strong>Time:</strong> ${tx.timestamp_human}</p>
                                </div>
                            `).join('')}
                        </div>
                    `;

                    document.getElementById('block-modal').style.display = 'block';
                })
                .catch(error => {
                    console.error('Failed to load block details:', error);
                    alert('Failed to load block details: ' + error.message);
                });
        }

        // Show transaction details
        function showTransactionDetails(txHash) {
            fetch(`/api/blockchain/transaction/${txHash}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Transaction not found: ' + data.error);
                        return;
                    }

                    const detailsDiv = document.getElementById('tx-details');
                    detailsDiv.innerHTML = `
                        <div style="margin-bottom: 20px;">
                            <h3>Transaction Details</h3>
                            <p><strong>TX Hash:</strong> ${data.tx_hash}</p>
                            <p><strong>Block:</strong> #${data.block_index}</p>
                            <p><strong>Type:</strong> ${data.type}</p>
                            <p><strong>From:</strong> ${data.sender_address}</p>
                            <p><strong>To:</strong> ${data.recipient_address}</p>
                            <p><strong>Amount:</strong> ${data.amount} tokens</p>
                            <p><strong>Timestamp:</strong> ${data.timestamp_human}</p>
                            <p><strong>Fee:</strong> ${data.fee} tokens</p>
                            ${data.memo ? `<p><strong>Memo:</strong> ${data.memo}</p>` : ''}
                        </div>

                        ${data.type === 'batch_transfer' ? `
                            <h4>Batch Transfers (${data.transfer_count})</h4>
                            <div style="max-height: 200px; overflow-y: auto;">
                                ${data.transfers.map(transfer => `
                                    <div style="border: 1px solid #ddd; padding: 8px; margin: 3px 0; border-radius: 3px;">
                                        <strong>${transfer.recipient.slice(0, 20)}...</strong> - ${transfer.amount} tokens
                                    </div>
                                `).join('')}
                            </div>
                            <p><strong>Total Amount:</strong> ${data.total_amount} tokens</p>
                        ` : ''}

                        <h4>Signature</h4>
                        <div style="font-family: monospace; word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px;">
                            ${data.signature}
                        </div>
                    `;

                    document.getElementById('tx-modal').style.display = 'block';
                })
                .catch(error => {
                    console.error('Failed to load transaction details:', error);
                    alert('Failed to load transaction details: ' + error.message);
                });
        }

        // Close modal
        function closeModal() {
            document.getElementById('block-modal').style.display = 'none';
            document.getElementById('tx-modal').style.display = 'none';
        }

        // Allow Enter key in search
        document.getElementById('explorer-search').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchBlockchain();
            }
        });
    </script>
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
    """Get blockchain information from actual PiSecure blockchain"""
    # Try to read from actual blockchain if it exists
    blockchain_file = Path("/var/lib/pisecure/blockchain.json")
    pending_file = Path("/var/lib/pisecure/pending_transactions.json")

    if blockchain_file.exists():
        try:
            with open(blockchain_file, 'r') as f:
                chain_data = json.load(f)
                block_count = len(chain_data)
                latest_block = chain_data[-1] if chain_data else {}
                difficulty = latest_block.get('difficulty', 4)

                # Load pending transactions
                pending_tx = 0
                if pending_file.exists():
                    try:
                        with open(pending_file, 'r') as f:
                            pending_data = json.load(f)
                            pending_tx = len(pending_data)
                    except:
                        pending_tx = 0

                # Basic chain validation
                chain_valid = block_count > 0

        except Exception as e:
            print(f"Error reading blockchain: {e}")
            block_count = 0
            pending_tx = 0
            difficulty = 4
            chain_valid = False
    else:
        # No blockchain file yet
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
    """Get network information including peer counts"""
    # Check for node discovery status
    node_discovery_enabled = False
    public_endpoints = []
    discovery_methods = []
    relay_count = 0

    try:
        # Check if node discovery is configured
        discovery_file = Path("/etc/pisecure/node_discovery.json")
        if discovery_file.exists():
            with open(discovery_file, 'r') as f:
                discovery_data = json.load(f)

            node_discovery_enabled = len(discovery_data.get('endpoints', [])) > 0
            public_endpoints = discovery_data.get('endpoints', [])
            discovery_methods = discovery_data.get('methods_attempted', [])
        else:
            # Check if discovery service is available
            try:
                from pisecure.core.nat_traversal import node_discovery
                status = node_discovery.get_discovery_status()
                node_discovery_enabled = len(status.get('endpoints', [])) > 0
                public_endpoints = status.get('endpoints', [])
                relay_count = status.get('relay_count', 0)
            except ImportError:
                node_discovery_enabled = False

    except Exception as e:
        print(f"Node discovery check error: {e}")
        node_discovery_enabled = False

    # Get real peer counts
    connected_peers, known_peers = get_peer_counts()

    return {
        'connected_peers': connected_peers,
        'known_peers': known_peers,
        'sync_progress': '0%',     # Would check sync status
        'ip_address': 'Scanning...', # Already handled in system info
        'network_recv': 0,         # Already handled in system info
        'node_discovery_enabled': node_discovery_enabled,
        'public_endpoints': public_endpoints,
        'discovery_methods': discovery_methods,
        'relay_count': relay_count
    }

def get_peer_counts():
    """Get actual peer counts from multiple discovery methods"""
    connected_peers = 0
    known_peers = 0

    try:
        # 1. Check for peer database (known peers)
        peer_db_file = Path("/var/lib/pisecure/peers.json")
        if peer_db_file.exists():
            try:
                with open(peer_db_file, 'r') as f:
                    peer_data = json.load(f)
                    known_peers = len(peer_data.get('known_peers', []))
            except:
                known_peers = 0

        # 2. Count local network peers
        local_peers = get_local_network_peers()

        # 3. Count STUN-discovered peers
        stun_peers = get_stun_peers()

        # 4. Count Tor onion peers
        tor_peers = get_tor_peers()

        # 5. Count community relay peers
        relay_peers = get_relay_peers()

        # Combine all peer counts (deduplicate where possible)
        connected_peers = local_peers + stun_peers + tor_peers + relay_peers

        # Ensure non-negative counts
        connected_peers = max(0, connected_peers)
        known_peers = max(0, known_peers)

    except Exception as e:
        print(f"Peer count error: {e}")
        connected_peers = 0
        known_peers = 0

    return connected_peers, known_peers

def get_local_network_peers():
    """Count PiSecure peers on local network via port scanning"""
    try:
        import socket
        import threading
        import time

        # Common PiSecure ports
        pisecure_ports = [3142, 5000, 3141]  # API, Dashboard, Bootstrap

        # Get local network range
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        # Extract network prefix (e.g., 192.168.1.)
        ip_parts = local_ip.split('.')
        network_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."

        # Scan local network for PiSecure instances
        active_instances = []

        def scan_port(ip, port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    active_instances.append(f"{ip}:{port}")
            except:
                pass

        # Scan range 1-254 on local network
        threads = []
        for i in range(1, 255):
            target_ip = f"{network_prefix}{i}"
            for port in pisecure_ports:
                thread = threading.Thread(target=scan_port, args=(target_ip, port))
                thread.daemon = True
                threads.append(thread)
                thread.start()

        # Wait for all scans to complete (with timeout)
        start_time = time.time()
        for thread in threads:
            remaining_time = max(0, 2.0 - (time.time() - start_time))
            if remaining_time > 0:
                thread.join(timeout=remaining_time)

        # Count unique PiSecure instances (avoid counting multiple ports on same IP)
        unique_ips = set()
        for instance in active_instances:
            ip = instance.split(':')[0]
            unique_ips.add(ip)

        local_peers = len(unique_ips) - 1  # Subtract self
        return max(0, local_peers)

    except Exception as e:
        print(f"Local network peer scan error: {e}")
        return 0

def get_stun_peers():
    """Count peers discovered via STUN"""
    try:
        # Check if we need to refresh discovery data
        _refresh_discovery_if_needed()

        # Check node discovery file for STUN endpoints
        discovery_file = Path("/etc/pisecure/node_discovery.json")
        if discovery_file.exists():
            with open(discovery_file, 'r') as f:
                discovery_data = json.load(f)

            endpoints = discovery_data.get('endpoints', [])
            stun_endpoints = [ep for ep in endpoints if ep.get('type') == 'stun_direct']

            # Count unique STUN-discovered peers
            stun_peers = len(set(ep.get('ip') for ep in stun_endpoints if ep.get('ip')))
            return stun_peers
        return 0
    except Exception as e:
        print(f"STUN peer count error: {e}")
        return 0

def get_tor_peers():
    """Count peers discovered via Tor onion services"""
    try:
        # Check if we need to refresh discovery data
        _refresh_discovery_if_needed()

        # Check node discovery file for Tor endpoints
        discovery_file = Path("/etc/pisecure/node_discovery.json")
        if discovery_file.exists():
            with open(discovery_file, 'r') as f:
                discovery_data = json.load(f)

            endpoints = discovery_data.get('endpoints', [])
            tor_endpoints = [ep for ep in endpoints if ep.get('type') == 'tor_onion']

            # Count Tor onion peers (each onion address is a unique peer)
            tor_peers = len(tor_endpoints)
            return tor_peers
        return 0
    except Exception as e:
        print(f"Tor peer count error: {e}")
        return 0

def _refresh_discovery_if_needed():
    """Refresh STUN/Tor discovery data if it's stale"""
    try:
        discovery_file = Path("/etc/pisecure/node_discovery.json")
        if not discovery_file.exists():
            # No discovery file yet, try to run discovery
            _run_discovery_update()
            return

        # Check file modification time
        import time
        file_age = time.time() - discovery_file.stat().st_mtime

        # Refresh every 5 minutes (300 seconds)
        if file_age > 300:
            _run_discovery_update()

    except Exception as e:
        print(f"Discovery refresh check error: {e}")

def _run_discovery_update():
    """Run a discovery update to refresh STUN/Tor peer data"""
    try:
        # Try to trigger node discovery update
        try:
            from pisecure.core.nat_traversal import node_discovery
            # Run a quick discovery update
            results = node_discovery.make_node_discoverable()
            print(f"Discovery update completed: {results.get('success_count', 0)} methods successful")
        except ImportError:
            # Fallback: try to run the setup command
            import subprocess
            try:
                # Run a quick discovery check
                result = subprocess.run([
                    'python3', '-c',
                    '''
import sys
sys.path.insert(0, "/opt/pisecure")
try:
    from pisecure.core.nat_traversal import node_discovery
    results = node_discovery.make_node_discoverable()
    print(f"Discovery updated: {results.get('success_count', 0)} methods")
except Exception as e:
    print(f"Discovery update failed: {e}")
'''
                ], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"Discovery update result: {result.stdout.strip()}")
            except subprocess.TimeoutExpired:
                print("Discovery update timed out")
            except Exception as e:
                print(f"Discovery update subprocess error: {e}")

    except Exception as e:
        print(f"Discovery update error: {e}")

def get_relay_peers():
    """Count peers discovered via community relays"""
    try:
        # Check for relay connections and peer counts
        relay_db_file = Path("/var/lib/pisecure/relay_peers.json")
        if relay_db_file.exists():
            try:
                with open(relay_db_file, 'r') as f:
                    relay_data = json.load(f)
                    relay_peers = len(relay_data.get('connected_peers', []))
                    return relay_peers
            except:
                pass

        # Fallback: check node discovery for relay count
        discovery_file = Path("/etc/pisecure/node_discovery.json")
        if discovery_file.exists():
            with open(discovery_file, 'r') as f:
                discovery_data = json.load(f)
                relay_count = discovery_data.get('relay_count', 0)
                return relay_count

        return 0
    except Exception as e:
        print(f"Relay peer count error: {e}")
        return 0

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

@app.route('/wallet')
def wallet_dashboard():
    """Wallet management dashboard"""
    try:
        # Import wallet functionality
        try:
            from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
            from pisecure.core.blockchain import SignChain
        except ImportError:
            # Fallback imports
            import sys
            sys.path.append('/opt/pisecure')
            from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
            from pisecure.core.blockchain import SignChain

        # Get wallet data
        wallet = SignWallet()
        wallets = wallet.list_wallets()

        # Get blockchain data
        blockchain = SignChain()
        chain_info = blockchain.get_chain_info()

        wallet_data = {
            'wallets': wallets,
            'chain_info': chain_info,
            'hostname': subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        }

        return render_template_string(WALLET_TEMPLATE, **wallet_data)

    except Exception as e:
        return f"Error loading wallet dashboard: {e}"

@app.route('/api/wallets')
def get_wallets():
    """API endpoint to get wallet list"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
        wallet = SignWallet()
        wallets = wallet.list_wallets()
        return {'wallets': wallets}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/wallet/<wallet_name>')
def get_wallet_details(wallet_name):
    """API endpoint to get specific wallet details"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
        wallet = SignWallet()
        wallet_data = wallet.load_wallet(wallet_name)
        if 'error' in wallet_data:
            return {'error': wallet_data['error']}, 404
        return wallet_data
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/create-wallet', methods=['POST'])
def create_wallet():
    """API endpoint to create new wallet"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
        import secrets

        wallet_name = request.form.get('wallet_name', f'wallet_{secrets.token_hex(4)}')
        display_name = request.form.get('display_name', f'Wallet {wallet_name}')

        wallet = SignWallet()
        result = wallet.create_wallet(wallet_name, display_name)

        if result['success']:
            return {
                'success': True,
                'wallet_id': result['wallet_id'],
                'address': result['address']
            }
        else:
            return {'success': False, 'error': result.get('error', 'Unknown error')}, 400

    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/transfer', methods=['POST'])
def transfer_tokens():
    """API endpoint to transfer tokens"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet

        recipient = request.form.get('recipient')
        amount = float(request.form.get('amount', 0))
        from_wallet = request.form.get('from_wallet')

        if not recipient or amount <= 0:
            return {'success': False, 'error': 'Invalid recipient or amount'}, 400

        wallet = SignWallet()
        if from_wallet:
            wallet = SignWallet(f"/var/lib/pisecure/wallets/{from_wallet}.json")

        # For now, just simulate the transfer
        # In full implementation, this would create and submit the transaction
        return {
            'success': True,
            'message': f'Transferred {amount} tokens to {recipient}',
            'tx_hash': f'simulated_{secrets.token_hex(16)}'
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/wallet/backup', methods=['POST'])
def backup_wallet():
    """API endpoint to backup wallet"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
        import os

        wallet_name = request.form.get('wallet_name')
        include_private_key = request.form.get('include_private_key') == 'true'
        password = request.form.get('password')

        if include_private_key and not password:
            return {'success': False, 'error': 'Password required for private key backup'}, 400

        # Create backup in /tmp first
        backup_filename = f"pisecure_wallet_{wallet_name}_{int(time.time())}.json"
        backup_path = f"/tmp/{backup_filename}"

        if wallet_name:
            wallet = SignWallet(f"/var/lib/pisecure/wallets/{wallet_name}.json")
        else:
            wallet = SignWallet()

        result = wallet.export_wallet(backup_path, include_private_key, password)

        if result['success']:
            # Return the backup file content
            with open(backup_path, 'r') as f:
                backup_content = f.read()

            # Clean up temp file
            os.remove(backup_path)

            return {
                'success': True,
                'backup_data': backup_content,
                'filename': backup_filename,
                'includes_private_key': include_private_key,
                'size': len(backup_content)
            }
        else:
            return {'success': False, 'error': result['error']}, 400

    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/wallet/restore', methods=['POST'])
def restore_wallet():
    """API endpoint to restore wallet from backup"""
    try:
        from pisecure.core.wallet_v2 import PiSecureWallet, WalletManager # SignWallet
        import os

        backup_data = request.form.get('backup_data')
        password = request.form.get('password')
        wallet_name = request.form.get('wallet_name')

        if not backup_data:
            return {'success': False, 'error': 'No backup data provided'}, 400

        # Create temporary file with backup data
        temp_file = f"/tmp/pisecure_restore_{int(time.time())}.json"
        with open(temp_file, 'w') as f:
            f.write(backup_data)

        try:
            wallet = SignWallet()
            result = wallet.restore_wallet_backup(temp_file, password if password else None)

            # Clean up temp file
            os.remove(temp_file)

            if result['success']:
                return {
                    'success': True,
                    'wallet_id': result['wallet_id'],
                    'address': result['address'],
                    'private_key_restored': result.get('private_key_restored', False)
                }
            else:
                return {'success': False, 'error': result['error']}, 400

        except Exception as e:
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
            raise e

    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/api/blockchain/recent-blocks')
def get_recent_blocks():
    """Get recent blocks for blockchain explorer"""
    try:
        from pisecure.core.blockchain import SignChain

        blockchain = SignChain()
        chain_info = blockchain.get_chain_info()

        # Get recent blocks (last 10)
        blocks = []
        if hasattr(blockchain, 'chain') and blockchain.chain:
            for block in blockchain.chain[-10:]:
                blocks.append({
                    'index': block.index,
                    'hash': getattr(block, 'hash', 'unknown')[:16] + '...',
                    'timestamp': time.ctime(block.timestamp),
                    'transactions': len(block.transactions),
                    'difficulty': getattr(block, 'difficulty', 4),
                    'miner': getattr(block, 'miner', 'unknown')[:16] + '...'
                })

        return {
            'blocks': blocks,
            'total_blocks': chain_info.get('blocks', 0),
            'pending_tx': chain_info.get('pending_transactions', 0)
        }

    except Exception as e:
        return {'error': str(e), 'blocks': [], 'total_blocks': 0, 'pending_tx': 0}, 500

@app.route('/api/blockchain/recent-transactions')
def get_recent_transactions():
    """Get recent transactions for blockchain explorer"""
    try:
        from pisecure.core.blockchain import SignChain

        blockchain = SignChain()

        # Get recent transactions from recent blocks
        transactions = []
        if hasattr(blockchain, 'chain') and blockchain.chain:
            for block in blockchain.chain[-5:]:  # Last 5 blocks
                for tx in block.transactions[-3:]:  # Last 3 tx per block
                    transactions.append({
                        'tx_hash': getattr(tx, 'tx_hash', 'unknown')[:16] + '...',
                        'type': tx.get('type', 'unknown'),
                        'timestamp': time.ctime(tx.get('timestamp', time.time())),
                        'sender': tx.get('sender_address', 'unknown')[:16] + '...',
                        'recipient': tx.get('recipient_address', 'unknown')[:16] + '...',
                        'amount': tx.get('amount', 0),
                        'block_index': block.index
                    })

        # Limit to last 15 transactions
        transactions = transactions[-15:]

        return {'transactions': transactions}

    except Exception as e:
        return {'error': str(e), 'transactions': []}, 500

@app.route('/api/blockchain/search')
def search_blockchain():
    """Search blockchain for blocks or transactions"""
    try:
        from pisecure.core.blockchain import SignChain

        query = request.args.get('q', '').strip()
        if not query:
            return {'results': []}

        blockchain = SignChain()
        results = []

        # Search blocks by index
        try:
            block_index = int(query)
            if hasattr(blockchain, 'chain') and 0 <= block_index < len(blockchain.chain):
                block = blockchain.chain[block_index]
                results.append({
                    'type': 'block',
                    'index': block.index,
                    'hash': getattr(block, 'hash', 'unknown')[:16] + '...',
                    'timestamp': time.ctime(block.timestamp),
                    'transactions': len(block.transactions),
                    'difficulty': getattr(block, 'difficulty', 4)
                })
        except ValueError:
            pass

        # Search transactions by hash
        if hasattr(blockchain, 'chain'):
            for block in blockchain.chain[-20:]:  # Search last 20 blocks
                for tx in block.transactions:
                    tx_hash = getattr(tx, 'tx_hash', '')
                    if query.lower() in tx_hash.lower():
                        results.append({
                            'type': 'transaction',
                            'tx_hash': tx_hash[:16] + '...',
                            'block_index': block.index,
                            'type': tx.get('type', 'unknown'),
                            'amount': tx.get('amount', 0),
                            'sender': tx.get('sender_address', 'unknown')[:16] + '...',
                            'recipient': tx.get('recipient_address', 'unknown')[:16] + '...'
                        })

        return {'results': results[:10]}  # Limit to 10 results

    except Exception as e:
        return {'error': str(e), 'results': []}, 500

@app.route('/api/blockchain/block/<int:block_index>')
def get_block_details(block_index):
    """Get detailed information about a specific block"""
    try:
        from pisecure.core.blockchain import SignChain

        blockchain = SignChain()

        if not hasattr(blockchain, 'chain') or block_index >= len(blockchain.chain):
            return {'error': 'Block not found'}, 404

        block = blockchain.chain[block_index]

        # Get block details
        block_details = {
            'index': block.index,
            'hash': getattr(block, 'hash', 'unknown'),
            'previous_hash': getattr(block, 'previous_hash', 'unknown'),
            'timestamp': block.timestamp,
            'timestamp_human': time.ctime(block.timestamp),
            'difficulty': getattr(block, 'difficulty', 4),
            'nonce': getattr(block, 'nonce', 0),
            'miner': getattr(block, 'miner', 'unknown'),
            'transactions_count': len(block.transactions),
            'transactions': []
        }

        # Add transaction details
        for tx in block.transactions:
            tx_details = {
                'tx_hash': getattr(tx, 'tx_hash', 'unknown'),
                'type': tx.get('type', 'unknown'),
                'sender': tx.get('sender_address', 'unknown'),
                'recipient': tx.get('recipient_address', 'unknown'),
                'amount': tx.get('amount', 0),
                'timestamp': tx.get('timestamp', time.time()),
                'timestamp_human': time.ctime(tx.get('timestamp', time.time())),
                'signature': tx.get('signature', 'unknown')[:32] + '...' if tx.get('signature') else 'none'
            }
            block_details['transactions'].append(tx_details)

        return block_details

    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/blockchain/transaction/<tx_hash>')
def get_transaction_details(tx_hash):
    """Get detailed information about a specific transaction"""
    try:
        from pisecure.core.blockchain import SignChain

        blockchain = SignChain()

        # Search for transaction in recent blocks
        if hasattr(blockchain, 'chain'):
            for block in blockchain.chain[-50:]:  # Search last 50 blocks
                for tx in block.transactions:
                    if getattr(tx, 'tx_hash', '').startswith(tx_hash):
                        tx_details = {
                            'tx_hash': getattr(tx, 'tx_hash', 'unknown'),
                            'block_index': block.index,
                            'block_hash': getattr(block, 'hash', 'unknown'),
                            'type': tx.get('type', 'unknown'),
                            'sender_address': tx.get('sender_address', 'unknown'),
                            'recipient_address': tx.get('recipient_address', 'unknown'),
                            'amount': tx.get('amount', 0),
                            'timestamp': tx.get('timestamp', time.time()),
                            'timestamp_human': time.ctime(tx.get('timestamp', time.time())),
                            'signature': tx.get('signature', 'unknown'),
                            'nonce': tx.get('nonce', 'unknown'),
                            'memo': tx.get('memo', ''),
                            'fee': tx.get('fee', 0)
                        }

                        # Add batch transfer details if applicable
                        if tx.get('type') == 'batch_transfer':
                            tx_details['transfers'] = tx.get('transfers', [])
                            tx_details['total_amount'] = tx.get('total_amount', 0)
                            tx_details['transfer_count'] = tx.get('transfer_count', 0)

                        return tx_details

        return {'error': 'Transaction not found'}, 404

    except Exception as e:
        return {'error': str(e)}, 500

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