# PiSecure Go Client

A production-ready Go SDK for interacting with the PiSecure blockchain network.

## Installation

```bash
go get github.com/UnderhillForge/PiSecure/clients/go
```

## Quick Start

```go
package main

import (
    "fmt"
    "log"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    // Initialize client
    client, err := pisecure.NewClient()
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    // Get blockchain info
    info, err := client.GetBlockchainInfo()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Blockchain has %d blocks\n", info.Blocks)

    // Get wallet balance
    balance, err := client.GetWalletBalance("your_wallet_address")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Balance: %.2f tokens\n", balance)

    // Create and submit transaction
    tx := client.CreateTransferTransaction(
        "from_wallet_id",
        "to_address",
        100.0,
        "Payment memo",
    )

    txHash, err := client.SubmitTransaction(tx)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Transaction submitted: %s\n", txHash)
}
```

## Features

- 🚀 **High Performance**: Goroutines and channels for concurrent operations
- 🛡️ **Type Safe**: Strong typing with interfaces and structs
- 📦 **Standard Library**: No external dependencies for core functionality
- 🔄 **Context Support**: Proper cancellation and timeouts
- ⚡ **Fast**: Optimized HTTP client with connection pooling
- 🏗️ **Production Ready**: Comprehensive error handling and logging

## API Reference

### Client

```go
type Client struct {
    // Implementation details
}

func NewClient() (*Client, error)
func NewClientWithOptions(opts *ClientOptions) (*Client, error)

func (c *Client) Close() error

// Blockchain operations
func (c *Client) GetBlockchainInfo(ctx context.Context) (*BlockchainInfo, error)
func (c *Client) GetBlock(ctx context.Context, index uint64) (*Block, error)
func (c *Client) GetBlocks(ctx context.Context, limit, offset uint32) ([]*Block, error)
func (c *Client) GetTransaction(ctx context.Context, txHash string) (*Transaction, error)

// Wallet operations
func (c *Client) GetWalletBalance(ctx context.Context, address string) (float64, error)
func (c *Client) GetWalletTransactions(ctx context.Context, address string, limit uint32) ([]*Transaction, error)
func (c *Client) CreateWallet(ctx context.Context, name, displayName *string) (*Wallet, error)
func (c *Client) ListWallets(ctx context.Context) ([]*Wallet, error)

// Transaction operations
func (c *Client) SubmitTransaction(ctx context.Context, tx *Transaction) (string, error)
func (c *Client) CreateTransferTransaction(fromWallet, toAddress string, amount float64, memo string) *Transaction

// Network operations
func (c *Client) GetNetworkStatus(ctx context.Context) (*NetworkStatus, error)
func (c *Client) GetNetworkPeers(ctx context.Context) ([]string, error)
func (c *Client) HealthCheck(ctx context.Context) (*HealthStatus, error)
```

### Data Structures

```go
type BlockchainInfo struct {
    Blocks             uint64 `json:"blocks"`
    PendingTransactions uint32 `json:"pending_transactions"`
    Difficulty         uint32 `json:"difficulty"`
    IsValid           bool   `json:"is_valid"`
    NetworkHealth     string `json:"network_health"`
    LatestBlock       *Block `json:"latest_block,omitempty"`
}

type Block struct {
    Index        uint64         `json:"index"`
    Timestamp    uint64         `json:"timestamp"`
    Transactions []*Transaction `json:"transactions"`
    PreviousHash string         `json:"previous_hash"`
    Hash         string         `json:"hash"`
    Nonce        uint64         `json:"nonce"`
}

type Transaction struct {
    Type      string      `json:"type"`
    Data      interface{} `json:"data"`
    Signature string      `json:"signature"`
    Timestamp uint64      `json:"timestamp"`
    Hash      *string     `json:"hash,omitempty"`
}

type Wallet struct {
    ID      string  `json:"id"`
    Name    string  `json:"name"`
    Address string  `json:"address"`
    Balance float64 `json:"balance"`
}
```

### Client Options

```go
type ClientOptions struct {
    BootstrapPeers []string      `json:"bootstrap_peers"`
    APIVersion     string        `json:"api_version"`
    Timeout        time.Duration `json:"timeout"`
    MaxRetries     int           `json:"max_retries"`
    TLSConfig      *tls.Config   `json:"tls_config"`
}
```

## Error Handling

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    client, err := pisecure.NewClient()
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    ctx := context.Background()
    balance, err := client.GetWalletBalance(ctx, "some_address")
    if err != nil {
        var apiErr *pisecure.APIError
        if errors.As(err, &apiErr) {
            fmt.Printf("API error %d: %s\n", apiErr.StatusCode, apiErr.Message)
            return
        }

        var connErr *pisecure.ConnectionError
        if errors.As(err, &connErr) {
            fmt.Println("No PiSecure nodes available")
            return
        }

        fmt.Printf("Other error: %v\n", err)
        return
    }

    fmt.Printf("Balance: %.2f tokens\n", balance)
}
```

## Advanced Usage

### Custom Configuration

```go
package main

import (
    "crypto/tls"
    "time"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    opts := &pisecure.ClientOptions{
        BootstrapPeers: []string{
            "https://my-node.com/peers.json",
            "http://trusted-peer.local:3142",
        },
        APIVersion: "v1",
        Timeout:    30 * time.Second,
        MaxRetries: 3,
        TLSConfig: &tls.Config{
            InsecureSkipVerify: false, // Production should use proper certs
        },
    }

    client, err := pisecure.NewClientWithOptions(opts)
    if err != nil {
        panic(err)
    }
    defer client.Close()

    // Use client...
}
```

### Concurrent Operations

```go
package main

import (
    "context"
    "fmt"
    "sync"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    client, err := pisecure.NewClient()
    if err != nil {
        panic(err)
    }
    defer client.Close()

    addresses := []string{"addr1", "addr2", "addr3"}
    results := make(chan Result, len(addresses))

    var wg sync.WaitGroup
    for _, addr := range addresses {
        wg.Add(1)
        go func(address string) {
            defer wg.Done()

            balance, err := client.GetWalletBalance(context.Background(), address)
            results <- Result{Address: address, Balance: balance, Error: err}
        }(addr)
    }

    wg.Wait()
    close(results)

    for result := range results {
        if result.Error != nil {
            fmt.Printf("Error getting balance for %s: %v\n", result.Address, result.Error)
        } else {
            fmt.Printf("Balance for %s: %.2f\n", result.Address, result.Balance)
        }
    }
}

type Result struct {
    Address string
    Balance float64
    Error   error
}
```

### Context and Cancellation

```go
package main

import (
    "context"
    "fmt"
    "time"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

func main() {
    client, err := pisecure.NewClient()
    if err != nil {
        panic(err)
    }
    defer client.Close()

    // Create context with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    // This will cancel if it takes longer than 10 seconds
    balance, err := client.GetWalletBalance(ctx, "address")
    if err != nil {
        if ctx.Err() == context.DeadlineExceeded {
            fmt.Println("Request timed out")
        } else {
            fmt.Printf("Error: %v\n", err)
        }
    } else {
        fmt.Printf("Balance: %.2f\n", balance)
    }
}
```

### Enterprise Integration

```go
package main

import (
    "context"
    "fmt"
    "log"
    "time"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

type PaymentProcessor struct {
    client *pisecure.Client
}

func NewPaymentProcessor() (*PaymentProcessor, error) {
    client, err := pisecure.NewClient()
    if err != nil {
        return nil, err
    }

    return &PaymentProcessor{client: client}, nil
}

func (p *PaymentProcessor) ProcessPayment(ctx context.Context, customerWallet, merchantWallet string, amount float64, orderID string) error {
    // Check customer balance
    balance, err := p.client.GetWalletBalance(ctx, customerWallet)
    if err != nil {
        return fmt.Errorf("failed to check balance: %w", err)
    }

    if balance < amount {
        return fmt.Errorf("insufficient balance: %.2f < %.2f", balance, amount)
    }

    // Create payment transaction
    tx := p.client.CreateTransferTransaction(
        customerWallet,
        merchantWallet,
        amount,
        fmt.Sprintf("Payment for order #%s", orderID),
    )

    // Submit transaction
    txHash, err := p.client.SubmitTransaction(ctx, tx)
    if err != nil {
        return fmt.Errorf("failed to submit transaction: %w", err)
    }

    log.Printf("Payment processed successfully: %s", txHash)
    return nil
}

func (p *PaymentProcessor) Close() error {
    return p.client.Close()
}
```

## Use Cases

### Microservices Architecture

```go
package main

import (
    "context"
    "net/http"
    "time"

    "github.com/gin-gonic/gin"
    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

type BlockchainService struct {
    client *pisecure.Client
}

func NewBlockchainService() (*BlockchainService, error) {
    client, err := pisecure.NewClient()
    if err != nil {
        return nil, err
    }

    return &BlockchainService{client: client}, nil
}

func (s *BlockchainService) GetBlockchainHandler(c *gin.Context) {
    ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
    defer cancel()

    info, err := s.client.GetBlockchainInfo(ctx)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, info)
}

func (s *BlockchainService) GetBalanceHandler(c *gin.Context) {
    address := c.Param("address")

    ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
    defer cancel()

    balance, err := s.client.GetWalletBalance(ctx, address)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, gin.H{"address": address, "balance": balance})
}
```

### IoT Device Integration

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

type SensorData struct {
    DeviceID    string  `json:"device_id"`
    Temperature float64 `json:"temperature"`
    Humidity    float64 `json:"humidity"`
    Timestamp   int64   `json:"timestamp"`
}

type IoTDevice struct {
    client   *pisecure.Client
    deviceID string
}

func NewIoTDevice(deviceID string) (*IoTDevice, error) {
    client, err := pisecure.NewClient()
    if err != nil {
        return nil, err
    }

    return &IoTDevice{
        client:   client,
        deviceID: deviceID,
    }, nil
}

func (d *IoTDevice) SubmitSensorReading(temperature, humidity float64) error {
    data := SensorData{
        DeviceID:    d.deviceID,
        Temperature: temperature,
        Humidity:    humidity,
        Timestamp:   time.Now().Unix(),
    }

    // Convert to JSON for transaction data
    jsonData, err := json.Marshal(data)
    if err != nil {
        return fmt.Errorf("failed to marshal sensor data: %w", err)
    }

    // Create transaction
    tx := &pisecure.Transaction{
        Type:      "sensor_reading",
        Data:      json.RawMessage(jsonData),
        Signature: "", // Would be signed in real implementation
        Timestamp: uint64(time.Now().Unix()),
    }

    ctx := context.Background()
    _, err = d.client.SubmitTransaction(ctx, tx)
    if err != nil {
        return fmt.Errorf("failed to submit sensor data: %w", err)
    }

    fmt.Printf("Sensor data submitted for device %s\n", d.deviceID)
    return nil
}

func (d *IoTDevice) Close() error {
    return d.client.Close()
}
```

### Blockchain Analytics

```go
package main

import (
    "context"
    "fmt"
    "log"
    "sort"
    "time"

    pisecure "github.com/UnderhillForge/PiSecure/clients/go"
)

type AnalyticsEngine struct {
    client *pisecure.Client
}

func NewAnalyticsEngine() (*AnalyticsEngine, error) {
    client, err := pisecure.NewClient()
    if err != nil {
        return nil, err
    }

    return &AnalyticsEngine{client: client}, nil
}

func (a *AnalyticsEngine) AnalyzeNetworkActivity(ctx context.Context, hours int) error {
    // Get recent blocks
    endTime := time.Now()
    startTime := endTime.Add(-time.Duration(hours) * time.Hour)

    // Calculate how many blocks to fetch (assuming ~10 min block time)
    blocksToFetch := uint32((hours * 60) / 10)

    blocks, err := a.client.GetBlocks(ctx, blocksToFetch, 0)
    if err != nil {
        return fmt.Errorf("failed to get blocks: %w", err)
    }

    // Analyze transaction patterns
    txCount := 0
    uniqueAddresses := make(map[string]bool)
    transactionTypes := make(map[string]int)

    for _, block := range blocks {
        if block.Timestamp < uint64(startTime.Unix()) {
            continue
        }

        for _, tx := range block.Transactions {
            txCount++

            // Track transaction types
            if txType, ok := tx.Data.(map[string]interface{})["type"].(string); ok {
                transactionTypes[txType]++
            }

            // Extract addresses from transaction data
            if txData, ok := tx.Data.(map[string]interface{}); ok {
                if recipient, ok := txData["recipient"].(string); ok {
                    uniqueAddresses[recipient] = true
                }
                if sender, ok := txData["sender"].(string); ok {
                    uniqueAddresses[sender] = true
                }
            }
        }
    }

    // Generate report
    fmt.Printf("=== Network Analytics Report ===\n")
    fmt.Printf("Period: Last %d hours\n", hours)
    fmt.Printf("Total Transactions: %d\n", txCount)
    fmt.Printf("Unique Addresses: %d\n", len(uniqueAddresses))
    fmt.Printf("Average TX/Block: %.2f\n", float64(txCount)/float64(len(blocks)))
    fmt.Printf("\nTransaction Types:\n")

    // Sort transaction types by frequency
    type kv struct {
        Key   string
        Value int
    }
    var sortedTypes []kv
    for k, v := range transactionTypes {
        sortedTypes = append(sortedTypes, kv{k, v})
    }
    sort.Slice(sortedTypes, func(i, j int) bool {
        return sortedTypes[i].Value > sortedTypes[j].Value
    })

    for _, kv := range sortedTypes {
        fmt.Printf("  %s: %d\n", kv.Key, kv.Value)
    }

    return nil
}

func (a *AnalyticsEngine) Close() error {
    return a.client.Close()
}
```

## Dependencies

```go
module github.com/UnderhillForge/PiSecure/clients/go

go 1.18

require (
    golang.org/x/net v0.0.0-20220607020251-c690dde0001d
    golang.org/x/oauth2 v0.0.0-20220608161450-d0670ef3b1eb
)
```

## Platform Support

- ✅ **Linux** (amd64, arm64, arm)
- ✅ **macOS** (amd64, arm64)
- ✅ **Windows** (amd64)
- ✅ **FreeBSD** (amd64)
- ✅ **Docker** (multi-platform)

## Building

```bash
git clone https://github.com/UnderhillForge/PiSecure.git
cd clients/go
go build ./...
```

## Testing

```bash
go test ./...
```

## Benchmarks

```bash
go test -bench=. ./...
```

## Contributing

See the main PiSecure repository for contribution guidelines.

## License

MIT License