# PiSecure C++ Client

A modern C++17 library for interacting with the PiSecure blockchain network.

## Installation

### Using CMake

```cmake
cmake_minimum_required(VERSION 3.16)
project(MyPiSecureApp)

find_package(PiSecure REQUIRED)

add_executable(my_app main.cpp)
target_link_libraries(my_app PiSecure::pisecure-client)
```

### Using vcpkg

```bash
vcpkg install pisecure-client
```

### From Source

```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd clients/cpp
mkdir build && cd build
cmake ..
make
sudo make install
```

## Dependencies

- C++17 compiler
- CMake 3.16+
- PiSecure C client library
- OpenSSL (for cryptography)
- Optional: Boost.Asio (for async operations)

## Quick Start

```cpp
#include <pisecure/client.hpp>
#include <iostream>

int main() {
    try {
        // Initialize client
        pisecure::Client client;

        // Get blockchain info
        auto info = client.getBlockchainInfo();
        std::cout << "Blockchain has " << info.blocks << " blocks" << std::endl;

        // Get wallet balance
        double balance = client.getWalletBalance("your_wallet_address");
        std::cout << "Balance: " << balance << " tokens" << std::endl;

        // Create and submit transaction
        auto tx = client.createTransferTransaction(
            "from_wallet_id",
            "to_address",
            100.0,
            "Payment memo"
        );

        std::string txHash = client.submitTransaction(tx);
        std::cout << "Transaction submitted: " << txHash << std::endl;

    } catch (const pisecure::ConnectionError& e) {
        std::cerr << "Connection failed: " << e.what() << std::endl;
    } catch (const pisecure::ApiError& e) {
        std::cerr << "API error: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    return 0;
}
```

## Features

- 🚀 **High Performance**: Zero-cost abstractions and modern C++ features
- 🛡️ **Type Safe**: Strong typing with RAII and smart pointers
- 📦 **Header-only Option**: Template-based implementation available
- 🔄 **Async Support**: C++20 coroutines and futures
- ⚡ **Fast**: Direct C bindings with minimal overhead
- 🏗️ **Modern C++**: Uses C++17 features extensively
- 💰 **314ST Token Economics**: Built-in token-powered access control
- 🏦 **Developer Trust Funds**: Subscription and funding models
- 🏛️ **Foundation Governance**: Community-controlled development
- 👥 **End User Abstraction**: Blockchain invisible to users

## API Reference

### Client Class

```cpp
namespace pisecure {

class Client {
public:
    // Constructors
    Client();
    explicit Client(const ClientOptions& options);

    // Blockchain operations
    BlockchainInfo getBlockchainInfo();
    Block getBlock(uint64_t index);
    std::vector<Block> getBlocks(uint32_t limit = 10, uint32_t offset = 0);
    Transaction getTransaction(const std::string& txHash);

    // Wallet operations
    double getWalletBalance(const std::string& address);
    std::vector<Transaction> getWalletTransactions(const std::string& address, uint32_t limit = 20);
    Wallet createWallet(const std::string& name = "", const std::string& displayName = "");
    std::vector<Wallet> listWallets();

    // Transaction operations
    std::string submitTransaction(const Transaction& tx);
    Transaction createTransferTransaction(const std::string& fromWallet,
                                        const std::string& toAddress,
                                        double amount,
                                        const std::string& memo = "");

    // Network operations
    NetworkStatus getNetworkStatus();
    std::vector<std::string> getNetworkPeers();
    HealthStatus healthCheck();

    // Configuration
    void setBootstrapPeers(const std::vector<std::string>& peers);
    void setTimeout(std::chrono::milliseconds timeout);
    void setApiVersion(const std::string& version);
};

} // namespace pisecure
```

### Data Structures

```cpp
namespace pisecure {

struct BlockchainInfo {
    uint64_t blocks;
    uint32_t pendingTransactions;
    uint32_t difficulty;
    bool isValid;
    std::string networkHealth;
    std::optional<Block> latestBlock;
};

struct Block {
    uint64_t index;
    uint64_t timestamp;
    std::vector<Transaction> transactions;
    std::string previousHash;
    std::string hash;
    uint64_t nonce;
};

struct Transaction {
    std::string type;
    nlohmann::json data;  // JSON data
    std::string signature;
    uint64_t timestamp;
    std::optional<std::string> hash;
};

struct Wallet {
    std::string id;
    std::string name;
    std::string address;
    double balance;
};

struct NetworkStatus {
    size_t connectedPeers;
    size_t knownPeers;
    std::string nodeId;
    uint16_t listeningPort;
};

struct ClientOptions {
    std::vector<std::string> bootstrapPeers;
    std::string apiVersion = "v1";
    std::chrono::milliseconds timeout = std::chrono::seconds(30);
    int maxRetries = 3;
    std::optional<std::string> apiKey;  // For authenticated requests
};

} // namespace pisecure
```

## Error Handling

```cpp
#include <pisecure/client.hpp>
#include <iostream>

int main() {
    pisecure::Client client;

    try {
        double balance = client.getWalletBalance("some_address");
        std::cout << "Balance: " << balance << std::endl;

    } catch (const pisecure::ConnectionError& e) {
        std::cout << "No PiSecure nodes available: " << e.what() << std::endl;

    } catch (const pisecure::ApiError& e) {
        std::cout << "API error " << e.statusCode() << ": " << e.what() << std::endl;

    } catch (const pisecure::ValidationError& e) {
        std::cout << "Invalid input: " << e.what() << std::endl;

    } catch (const std::exception& e) {
        std::cout << "Unexpected error: " << e.what() << std::endl;
    }

    return 0;
}
```

## Advanced Usage

### Custom Configuration

```cpp
#include <pisecure/client.hpp>

int main() {
    pisecure::ClientOptions options;
    options.bootstrapPeers = {
        "https://my-node.com/peers.json",
        "http://trusted-peer.local:3142"
    };
    options.timeout = std::chrono::seconds(10);
    options.maxRetries = 5;
    options.apiVersion = "v1";

    pisecure::Client client(options);

    // Use client...
    return 0;
}
```

### Asynchronous Operations (C++20)

```cpp
#include <pisecure/client.hpp>
#include <coroutine>
#include <iostream>

pisecure::Task<double> getBalanceAsync(pisecure::Client& client, const std::string& address) {
    try {
        double balance = co_await client.getWalletBalanceAsync(address);
        co_return balance;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        co_return 0.0;
    }
}

int main() {
    pisecure::Client client;

    // Start async operation
    auto future = getBalanceAsync(client, "wallet_address");

    // Do other work...

    // Get result
    double balance = future.get();
    std::cout << "Balance: " << balance << std::endl;

    return 0;
}
```

### Concurrent Operations

```cpp
#include <pisecure/client.hpp>
#include <vector>
#include <thread>
#include <future>
#include <iostream>

int main() {
    pisecure::Client client;
    std::vector<std::string> addresses = {"addr1", "addr2", "addr3"};

    // Concurrent balance queries
    std::vector<std::future<double>> futures;
    for (const auto& addr : addresses) {
        futures.push_back(std::async(std::launch::async, [&client, addr]() {
            try {
                return client.getWalletBalance(addr);
            } catch (...) {
                return 0.0;
            }
        }));
    }

    // Collect results
    for (size_t i = 0; i < futures.size(); ++i) {
        double balance = futures[i].get();
        std::cout << "Balance for " << addresses[i] << ": " << balance << std::endl;
    }

    return 0;
}
```

### RAII and Smart Pointers

```cpp
#include <pisecure/client.hpp>
#include <memory>

class PaymentProcessor {
private:
    std::unique_ptr<pisecure::Client> client_;

public:
    PaymentProcessor()
        : client_(std::make_unique<pisecure::Client>()) {}

    bool processPayment(const std::string& customerWallet,
                       const std::string& merchantWallet,
                       double amount,
                       const std::string& orderId) {

        try {
            // Check balance
            double balance = client_->getWalletBalance(customerWallet);
            if (balance < amount) {
                return false;
            }

            // Create transaction
            auto tx = client_->createTransferTransaction(
                customerWallet,
                merchantWallet,
                amount,
                "Payment for order #" + orderId
            );

            // Submit transaction
            std::string txHash = client_->submitTransaction(tx);

            std::cout << "Payment processed: " << txHash << std::endl;
            return true;

        } catch (const std::exception& e) {
            std::cerr << "Payment failed: " << e.what() << std::endl;
            return false;
        }
    }
};
```

### Template Metaprogramming (Advanced)

```cpp
#include <pisecure/client.hpp>
#include <type_traits>

// Compile-time API validation
template<typename T>
concept BlockchainClient = requires(T client) {
    { client.getBlockchainInfo() } -> std::same_as<pisecure::BlockchainInfo>;
    { client.getWalletBalance(std::string{}) } -> std::same_as<double>;
};

template<BlockchainClient ClientType>
class BlockchainService {
private:
    ClientType& client_;

public:
    explicit BlockchainService(ClientType& client) : client_(client) {}

    auto getInfo() {
        return client_.getBlockchainInfo();
    }

    double getBalance(const std::string& address) {
        return client_.getWalletBalance(address);
    }
};

int main() {
    pisecure::Client client;

    // Compile-time validation that Client satisfies BlockchainClient concept
    BlockchainService service(client);

    auto info = service.getInfo();
    std::cout << "Blocks: " << info.blocks << std::endl;

    return 0;
}
```

## Use Cases

### Enterprise E-commerce Platform

```cpp
#include <pisecure/client.hpp>
#include <string>
#include <vector>
#include <stdexcept>

class EcommercePlatform {
private:
    pisecure::Client client_;

public:
    struct Product {
        std::string id;
        std::string name;
        double price;
    };

    struct Order {
        std::string id;
        std::string customerWallet;
        std::vector<Product> items;
        double totalAmount;
    };

    bool processOrder(const Order& order) {
        try {
            // Verify customer has sufficient balance
            double balance = client_.getWalletBalance(order.customerWallet);
            if (balance < order.totalAmount) {
                throw std::runtime_error("Insufficient balance");
            }

            // Create transaction for the order
            std::string memo = "Order #" + order.id + " - " +
                             std::to_string(order.items.size()) + " items";

            auto tx = client_.createTransferTransaction(
                order.customerWallet,
                merchantWallet_,  // Platform's wallet
                order.totalAmount,
                memo
            );

            // Submit transaction
            std::string txHash = client_.submitTransaction(tx);

            // Log successful transaction
            logTransaction(order.id, txHash, order.totalAmount);

            return true;

        } catch (const pisecure::ConnectionError&) {
            // Retry with different node or queue for later
            queueOrderForRetry(order);
            return false;

        } catch (const std::exception& e) {
            // Log error and notify customer
            logError("Order processing failed: " + std::string(e.what()));
            return false;
        }
    }

private:
    std::string merchantWallet_;

    void logTransaction(const std::string& orderId, const std::string& txHash, double amount) {
        // Implementation...
    }

    void logError(const std::string& message) {
        // Implementation...
    }

    void queueOrderForRetry(const Order& order) {
        // Implementation...
    }
};
```

### High-Frequency Trading System

```cpp
#include <pisecure/client.hpp>
#include <atomic>
#include <thread>
#include <vector>
#include <chrono>

class TradingEngine {
private:
    pisecure::Client client_;
    std::atomic<bool> running_;
    std::vector<std::thread> workers_;

    struct TradeSignal {
        std::string symbol;
        std::string action;  // "buy" or "sell"
        double amount;
        double price;
    };

public:
    TradingEngine() : running_(true) {
        // Start worker threads
        unsigned int numThreads = std::thread::hardware_concurrency();
        for (unsigned int i = 0; i < numThreads; ++i) {
            workers_.emplace_back(&TradingEngine::tradingWorker, this, i);
        }
    }

    ~TradingEngine() {
        running_ = false;
        for (auto& worker : workers_) {
            worker.join();
        }
    }

    void submitTrade(const TradeSignal& signal) {
        // Add to trade queue for processing by workers
        tradeQueue_.push(signal);
    }

private:
    ThreadSafeQueue<TradeSignal> tradeQueue_;

    void tradingWorker(int workerId) {
        pisecure::Client workerClient(client_);  // Each worker has its own client

        while (running_) {
            TradeSignal signal;
            if (tradeQueue_.waitAndPop(signal, std::chrono::milliseconds(100))) {
                processTrade(workerClient, signal);
            }
        }
    }

    void processTrade(pisecure::Client& client, const TradeSignal& signal) {
        try {
            // Check market conditions
            auto networkStatus = client.getNetworkStatus();
            auto blockchainInfo = client.getBlockchainInfo();

            if (shouldExecuteTrade(signal, networkStatus, blockchainInfo)) {
                // Execute trade
                auto tx = client.createTransferTransaction(
                    tradingWallet_,
                    counterpartyWallet_,
                    signal.amount,
                    "Auto trade: " + signal.symbol + " " + signal.action
                );

                std::string txHash = client.submitTransaction(tx);

                logTrade(signal, txHash);
            }

        } catch (const std::exception& e) {
            logError("Trade execution failed: " + std::string(e.what()));
        }
    }

    bool shouldExecuteTrade(const TradeSignal& signal,
                          const pisecure::NetworkStatus& network,
                          const pisecure::BlockchainInfo& blockchain) {
        // Implement trading logic based on network conditions
        // Return true if trade should be executed
        return network.connectedPeers > 5 && blockchain.isValid;
    }

private:
    std::string tradingWallet_;
    std::string counterpartyWallet_;

    void logTrade(const TradeSignal& signal, const std::string& txHash) {
        // Implementation...
    }

    void logError(const std::string& message) {
        // Implementation...
    }
};
```

### IoT Device Management Platform

```cpp
#include <pisecure/client.hpp>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <chrono>

class IoTDeviceManager {
private:
    pisecure::Client client_;

public:
    struct DeviceData {
        std::string deviceId;
        std::string deviceType;
        nlohmann::json sensorData;
        std::chrono::system_clock::time_point timestamp;
    };

    void registerDevice(const std::string& deviceId, const std::string& deviceType) {
        // Create device wallet
        auto wallet = client_.createWallet(
            deviceId + "_wallet",
            deviceType + " Device Wallet"
        );

        // Store device registration on blockchain
        nlohmann::json registrationData = {
            {"device_id", deviceId},
            {"device_type", deviceType},
            {"wallet_address", wallet.address},
            {"registration_timestamp", std::chrono::system_clock::now().time_since_epoch().count()}
        };

        pisecure::Transaction tx{
            .type = "device_registration",
            .data = registrationData,
            .signature = "",  // Would be signed by device key
            .timestamp = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now())
        };

        client_.submitTransaction(tx);
    }

    void submitDeviceData(const DeviceData& data) {
        // Submit sensor data to blockchain
        pisecure::Transaction tx{
            .type = "sensor_data",
            .data = {
                {"device_id", data.deviceId},
                {"device_type", data.deviceType},
                {"sensor_readings", data.sensorData},
                {"timestamp", std::chrono::system_clock::to_time_t(data.timestamp)}
            },
            .signature = "",  // Would be signed by device
            .timestamp = std::chrono::system_clock::to_time_t(data.timestamp)
        };

        try {
            std::string txHash = client_.submitTransaction(tx);
            std::cout << "Device data submitted: " << txHash << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "Failed to submit device data: " << e.what() << std::endl;
            // Queue for retry
            queueForRetry(data);
        }
    }

    std::vector<DeviceData> getDeviceHistory(const std::string& deviceId, int hours) {
        // Get recent transactions for device
        auto transactions = client_.getWalletTransactions(deviceId + "_wallet", 100);

        std::vector<DeviceData> history;
        auto cutoff = std::chrono::system_clock::now() - std::chrono::hours(hours);

        for (const auto& tx : transactions) {
            if (tx.type == "sensor_data") {
                auto timestamp = std::chrono::system_clock::from_time_t(tx.timestamp);

                if (timestamp >= cutoff) {
                    DeviceData data{
                        .deviceId = tx.data["device_id"],
                        .deviceType = tx.data["device_type"],
                        .sensorData = tx.data["sensor_readings"],
                        .timestamp = timestamp
                    };
                    history.push_back(data);
                }
            }
        }

        return history;
    }

private:
    void queueForRetry(const DeviceData& data) {
        // Implementation for queuing failed submissions
    }
};
```

### Real-time Blockchain Analytics

```cpp
#include <pisecure/client.hpp>
#include <nlohmann/json.hpp>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <iostream>
#include <thread>
#include <chrono>

class BlockchainAnalytics {
private:
    pisecure::Client client_;
    std::unordered_map<std::string, AddressAnalytics> addressStats_;
    std::vector<std::string> topAddresses_;

public:
    struct AddressAnalytics {
        double totalReceived = 0.0;
        double totalSent = 0.0;
        size_t transactionCount = 0;
        std::chrono::system_clock::time_point lastActivity;
    };

    void analyzeRecentBlocks(size_t blockCount = 1000) {
        std::cout << "Analyzing last " << blockCount << " blocks..." << std::endl;

        auto blocks = client_.getBlocks(blockCount, 0);

        for (const auto& block : blocks) {
            for (const auto& tx : block.transactions) {
                analyzeTransaction(tx);
            }
        }

        updateTopAddresses();
        printAnalytics();
    }

    void monitorRealTime() {
        std::cout << "Starting real-time blockchain monitoring..." << std::endl;

        while (true) {
            try {
                // Get latest blockchain info
                auto info = client_.getBlockchainInfo();

                if (info.blocks > lastAnalyzedBlock_) {
                    // Analyze new blocks
                    size_t newBlocks = info.blocks - lastAnalyzedBlock_;
                    auto blocks = client_.getBlocks(newBlocks, lastAnalyzedBlock_);

                    for (const auto& block : blocks) {
                        for (const auto& tx : block.transactions) {
                            analyzeTransaction(tx);
                        }
                    }

                    lastAnalyzedBlock_ = info.blocks;
                    updateTopAddresses();

                    // Print periodic updates
                    static int counter = 0;
                    if (++counter % 10 == 0) {
                        printAnalytics();
                    }
                }

            } catch (const std::exception& e) {
                std::cerr << "Monitoring error: " << e.what() << std::endl;
            }

            std::this_thread::sleep_for(std::chrono::seconds(30));
        }
    }

private:
    size_t lastAnalyzedBlock_ = 0;

    void analyzeTransaction(const pisecure::Transaction& tx) {
        // Extract addresses from transaction data
        std::vector<std::string> addresses;

        if (tx.data.contains("recipient")) {
            addresses.push_back(tx.data["recipient"]);
        }
        if (tx.data.contains("sender")) {
            addresses.push_back(tx.data["sender"]);
        }
        if (tx.data.contains("from")) {
            addresses.push_back(tx.data["from"]);
        }
        if (tx.data.contains("to")) {
            addresses.push_back(tx.data["to"]);
        }

        // Update analytics for each address
        for (const auto& addr : addresses) {
            if (addressStats_.find(addr) == addressStats_.end()) {
                addressStats_[addr] = AddressAnalytics{};
            }

            auto& stats = addressStats_[addr];
            stats.transactionCount++;
            stats.lastActivity = std::chrono::system_clock::from_time_t(tx.timestamp);

            // Estimate amounts (simplified)
            if (tx.data.contains("amount")) {
                double amount = tx.data["amount"];
                if (tx.data.contains("recipient") && tx.data["recipient"] == addr) {
                    stats.totalReceived += amount;
                } else if (tx.data.contains("sender") && tx.data["sender"] == addr) {
                    stats.totalSent += amount;
                }
            }
        }
    }

    void updateTopAddresses() {
        // Sort addresses by transaction count
        std::vector<std::pair<std::string, size_t>> sortedAddresses;

        for (const auto& [addr, stats] : addressStats_) {
            sortedAddresses.emplace_back(addr, stats.transactionCount);
        }

        std::sort(sortedAddresses.begin(), sortedAddresses.end(),
                 [](const auto& a, const auto& b) { return a.second > b.second; });

        topAddresses_.clear();
        for (size_t i = 0; i < std::min(size_t(10), sortedAddresses.size()); ++i) {
            topAddresses_.push_back(sortedAddresses[i].first);
        }
    }

    void printAnalytics() {
        std::cout << "\n=== Blockchain Analytics ===\n";
        std::cout << "Total addresses tracked: " << addressStats_.size() << "\n";
        std::cout << "Top 10 most active addresses:\n";

        for (size_t i = 0; i < topAddresses_.size(); ++i) {
            const auto& addr = topAddresses_[i];
            const auto& stats = addressStats_[addr];

            std::cout << std::setw(2) << (i + 1) << ". "
                     << addr.substr(0, 16) << "... "
                     << "TX: " << stats.transactionCount << " "
                     << "Received: " << stats.totalReceived << " "
                     << "Sent: " << stats.totalSent << "\n";
        }

        std::cout << std::endl;
    }
};
```

## Building and Linking

### CMake Integration

```cmake
cmake_minimum_required(VERSION 3.16)
project(MyPiSecureApp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PiSecure REQUIRED)

add_executable(my_app main.cpp)
target_link_libraries(my_app PiSecure::pisecure-client-cpp)
target_compile_options(my_app PRIVATE -Wall -Wextra)
```

### Manual Compilation

```bash
g++ -std=c++17 -o my_app main.cpp -lpisecure-client-cpp -lpisecure-client -lcurl -ljansson -lssl -lcrypto
```

### Using with vcpkg

```cmake
find_package(pisecure-client CONFIG REQUIRED)
target_link_libraries(my_app pisecure-client::pisecure-client)
```

## Platform Support

- ✅ **Linux** (GCC 7+, Clang 5+)
- ✅ **macOS** (Xcode 10+, Clang)
- ✅ **Windows** (MSVC 2017+, MinGW)
- ✅ **Embedded** (ARM, RISC-V with appropriate toolchains)

## Testing

```bash
# Unit tests
ctest --output-on-failure

# Integration tests
./test_integration

# Performance benchmarks
./benchmark_cpp_client
```

## Benchmarks

```bash
# Single-threaded performance
./benchmark_single_thread

# Concurrent operations
./benchmark_concurrent 50

# Memory usage
./benchmark_memory_usage
```

## Contributing

See the main PiSecure repository for contribution guidelines.

## License

MIT License