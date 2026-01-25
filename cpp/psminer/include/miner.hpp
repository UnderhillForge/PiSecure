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

namespace psminer
{

    struct MiningStats
    {
        std::atomic<uint64_t> hashes_computed{0};
        std::atomic<uint64_t> blocks_found{0};
        std::atomic<uint32_t> current_difficulty{146};
        std::atomic<double> hashrate_mhs{0.0};
        std::atomic<uint64_t> uptime_seconds{0};
        std::atomic<bool> hardware_verified{false};

        // Hardware stats
        std::atomic<int> cpu_temp_c{0};
        std::atomic<int> gpu_temp_c{0};
        std::atomic<int> cpu_freq_mhz{0};
        std::atomic<int> throttle_status{0};
    };

    class Miner
    {
    public:
        explicit Miner(const struct Config &config);
        ~Miner();

        // Start mining
        bool start();

        // Stop mining
        void stop();

        // Check if mining is active
        bool is_running() const { return running_; }

        // Get current statistics
        const MiningStats &stats() const { return stats_; }

        // Callback for new blocks
        using BlockCallback = std::function<void(uint32_t nonce, const std::string &hash)>;
        void set_block_callback(BlockCallback callback) { block_callback_ = callback; }

    private:
        void mining_loop(int thread_id);
        void stats_update_loop();
        void hardware_monitor_loop();

        bool verify_hardware();
        std::string get_block_template();
        bool submit_block(uint32_t nonce, const std::string &hash);

        const struct Config &config_;
        MiningStats stats_;
        std::atomic<bool> running_{false};
        BlockCallback block_callback_;
        std::unique_ptr<pisecured::WSClient> ws_client_;

        std::vector<std::thread> mining_threads_;
        std::thread stats_thread_;
        std::thread hardware_thread_;
    };

} // namespace psminer
