# PiSecure C Client

A high-performance C library for interacting with the PiSecure blockchain network.

## Installation

### From Source

```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd clients/c
mkdir build && cd build
cmake ..
make
sudo make install
```

### Dependencies

- libcurl (for HTTP requests)
- jansson (for JSON parsing)
- OpenSSL (for cryptography)

```bash
# Ubuntu/Debian
sudo apt install libcurl4-openssl-dev libjansson-dev libssl-dev

# macOS
brew install curl jansson openssl

# CentOS/RHEL
sudo yum install libcurl-devel jansson-devel openssl-devel
```

## Quick Start

```c
#include <pisecure/client.h>
#include <stdio.h>

int main() {
    // Initialize client
    pisecure_client_t *client = pisecure_client_new();
    if (!client) {
        fprintf(stderr, "Failed to create client\n");
        return 1;
    }

    // Get blockchain info
    pisecure_blockchain_info_t info;
    if (pisecure_client_get_blockchain_info(client, &info) == 0) {
        printf("Blockchain has %llu blocks\n", info.blocks);
    }

    // Get wallet balance
    double balance;
    if (pisecure_client_get_wallet_balance(client, "your_wallet_address", &balance) == 0) {
        printf("Balance: %.2f tokens\n", balance);
    }

    // Create and submit transaction
    pisecure_transaction_t tx = {
        .type = "transfer",
        .data = "{\"recipient\":\"to_address\",\"amount\":100.0,\"memo\":\"Payment\"}",
        .signature = "signature_here",
        .timestamp = time(NULL)
    };

    char tx_hash[65];
    if (pisecure_client_submit_transaction(client, &tx, tx_hash, sizeof(tx_hash)) == 0) {
        printf("Transaction submitted: %s\n", tx_hash);
    }

    // Cleanup
    pisecure_client_free(client);
    return 0;
}
```

## Features

- 🚀 **High Performance**: Low-level C implementation with minimal overhead
- 🛡️ **Memory Safe**: Careful memory management with RAII-like patterns
- 📦 **Lightweight**: Small binary footprint, suitable for embedded systems
- 🔄 **Thread Safe**: Designed for concurrent applications
- ⚡ **Fast**: Direct HTTP calls without runtime overhead
- 🏗️ **C Compatible**: Can be used from C++ and other languages
- 💰 **314ST Token Economics**: Built-in token-powered access control
- 🏦 **Developer Trust Funds**: Subscription and funding models
- 🏛️ **Foundation Governance**: Community-controlled development
- 👥 **End User Abstraction**: Blockchain invisible to users

## API Reference

### Client Management

```c
// Create/destroy client
pisecure_client_t* pisecure_client_new(void);
void pisecure_client_free(pisecure_client_t *client);

// Configuration
int pisecure_client_set_bootstrap_peers(pisecure_client_t *client, const char **peers, size_t count);
int pisecure_client_set_timeout(pisecure_client_t *client, long timeout_ms);
int pisecure_client_set_api_version(pisecure_client_t *client, const char *version);
```

### Blockchain Operations

```c
// Get blockchain information
int pisecure_client_get_blockchain_info(pisecure_client_t *client, pisecure_blockchain_info_t *info);

// Get specific block
int pisecure_client_get_block(pisecure_client_t *client, uint64_t block_index, pisecure_block_t *block);

// Get multiple blocks
int pisecure_client_get_blocks(pisecure_client_t *client, uint32_t limit, uint32_t offset,
                              pisecure_block_t **blocks, size_t *count);

// Get transaction by hash
int pisecure_client_get_transaction(pisecure_client_t *client, const char *tx_hash,
                                   pisecure_transaction_t *transaction);
```

### Wallet Operations

```c
// Get wallet balance
int pisecure_client_get_wallet_balance(pisecure_client_t *client, const char *address, double *balance);

// Get wallet transactions
int pisecure_client_get_wallet_transactions(pisecure_client_t *client, const char *address,
                                          uint32_t limit, pisecure_transaction_t **transactions, size_t *count);

// Create new wallet
int pisecure_client_create_wallet(pisecure_client_t *client, const char *name, const char *display_name,
                                 pisecure_wallet_t *wallet);

// List wallets
int pisecure_client_list_wallets(pisecure_client_t *client, pisecure_wallet_t **wallets, size_t *count);
```

### Transaction Operations

```c
// Submit transaction
int pisecure_client_submit_transaction(pisecure_client_t *client, const pisecure_transaction_t *tx,
                                     char *tx_hash, size_t hash_size);

// Create transfer transaction helper
void pisecure_transaction_create_transfer(pisecure_transaction_t *tx,
                                        const char *from_wallet, const char *to_address,
                                        double amount, const char *memo);
```

### Network Operations

```c
// Get network status
int pisecure_client_get_network_status(pisecure_client_t *client, pisecure_network_status_t *status);

// Get network peers
int pisecure_client_get_network_peers(pisecure_client_t *client, char ***peers, size_t *count);

// Health check
int pisecure_client_health_check(pisecure_client_t *client, pisecure_health_status_t *status);
```

### Data Structures

```c
typedef struct {
    uint64_t blocks;
    uint32_t pending_transactions;
    uint32_t difficulty;
    bool is_valid;
    char network_health[64];
    pisecure_block_t *latest_block;
} pisecure_blockchain_info_t;

typedef struct {
    uint64_t index;
    uint64_t timestamp;
    pisecure_transaction_t *transactions;
    size_t transaction_count;
    char previous_hash[65];
    char hash[65];
    uint64_t nonce;
} pisecure_block_t;

typedef struct {
    char type[32];
    char *data;  // JSON string
    char signature[129];  // Hex-encoded signature
    uint64_t timestamp;
    char hash[65];
} pisecure_transaction_t;

typedef struct {
    char id[37];  // UUID
    char name[256];
    char address[45];  // Wallet address
    double balance;
} pisecure_wallet_t;
```

## Error Handling

```c
#include <pisecure/client.h>
#include <stdio.h>

int main() {
    pisecure_client_t *client = pisecure_client_new();

    double balance;
    int result = pisecure_client_get_wallet_balance(client, "address", &balance);

    if (result != 0) {
        const char *error_msg = pisecure_client_get_error(client);
        printf("Error: %s\n", error_msg);

        // Get error code for specific handling
        pisecure_error_code_t error_code = pisecure_client_get_error_code(client);
        switch (error_code) {
            case PISECURE_ERROR_CONNECTION:
                printf("Network connection failed\n");
                break;
            case PISECURE_ERROR_API:
                printf("API request failed\n");
                break;
            case PISECURE_ERROR_INVALID_RESPONSE:
                printf("Invalid response from server\n");
                break;
            default:
                printf("Unknown error\n");
        }
    } else {
        printf("Balance: %.2f\n", balance);
    }

    pisecure_client_free(client);
    return 0;
}
```

## Advanced Usage

### Custom Configuration

```c
#include <pisecure/client.h>

int main() {
    pisecure_client_t *client = pisecure_client_new();

    // Set custom bootstrap peers
    const char *peers[] = {
        "https://node1.pisecure.net/peers.json",
        "http://node2.local:3142"
    };
    pisecure_client_set_bootstrap_peers(client, peers, 2);

    // Set timeout (30 seconds)
    pisecure_client_set_timeout(client, 30000);

    // Set API version
    pisecure_client_set_api_version(client, "v1");

    // Use client...
    pisecure_client_free(client);
    return 0;
}
```

### Memory Management

```c
#include <pisecure/client.h>

// Arrays returned by the API must be freed
int main() {
    pisecure_client_t *client = pisecure_client_new();

    // Get blocks (returns dynamically allocated array)
    pisecure_block_t *blocks;
    size_t count;
    if (pisecure_client_get_blocks(client, 10, 0, &blocks, &count) == 0) {
        for (size_t i = 0; i < count; i++) {
            printf("Block %llu\n", blocks[i].index);
        }

        // Free the returned array
        pisecure_blocks_free(blocks, count);
    }

    // Get peers (returns array of strings)
    char **peers;
    if (pisecure_client_get_network_peers(client, &peers, &count) == 0) {
        for (size_t i = 0; i < count; i++) {
            printf("Peer: %s\n", peers[i]);
        }

        // Free the returned array
        pisecure_string_array_free(peers, count);
    }

    pisecure_client_free(client);
    return 0;
}
```

### Thread Safety

```c
#include <pisecure/client.h>
#include <pthread.h>
#include <stdio.h>

typedef struct {
    pisecure_client_t *client;
    const char *address;
    double *result;
} balance_query_t;

void* get_balance_thread(void *arg) {
    balance_query_t *query = (balance_query_t*)arg;

    // Each thread should use its own client instance
    pisecure_client_t *client = pisecure_client_new();
    pisecure_client_get_wallet_balance(client, query->address, query->result);
    pisecure_client_free(client);

    return NULL;
}

int main() {
    const char *addresses[] = {"addr1", "addr2", "addr3"};
    double balances[3];
    pthread_t threads[3];

    // Start concurrent balance queries
    for (int i = 0; i < 3; i++) {
        balance_query_t *query = malloc(sizeof(balance_query_t));
        query->address = addresses[i];
        query->result = &balances[i];

        pthread_create(&threads[i], NULL, get_balance_thread, query);
    }

    // Wait for all threads
    for (int i = 0; i < 3; i++) {
        pthread_join(threads[i], NULL);
        printf("Balance for %s: %.2f\n", addresses[i], balances[i]);
    }

    return 0;
}
```

### Embedded Systems Usage

```c
// For embedded systems with limited resources
#include <pisecure/client.h>

// Use minimal configuration for constrained environments
int main() {
    pisecure_client_t *client = pisecure_client_new();

    // Configure for embedded use
    pisecure_client_set_timeout(client, 10000);  // 10 second timeout
    const char *peers[] = {"http://local-pi:3142"};  // Local node only
    pisecure_client_set_bootstrap_peers(client, peers, 1);

    // Simple operations
    double balance;
    if (pisecure_client_get_wallet_balance(client, "device_wallet", &balance) == 0) {
        printf("Device balance: %.2f\n", balance);
    }

    pisecure_client_free(client);
    return 0;
}
```

## Use Cases

### IoT Device Firmware

```c
#include <pisecure/client.h>
#include <stdio.h>
#include <time.h>

typedef struct {
    char device_id[32];
    float temperature;
    float humidity;
    time_t timestamp;
} sensor_reading_t;

int submit_sensor_data(pisecure_client_t *client, const sensor_reading_t *reading) {
    char json_data[256];
    snprintf(json_data, sizeof(json_data),
             "{\"device_id\":\"%s\",\"temperature\":%.2f,\"humidity\":%.2f,\"timestamp\":%ld}",
             reading->device_id, reading->temperature, reading->humidity, reading->timestamp);

    pisecure_transaction_t tx = {
        .type = "sensor_reading",
        .data = json_data,
        .signature = "",  // Would be computed in real implementation
        .timestamp = reading->timestamp
    };

    char tx_hash[65];
    int result = pisecure_client_submit_transaction(client, &tx, tx_hash, sizeof(tx_hash));

    if (result == 0) {
        printf("Sensor data submitted: %s\n", tx_hash);
        return 0;
    } else {
        return -1;
    }
}

int main() {
    pisecure_client_t *client = pisecure_client_new();

    sensor_reading_t reading = {
        .device_id = "esp32_sensor_001",
        .temperature = 23.5f,
        .humidity = 65.2f,
        .timestamp = time(NULL)
    };

    if (submit_sensor_data(client, &reading) != 0) {
        printf("Failed to submit sensor data\n");
    }

    pisecure_client_free(client);
    return 0;
}
```

### High-Performance Trading System

```c
#include <pisecure/client.h>
#include <stdio.h>
#include <time.h>

#define MAX_CONCURRENT_REQUESTS 100

typedef struct {
    const char *address;
    double balance;
    int completed;
} balance_request_t;

void* balance_worker(void *arg) {
    balance_request_t *req = (balance_request_t*)arg;

    // Each worker thread uses its own client
    pisecure_client_t *client = pisecure_client_new();

    if (pisecure_client_get_wallet_balance(client, req->address, &req->balance) == 0) {
        req->completed = 1;
    } else {
        req->completed = -1;
    }

    pisecure_client_free(client);
    return NULL;
}

int main() {
    const char *addresses[] = {
        "trader_wallet_1", "trader_wallet_2", /* ... */ "trader_wallet_100"
    };

    balance_request_t requests[MAX_CONCURRENT_REQUESTS];
    pthread_t threads[MAX_CONCURRENT_REQUESTS];

    // Initialize requests
    for (int i = 0; i < MAX_CONCURRENT_REQUESTS; i++) {
        requests[i].address = addresses[i];
        requests[i].completed = 0;
        requests[i].balance = 0.0;
    }

    // Start concurrent requests
    clock_t start = clock();
    for (int i = 0; i < MAX_CONCURRENT_REQUESTS; i++) {
        pthread_create(&threads[i], NULL, balance_worker, &requests[i]);
    }

    // Wait for completion
    for (int i = 0; i < MAX_CONCURRENT_REQUESTS; i++) {
        pthread_join(threads[i], NULL);
    }
    clock_t end = clock();

    // Report results
    int successful = 0;
    double total_balance = 0.0;

    for (int i = 0; i < MAX_CONCURRENT_REQUESTS; i++) {
        if (requests[i].completed == 1) {
            successful++;
            total_balance += requests[i].balance;
        }
    }

    double time_taken = (double)(end - start) / CLOCKS_PER_SEC;

    printf("Completed %d/%d balance queries in %.2f seconds\n",
           successful, MAX_CONCURRENT_REQUESTS, time_taken);
    printf("Average time per query: %.4f seconds\n",
           time_taken / MAX_CONCURRENT_REQUESTS);
    printf("Total balance across all wallets: %.2f\n", total_balance);

    return 0;
}
```

### System Monitoring Agent

```c
#include <pisecure/client.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef struct {
    char hostname[256];
    double cpu_usage;
    uint64_t memory_used;
    uint64_t disk_used;
    time_t timestamp;
} system_metrics_t;

int collect_system_metrics(system_metrics_t *metrics) {
    // In real implementation, would collect actual system metrics
    // For demo, using mock data
    strcpy(metrics->hostname, "monitoring-server-01");
    metrics->cpu_usage = 45.2;
    metrics->memory_used = 2147483648;  // 2GB
    metrics->disk_used = 10737418240;   // 10GB
    metrics->timestamp = time(NULL);

    return 0;
}

int submit_system_metrics(pisecure_client_t *client) {
    system_metrics_t metrics;
    if (collect_system_metrics(&metrics) != 0) {
        return -1;
    }

    char json_data[512];
    snprintf(json_data, sizeof(json_data),
             "{\"hostname\":\"%s\",\"cpu_usage\":%.2f,\"memory_used\":%llu,\"disk_used\":%llu,\"timestamp\":%ld}",
             metrics.hostname, metrics.cpu_usage, metrics.memory_used,
             metrics.disk_used, metrics.timestamp);

    pisecure_transaction_t tx = {
        .type = "system_metrics",
        .data = json_data,
        .signature = "system_monitoring_key_signature",  // Would be real signature
        .timestamp = metrics.timestamp
    };

    char tx_hash[65];
    if (pisecure_client_submit_transaction(client, &tx, tx_hash, sizeof(tx_hash)) == 0) {
        printf("System metrics submitted: %s\n", tx_hash);
        return 0;
    } else {
        return -1;
    }
}

int main() {
    pisecure_client_t *client = pisecure_client_new();

    // Submit metrics every 5 minutes
    while (1) {
        if (submit_system_metrics(client) != 0) {
            fprintf(stderr, "Failed to submit system metrics\n");
        }

        sleep(300);  // 5 minutes
    }

    pisecure_client_free(client);
    return 0;
}
```

## Building and Linking

### CMake Configuration

```cmake
cmake_minimum_required(VERSION 3.10)
project(MyPiSecureApp)

find_package(PkgConfig REQUIRED)
pkg_check_modules(PiSecure REQUIRED pisecure-client)

add_executable(my_app main.c)
target_link_libraries(my_app ${PiSecure_LIBRARIES})
target_include_directories(my_app PUBLIC ${PiSecure_INCLUDE_DIRS})
```

### Manual Compilation

```bash
gcc -o my_app main.c -lpisecure-client -lcurl -ljansson -lssl -lcrypto
```

### Cross-Compilation for Embedded

```bash
# For ARM embedded systems
export CC=arm-linux-gnueabihf-gcc
export CXX=arm-linux-gnueabihf-g++
cmake .. -DCMAKE_TOOLCHAIN_FILE=../toolchains/armhf.cmake
make
```

## Platform Support

- ✅ **Linux** (x86_64, ARM64, ARM, MIPS)
- ✅ **macOS** (x86_64, ARM64)
- ✅ **Windows** (x86_64, i686, ARM64)
- ✅ **FreeBSD** (x86_64)
- ✅ **Embedded** (bare metal, RTOS)

## Testing

```bash
# Build tests
make test

# Run unit tests
./test_pisecure_client

# Run integration tests (requires running PiSecure node)
./test_integration
```

## Performance Benchmarks

```bash
# Basic performance test
./benchmark_client

# Concurrent request benchmark
./benchmark_concurrent 100

# Memory usage benchmark
./benchmark_memory
```

## Contributing

See the main PiSecure repository for contribution guidelines.

## License

MIT License