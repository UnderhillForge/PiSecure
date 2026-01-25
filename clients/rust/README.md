# PiSecure Rust Client

A high-performance Rust SDK for interacting with the PiSecure blockchain network.

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
pisecure-client = "0.1.0"
# or from git
pisecure-client = { git = "https://github.com/UnderhillForge/PiSecure", branch = "main" }
```

## Quick Start

```rust
use pisecure_client::PiSecureClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize client
    let client = PiSecureClient::new()?;

    // Get blockchain info
    let info = client.get_blockchain_info().await?;
    println!("Blockchain has {} blocks", info.blocks);

    // Get wallet balance
    let balance = client.get_wallet_balance("your_wallet_address").await?;
    println!("Balance: {} tokens", balance);

    // Create and submit transaction
    let tx = client.create_transfer_transaction(
        "from_wallet_id",
        "to_address",
        100.0,
        Some("Payment memo")
    );

    let tx_hash = client.submit_transaction(&tx).await?;
    println!("Transaction submitted: {}", tx_hash);

    Ok(())
}
```

## Features

- 🚀 **High Performance**: Zero-cost abstractions and async/await
- 🔒 **Memory Safe**: Rust's ownership system prevents memory bugs
- 📦 **No Runtime**: Can be compiled to WebAssembly
- 🔄 **Async Support**: Built on tokio for concurrent operations
- ⚡ **Fast**: Optimized for high-throughput applications
- 🛡️ **Type Safe**: Compile-time guarantees
- 💰 **314ST Token Economics**: Built-in token-powered access control
- 🏦 **Developer Trust Funds**: Subscription and funding models
- 🏛️ **Foundation Governance**: Community-controlled development
- 👥 **End User Abstraction**: Blockchain invisible to users

## API Reference

### PiSecureClient

```rust
pub struct PiSecureClient {
    // Implementation details
}

impl PiSecureClient {
    pub fn new() -> Result<Self, Error>
    pub fn with_bootstrap_peers(peers: Vec<String>) -> Result<Self, Error>

    // Blockchain operations
    pub async fn get_blockchain_info(&self) -> Result<BlockchainInfo, Error>
    pub async fn get_block(&self, index: u64) -> Result<Block, Error>
    pub async fn get_blocks(&self, limit: u32, offset: u32) -> Result<Vec<Block>, Error>
    pub async fn get_transaction(&self, tx_hash: &str) -> Result<Transaction, Error>

    // Wallet operations
    pub async fn get_wallet_balance(&self, address: &str) -> Result<f64, Error>
    pub async fn get_wallet_transactions(&self, address: &str, limit: u32) -> Result<Vec<Transaction>, Error>
    pub async fn create_wallet(&self, name: Option<&str>, display_name: Option<&str>) -> Result<Wallet, Error>
    pub async fn list_wallets(&self) -> Result<Vec<Wallet>, Error>

    // Transaction operations
    pub async fn submit_transaction(&self, tx: &Transaction) -> Result<String, Error>
    pub fn create_transfer_transaction(&self, from_wallet: &str, to_address: &str, amount: f64, memo: Option<&str>) -> Transaction

    // Network operations
    pub async fn get_network_status(&self) -> Result<NetworkStatus, Error>
    pub async fn get_network_peers(&self) -> Result<Vec<String>, Error>
    pub async fn health_check(&self) -> Result<HealthStatus, Error>
}
```

### Data Structures

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockchainInfo {
    pub blocks: u64,
    pub pending_transactions: u32,
    pub difficulty: u32,
    pub is_valid: bool,
    pub network_health: String,
    pub latest_block: Option<Block>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub index: u64,
    pub timestamp: u64,
    pub transactions: Vec<Transaction>,
    pub previous_hash: String,
    pub hash: String,
    pub nonce: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub transaction_type: String,
    pub data: serde_json::Value,
    pub signature: String,
    pub timestamp: u64,
    pub hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wallet {
    pub id: String,
    pub name: String,
    pub address: String,
    pub balance: f64,
}
```

## Error Handling

```rust
use pisecure_client::{PiSecureClient, Error};

#[tokio::main]
async fn main() {
    let client = PiSecureClient::new().unwrap();

    match client.get_wallet_balance("some_address").await {
        Ok(balance) => println!("Balance: {}", balance),
        Err(Error::ConnectionError) => println!("No PiSecure nodes available"),
        Err(Error::ApiError { status, message }) => println!("API error {}: {}", status, message),
        Err(e) => println!("Other error: {}", e),
    }
}
```

## Advanced Usage

### Custom Configuration

```rust
use pisecure_client::PiSecureClient;
use std::time::Duration;

let client = PiSecureClient::builder()
    .bootstrap_peers(vec![
        "https://my-node.com/peers.json".to_string(),
        "http://trusted-peer.local:3142".to_string(),
    ])
    .api_version("v1")
    .timeout(Duration::from_secs(30))
    .max_retries(3)
    .build()?;
```

### High-Performance Applications

```rust
use pisecure_client::PiSecureClient;
use futures::stream::{self, StreamExt};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = PiSecureClient::new()?;

    // Process multiple addresses concurrently
    let addresses = vec!["addr1", "addr2", "addr3"];

    let balances = stream::iter(addresses)
        .map(|addr| {
            let client = &client;
            async move {
                client.get_wallet_balance(addr).await
            }
        })
        .buffer_unordered(10)  // Concurrent requests
        .collect::<Vec<_>>()
        .await;

    for result in balances {
        match result {
            Ok(balance) => println!("Balance: {}", balance),
            Err(e) => println!("Error: {}", e),
        }
    }

    Ok(())
}
```

### Embedded Systems (no_std)

```rust
// For embedded systems without std
#![no_std]

extern crate alloc;

use pisecure_client::PiSecureClient;
use alloc::string::String;

// Limited API for constrained environments
let client = PiSecureClient::new()?;
let balance = client.get_balance_simple("address")?;
```

## Use Cases

### High-Frequency Trading Bot

```rust
use pisecure_client::PiSecureClient;
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn trading_bot() -> Result<(), Box<dyn std::error::Error>> {
    let client = PiSecureClient::new()?;

    loop {
        // Check market conditions
        let network_status = client.get_network_status().await?;
        let blockchain_info = client.get_blockchain_info().await?;

        // Execute trading logic
        if should_buy(&network_status, &blockchain_info) {
            let tx = client.create_transfer_transaction(
                "trading_wallet",
                "target_address",
                1000.0,
                Some("Automated trade")
            );
            client.submit_transaction(&tx).await?;
        }

        sleep(Duration::from_secs(1)).await;
    }
}
```

### IoT Device Firmware

```rust
// For ESP32, RP2040, or other microcontrollers
use pisecure_client::{PiSecureClient, Transaction};
use serde_json::json;

fn submit_sensor_reading(temperature: f32, humidity: f32) {
    let mut client = PiSecureClient::new()?;

    let tx_data = json!({
        "type": "sensor_reading",
        "device_id": "esp32_001",
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_secs()
    });

    let tx = Transaction {
        transaction_type: "sensor_data".to_string(),
        data: tx_data,
        signature: "".to_string(), // Would be signed in real implementation
        timestamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_secs(),
        hash: None,
    };

    client.submit_transaction(&tx)?;
}
```

### Blockchain Analytics Engine

```rust
use pisecure_client::PiSecureClient;
use std::collections::HashMap;

struct AnalyticsEngine {
    client: PiSecureClient,
    address_stats: HashMap<String, AddressStats>,
}

impl AnalyticsEngine {
    async fn analyze_blockchain(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let blocks = self.client.get_blocks(1000, 0).await?;

        for block in blocks {
            for tx in &block.transactions {
                self.process_transaction(tx).await?;
            }
        }

        Ok(())
    }

    async fn process_transaction(&mut self, tx: &Transaction) -> Result<(), Box<dyn std::error::Error>> {
        // Analyze transaction patterns, track addresses, etc.
        // Implementation details...
        Ok(())
    }
}
```

## Dependencies

```toml
[dependencies]
tokio = { version = "1.0", features = ["full"] }
reqwest = { version = "0.11", features = ["json"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
thiserror = "1.0"
url = "2.2"
```

## Platform Support

- ✅ **Linux** (x86_64, ARM64, ARM)
- ✅ **macOS** (x86_64, ARM64)
- ✅ **Windows** (x86_64)
- ✅ **WebAssembly** (for web applications)
- ✅ **Embedded** (no_std support planned)

## Building

```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd clients/rust
cargo build --release
```

## Testing

```bash
cargo test
```

## Benchmarks

```bash
cargo bench
```

## Contributing

See the main PiSecure repository for contribution guidelines.

## License

MIT License