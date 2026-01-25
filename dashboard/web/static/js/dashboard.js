/**
 * PiSecure Dashboard JavaScript
 * Handles real-time updates, WebSocket communication, and UI interactions
 */

class PiSecureDashboard {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.dataHistory = {
            cpu: [],
            memory: [],
            hashrate: [],
            timestamps: []
        };
        this.maxDataPoints = 60; // 5 minutes of data at 5-second intervals

        this.initializeSocket();
        this.initializeCharts();
        this.setupEventListeners();
        this.startPeriodicUpdates();
    }

    initializeSocket() {
        // Initialize Socket.IO connection
        this.socket = io();

        this.socket.on('connect', () => {
            this.updateConnectionStatus(true, 'Connected');
            console.log('Connected to PiSecure Dashboard');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false, 'Disconnected');
            console.log('Disconnected from PiSecure Dashboard');
        });

        this.socket.on('status', (data) => {
            console.log('Status:', data.message);
        });

        // Handle real-time updates
        this.socket.on('system_update', (data) => {
            this.updateSystemStats(data);
        });

        this.socket.on('blockchain_update', (data) => {
            this.updateBlockchainStats(data);
        });

        this.socket.on('mining_update', (data) => {
            this.updateMiningStats(data);
        });

        this.socket.on('network_update', (data) => {
            this.updateNetworkStats(data);
        });
    }

    updateConnectionStatus(connected, message) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');

        if (connected) {
            statusDot.className = 'status-dot connected';
            statusText.textContent = message;
        } else {
            statusDot.className = 'status-dot disconnected';
            statusText.textContent = message;
        }
    }

    updateSystemStats(data) {
        if (data.error) {
            console.error('System stats error:', data.error);
            return;
        }

        // Update CPU
        this.updateElement('cpu-percent', `${data.cpu_percent.toFixed(1)}%`);
        this.updateProgressBar('cpu-bar', data.cpu_percent);

        // Update Memory
        this.updateElement('memory-percent', `${data.memory_percent.toFixed(1)}%`);
        this.updateProgressBar('memory-bar', data.memory_percent);

        // Update Disk
        this.updateElement('disk-percent', `${data.disk_percent.toFixed(1)}%`);
        this.updateProgressBar('disk-bar', data.disk_percent);

        // Update Temperature
        const temp = data.temperature ? `${data.temperature.toFixed(1)}°C` : '--°C';
        this.updateElement('temperature', temp);

        // Add to history for charting
        this.addToHistory('cpu', data.cpu_percent);
        this.addToHistory('memory', data.memory_percent);
        this.updatePerformanceChart();
    }

    updateBlockchainStats(data) {
        if (data.error) {
            console.error('Blockchain stats error:', data.error);
            return;
        }

        if (data.status === 'not_initialized') {
            this.updateElement('block-count', '--');
            this.updateElement('pending-tx', '--');
            this.updateElement('difficulty', '--');
            this.updateElement('valid-indicator', '❓');
            return;
        }

        this.updateElement('block-count', data.blocks || 0);
        this.updateElement('pending-tx', data.pending_transactions || 0);
        this.updateElement('difficulty', data.difficulty || 0);

        const isValid = data.is_valid ? '✅' : '❌';
        this.updateElement('valid-indicator', isValid);

        // Update recent blocks
        if (data.blocks > 0) {
            this.updateRecentBlocks();
        }
    }

    updateMiningStats(data) {
        if (data.error) {
            console.error('Mining stats error:', data.error);
            return;
        }

        const statusElement = document.getElementById('mining-status');
        const status = data.status || 'unknown';

        // Update status with appropriate styling
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusElement.className = `mining-value status-${status}`;

        this.updateElement('hashrate', `${data.hashrate || 0} MH/s`);
        this.updateElement('blocks-found', data.blocks_found || 0);
        this.updateElement('mining-uptime', data.uptime || '0m');

        // Add hashrate to history
        if (data.hashrate) {
            this.addToHistory('hashrate', data.hashrate);
            this.updatePerformanceChart();
        }
    }

    updateNetworkStats(data) {
        if (data.error) {
            console.error('Network stats error:', data.error);
            return;
        }

        if (data.status === 'not_initialized') {
            this.updateElement('connected-peers', '--');
            this.updateElement('known-peers', '--');
            this.updateElement('sync-progress', '--');
            this.updateElement('network-health', '--');
            return;
        }

        this.updateElement('connected-peers', data.connected_peers || 0);
        this.updateElement('known-peers', data.total_known_peers || 0);

        // Calculate sync progress (simplified)
        const syncProgress = data.connected_peers > 0 ? '100%' : '0%';
        this.updateElement('sync-progress', syncProgress);

        // Network health based on peer count
        let health = 'Poor';
        if (data.connected_peers >= 8) health = 'Excellent';
        else if (data.connected_peers >= 5) health = 'Good';
        else if (data.connected_peers >= 2) health = 'Fair';

        this.updateElement('network-health', health);
    }

    async updateRecentBlocks() {
        try {
            const response = await fetch('/api/blockchain/blocks?limit=5');
            const blocks = await response.json();

            const container = document.getElementById('recent-blocks');
            container.innerHTML = '';

            if (blocks.length === 0) {
                container.innerHTML = '<div class="activity-item">No blocks found</div>';
                return;
            }

            blocks.forEach(block => {
                const item = document.createElement('div');
                item.className = 'activity-item';

                const time = new Date(block.timestamp * 1000).toLocaleTimeString();
                const desc = `Block #${block.index}: ${block.transactions} transactions (${block.size} bytes)`;

                item.innerHTML = `
                    <span class="activity-time">${time}</span>
                    <span class="activity-desc">${desc}</span>
                `;

                container.appendChild(item);
            });
        } catch (error) {
            console.error('Failed to update recent blocks:', error);
        }
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    updateProgressBar(id, percentage) {
        const bar = document.getElementById(id);
        if (bar) {
            bar.style.width = `${percentage}%`;
        }
    }

    addToHistory(metric, value) {
        this.dataHistory[metric].push(value);
        this.dataHistory.timestamps.push(new Date());

        // Keep only recent data
        if (this.dataHistory[metric].length > this.maxDataPoints) {
            this.dataHistory[metric].shift();
            this.dataHistory.timestamps.shift();
        }
    }

    initializeCharts() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;

        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Memory Usage (%)',
                    data: [],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Hashrate (MH/s)',
                    data: [],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4,
                    yAxisID: 'hashrate'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Usage (%)'
                        }
                    },
                    hashrate: {
                        position: 'right',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Hashrate (MH/s)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }

    updatePerformanceChart() {
        if (!this.charts.performance) return;

        const chart = this.charts.performance;
        const labels = this.dataHistory.timestamps.map(ts =>
            ts.toISOString().slice(11, 16) // HH:MM format
        );

        chart.data.labels = labels;
        chart.data.datasets[0].data = this.dataHistory.cpu;
        chart.data.datasets[1].data = this.dataHistory.memory;
        chart.data.datasets[2].data = this.dataHistory.hashrate;

        chart.update('none'); // Update without animation for performance
    }

    setupEventListeners() {
        // Request initial data on page load
        window.addEventListener('load', () => {
            this.requestInitialData();
        });

        // Handle navigation
        document.querySelectorAll('nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                // Remove active class from all links
                document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
                // Add active class to clicked link
                e.target.classList.add('active');
            });
        });

        // Handle manual refresh
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.requestAllUpdates();
            }
        });
    }

    requestInitialData() {
        // Request initial data from all endpoints
        this.requestAllUpdates();

        // Load initial blocks
        this.updateRecentBlocks();
    }

    requestAllUpdates() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('request_update', { type: 'all' });
        }
    }

    startPeriodicUpdates() {
        // Request updates every 30 seconds as fallback
        setInterval(() => {
            if (this.socket && !this.socket.connected) {
                this.requestAllUpdates();
            }
        }, 30000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new PiSecureDashboard();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.dashboard) {
        // Refresh data when page becomes visible
        window.dashboard.requestAllUpdates();
    }
});