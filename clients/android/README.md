# PiSecure Android SDK

**Complete Android SDK for PiSecure blockchain integration**

This SDK provides a full-featured Android library for interacting with PiSecure blockchain nodes, enabling seamless integration of cryptocurrency functionality into Android applications.

## 🚀 Features

### ✅ **Complete API Coverage**
- **45+ REST API endpoints** fully supported
- **Real-time blockchain data** access
- **Wallet management** (create, import, export)
- **Transaction handling** (send, receive, sign)
- **PiNS name system** for user-friendly addresses
- **Mining operations** and statistics
- **Token economics** and trust funds

### ✅ **Android-Specific Features**
- **Kotlin-first** API design
- **Coroutines support** for async operations
- **Offline transaction signing** (secure key management)
- **Push notifications** for transaction updates
- **QR code generation** for easy payments
- **Biometric authentication** integration

### ✅ **Security & Performance**
- **No sensitive data** stored on device
- **Hardware-backed keystore** integration
- **Certificate pinning** for API security
- **Automatic retries** and connection management
- **Minimal battery impact** through efficient polling

---

## 📱 Installation

### Gradle (Kotlin DSL)
```kotlin
dependencies {
    implementation("com.underhillforge.pisecure:android-sdk:1.0.0")
}
```

### Gradle (Groovy)
```groovy
dependencies {
    implementation 'com.underhillforge.pisecure:android-sdk:1.0.0'
}
```

---

## 🏗️ Quick Start

### Initialize SDK
```kotlin
import com.underhillforge.pisecure.PiSecureSDK

class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        // Initialize with your node URL
        PiSecureSDK.initialize(
            context = this,
            nodeUrl = "https://your-pisecure-node.com",
            enablePushNotifications = true
        )
    }
}
```

### Create Wallet
```kotlin
import com.underhillforge.pisecure.wallet.PiSecureWallet

// Create a new wallet
val wallet = PiSecureWallet.create(
    name = "My Mobile Wallet",
    enableBiometricAuth = true
)

// Wallet is automatically secured with device keystore
println("Wallet created: ${wallet.address}")
```

### Check Balance
```kotlin
// Get wallet balance
val balance = wallet.getBalance()
println("Balance: ${balance.amount} PSC")

// Listen for balance changes
wallet.addBalanceListener { newBalance ->
    println("Balance updated: ${newBalance.amount}")
}
```

### Send Transaction
```kotlin
// Send tokens (using PiNS names!)
val transaction = wallet.sendTokens(
    recipient = "alice",  // PiNS name or wallet address
    amount = 10.5,
    memo = "Coffee payment",
    fee = TransactionFee.PRIORITY
)

// Transaction submitted to network
println("Transaction sent: ${transaction.hash}")
```

### Register PiNS Name
```kotlin
// Register a human-readable name
val nameRegistration = PiSecureWallet.registerName(
    name = "mybusiness",
    wallet = wallet
)

// Check registration status
when (nameRegistration.status) {
    NameRegistrationStatus.PENDING -> println("Registration pending...")
    NameRegistrationStatus.CONFIRMED -> println("Name registered!")
    NameRegistrationStatus.FAILED -> println("Registration failed")
}
```

### Explore Blockchain
```kotlin
import com.underhillforge.pisecure.explorer.BlockchainExplorer

// Get latest blocks
val latestBlocks = BlockchainExplorer.getLatestBlocks(limit = 10)

// Search for transactions
val transactions = BlockchainExplorer.searchTransactions(
    query = "alice",  // Search by address, name, or hash
    limit = 20
)

// Get network statistics
val networkStats = BlockchainExplorer.getNetworkStats()
println("Network hashrate: ${networkStats.hashrate}")
```

---

## 🔧 Advanced Usage

### Custom Node Configuration
```kotlin
val config = PiSecureConfig.Builder()
    .nodeUrl("https://custom-node.example.com")
    .enableCaching(true)
    .cacheSize(50) // MB
    .timeout(30) // seconds
    .certificatePinning(true)
    .build()

PiSecureSDK.initialize(this, config)
```

### Transaction Signing (Offline)
```kotlin
// Sign transaction without broadcasting
val signedTransaction = wallet.signTransaction(
    recipient = "bob",
    amount = 5.0,
    memo = "Offline payment"
)

// Store for later broadcasting
val serialized = signedTransaction.serialize()

// Later, broadcast when online
PiSecureSDK.broadcastTransaction(serialized)
```

### Mining Integration
```kotlin
import com.underhillforge.pisecure.mining.MiningManager

// Check mining status
val miningStatus = MiningManager.getStatus()

// Start mining (if supported by device)
MiningManager.startMining(wallet)

// Monitor mining progress
MiningManager.addProgressListener { progress ->
    println("Mining progress: ${progress.blocksMined} blocks")
}
```

### Push Notifications
```kotlin
class TransactionReceiver : PiSecureBroadcastReceiver() {
    override fun onTransactionReceived(transaction: Transaction) {
        // Handle incoming transaction
        showNotification("Received ${transaction.amount} PSC")
    }

    override fun onTransactionSent(transaction: Transaction) {
        // Handle outgoing transaction
        updateTransactionHistory()
    }
}
```

---

## 📚 API Reference

### Core Classes

#### `PiSecureSDK`
Main SDK entry point and configuration.

#### `PiSecureWallet`
Wallet management, transactions, and balance operations.

#### `BlockchainExplorer`
Blockchain data access and search functionality.

#### `PiNSManager`
Pi Name System operations and name resolution.

#### `MiningManager`
Mining operations and statistics.

#### `TrustManager`
Token economics and developer trust funds.

### Key Methods

#### Wallet Operations
```kotlin
// Create wallet
PiSecureWallet.create(name: String, biometric: Boolean = false): PiSecureWallet

// Import wallet
PiSecureWallet.importWallet(seedPhrase: String, name: String): PiSecureWallet

// Get balance
wallet.getBalance(): Balance

// Send tokens
wallet.sendTokens(recipient: String, amount: Double, memo: String): TransactionResult
```

#### PiNS Operations
```kotlin
// Check name availability
PiNSManager.checkAvailability(name: String): NameAvailability

// Register name
PiNSManager.registerName(name: String, wallet: PiSecureWallet): NameRegistration

// Resolve name to address
PiNSManager.resolveName(name: String): String?
```

#### Blockchain Exploration
```kotlin
// Get blockchain info
BlockchainExplorer.getInfo(): BlockchainInfo

// Get specific block
BlockchainExplorer.getBlock(index: Int): Block

// Search transactions
BlockchainExplorer.searchTransactions(query: String): List<Transaction>
```

---

## 🔒 Security Features

### Device Security
- **Hardware-backed keystore** for private key storage
- **Biometric authentication** support (Fingerprint/Face ID)
- **Secure enclave** integration where available

### Network Security
- **TLS certificate pinning** to prevent MITM attacks
- **Request signing** for authenticated operations
- **Rate limiting** awareness and automatic backoff

### Data Privacy
- **No sensitive data** stored in app sandbox
- **Encrypted local storage** for cached data
- **Minimal data collection** - only what's necessary

---

## 🧪 Example Android App

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var wallet: PiSecureWallet
    private lateinit var balanceText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        balanceText = findViewById(R.id.balanceText)

        // Initialize wallet
        initializeWallet()
        updateBalance()
    }

    private fun initializeWallet() {
        // Try to load existing wallet
        wallet = PiSecureWallet.loadExisting() ?: run {
            // Create new wallet if none exists
            PiSecureWallet.create("Mobile Wallet", enableBiometricAuth = true)
        }
    }

    private fun updateBalance() {
        lifecycleScope.launch {
            try {
                val balance = wallet.getBalance()
                balanceText.text = "${balance.amount} PSC"
            } catch (e: Exception) {
                balanceText.text = "Error loading balance"
            }
        }
    }

    fun onSendButtonClick(view: View) {
        val intent = Intent(this, SendActivity::class.java)
        intent.putExtra("wallet_address", wallet.address)
        startActivity(intent)
    }
}
```

---

## 📋 Requirements

- **Android API 23+** (Android 6.0)
- **Kotlin 1.5+**
- **Android Gradle Plugin 7.0+**

### Permissions
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

---

## 🔄 SDK Updates

The SDK automatically checks for updates and can update itself:

```kotlin
// Check for SDK updates
PiSecureSDK.checkForUpdates { updateAvailable ->
    if (updateAvailable) {
        PiSecureSDK.updateSDK { success ->
            if (success) {
                // SDK updated, restart app recommended
                Toast.makeText(this, "SDK updated!", Toast.LENGTH_LONG).show()
            }
        }
    }
}
```

---

## 🐛 Troubleshooting

### Common Issues

**"Node connection failed"**
```kotlin
// Check node URL and network connectivity
PiSecureSDK.testConnection { connected ->
    if (!connected) {
        // Try different node or check internet connection
    }
}
```

**"Biometric authentication failed"**
```kotlin
// Check if device supports biometrics
if (BiometricManager.from(this).canAuthenticate() == BiometricManager.BIOMETRIC_SUCCESS) {
    // Device supports biometrics
} else {
    // Fall back to PIN/password authentication
}
```

**"Transaction failed"**
```kotlin
// Check wallet balance and network status
val balance = wallet.getBalance()
if (balance.amount < transactionAmount) {
    showError("Insufficient balance")
    return
}
```

---

## 📞 Support & Documentation

- **Full API Documentation**: https://pisecure.dev/android-sdk
- **Example Apps**: https://github.com/UnderhillForge/PiSecure/tree/main/clients/android/examples
- **Community Forum**: https://community.pisecure.dev
- **Issue Tracking**: https://github.com/UnderhillForge/PiSecure/issues

---

## 🎯 What's Next

**Future SDK versions will include:**
- **Lightning Network** integration for instant payments
- **Hardware wallet** support (Ledger, Trezor)
- **DeFi protocols** for lending and staking
- **NFT marketplace** functionality
- **Multi-signature** wallet support

**PiSecure Android SDK - Build the future of mobile cryptocurrency! 🚀**