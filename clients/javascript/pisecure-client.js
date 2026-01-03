#!/usr/bin/env node

/**
 * PiSecure JavaScript/TypeScript Client
 * =====================================
 *
 * Production-ready JavaScript client for PiSecure blockchain API.
 * Supports both Node.js and browser environments.
 */

const axios = require('axios');
const WebSocket = require('ws'); // For Node.js - browser would use native WebSocket
const EventEmitter = require('events');

/**
 * PiSecure Client Configuration
 */
class PiSecureConfig {
  constructor(options = {}) {
    this.apiVersion = options.apiVersion || 'v1';
    this.timeout = options.timeout || 30000;
    this.maxRetries = options.maxRetries || 3;
    this.bootstrapPeers = options.bootstrapPeers || [
      'https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/peers.json'
    ];
    this.enableWebSocket = options.enableWebSocket !== false;
    this.cacheEnabled = options.cacheEnabled !== false;
    this.cacheTTL = options.cacheTTL || 30000; // 30 seconds
  }
}

/**
 * Connection Pool for Load Balancing
 */
class ConnectionPool {
  constructor(endpoints = []) {
    this.endpoints = endpoints;
    this.currentIndex = 0;
    this.healthStatus = new Map();
  }

  addEndpoint(endpoint) {
    if (!this.endpoints.includes(endpoint)) {
      this.endpoints.push(endpoint);
    }
  }

  getNextEndpoint() {
    if (this.endpoints.length === 0) {
      throw new Error('No available endpoints');
    }

    // Simple round-robin with health check
    let attempts = 0;
    while (attempts < this.endpoints.length) {
      const endpoint = this.endpoints[this.currentIndex];
      this.currentIndex = (this.currentIndex + 1) % this.endpoints.length;

      if (this.isHealthy(endpoint)) {
        return endpoint;
      }
      attempts++;
    }

    throw new Error('No healthy endpoints available');
  }

  markHealthy(endpoint) {
    this.healthStatus.set(endpoint, { healthy: true, lastCheck: Date.now() });
  }

  markUnhealthy(endpoint) {
    this.healthStatus.set(endpoint, { healthy: false, lastCheck: Date.now() });
  }

  isHealthy(endpoint) {
    const status = this.healthStatus.get(endpoint);
    if (!status) return true; // Assume healthy if not checked

    // If marked unhealthy recently, consider unhealthy
    if (!status.healthy && Date.now() - status.lastCheck < 60000) {
      return false;
    }

    return true;
  }
}

/**
 * Cache for API Responses
 */
class ResponseCache {
  constructor(ttl = 30000) {
    this.cache = new Map();
    this.ttl = ttl;
  }

  get(key) {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() - entry.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  clear() {
    this.cache.clear();
  }

  size() {
    return this.cache.size;
  }
}

/**
 * PiSecure JavaScript Client
 */
class PiSecureClient extends EventEmitter {
  constructor(config = {}) {
    super();

    this.config = new PiSecureConfig(config);
    this.connectionPool = new ConnectionPool();
    this.cache = new ResponseCache(this.config.cacheTTL);
    this.httpClient = axios.create({
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'PiSecure-JS-Client/1.0.0'
      }
    });

    // WebSocket connections
    this.webSockets = new Map();

    // Metrics
    this.metrics = {
      requestsTotal: 0,
      requestsFailed: 0,
      cacheHits: 0,
      cacheMisses: 0,
      avgResponseTime: 0
    };

    // Initialize
    this._initialize();
  }

  async _initialize() {
    try {
      await this._discoverEndpoints();
      this.emit('ready');
    } catch (error) {
      this.emit('error', error);
    }
  }

  async _discoverEndpoints() {
    // Try to fetch peer list from bootstrap
    for (const bootstrapUrl of this.config.bootstrapPeers) {
      try {
        const response = await axios.get(bootstrapUrl, { timeout: 5000 });
        const peers = response.data.peers || [];

        for (const peer of peers) {
          const apiUrl = peer.api_url || `http://${peer.host}:${peer.port || 3142}`;
          this.connectionPool.addEndpoint(apiUrl);
        }

        if (this.connectionPool.endpoints.length > 0) {
          break;
        }
      } catch (error) {
        // Continue to next bootstrap peer
        continue;
      }
    }

    // Fallback endpoints
    if (this.connectionPool.endpoints.length === 0) {
      this.connectionPool.addEndpoint('http://localhost:3142');
      this.connectionPool.addEndpoint('http://pisecure-node.local:3142');
    }
  }

  _getCacheKey(method, endpoint, params = {}) {
    const sortedParams = Object.keys(params).sort()
      .reduce((result, key) => {
        result[key] = params[key];
        return result;
      }, {});
    return `${method}:${endpoint}:${JSON.stringify(sortedParams)}`;
  }

  async _makeRequest(method, endpoint, data = null, params = {}, useCache = true) {
    const startTime = Date.now();

    // Check cache for GET requests
    const cacheKey = this._getCacheKey(method, endpoint, params);
    if (useCache && method === 'GET') {
      const cached = this.cache.get(cacheKey);
      if (cached) {
        this.metrics.cacheHits++;
        return cached;
      }
      this.metrics.cacheMisses++;
    }

    let lastError = null;

    for (let attempt = 0; attempt < this.config.maxRetries; attempt++) {
      try {
        const baseUrl = this.connectionPool.getNextEndpoint();
        const url = `${baseUrl}/api/${this.config.apiVersion}/${endpoint.replace(/^\//, '')}`;

        const config = {
          method,
          url,
          params: method === 'GET' ? params : undefined,
          data: method !== 'GET' ? data : undefined
        };

        const response = await this.httpClient.request(config);
        const result = response.data;

        // Update metrics
        this.metrics.requestsTotal++;
        const responseTime = Date.now() - startTime;
        this.metrics.avgResponseTime =
          (this.metrics.avgResponseTime * (this.metrics.requestsTotal - 1) + responseTime) /
          this.metrics.requestsTotal;

        // Mark endpoint as healthy
        this.connectionPool.markHealthy(baseUrl);

        // Cache successful GET responses
        if (useCache && method === 'GET') {
          this.cache.set(cacheKey, result);
        }

        return result;

      } catch (error) {
        lastError = error;
        this.metrics.requestsFailed++;

        // Mark endpoint as unhealthy
        try {
          const baseUrl = this.connectionPool.getNextEndpoint();
          this.connectionPool.markUnhealthy(baseUrl);
        } catch (e) {
          // Ignore
        }

        // Exponential backoff
        if (attempt < this.config.maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 100));
        }
      }
    }

    throw new Error(`Request failed after ${this.config.maxRetries} attempts: ${lastError.message}`);
  }

  // Blockchain Operations

  async getBlockchainInfo() {
    return await this._makeRequest('GET', 'blockchain/info');
  }

  async getBlock(blockIndex) {
    return await this._makeRequest('GET', `blockchain/block/${blockIndex}`);
  }

  async getBlocks(limit = 10, offset = 0) {
    const params = { limit: Math.min(limit, 100), offset };
    const response = await this._makeRequest('GET', 'blockchain/blocks', null, params);
    return Array.isArray(response) ? response : [];
  }

  async getTransaction(txHash) {
    return await this._makeRequest('GET', `blockchain/transaction/${txHash}`);
  }

  // Wallet Operations

  async getWalletBalance(address) {
    const response = await this._makeRequest('GET', `wallet/${address}/balance`);
    return parseFloat(response.balance || 0);
  }

  async getWalletTransactions(address, limit = 20) {
    const params = { limit: Math.min(limit, 100) };
    const response = await this._makeRequest('GET', `wallet/${address}/transactions`, null, params);
    return response.transactions || [];
  }

  async createWallet(name = null, displayName = null) {
    const data = {};
    if (name) data.name = name;
    if (displayName) data.display_name = displayName;
    return await this._makeRequest('POST', 'wallet', data);
  }

  async listWallets() {
    const response = await this._makeRequest('GET', 'wallets');
    return response.wallets || [];
  }

  // Transaction Operations

  async submitTransaction(txData) {
    const response = await this._makeRequest('POST', 'transaction', txData);
    return response.transaction_hash || '';
  }

  createTransferTransaction(fromWallet, toAddress, amount, memo = '') {
    return {
      type: 'transfer',
      from_wallet: fromWallet,
      to_address: toAddress,
      amount: amount,
      memo: memo,
      timestamp: Date.now() / 1000,
      data: {
        recipient: toAddress,
        amount: amount,
        memo: memo
      }
    };
  }

  // Batch Operations

  async submitTransactionBatch(transactions) {
    const promises = transactions.map(tx => this.submitTransaction(tx));
    const results = await Promise.allSettled(promises);
    return results.map((result, index) => ({
      index,
      success: result.status === 'fulfilled',
      hash: result.status === 'fulfilled' ? result.value : null,
      error: result.status === 'rejected' ? result.reason.message : null
    }));
  }

  async getMultipleBalances(addresses) {
    const promises = addresses.map(addr => this.getWalletBalance(addr));
    const results = await Promise.allSettled(promises);
    return addresses.reduce((acc, addr, index) => {
      const result = results[index];
      acc[addr] = result.status === 'fulfilled' ? result.value : 0;
      return acc;
    }, {});
  }

  // Network Operations

  async getNetworkStatus() {
    return await this._makeRequest('GET', 'network/status');
  }

  async getNetworkPeers() {
    const response = await this._makeRequest('GET', 'network/peers');
    return response.peers || [];
  }

  async healthCheck() {
    return await this._makeRequest('GET', 'health');
  }

  // WebSocket Streaming

  connectWebSocket(streamType = 'blocks') {
    return new Promise((resolve, reject) => {
      if (!this.config.enableWebSocket) {
        reject(new Error('WebSocket support disabled'));
        return;
      }

      try {
        const baseUrl = this.connectionPool.getNextEndpoint();
        const wsUrl = baseUrl.replace(/^http/, 'ws') +
                     `/api/${this.config.apiVersion}/stream?type=${streamType}`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          this.webSockets.set(streamType, ws);
          this.emit('websocket:connected', streamType);
          resolve(ws);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.emit('stream:event', {
              type: streamType,
              eventType: data.type,
              data: data.data,
              timestamp: Date.now()
            });
          } catch (error) {
            this.emit('websocket:error', error);
          }
        };

        ws.onerror = (error) => {
          this.emit('websocket:error', error);
          reject(error);
        };

        ws.onclose = () => {
          this.webSockets.delete(streamType);
          this.emit('websocket:disconnected', streamType);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnectWebSocket(streamType) {
    const ws = this.webSockets.get(streamType);
    if (ws) {
      ws.close();
      this.webSockets.delete(streamType);
    }
  }

  // 314ST Token Economics (Advanced Features)

  async createDeveloperTrust(developerAddress, trustType, initialFunding) {
    const data = {
      developer_address: developerAddress,
      trust_type: trustType,
      initial_funding: initialFunding
    };
    return await this._makeRequest('POST', 'trust', data);
  }

  async getTrust(trustId) {
    return await this._makeRequest('GET', `trust/${trustId}`);
  }

  async fundTrust(trustId, amount) {
    const data = { amount };
    return await this._makeRequest('POST', `trust/${trustId}/fund`, data);
  }

  async createSubscriptionPlan(trustId, planData) {
    return await this._makeRequest('POST', `trust/${trustId}/plan`, planData);
  }

  async addSubscriber(trustId, userId, planId) {
    const data = { user_id: userId, plan_id: planId };
    return await this._makeRequest('POST', `trust/${trustId}/subscribe`, data);
  }

  async checkUserAccess(trustId, userId, operationCost) {
    const data = { user_id: userId, operation_cost: operationCost };
    return await this._makeRequest('POST', `trust/${trustId}/access/${userId}`, data);
  }

  // Monitoring and Metrics

  getMetrics() {
    return {
      ...this.metrics,
      activeWebSockets: this.webSockets.size,
      cacheSize: this.cache.size(),
      healthyEndpoints: this.connectionPool.endpoints.filter(
        ep => this.connectionPool.isHealthy(ep)
      ).length,
      totalEndpoints: this.connectionPool.endpoints.length
    };
  }

  clearCache() {
    this.cache.clear();
  }

  refreshPeers() {
    return this._discoverEndpoints();
  }

  // Utility Methods

  setCacheEnabled(enabled) {
    this.config.cacheEnabled = enabled;
  }

  setCacheTTL(ttl) {
    this.config.cacheTTL = ttl;
    this.cache = new ResponseCache(ttl);
  }
}

// Convenience functions
async function getBalance(address) {
  const client = new PiSecureClient();
  try {
    return await client.getWalletBalance(address);
  } finally {
    // Cleanup if needed
  }
}

async function submitTx(txData) {
  const client = new PiSecureClient();
  try {
    return await client.submitTransaction(txData);
  } finally {
    // Cleanup if needed
  }
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
  // Node.js
  module.exports = { PiSecureClient, getBalance, submitTx };
} else if (typeof window !== 'undefined') {
  // Browser
  window.PiSecureClient = PiSecureClient;
  window.piSecureGetBalance = getBalance;
  window.piSecureSubmitTx = submitTx;
}

// Example usage
if (require.main === module) {
  async function example() {
    const client = new PiSecureClient();

    try {
      // Basic operations
      const info = await client.getBlockchainInfo();
      console.log(`Blockchain: ${info.blocks} blocks`);

      const balance = await client.getWalletBalance('some_address');
      console.log(`Balance: ${balance} tokens`);

      // Batch operations
      const addresses = ['addr1', 'addr2', 'addr3'];
      const balances = await client.getMultipleBalances(addresses);
      console.log('Balances:', balances);

      // WebSocket streaming
      await client.connectWebSocket('transactions');
      client.on('stream:event', (event) => {
        console.log('New event:', event);
      });

      // Metrics
      const metrics = client.getMetrics();
      console.log('Client metrics:', metrics);

    } catch (error) {
      console.error('Error:', error.message);
    }
  }

  example();
}