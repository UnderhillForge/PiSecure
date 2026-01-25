#pragma once

#include <string>
#include <atomic>
#include <cstdint>
#include <memory>
#include <functional>
#include <thread>
#include <vector>

namespace pisecured
{
    class WSClient;
}

namespace psvalidator
{
    struct ValidatorStats
    {
        std::atomic<uint64_t> blocks_validated{0};
        std::atomic<uint64_t> transactions_validated{0};
        std::atomic<uint64_t> invalid_blocks_detected{0};
        std::atomic<uint64_t> invalid_transactions_detected{0};
        std::atomic<double> total_rewards_earned{0.0};
        std::atomic<double> current_bucket_balance{0.0};
        std::atomic<uint64_t> uptime_seconds{0};
        std::atomic<uint32_t> peer_count{0};
        std::atomic<uint32_t> current_height{0};
        std::atomic<bool> connected_to_daemon{false};
    };

    struct Config
    {
        std::string wallet_address;
        std::string daemon_url = "ws://127.0.0.1:3142";
        bool testnet = false;
        bool daemon = false;
        bool monitor_tui = true;
        bool verbose = false;
        uint32_t validation_threads = 4;
        uint32_t poll_interval_ms = 1000;
    };

    class Validator
    {
    public:
        explicit Validator(const Config &config);
        ~Validator();

        // Start validation
        bool start();

        // Stop validation
        void stop();

        // Check if running
        bool is_running() const { return running_; }

        // Get current statistics
        const ValidatorStats &stats() const { return stats_; }

        // Callbacks
        using BlockCallback = std::function<void(uint32_t height, const std::string &hash, bool valid)>;
        void set_block_callback(BlockCallback callback) { block_callback_ = callback; }

        using RewardCallback = std::function<void(double amount, uint32_t block_height)>;
        void set_reward_callback(RewardCallback callback) { reward_callback_ = callback; }

    private:
        void validation_loop();
        void stats_update_loop();
        void bucket_monitor_loop();

        bool connect_to_daemon();
        bool validate_block(const nlohmann::json &block_data);
        bool validate_transaction(const nlohmann::json &tx_data);
        bool validate_pow(const std::string &hash, uint32_t difficulty);
        uint32_t count_leading_zero_bits(const std::string &hash_hex);

        const Config &config_;
        std::atomic<bool> running_{false};
        ValidatorStats stats_;
        BlockCallback block_callback_;
        RewardCallback reward_callback_;
        std::unique_ptr<pisecured::WSClient> ws_client_;

        std::thread validation_thread_;
        std::thread stats_thread_;
        std::thread bucket_thread_;

        uint32_t last_processed_height_{0};
    };

} // namespace psvalidator
