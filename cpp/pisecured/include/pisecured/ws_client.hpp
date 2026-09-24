#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <optional>
#include <memory>
#include <mutex>
#include <atomic>
#include <functional>

using json = nlohmann::json;

namespace pisecured
{
    /**
     * WebSocket JSON-RPC 2.0 client for communicating with pisecured daemon
     * Used by psminer and pswallet to interact with blockchain
     */
    class WSClient
    {
    public:
        WSClient(const std::string &url = "ws://127.0.0.1:3144");
        ~WSClient();

        // Connection management
        bool connect();
        void disconnect();
        bool is_connected() const { return connected_; }

        // JSON-RPC 2.0 requests
        std::optional<json> call(const std::string &method, const json &params = json::array());

        // Specific blockchain queries
        std::optional<uint32_t> get_block_count();
        std::optional<json> get_block(const std::string &hash_or_height);
        std::optional<json> get_block_header(uint32_t height);
        std::optional<json> get_network_stats();
        std::optional<json> get_mempool(size_t limit = 100);

        // Transaction operations
        std::optional<std::string> submit_transaction(const json &tx_data);
        std::optional<json> get_transaction(const std::string &tx_hash);

        // Mining operations
        std::optional<json> get_block_template();
        bool submit_block(uint32_t nonce, const std::string &hash, const json &block_data);

        // Validator operations
        std::optional<json> get_bucket_status();
        std::optional<json> get_validator_stats();

        // Subscriptions (async notifications)
        void subscribe(const std::string &channel, std::function<void(const json &)> callback);
        void unsubscribe(const std::string &channel);

    private:
        struct WSConnectionImpl;
        std::string url_;
        std::unique_ptr<WSConnectionImpl> ws_; // WebSocket connection with managed thread
        std::atomic<bool> connected_{false};
        std::atomic<int> request_id_{0};
        mutable std::mutex mutex_;

        json create_request(const std::string &method, const json &params);
        std::optional<json> send_request(const json &request);
    };
}
