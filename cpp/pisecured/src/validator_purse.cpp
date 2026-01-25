#include "pisecured/validator_purse.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <algorithm>
#include <stdexcept>
#include <sys/stat.h>
#include <cerrno>
#include <cstring>

// Simple JSON serialization (no external dependencies)
#include <nlohmann/json.hpp>
#include "pisecured/ws_server.hpp"

using json = nlohmann::json;

namespace pisecured
{
    ValidatorPurse::ValidatorPurse(const std::string &purse_path, double rewards_percentage)
        : purse_path_(purse_path),
          rewards_percentage_(rewards_percentage),
          dirty_(false)
    {
        if (rewards_percentage_ <= 0.0 || rewards_percentage_ >= 1.0)
        {
            throw std::invalid_argument("Rewards percentage must be between 0 and 1");
        }

        // Try to load existing purse, create new if doesn't exist
        if (!load_from_disk())
        {
            // Initialize new purse
            state_.total_balance = 0.0;
            state_.lifetime_earned = 0.0;
            state_.lifetime_withdrawn = 0.0;
            state_.blocks_validated = 0;
            state_.last_block_height = 0;
            state_.created_at = get_current_timestamp();
            state_.last_updated = state_.created_at;
            state_.version = "1.0";

            // Save initial state
            save_to_disk();
        }
    }

    ValidatorPurse::~ValidatorPurse()
    {
        // Auto-save on destruction if dirty
        if (dirty_)
        {
            save_to_disk();
        }
    }

    double ValidatorPurse::add_reward(uint64_t block_height,
                                      const std::string &block_hash,
                                      double block_reward,
                                      uint32_t validator_count)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Prevent duplicate rewards for same block
        if (block_height <= state_.last_block_height)
        {
            return 0.0;
        }

        // Calculate validator share
        double total_validator_pool = block_reward * rewards_percentage_;
        double reward_amount = (validator_count > 0)
                                   ? (total_validator_pool / validator_count)
                                   : 0.0;

        if (reward_amount <= 0.0)
        {
            return 0.0;
        }

        // Update state
        state_.total_balance += reward_amount;
        state_.lifetime_earned += reward_amount;
        state_.blocks_validated++;
        state_.last_block_height = block_height;
        state_.last_updated = get_current_timestamp();

        // Add to recent rewards history
        RewardEntry entry;
        entry.block_height = block_height;
        entry.amount = reward_amount;
        entry.block_reward = block_reward;
        entry.percentage = rewards_percentage_;
        entry.timestamp = state_.last_updated;
        entry.validator_count = validator_count;
        entry.block_hash = block_hash;

        add_recent_reward(entry);
        mark_dirty();

        // Notify WebSocket subscribers about purse update
        if (WebSocketServer::instance())
        {
            json bucket_obj = {
                {"balance", state_.total_balance},
                {"lifetime_earned", state_.lifetime_earned},
                {"blocks_validated", state_.blocks_validated},
                {"last_block_height", state_.last_block_height},
                {"last_updated", state_.last_updated},
                {"wallet", state_.linked_wallet_address}};
            WebSocketServer::instance()->broadcast_bucket_update(bucket_obj);
        }

        return reward_amount;
    }

    double ValidatorPurse::withdraw(double amount, const std::string &wallet_address)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Withdraw all if amount is 0
        double withdraw_amount = (amount <= 0.0) ? state_.total_balance : amount;

        // Check sufficient balance
        if (withdraw_amount > state_.total_balance)
        {
            return 0.0;
        }

        // Update state
        state_.total_balance -= withdraw_amount;
        state_.lifetime_withdrawn += withdraw_amount;
        state_.last_updated = get_current_timestamp();

        mark_dirty();
        save_to_disk(); // Immediate save for withdrawals

        // Notify WebSocket subscribers about purse withdrawal
        if (WebSocketServer::instance())
        {
            json bucket_obj = {
                {"balance", state_.total_balance},
                {"lifetime_withdrawn", state_.lifetime_withdrawn},
                {"last_updated", state_.last_updated},
                {"wallet", state_.linked_wallet_address}};
            WebSocketServer::instance()->broadcast_bucket_update(bucket_obj);
        }

        return withdraw_amount;
    }

    double ValidatorPurse::get_balance() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_.total_balance;
    }

    ValidatorPurse::PurseState ValidatorPurse::get_state() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_;
    }

    std::vector<ValidatorPurse::RewardEntry> ValidatorPurse::get_recent_rewards(size_t limit) const
    {
        std::lock_guard<std::mutex> lock(mutex_);

        size_t count = std::min(limit, state_.recent_rewards.size());
        return std::vector<RewardEntry>(
            state_.recent_rewards.begin(),
            state_.recent_rewards.begin() + count);
    }

    double ValidatorPurse::get_lifetime_earned() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_.lifetime_earned;
    }

    uint64_t ValidatorPurse::get_blocks_validated() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_.blocks_validated;
    }

    bool ValidatorPurse::save()
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return save_to_disk();
    }

    bool ValidatorPurse::is_valid() const
    {
        struct stat buffer;
        return (stat(purse_path_.c_str(), &buffer) == 0);
    }

    void ValidatorPurse::reset()
    {
        std::lock_guard<std::mutex> lock(mutex_);

        state_.total_balance = 0.0;
        state_.lifetime_earned = 0.0;
        state_.lifetime_withdrawn = 0.0;
        state_.blocks_validated = 0;
        state_.last_block_height = 0;
        state_.created_at = get_current_timestamp();
        state_.last_updated = state_.created_at;
        state_.recent_rewards.clear();

        save_to_disk();
    }

    // Private methods

    bool ValidatorPurse::load_from_disk()
    {
        std::ifstream file(purse_path_);
        if (!file.is_open())
        {
            return false;
        }

        try
        {
            std::stringstream buffer;
            buffer << file.rdbuf();
            file.close();

            return deserialize_state(buffer.str());
        }
        catch (const std::exception &e)
        {
            file.close();

            // Try to restore from backup
            if (restore_from_backup())
            {
                return true;
            }

            return false;
        }
    }

    bool ValidatorPurse::save_to_disk()
    {
        if (!dirty_)
        {
            return true;
        }

        // Create backup before saving
        create_backup();

        try
        {
            std::string json_data = serialize_state();

            // Atomic write: write to temp file, then rename
            std::string temp_path = purse_path_ + ".tmp";
            std::ofstream file(temp_path, std::ios::trunc);

            if (!file.is_open())
            {
                return false;
            }

            file << json_data;
            file.flush();
            file.close();

            // Atomic rename
            if (std::rename(temp_path.c_str(), purse_path_.c_str()) != 0)
            {
                return false;
            }

            dirty_ = false;
            return true;
        }
        catch (const std::exception &e)
        {
            return false;
        }
    }

    bool ValidatorPurse::create_backup()
    {
        if (!is_valid())
        {
            return false;
        }

        std::string backup_path = purse_path_ + ".bak";

        try
        {
            std::ifstream src(purse_path_, std::ios::binary);
            std::ofstream dst(backup_path, std::ios::binary | std::ios::trunc);

            if (!src.is_open() || !dst.is_open())
            {
                return false;
            }

            dst << src.rdbuf();
            src.close();
            dst.close();

            return true;
        }
        catch (const std::exception &e)
        {
            return false;
        }
    }

    bool ValidatorPurse::restore_from_backup()
    {
        std::string backup_path = purse_path_ + ".bak";

        std::ifstream file(backup_path);
        if (!file.is_open())
        {
            return false;
        }

        try
        {
            std::stringstream buffer;
            buffer << file.rdbuf();
            file.close();

            if (deserialize_state(buffer.str()))
            {
                // Restore successful, copy backup to main file
                std::ifstream src(backup_path, std::ios::binary);
                std::ofstream dst(purse_path_, std::ios::binary | std::ios::trunc);
                dst << src.rdbuf();
                src.close();
                dst.close();

                return true;
            }
        }
        catch (const std::exception &e)
        {
            file.close();
        }

        return false;
    }

    std::string ValidatorPurse::serialize_state() const
    {
        json j;

        j["version"] = state_.version;
        j["total_balance"] = state_.total_balance;
        j["lifetime_earned"] = state_.lifetime_earned;
        j["lifetime_withdrawn"] = state_.lifetime_withdrawn;
        j["blocks_validated"] = state_.blocks_validated;
        j["last_block_height"] = state_.last_block_height;
        j["created_at"] = state_.created_at;
        j["last_updated"] = state_.last_updated;
        j["rewards_percentage"] = rewards_percentage_;
        j["linked_wallet_address"] = state_.linked_wallet_address;
        j["auto_sweep_enabled"] = state_.auto_sweep_enabled;
        j["auto_sweep_threshold"] = state_.auto_sweep_threshold;

        // Serialize recent rewards
        json rewards_array = json::array();
        for (const auto &entry : state_.recent_rewards)
        {
            json reward;
            reward["block_height"] = entry.block_height;
            reward["amount"] = entry.amount;
            reward["block_reward"] = entry.block_reward;
            reward["percentage"] = entry.percentage;
            reward["timestamp"] = entry.timestamp;
            reward["validator_count"] = entry.validator_count;
            reward["block_hash"] = entry.block_hash;
            rewards_array.push_back(reward);
        }
        j["recent_rewards"] = rewards_array;

        return j.dump(2); // Pretty print with 2-space indent
    }

    bool ValidatorPurse::deserialize_state(const std::string &json_data)
    {
        try
        {
            json j = json::parse(json_data);

            state_.version = j.value("version", "1.0");
            state_.total_balance = j.value("total_balance", 0.0);
            state_.lifetime_earned = j.value("lifetime_earned", 0.0);
            state_.lifetime_withdrawn = j.value("lifetime_withdrawn", 0.0);
            state_.blocks_validated = j.value("blocks_validated", 0);
            state_.last_block_height = j.value("last_block_height", 0);
            state_.created_at = j.value("created_at", get_current_timestamp());
            state_.last_updated = j.value("last_updated", get_current_timestamp());

            // Load rewards percentage if available
            if (j.contains("rewards_percentage"))
            {
                rewards_percentage_ = j["rewards_percentage"];
            }

            // Load wallet linking (optional, for backward compatibility)
            state_.linked_wallet_address = j.value("linked_wallet_address", "");
            state_.auto_sweep_enabled = j.value("auto_sweep_enabled", false);
            state_.auto_sweep_threshold = j.value("auto_sweep_threshold", 0.0);

            // Deserialize recent rewards
            state_.recent_rewards.clear();
            if (j.contains("recent_rewards") && j["recent_rewards"].is_array())
            {
                for (const auto &reward_json : j["recent_rewards"])
                {
                    RewardEntry entry;
                    entry.block_height = reward_json.value("block_height", 0);
                    entry.amount = reward_json.value("amount", 0.0);
                    entry.block_reward = reward_json.value("block_reward", 0.0);
                    entry.percentage = reward_json.value("percentage", 0.0);
                    entry.timestamp = reward_json.value("timestamp", 0);
                    entry.validator_count = reward_json.value("validator_count", 0);
                    entry.block_hash = reward_json.value("block_hash", "");
                    state_.recent_rewards.push_back(entry);
                }
            }

            return true;
        }
        catch (const std::exception &e)
        {
            return false;
        }
    }

    uint64_t ValidatorPurse::get_current_timestamp() const
    {
        return static_cast<uint64_t>(std::time(nullptr));
    }

    void ValidatorPurse::add_recent_reward(const RewardEntry &entry)
    {
        // Add to front, keep last 100
        state_.recent_rewards.insert(state_.recent_rewards.begin(), entry);

        if (state_.recent_rewards.size() > 100)
        {
            state_.recent_rewards.resize(100);
        }
    }

    void ValidatorPurse::mark_dirty()
    {
        dirty_ = true;
    }

    // Static network validation methods
    bool ValidatorPurse::validate_percentage(double percentage)
    {
        double max_pct = get_network_max_percentage();
        return percentage > 0.0 && percentage <= max_pct;
    }

    double ValidatorPurse::get_network_max_percentage()
    {
        // 5% maximum - prevents greedy validator reward configurations
        // This should align with network consensus rules
        return 0.05;
    }

    // Wallet linking implementation
    bool ValidatorPurse::link_wallet(const std::string &wallet_address)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (wallet_address.empty())
        {
            return false;
        }

        state_.linked_wallet_address = wallet_address;
        state_.last_updated = get_current_timestamp();
        mark_dirty();
        save_to_disk();

        return true;
    }

    std::string ValidatorPurse::get_linked_wallet() const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return state_.linked_wallet_address;
    }

    void ValidatorPurse::set_auto_sweep(bool enabled, double threshold)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        state_.auto_sweep_enabled = enabled;
        state_.auto_sweep_threshold = threshold;
        state_.last_updated = get_current_timestamp();
        mark_dirty();
    }

    bool ValidatorPurse::should_auto_sweep() const
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!state_.auto_sweep_enabled || state_.linked_wallet_address.empty())
        {
            return false;
        }

        // If threshold is 0, always sweep
        if (state_.auto_sweep_threshold <= 0.0)
        {
            return state_.total_balance > 0.0;
        }

        // Sweep if balance exceeds threshold
        return state_.total_balance >= state_.auto_sweep_threshold;
    }
}
