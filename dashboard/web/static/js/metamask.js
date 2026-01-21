/**
 * PiSecure Metamask Integration Module
 * Handles MetaMask wallet connection and interaction with PiSecure blockchain
 */

class MetamaskIntegration {
    constructor() {
        this.ethereum = null;
        this.account = null;
        this.connected = false;
        this.chainId = null;
        this.initializeMetamask();
    }

    /**
     * Initialize Metamask detection
     */
    initializeMetamask() {
        // Check if MetaMask is installed
        if (typeof window.ethereum !== 'undefined') {
            this.ethereum = window.ethereum;
            console.log('MetaMask detected!');
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Check if already connected
            this.checkConnection();
        } else {
            console.log('MetaMask not detected');
        }
    }

    /**
     * Setup MetaMask event listeners
     */
    setupEventListeners() {
        if (!this.ethereum) return;

        // Listen for account changes
        this.ethereum.on('accountsChanged', (accounts) => {
            console.log('Accounts changed:', accounts);
            if (accounts.length === 0) {
                this.handleDisconnect();
            } else {
                this.account = accounts[0];
                this.updateUI();
            }
        });

        // Listen for chain changes
        this.ethereum.on('chainChanged', (chainId) => {
            console.log('Chain changed:', chainId);
            this.chainId = chainId;
            // Reload page when chain changes as recommended by MetaMask
            window.location.reload();
        });

        // Listen for connection
        this.ethereum.on('connect', (connectInfo) => {
            console.log('MetaMask connected:', connectInfo);
            this.chainId = connectInfo.chainId;
        });

        // Listen for disconnection
        this.ethereum.on('disconnect', (error) => {
            console.log('MetaMask disconnected:', error);
            this.handleDisconnect();
        });
    }

    /**
     * Check if MetaMask is already connected
     */
    async checkConnection() {
        if (!this.ethereum) return false;

        try {
            const accounts = await this.ethereum.request({ 
                method: 'eth_accounts' 
            });
            
            if (accounts.length > 0) {
                this.account = accounts[0];
                this.connected = true;
                
                // Get chain ID
                this.chainId = await this.ethereum.request({ 
                    method: 'eth_chainId' 
                });
                
                this.updateUI();
                return true;
            }
        } catch (error) {
            console.error('Error checking connection:', error);
        }
        
        return false;
    }

    /**
     * Connect to MetaMask
     */
    async connect() {
        if (!this.ethereum) {
            alert('MetaMask is not installed! Please install MetaMask browser extension.');
            window.open('https://metamask.io/download/', '_blank');
            return false;
        }

        try {
            // Request account access
            const accounts = await this.ethereum.request({ 
                method: 'eth_requestAccounts' 
            });
            
            if (accounts.length > 0) {
                this.account = accounts[0];
                this.connected = true;
                
                // Get chain ID
                this.chainId = await this.ethereum.request({ 
                    method: 'eth_chainId' 
                });
                
                console.log('Connected to MetaMask:', this.account);
                console.log('Chain ID:', this.chainId);
                
                this.updateUI();
                
                // Register wallet with PiSecure backend
                await this.registerWalletWithPiSecure();
                
                return true;
            }
        } catch (error) {
            console.error('Error connecting to MetaMask:', error);
            
            if (error.code === 4001) {
                // User rejected the request
                alert('Connection request rejected. Please try again.');
            } else {
                alert('Failed to connect to MetaMask: ' + error.message);
            }
        }
        
        return false;
    }

    /**
     * Disconnect from MetaMask
     */
    handleDisconnect() {
        this.account = null;
        this.connected = false;
        this.chainId = null;
        this.updateUI();
    }

    /**
     * Get current account balance from blockchain
     */
    async getBalance() {
        if (!this.ethereum || !this.account) return '0';

        try {
            const balance = await this.ethereum.request({
                method: 'eth_getBalance',
                params: [this.account, 'latest']
            });
            
            // Convert from wei to ether
            const ethBalance = parseInt(balance, 16) / 1e18;
            return ethBalance.toFixed(4);
        } catch (error) {
            console.error('Error getting balance:', error);
            return '0';
        }
    }

    /**
     * Sign a message with MetaMask
     */
    async signMessage(message) {
        if (!this.ethereum || !this.account) {
            throw new Error('MetaMask not connected');
        }

        try {
            const signature = await this.ethereum.request({
                method: 'personal_sign',
                params: [message, this.account]
            });
            
            return signature;
        } catch (error) {
            console.error('Error signing message:', error);
            throw error;
        }
    }

    /**
     * Register MetaMask wallet with PiSecure backend
     */
    async registerWalletWithPiSecure() {
        if (!this.account) return;

        try {
            // Create a signature to prove ownership
            const timestamp = Date.now();
            const message = `PiSecure Wallet Link: ${this.account} at ${timestamp}`;
            const signature = await this.signMessage(message);

            // Send to PiSecure API
            const response = await fetch('/api/wallets/metamask/link', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    address: this.account,
                    chain_id: this.chainId,
                    signature: signature,
                    message: message,
                    timestamp: timestamp
                })
            });

            const data = await response.json();
            
            if (data.error) {
                console.error('Error registering wallet:', data.error);
                return false;
            }

            console.log('Wallet registered with PiSecure:', data);
            return true;
        } catch (error) {
            console.error('Error registering wallet with PiSecure:', error);
            return false;
        }
    }

    /**
     * Update UI elements
     */
    updateUI() {
        const connectBtn = document.getElementById('metamask-connect-btn');
        const statusDiv = document.getElementById('metamask-status');
        const accountDiv = document.getElementById('metamask-account');
        const chainDiv = document.getElementById('metamask-chain');

        if (!connectBtn) return;

        if (this.connected && this.account) {
            // Update button
            connectBtn.textContent = 'Connected';
            connectBtn.style.background = '#28a745';
            connectBtn.disabled = true;

            // Update status
            if (statusDiv) {
                statusDiv.innerHTML = '<span style="color: #28a745;">✓ Connected</span>';
            }

            // Update account display
            if (accountDiv) {
                const shortAddress = `${this.account.substring(0, 6)}...${this.account.substring(38)}`;
                accountDiv.textContent = `Account: ${shortAddress}`;
                accountDiv.title = this.account; // Show full address on hover
            }

            // Update chain display
            if (chainDiv) {
                const chainName = this.getChainName(this.chainId);
                chainDiv.textContent = `Network: ${chainName}`;
            }

            // Fetch and display balance
            this.getBalance().then(balance => {
                const balanceDiv = document.getElementById('metamask-balance');
                if (balanceDiv) {
                    balanceDiv.textContent = `Balance: ${balance} ETH`;
                }
            });
        } else {
            // Update button
            connectBtn.textContent = 'Connect MetaMask';
            connectBtn.style.background = '#007bff';
            connectBtn.disabled = false;

            // Clear status
            if (statusDiv) {
                statusDiv.innerHTML = '<span style="color: #999;">Not connected</span>';
            }
            if (accountDiv) accountDiv.textContent = '';
            if (chainDiv) chainDiv.textContent = '';
        }
    }

    /**
     * Get human-readable chain name
     */
    getChainName(chainId) {
        const chains = {
            '0x1': 'Ethereum Mainnet',
            '0x3': 'Ropsten Testnet',
            '0x4': 'Rinkeby Testnet',
            '0x5': 'Goerli Testnet',
            '0x2a': 'Kovan Testnet',
            '0x89': 'Polygon Mainnet',
            '0x13881': 'Polygon Mumbai',
            '0xa4b1': 'Arbitrum One',
            '0xa': 'Optimism',
            '0x38': 'BSC Mainnet',
            '0x61': 'BSC Testnet'
        };
        
        return chains[chainId] || `Chain ${chainId}`;
    }

    /**
     * Check if MetaMask is installed
     */
    isInstalled() {
        return this.ethereum !== null;
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Get current account
     */
    getAccount() {
        return this.account;
    }

    /**
     * Get chain ID
     */
    getChainId() {
        return this.chainId;
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetamaskIntegration;
}
