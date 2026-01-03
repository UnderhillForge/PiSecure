# 💱 Exchange Integration Guide: Adding 314ST Support

This guide explains how cryptocurrency exchanges can integrate PiSecure's 314ST token for storage, trading, deposits, and withdrawals.

## Prerequisites

- **PiSecure Node**: Run a full PiSecure node or connect to public nodes
- **Client SDK**: Use one of PiSecure's multi-language SDKs
- **Security Infrastructure**: Cold storage, hot wallets, and security protocols
- **Trading Engine**: Integration with your exchange's matching engine

---

## 1. Node Setup & Connection

### Option A: Run Your Own PiSecure Node
```bash
# Install PiSecure
curl -fsSL https://raw.githubusercontent.com/UnderhillForge/PiSecure/main/install.sh | bash

# Configure for exchange use
sudo nano /etc/pisecure/config.json
```

```json
{
  "network": {
    "port": 3142,
    "max_peers": 100,
    "relay_enabled": true
  },
  "api": {
    "rate_limit": "1000 per minute",
    "cors_origins": ["https://your-exchange.com"],
    "auth_required": true
  },
  "storage": {
    "use_hybrid_storage": true,
    "cache_size_mb": 512
  }
}
```

### Option B: Connect to Public Nodes
```javascript
const client = new PiSecureClient({
  nodes: [
    'https://node1.pisecure.io:3142',
    'https://node2.pisecure.io:3142',
    'wss://node3.pisecure.io:3143'
  ],
  failover: true
});
```

---

## 2. Wallet Management for Exchanges

### Hot Wallet Setup (for active trading)
```python
from pisecure_client import PiSecureClient

class ExchangeHotWallet:
    def __init__(self):
        self.client = PiSecureClient()
        self.hot_wallet = self.client.create_wallet("exchange_hot_wallet")

    def get_deposit_address(self, user_id: str) -> str:
        """Generate unique deposit address for user"""
        # Create user-specific wallet or sub-address
        user_wallet = self.client.create_wallet(f"user_{user_id}_deposit")
        return user_wallet.address

    def check_balance(self, wallet_id: str) -> float:
        """Check wallet balance"""
        return self.client.get_wallet_balance(wallet_id)

    def transfer_to_cold(self, amount: float, cold_wallet: str):
        """Move funds to cold storage"""
        tx = self.client.create_transfer_transaction(
            self.hot_wallet.id,
            cold_wallet,
            amount,
            "Cold storage transfer"
        )
        return self.client.submit_transaction(tx)
```

### Cold Storage Integration
```python
class ExchangeColdStorage:
    def __init__(self, cold_wallet_address: str):
        self.cold_address = cold_wallet_address
        self.client = PiSecureClient()

    def receive_from_hot(self, amount: float) -> bool:
        """Receive funds from hot wallet"""
        # Monitor incoming transactions to cold address
        balance = self.client.get_wallet_balance(self.cold_address)
        return balance >= amount

    def emergency_withdrawal(self, destination: str, amount: float):
        """Emergency withdrawal from cold storage"""
        # This would require manual signing with cold wallet
        pass
```

---

## 3. Deposit Handling

### User Deposit Flow
```javascript
class DepositHandler {
    constructor() {
        this.client = new PiSecureClient();
        this.pendingDeposits = new Map();
    }

    async generateDepositAddress(userId) {
        // Create unique deposit address for user
        const wallet = await this.client.createWallet(`deposit_${userId}`);
        this.pendingDeposits.set(wallet.address, {
            userId,
            walletId: wallet.id,
            created: Date.now()
        });
        return wallet.address;
    }

    async monitorDeposits() {
        // Check for new deposits every 30 seconds
        setInterval(async () => {
            for (const [address, deposit] of this.pendingDeposits) {
                try {
                    const balance = await this.client.getWalletBalance(address);
                    if (balance > 0) {
                        // Deposit detected
                        await this.processDeposit(deposit.userId, balance, address);
                        this.pendingDeposits.delete(address);
                    }
                } catch (error) {
                    console.error(`Error checking deposit for ${address}:`, error);
                }
            }
        }, 30000);
    }

    async processDeposit(userId, amount, depositAddress) {
        // Credit user account
        await this.updateUserBalance(userId, amount);

        // Move to hot wallet for trading
        const hotWalletTx = await this.client.createTransferTransaction(
            depositAddress,
            process.env.EXCHANGE_HOT_WALLET,
            amount,
            `Deposit for user ${userId}`
        );
        await this.client.submitTransaction(hotWalletTx);

        // Log transaction
        await this.logDeposit(userId, amount, depositAddress);
    }
}
```

---

## 4. Withdrawal Processing

### Secure Withdrawal Flow
```python
class WithdrawalProcessor:
    def __init__(self):
        self.client = PiSecureClient()
        self.pending_withdrawals = {}

    def request_withdrawal(self, user_id: str, amount: float, destination: str) -> str:
        """Process withdrawal request"""
        # Security checks
        if not self._validate_withdrawal_request(user_id, amount):
            raise ValueError("Invalid withdrawal request")

        # Create withdrawal record
        withdrawal_id = self._generate_withdrawal_id()
        self.pending_withdrawals[withdrawal_id] = {
            'user_id': user_id,
            'amount': amount,
            'destination': destination,
            'status': 'pending',
            'created': time.time()
        }

        # Queue for processing
        self._queue_withdrawal(withdrawal_id)
        return withdrawal_id

    def process_withdrawal(self, withdrawal_id: str) -> bool:
        """Execute withdrawal from hot wallet"""
        withdrawal = self.pending_withdrawals.get(withdrawal_id)
        if not withdrawal or withdrawal['status'] != 'pending':
            return False

        try:
            # Create transaction from hot wallet
            tx = self.client.create_transfer_transaction(
                os.getenv('EXCHANGE_HOT_WALLET'),
                withdrawal['destination'],
                withdrawal['amount'],
                f"Withdrawal for user {withdrawal['user_id']}"
            )

            # Submit transaction
            tx_hash = self.client.submit_transaction(tx)

            # Update status
            withdrawal['status'] = 'completed'
            withdrawal['tx_hash'] = tx_hash
            withdrawal['completed'] = time.time()

            # Log successful withdrawal
            self._log_withdrawal(withdrawal)
            return True

        except Exception as e:
            withdrawal['status'] = 'failed'
            withdrawal['error'] = str(e)
            self._log_failed_withdrawal(withdrawal)
            return False

    def _validate_withdrawal_request(self, user_id: str, amount: float) -> bool:
        """Validate withdrawal meets exchange policies"""
        # Check user balance
        user_balance = self._get_user_balance(user_id)
        if user_balance < amount:
            return False

        # Check withdrawal limits
        if amount > self._get_max_withdrawal_limit(user_id):
            return False

        # Check AML/KYC compliance
        if not self._check_compliance(user_id, amount):
            return False

        return True
```

---

## 5. Trading Engine Integration

### Order Book Management
```javascript
class OrderBookManager {
    constructor() {
        this.client = new PiSecureClient();
        this.buyOrders = new Map();  // price -> [orders]
        this.sellOrders = new Map();
    }

    async placeBuyOrder(userId, price, amount) {
        const order = {
            id: this.generateOrderId(),
            userId,
            type: 'buy',
            price,
            amount,
            remaining: amount,
            status: 'open',
            timestamp: Date.now()
        };

        // Add to order book
        if (!this.buyOrders.has(price)) {
            this.buyOrders.set(price, []);
        }
        this.buyOrders.get(price).push(order);

        // Try to match immediately
        await this.matchOrders();

        return order.id;
    }

    async placeSellOrder(userId, price, amount) {
        const order = {
            id: this.generateOrderId(),
            userId,
            type: 'sell',
            price,
            amount,
            remaining: amount,
            status: 'open',
            timestamp: Date.now()
        };

        // Add to order book
        if (!this.sellOrders.has(price)) {
            this.sellOrders.set(price, []);
        }
        this.sellOrders.get(price).push(order);

        // Try to match immediately
        await this.matchOrders();

        return order.id;
    }

    async matchOrders() {
        // Sort buy orders by price (highest first)
        const buyPrices = Array.from(this.buyOrders.keys()).sort((a, b) => b - a);
        // Sort sell orders by price (lowest first)
        const sellPrices = Array.from(this.sellOrders.keys()).sort((a, b) => a - b);

        for (const buyPrice of buyPrices) {
            for (const sellPrice of sellPrices) {
                if (buyPrice >= sellPrice) {
                    await this.executeMatch(buyPrice, sellPrice);
                }
            }
        }
    }

    async executeMatch(buyPrice, sellPrice) {
        const buyOrders = this.buyOrders.get(buyPrice) || [];
        const sellOrders = this.sellOrders.get(sellPrice) || [];

        while (buyOrders.length > 0 && sellOrders.length > 0) {
            const buyOrder = buyOrders[0];
            const sellOrder = sellOrders[0];

            const matchAmount = Math.min(buyOrder.remaining, sellOrder.remaining);
            const matchPrice = sellPrice; // Price priority to seller

            // Execute blockchain transfer
            const tx = await this.client.createTransferTransaction(
                sellOrder.userId, // seller pays
                buyOrder.userId,   // buyer receives
                matchAmount,
                `Trade execution: ${matchAmount} 314ST @ ${matchPrice}`
            );

            await this.client.submitTransaction(tx);

            // Update order remaining amounts
            buyOrder.remaining -= matchAmount;
            sellOrder.remaining -= matchAmount;

            // Remove filled orders
            if (buyOrder.remaining === 0) buyOrders.shift();
            if (sellOrder.remaining === 0) sellOrders.shift();

            // Log trade
            await this.logTrade(buyOrder.userId, sellOrder.userId, matchAmount, matchPrice);
        }
    }
}
```

---

## 6. Security Best Practices

### Multi-Signature Wallets
```python
class MultiSigWallet:
    def __init__(self, required_signatures: int = 3):
        self.required_sigs = required_signatures
        self.pending_txs = {}

    def create_multi_sig_transaction(self, from_wallet: str, to_address: str,
                                   amount: float, description: str):
        """Create transaction requiring multiple approvals"""
        tx_id = self._generate_tx_id()
        self.pending_txs[tx_id] = {
            'from': from_wallet,
            'to': to_address,
            'amount': amount,
            'description': description,
            'signatures': [],
            'required': self.required_sigs,
            'status': 'pending'
        }
        return tx_id

    def approve_transaction(self, tx_id: str, approver_id: str, signature: str):
        """Add approval signature to pending transaction"""
        if tx_id not in self.pending_txs:
            raise ValueError("Transaction not found")

        tx = self.pending_txs[tx_id]
        if approver_id in [sig['approver'] for sig in tx['signatures']]:
            raise ValueError("Already approved by this user")

        tx['signatures'].append({
            'approver': approver_id,
            'signature': signature,
            'timestamp': time.time()
        })

        # Execute if we have enough signatures
        if len(tx['signatures']) >= tx['required']:
            self._execute_multi_sig_transaction(tx_id)

    def _execute_multi_sig_transaction(self, tx_id: str):
        """Execute transaction once all signatures are collected"""
        # Implementation depends on PiSecure's multi-sig support
        pass
```

### Cold Storage Rotation
```python
class ColdStorageManager:
    def __init__(self):
        self.client = PiSecureClient()
        self.cold_wallets = []
        self.rotation_threshold = 100000  # Rotate after 100k 314ST

    async def rotate_cold_wallet(self, old_wallet: str) -> str:
        """Create new cold wallet and transfer funds"""
        # Generate new cold wallet
        new_wallet = await self.client.create_wallet("cold_storage_new")

        # Transfer all funds from old wallet
        balance = await self.client.get_wallet_balance(old_wallet)
        if balance > 0:
            tx = await self.client.create_transfer_transaction(
                old_wallet,
                new_wallet.address,
                balance,
                "Cold storage rotation"
            )
            await self.client.submit_transaction(tx)

        # Update wallet list
        self.cold_wallets.remove(old_wallet)
        self.cold_wallets.append(new_wallet.address)

        return new_wallet.address

    async def check_rotation_needed(self):
        """Check if any cold wallets need rotation"""
        for wallet in self.cold_wallets:
            balance = await self.client.get_wallet_balance(wallet)
            if balance > self.rotation_threshold:
                await self.rotate_cold_wallet(wallet)
```

---

## 7. Monitoring & Alerting

### Transaction Monitoring
```javascript
class TransactionMonitor {
    constructor() {
        this.client = new PiSecureClient();
        this.alerts = [];
    }

    async monitorExchangeWallets() {
        const wallets = [
            process.env.HOT_WALLET,
            process.env.COLD_WALLET,
            ...this.getUserWallets()
        ];

        for (const wallet of wallets) {
            try {
                const balance = await this.client.getWalletBalance(wallet);
                const transactions = await this.client.getWalletTransactions(wallet, 10);

                // Check for unusual activity
                await this.detectAnomalies(wallet, balance, transactions);

                // Check confirmations for pending withdrawals
                await this.checkConfirmations(transactions);

            } catch (error) {
                await this.alert('WALLET_ERROR', {
                    wallet,
                    error: error.message
                });
            }
        }
    }

    async detectAnomalies(wallet, balance, transactions) {
        // Large balance changes
        const recentTx = transactions[0];
        if (recentTx && recentTx.amount > 10000) {
            await this.alert('LARGE_TRANSACTION', {
                wallet,
                amount: recentTx.amount,
                hash: recentTx.hash
            });
        }

        // Unusual transaction frequency
        const recentTxs = transactions.filter(tx =>
            tx.timestamp > (Date.now() - 3600000) // Last hour
        );

        if (recentTxs.length > 50) {
            await this.alert('HIGH_FREQUENCY', {
                wallet,
                transactions: recentTxs.length
            });
        }
    }

    async checkConfirmations(transactions) {
        for (const tx of transactions) {
            if (tx.confirmations < 6) {
                // Alert for transactions with low confirmations
                await this.alert('LOW_CONFIRMATIONS', {
                    hash: tx.hash,
                    confirmations: tx.confirmations
                });
            }
        }
    }

    async alert(type, data) {
        console.log(`🚨 ${type}:`, data);
        // Send to alerting system (email, Slack, etc.)
        this.alerts.push({ type, data, timestamp: Date.now() });
    }
}
```

---

## 8. API Rate Limiting & Scaling

### Load Balancing
```python
class LoadBalancedClient:
    def __init__(self, node_urls: list):
        self.nodes = node_urls
        self.current_node = 0
        self.failures = {}

    def get_client(self):
        """Get next available node with failover"""
        attempts = 0
        while attempts < len(self.nodes):
            node_url = self.nodes[self.current_node]
            self.current_node = (self.current_node + 1) % len(self.nodes)

            # Skip nodes with recent failures
            if self._is_node_healthy(node_url):
                try:
                    return PiSecureClient(node_url)
                except:
                    self._mark_node_failure(node_url)

            attempts += 1

        raise Exception("No healthy nodes available")

    def _is_node_healthy(self, node_url: str) -> bool:
        """Check if node is healthy"""
        recent_failures = self.failures.get(node_url, [])
        # Remove old failures (older than 5 minutes)
        recent_failures = [f for f in recent_failures if time.time() - f < 300]
        self.failures[node_url] = recent_failures
        return len(recent_failures) < 3  # Allow up to 2 failures

    def _mark_node_failure(self, node_url: str):
        """Mark node as failed"""
        if node_url not in self.failures:
            self.failures[node_url] = []
        self.failures[node_url].append(time.time())
```

---

## 9. Testing & Validation

### Integration Testing
```python
import unittest
from unittest.mock import Mock, patch

class ExchangeIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.exchange = ExchangeIntegration(self.client)

    @patch('pisecure_client.PiSecureClient.get_wallet_balance')
    def test_deposit_processing(self, mock_balance):
        mock_balance.return_value = 100.0

        # Test deposit detection
        result = self.exchange.process_deposit('user123', 'deposit_address')
        self.assertTrue(result['success'])
        self.assertEqual(result['amount'], 100.0)

    @patch('pisecure_client.PiSecureClient.submit_transaction')
    def test_withdrawal_processing(self, mock_submit):
        mock_submit.return_value = 'tx_hash_123'

        # Test withdrawal execution
        result = self.exchange.process_withdrawal('withdrawal_id_123')
        self.assertTrue(result['success'])
        self.assertEqual(result['tx_hash'], 'tx_hash_123')

    def test_order_matching(self):
        # Test buy/sell order matching
        self.exchange.place_buy_order('user1', 1.0, 100)
        self.exchange.place_sell_order('user2', 0.9, 50)

        # Should execute trade
        trades = self.exchange.get_recent_trades()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['amount'], 50)
```

---

## 10. Compliance & Regulation

### KYC/AML Integration
```python
class ComplianceManager:
    def __init__(self):
        self.client = PiSecureClient()
        self.risk_thresholds = {
            'daily_withdrawal': 10000,
            'suspicious_amount': 50000,
            'high_risk_countries': ['CountryA', 'CountryB']
        }

    async def check_withdrawal_compliance(self, user_id: str, amount: float,
                                        destination: str) -> dict:
        """Check if withdrawal complies with regulations"""
        # Check daily withdrawal limits
        daily_total = await self.get_daily_withdrawals(user_id)
        if daily_total + amount > self.risk_thresholds['daily_withdrawal']:
            return {
                'approved': False,
                'reason': 'Daily withdrawal limit exceeded',
                'limit': self.risk_thresholds['daily_withdrawal']
            }

        # Check for suspicious amounts
        if amount > self.risk_thresholds['suspicious_amount']:
            return {
                'approved': False,
                'reason': 'Amount requires enhanced due diligence',
                'requires': 'manual_review'
            }

        # Check destination risk
        if await self.is_high_risk_destination(destination):
            return {
                'approved': False,
                'reason': 'Destination requires additional verification',
                'requires': 'enhanced_kyc'
            }

        return {'approved': True}

    async def flag_suspicious_activity(self, user_id: str, activity: dict):
        """Flag suspicious activity for review"""
        # Log to compliance system
        await self.log_compliance_event({
            'user_id': user_id,
            'activity': activity,
            'flagged': True,
            'reason': 'Suspicious pattern detected',
            'timestamp': time.time()
        })

        # Potentially freeze account
        if activity['severity'] == 'high':
            await self.freeze_account(user_id, 'Compliance review required')
```

---

## Getting Started Checklist

- [ ] **Set up PiSecure node(s)** with proper configuration
- [ ] **Implement hot/cold wallet separation** for security
- [ ] **Integrate client SDK** in your preferred language
- [ ] **Build deposit monitoring system** with address generation
- [ ] **Implement withdrawal processing** with security checks
- [ ] **Connect trading engine** to order book management
- [ ] **Add monitoring and alerting** for system health
- [ ] **Implement compliance checks** for KYC/AML
- [ ] **Set up load balancing** for high availability
- [ ] **Test thoroughly** with small amounts first

## Support & Resources

- **API Documentation**: [PiSecure API Reference](https://pisecure.readthedocs.io/)
- **Client SDKs**: [Multi-language SDKs](clients/)
- **Community Support**: [GitHub Discussions](https://github.com/UnderhillForge/PiSecure/discussions)
- **Security Best Practices**: [Security Guide](docs/security-model.md)

For enterprise integration support, contact the PiSecure development team.