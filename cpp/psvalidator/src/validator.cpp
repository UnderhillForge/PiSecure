#include "validator.hpp"
#include "pisecured/ws_client.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <thread>
#include <chrono>
#include <iomanip>

using json = nlohmann::json;

namespace psvalidator
{
    Validator::Validator(const Config &config)
        : config_(config),
          ws_client_(std::make_unique<pisecured::WSClient>(config.daemon_url))
    {
    }

    Validator::~Validator()
    {
        stop();
    }

    bool Validator::start()
    {
        if (running_)
            return true;

        // Connect to pisecured daemon
        if (!connect_to_daemon())
        {
            std::cerr << "Failed to connect to pisecured daemon at " << config_.daemon_url << "\n";
            std::cerr << "Make sure pisecured is running before starting psvalidator\n";
            return false;
        }

        stats_.connected_to_daemon = true;
        running_ = true;

        if (config_.verbose)
        {
            std::cout << "✓ Connected to daemon\n";
            std::cout << "✓ Wallet: " << config_.wallet_address << "\n";
            std::cout << "✓ Network: " << (config_.testnet ? "testnet" : "mainnet") << "\n";
        }

        // Start validation thread
        validation_thread_ = std::thread(&Validator::validation_loop, this);

        // Start statistics thread
        stats_thread_ = std::thread(&Validator::stats_update_loop, this);

        // Start bucket monitoring thread
        bucket_thread_ = std::thread(&Validator::bucket_monitor_loop, this);

        return true;
    }

    void Validator::stop()
    {
        if (!running_)
            return;

        running_ = false;

        if (validation_thread_.joinable())
            validation_thread_.join();
        if (stats_thread_.joinable())
            stats_thread_.join();
        if (bucket_thread_.joinable())
            bucket_thread_.join();
    }

    bool Validator::connect_to_daemon()
    {
        return ws_client_->connect();
    }

    void Validator::validation_loop()
    {
        while (running_)
        {
            try
            {
                // Get current blockchain height
                auto block_count = ws_client_->get_block_count();
                if (!block_count)
                {
                    std::this_thread::sleep_for(std::chrono::milliseconds(config_.poll_interval_ms));
                    continue;
                }

                stats_.current_height = *block_count;

                // Check for new blocks to validate
                if (*block_count > last_processed_height_)
                {
                    for (uint32_t height = last_processed_height_ + 1; height <= *block_count; ++height)
                    {
                        // Get block data
                        auto block_result = ws_client_->get_block(std::to_string(height));
                        if (!block_result)
                        {
                            if (config_.verbose)
                                std::cerr << "Failed to fetch block at height " << height << "\n";
                            continue;
                        }

                        // Validate block
                        bool valid = validate_block(*block_result);

                        if (valid)
                        {
                            stats_.blocks_validated++;

                            // Callback for UI
                            if (block_callback_)
                            {
                                std::string hash = block_result->value("hash", "unknown");
                                block_callback_(height, hash, true);
                            }
                        }
                        else
                        {
                            stats_.invalid_blocks_detected++;

                            if (config_.verbose)
                                std::cerr << "Invalid block detected at height " << height << "\n";
                        }

                        last_processed_height_ = height;
                    }
                }

                // Get and validate pending transactions
                auto mempool = ws_client_->get_mempool(100);
                if (mempool && mempool->contains("transactions"))
                {
                    auto txs = (*mempool)["transactions"];
                    if (txs.is_array())
                    {
                        for (const auto &tx : txs)
                        {
                            if (validate_transaction(tx))
                            {
                                stats_.transactions_validated++;
                            }
                            else
                            {
                                stats_.invalid_transactions_detected++;
                            }
                        }
                    }
                }
            }
            catch (const std::exception &e)
            {
                if (config_.verbose)
                    std::cerr << "Validation error: " << e.what() << "\n";
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(config_.poll_interval_ms));
        }
    }

    void Validator::stats_update_loop()
    {
        auto start_time = std::chrono::steady_clock::now();

        while (running_)
        {
            std::this_thread::sleep_for(std::chrono::seconds(1));

            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - start_time);
            stats_.uptime_seconds = elapsed.count();

            // Get network stats
            try
            {
                auto net_stats = ws_client_->get_network_stats();
                if (net_stats && net_stats->contains("peer_count"))
                {
                    stats_.peer_count = (*net_stats)["peer_count"].get<uint32_t>();
                }
            }
            catch (...)
            {
                // Ignore errors in stats update
            }
        }
    }

    void Validator::bucket_monitor_loop()
    {
        while (running_)
        {
            try
            {
                // Check validator bucket for rewards
                auto bucket = ws_client_->get_bucket_status();
                if (bucket)
                {
                    double current_balance = bucket->value("current_balance", 0.0);
                    double lifetime_earned = bucket->value("lifetime_earned", 0.0);

                    // Check if we earned new rewards
                    if (current_balance > stats_.current_bucket_balance)
                    {
                        double new_rewards = current_balance - stats_.current_bucket_balance;
                        stats_.total_rewards_earned = lifetime_earned;

                        if (reward_callback_ && new_rewards > 0.0)
                        {
                            reward_callback_(new_rewards, stats_.current_height);
                        }
                    }

                    stats_.current_bucket_balance = current_balance;
                }
            }
            catch (const std::exception &e)
            {
                if (config_.verbose)
                    std::cerr << "Bucket monitoring error: " << e.what() << "\n";
            }

            // Check every 5 seconds
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }

    bool Validator::validate_block(const json &block_data)
    {
        try
        {
            // Basic validation checks
            if (!block_data.contains("hash") || !block_data.contains("difficulty"))
            {
                return false;
            }

            std::string hash = block_data["hash"];
            uint32_t difficulty = block_data["difficulty"];

            // Validate proof-of-work (zero bit counting)
            if (!validate_pow(hash, difficulty))
            {
                if (config_.verbose)
                    std::cerr << "Block failed PoW validation\n";
                return false;
            }

            // Additional validation would go here:
            // - Timestamp validation
            // - Previous hash linkage
            // - Transaction merkle root
            // - Signature verification

            return true;
        }
        catch (const std::exception &e)
        {
            if (config_.verbose)
                std::cerr << "Block validation exception: " << e.what() << "\n";
            return false;
        }
    }

    bool Validator::validate_transaction(const json &tx_data)
    {
        try
        {
            // Basic transaction validation
            if (!tx_data.contains("fee") || !tx_data.contains("size"))
            {
                return false;
            }

            // Additional validation would go here:
            // - Signature verification
            // - UTXO validation
            // - Double-spend check
            // - Fee validation

            return true;
        }
        catch (const std::exception &e)
        {
            if (config_.verbose)
                std::cerr << "Transaction validation exception: " << e.what() << "\n";
            return false;
        }
    }

    bool Validator::validate_pow(const std::string &hash, uint32_t difficulty)
    {
        uint32_t zero_bits = count_leading_zero_bits(hash);
        return zero_bits >= difficulty;
    }

    uint32_t Validator::count_leading_zero_bits(const std::string &hash_hex)
    {
        uint32_t count = 0;

        for (size_t i = 0; i < hash_hex.length(); i++)
        {
            char c = hash_hex[i];
            uint8_t nibble;

            if (c >= '0' && c <= '9')
                nibble = c - '0';
            else if (c >= 'a' && c <= 'f')
                nibble = c - 'a' + 10;
            else if (c >= 'A' && c <= 'F')
                nibble = c - 'A' + 10;
            else
                break;

            // Count zero bits in this nibble
            if (nibble == 0)
            {
                count += 4;
            }
            else
            {
                // Count leading zeros in non-zero nibble
                if (nibble < 8)
                    count++;
                if (nibble < 4)
                    count++;
                if (nibble < 2)
                    count++;
                break;
            }
        }

        return count;
    }

} // namespace psvalidator
