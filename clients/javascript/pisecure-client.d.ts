// TypeScript definitions for PiSecure JavaScript Client

export interface PiSecureConfig {
  apiVersion?: string;
  timeout?: number;
  maxRetries?: number;
  bootstrapPeers?: string[];
  enableWebSocket?: boolean;
  cacheEnabled?: boolean;
  cacheTTL?: number;
}

export interface BlockchainInfo {
  blocks: number;
  height: number;
  difficulty: number;
  pending_transactions: number;
  network_hash_rate: number;
}

export interface Block {
  index: number;
  timestamp: number;
  transactions: Transaction[];
  previous_hash: string;
  hash: string;
  nonce: number;
}

export interface Transaction {
  hash: string;
  type: string;
  timestamp: number;
  data: any;
  signature?: string;
}

export interface Wallet {
  address: string;
  name?: string;
  display_name?: string;
  balance: number;
  created_at: number;
}

export interface NetworkStatus {
  connected_peers: number;
  total_peers: number;
  network_hash_rate: number;
  version: string;
}

export interface StreamEvent {
  type: string;
  eventType: string;
  data: any;
  timestamp: number;
}

export interface TrustFund {
  id: string;
  developer_address: string;
  trust_type: string;
  balance: number;
  subscribers: number;
  created_at: number;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  description: string;
  price: number;
  features: string[];
}

export interface ClientMetrics {
  requestsTotal: number;
  requestsFailed: number;
  cacheHits: number;
  cacheMisses: number;
  avgResponseTime: number;
  activeWebSockets: number;
  cacheSize: number;
  healthyEndpoints: number;
  totalEndpoints: number;
}

export declare class PiSecureClient extends EventEmitter {
  constructor(config?: PiSecureConfig);

  // Blockchain Operations
  getBlockchainInfo(): Promise<BlockchainInfo>;
  getBlock(blockIndex: number): Promise<Block>;
  getBlocks(limit?: number, offset?: number): Promise<Block[]>;
  getTransaction(txHash: string): Promise<Transaction>;

  // Wallet Operations
  getWalletBalance(address: string): Promise<number>;
  getWalletTransactions(address: string, limit?: number): Promise<Transaction[]>;
  createWallet(name?: string, displayName?: string): Promise<Wallet>;
  listWallets(): Promise<Wallet[]>;

  // Transaction Operations
  submitTransaction(txData: any): Promise<string>;
  createTransferTransaction(fromWallet: string, toAddress: string, amount: number, memo?: string): any;

  // Batch Operations
  submitTransactionBatch(transactions: any[]): Promise<Array<{index: number, success: boolean, hash?: string, error?: string}>>;
  getMultipleBalances(addresses: string[]): Promise<Record<string, number>>;

  // Network Operations
  getNetworkStatus(): Promise<NetworkStatus>;
  getNetworkPeers(): Promise<string[]>;
  healthCheck(): Promise<any>;

  // WebSocket Streaming
  connectWebSocket(streamType?: string): Promise<WebSocket>;
  disconnectWebSocket(streamType: string): void;

  // 314ST Token Economics
  createDeveloperTrust(developerAddress: string, trustType: string, initialFunding: number): Promise<TrustFund>;
  getTrust(trustId: string): Promise<TrustFund>;
  fundTrust(trustId: string, amount: number): Promise<any>;
  createSubscriptionPlan(trustId: string, planData: any): Promise<SubscriptionPlan>;
  addSubscriber(trustId: string, userId: string, planId: string): Promise<any>;
  checkUserAccess(trustId: string, userId: string, operationCost: number): Promise<any>;

  // Monitoring and Metrics
  getMetrics(): ClientMetrics;
  clearCache(): void;
  refreshPeers(): Promise<void>;

  // Configuration
  setCacheEnabled(enabled: boolean): void;
  setCacheTTL(ttl: number): void;

  // EventEmitter interface
  on(event: string, listener: Function): this;
  emit(event: string, ...args: any[]): boolean;
}

// Convenience functions
export declare function getBalance(address: string): Promise<number>;
export declare function submitTx(txData: any): Promise<string>;

// Event types
export declare namespace PiSecureEvents {
  interface Ready extends Event {
    type: 'ready';
  }

  interface Error extends Event {
    type: 'error';
    error: Error;
  }

  interface WebSocketConnected extends Event {
    type: 'websocket:connected';
    streamType: string;
  }

  interface WebSocketDisconnected extends Event {
    type: 'websocket:disconnected';
    streamType: string;
  }

  interface WebSocketError extends Event {
    type: 'websocket:error';
    error: Error;
  }

  interface StreamEvent extends Event {
    type: 'stream:event';
    data: {
      type: string;
      eventType: string;
      data: any;
      timestamp: number;
    };
  }
}

declare global {
  interface Window {
    PiSecureClient: typeof PiSecureClient;
    piSecureGetBalance: typeof getBalance;
    piSecureSubmitTx: typeof submitTx;
  }
}