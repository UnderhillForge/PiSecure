# pisecured Memory Leak Analysis

## Summary
Found **1 critical memory leak** and **several potential issues** that could cause long-running memory problems in pisecured.

---

## CRITICAL ISSUE: WebSocket Client Memory Leak

**Location:** `cpp/pisecured/src/ws_client.cpp` lines 44, 65, 106

### The Problem
The `WSConnection` struct is allocated with `new` but has a detached thread that references it. If the connection is closed before the thread completes, memory is not freed.

```cpp
bool WSClient::connect()
{
    // ...
    auto conn = new WSConnection();  // ← ALLOCATED
    // ...
    // Thread detached - continues running even after disconnect()
    std::thread([conn]()
    { conn->client.run(); })
        .detach();  // ← DETACHED THREAD - may outlive cleanup
    // ...
}

void WSClient::disconnect()
{
    // ...
    delete conn;  // ← Only ONE delete, but thread may still reference it
    // ...
}
```

### Why It's Critical
- **Detached thread** can outlive the object deletion
- **Use-after-free** if thread tries to access `conn->client` after deletion
- **Memory leak** if disconnect never called or called while thread is active
- Compounds over time: each failed connection or reconnection leaks memory

### Symptom
After hours/days of operation:
- Memory usage gradually increases
- Eventual crash if connection attempts are frequent

---

## HIGH PRIORITY ISSUE: WebSocket Client Destruction Race Condition

**Location:** `cpp/pisecured/src/ws_client.cpp` lines 85-100

```cpp
void WSClient::disconnect()
{
    if (!connected_ || !ws_)
        return;

    auto conn = static_cast<WSConnection *>(ws_);
    try
    {
        conn->client.close(conn->hdl, websocketpp::close::status::normal, "Disconnect");
        conn->client.stop_perpetual();
        // ← No guarantee the background thread has exited
    }
    catch (...)
    {
    }

    delete conn;  // ← Deleted while thread may still running!
    ws_ = nullptr;
    connected_ = false;
}
```

### Problem
The background thread is started with `.detach()`, so:
1. Thread may still be running `conn->client.run()`
2. `stop_perpetual()` signals the thread to stop, but isn't synchronous
3. `delete conn` happens before thread actually exits
4. Thread tries to access deleted memory → **crash or undefined behavior**

---

## MODERATE ISSUE: Unterminated WebSocket Connections Accumulation

**Location:** `cpp/pisecured/src/ws_server.cpp` 

### Potential Problem
- If clients connect but don't properly close WebSocket connections
- Or if connection cleanup in `callback_pisecure` is incomplete
- Memory for `WsConnData` structures accumulates in `conns_` map

```cpp
std::unordered_map<uintptr_t, std::shared_ptr<WsConnData>> conns_;
```

Need to verify that all connection paths properly remove entries from this map.

---

## Recommendations

### 1. **IMMEDIATE FIX - Replace Detached Thread with Managed Thread**

```cpp
// ws_client.hpp
struct WSConnection
{
    ws_client client;
    websocketpp::connection_hdl hdl;
    std::string response;
    bool response_received = false;
    std::mutex response_mutex;
    std::condition_variable response_cv;
    std::thread run_thread;  // ← Add managed thread member
    std::atomic<bool> should_stop{false};  // ← Add stop flag
};
```

```cpp
bool WSClient::connect()
{
    if (connected_)
        return true;

    try
    {
        auto conn = new WSConnection();
        // ... setup code ...
        
        // Replace detached thread with managed thread
        conn->run_thread = std::thread([conn]() {
            while (!conn->should_stop.load()) {
                conn->client.run();
            }
        });
        
        ws_ = conn;
        connected_ = true;
        return true;
    }
    catch (const std::exception &e)
    {
        std::cerr << "WebSocket connection exception: " << e.what() << std::endl;
        if (ws_) delete static_cast<WSConnection *>(ws_);
        ws_ = nullptr;
        return false;
    }
}

void WSClient::disconnect()
{
    if (!connected_ || !ws_)
        return;

    auto conn = static_cast<WSConnection *>(ws_);
    try
    {
        conn->should_stop = true;  // ← Signal thread to stop
        conn->client.close(conn->hdl, websocketpp::close::status::normal, "Disconnect");
        conn->client.stop_perpetual();
        
        if (conn->run_thread.joinable()) {
            conn->run_thread.join();  // ← WAIT for thread to complete
        }
    }
    catch (...)
    {
    }

    delete conn;
    ws_ = nullptr;
    connected_ = false;
}
```

### 2. **Use RAII Pattern Instead of Manual Management**

```cpp
// Better approach: Use unique_ptr
WSClient::WSClient(const std::string &url)
    : url_(url), ws_(nullptr)
{
}

// Replace new/delete with unique_ptr
std::unique_ptr<WSConnection> ws_;

bool WSClient::connect()
{
    // ...
    ws_ = std::make_unique<WSConnection>();
    // Destructor will handle cleanup automatically
}
```

### 3. **Add Memory Monitoring**

```cpp
// Add to daemon.cpp
#include <fstream>

void log_memory_usage()
{
    std::ifstream status("/proc/self/status");
    std::string line;
    while (std::getline(status, line))
    {
        if (line.find("VmRSS") != std::string::npos ||
            line.find("VmSize") != std::string::npos)
        {
            std::cout << "[MEMORY] " << line << std::endl;
        }
    }
}
```

### 4. **Verify WebSocket Server Connection Cleanup**

Check `callback_pisecure` to ensure all paths properly clean up `WsConnData` from the `conns_` map.

---

## Testing the Fix

1. **Run extended stress test:**
```bash
# Start pisecured
./pisecured

# In another terminal, hammer with connections
while true; do
  curl http://localhost:3142/api/v1/chain || true
  sleep 0.1
done
```

2. **Monitor memory:**
```bash
# Watch memory growth
watch -n 1 'ps aux | grep pisecured'
```

3. **Use valgrind for leak detection** (on non-Pi):
```bash
valgrind --leak-check=full ./pisecured
```

---

## Summary of Changes Needed

| Issue | Severity | Type | Fix Time |
|-------|----------|------|----------|
| Detached thread leak (ws_client) | **CRITICAL** | Memory Leak | 30 min |
| Thread race condition (ws_client) | **CRITICAL** | Crash Risk | 30 min |
| Connection accumulation (ws_server) | **MODERATE** | Audit needed | 20 min |
| Memory monitoring | **LOW** | Diagnostic | 15 min |

**Total estimated fix time: 1.5-2 hours**

All issues are in the daemon, which runs in the background and can cause long-running degradation.
