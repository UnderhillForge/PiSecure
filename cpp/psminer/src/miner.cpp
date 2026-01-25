#include "miner.hpp"
#include "cli.hpp"
#include "hardware_verifier.hpp"
#include "pihash_adapter.hpp"
#include "pisecured/ws_client.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace psminer
{
    // Forward declaration
    bool hash_meets_difficulty(const std::string &hash_hex, uint32_t target_zero_bits);

    Miner::Miner(const Config &config)
        : config_(config),
          ws_client_(std::make_unique<pisecured::WSClient>("ws://127.0.0.1:3142"))
    {
    }

    Miner::~Miner()
    {
        stop();
    }

    bool Miner::start()
    {
        if (running_)
            return true;

        // Connect to pisecured
        if (!ws_client_->connect())
        {
            std::cerr << "Failed to connect to pisecured daemon\n";
            return false;
        }

        // Verify hardware
        if (!verify_hardware())
        {
            std::cerr << "Hardware verification failed\n";
            return false;
        }

        stats_.hardware_verified = true;
        running_ = true;

        // Start mining threads
        for (uint32_t i = 0; i < config_.threads; i++)
        {
            mining_threads_.emplace_back(&Miner::mining_loop, this, i);
        }

        // Start statistics thread
        stats_thread_ = std::thread(&Miner::stats_update_loop, this);

        // Start hardware monitoring thread
        hardware_thread_ = std::thread(&Miner::hardware_monitor_loop, this);

        return true;
    }

    void Miner::stop()
    {
        if (!running_)
            return;

        running_ = false;

        // Join all threads
        for (auto &thread : mining_threads_)
        {
            if (thread.joinable())
            {
                thread.join();
            }
        }

        if (stats_thread_.joinable())
        {
            stats_thread_.join();
        }

        if (hardware_thread_.joinable())
        {
            hardware_thread_.join();
        }

        mining_threads_.clear();
    }

    bool Miner::verify_hardware()
    {
        HardwareVerifier verifier;
        return verifier.verify();
    }

    std::string Miner::get_block_template()
    {
        // Get current blockchain height and construct template
        auto block_count = ws_client_->get_block_count();
        if (!block_count)
        {
            std::cerr << "Failed to get block count from daemon\n";
            return "";
        }

        auto now = std::chrono::system_clock::now();
        auto timestamp = std::chrono::system_clock::to_time_t(now);

        std::stringstream ss;
        ss << "block_" << (*block_count + 1) << "_"
           << config_.wallet_address << "_"
           << timestamp;

        return ss.str();
    }

    bool Miner::submit_block(uint32_t nonce, const std::string &hash)
    {
        // Submit block to pisecured via WebSocket
        nlohmann::json block_data;
        block_data["nonce"] = nonce;
        block_data["hash"] = hash;
        block_data["miner"] = config_.wallet_address;
        block_data["timestamp"] = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000;

        bool success = ws_client_->submit_block(nonce, hash, block_data);

        if (config_.verbose)
        {
            std::cout << "Block " << (success ? "accepted" : "rejected")
                      << ": nonce=" << nonce
                      << " hash=" << hash << "\n";
        }

        return success;
    }

    void Miner::mining_loop(int thread_id)
    {
        HardwareVerifier hw;
        auto fingerprint = hw.get_fingerprint();

        // Initialize PiHash
        PiHashAdapter pihash(config_.pihash_rounds, config_.pihash_memory_mb, config_.npu_enabled);

        uint32_t nonce_start = thread_id * (config_.max_nonce / config_.threads);
        uint32_t nonce_end = (thread_id + 1) * (config_.max_nonce / config_.threads);

        while (running_)
        {
            // Get block template
            std::string block_template = get_block_template();

            // Mine
            for (uint32_t nonce = nonce_start; nonce < nonce_end && running_; nonce++)
            {
                // Compute PiHash
                std::string hash = pihash.compute(
                    reinterpret_cast<const uint8_t *>(block_template.data()),
                    block_template.size(),
                    nonce,
                    nullptr // Hardware fingerprint handled internally
                );

                stats_.hashes_computed++;

                // Check if hash meets difficulty
                if (hash_meets_difficulty(hash, stats_.current_difficulty))
                {
                    stats_.blocks_found++;

                    // Submit block
                    submit_block(nonce, hash);

                    // Callback
                    if (block_callback_)
                    {
                        block_callback_(nonce, hash);
                    }

                    // Get new block template
                    break;
                }

                // Yield occasionally to prevent thread starvation
                if (nonce % 1000 == 0)
                {
                    std::this_thread::yield();
                }
            }

            // Small pause between block attempts
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    void Miner::stats_update_loop()
    {
        auto last_time = std::chrono::steady_clock::now();
        uint64_t last_hashes = 0;
        uint64_t start_time = std::time(nullptr);

        while (running_)
        {
            std::this_thread::sleep_for(std::chrono::seconds(1));

            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_time).count();

            if (elapsed >= 1000)
            {
                uint64_t current_hashes = stats_.hashes_computed.load();
                uint64_t hashes_delta = current_hashes - last_hashes;

                // Calculate hashrate in MH/s
                double hashrate_hs = static_cast<double>(hashes_delta) / (elapsed / 1000.0);
                stats_.hashrate_mhs = hashrate_hs / 1000000.0;

                last_hashes = current_hashes;
                last_time = now;
            }

            // Update uptime
            stats_.uptime_seconds = std::time(nullptr) - start_time;
        }
    }

    void Miner::hardware_monitor_loop()
    {
        HardwareVerifier hw;

        while (running_)
        {
            stats_.cpu_temp_c = hw.get_cpu_temp_c();
            stats_.gpu_temp_c = hw.get_gpu_temp_c();
            stats_.cpu_freq_mhz = hw.get_cpu_freq_mhz();
            stats_.throttle_status = hw.get_throttle_status();

            std::this_thread::sleep_for(std::chrono::seconds(2));
        }
    }

    // Helper function to check if hash meets difficulty
    bool hash_meets_difficulty(const std::string &hash_hex, uint32_t target_zero_bits)
    {
        // Count leading zero bits
        uint32_t zero_bits = 0;

        for (char c : hash_hex)
        {
            uint8_t nibble;
            if (c >= '0' && c <= '9')
                nibble = c - '0';
            else if (c >= 'a' && c <= 'f')
                nibble = c - 'a' + 10;
            else if (c >= 'A' && c <= 'F')
                nibble = c - 'A' + 10;
            else
                break;

            if (nibble == 0)
            {
                zero_bits += 4;
            }
            else
            {
                // Count leading zeros in this nibble
                if (nibble < 8)
                    zero_bits++;
                if (nibble < 4)
                    zero_bits++;
                if (nibble < 2)
                    zero_bits++;
                break;
            }
        }

        return zero_bits >= target_zero_bits;
    }

} // namespace psminer
