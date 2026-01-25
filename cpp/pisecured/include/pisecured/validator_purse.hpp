#pragma once

#include <string>
#include <mutex>
#include <cstdint>
#include <optional>
#include <vector>

namespace pisecured
{
    /**
     * @brief Persistent validator rewards accumulator
     *
     * The ValidatorPurse stores validator rewards in a temporary holding account
     * that persists across reboots. Rewards accumulate until the user requests
     * withdrawal to their actual wallet.
     *
     * Features:
     * - JSON-based persistence for cross-platform compatibility
     * - Thread-safe accumulation and withdrawal
     * - Atomic file operations with backup/recovery
     * - Percentage-based rewards calculation
     * - Detailed transaction history
     */
    class ValidatorPurse
    {
    public:
        struct RewardEntry
        {
            uint64_t block_height;
            double amount;            // 314ST tokens
            double block_reward;      // Original block reward
            double percentage;        // Percentage of block reward
            uint64_t timestamp;       // Unix timestamp
            uint32_t validator_count; // Total validators for this block
            std::string block_hash;
        };

        struct PurseState
        {
            double total_balance;                    // Current purse balance
            double lifetime_earned;                  // Total ever earned
            double lifetime_withdrawn;               // Total ever withdrawn
            uint64_t blocks_validated;               // Total blocks validated
            uint64_t last_block_height;              // Last processed block
            uint64_t created_at;                     // Purse creation time
            uint64_t last_updated;                   // Last modification time
            std::string linked_wallet_address;       // Wallet for auto-accumulation
            bool auto_sweep_enabled;                 // Auto-sweep to linked wallet
            double auto_sweep_threshold;             // Threshold before auto-sweep
            std::vector<RewardEntry> recent_rewards; // Last 100 rewards
            std::string version;                     // Purse format version
        };

        /**
         * @brief Create or load validator purse
         * @param purse_path Path to purse JSON file (e.g., /var/lib/pisecured/validator_purse.json)
         * @param rewards_percentage Percentage of block reward for validators (default 0.01 = 1%)
         */
        explicit ValidatorPurse(const std::string &purse_path,
                                double rewards_percentage = 0.01);

        ~ValidatorPurse();

        /**
         * @brief Add validator reward for a confirmed block
         * @param block_height Block height
         * @param block_hash Block hash (for tracking)
         * @param block_reward Original mining reward (e.g., 50.0 314ST)
         * @param validator_count Number of validators who validated this block
         * @return Amount added to purse
         */
        double add_reward(uint64_t block_height,
                          const std::string &block_hash,
                          double block_reward,
                          uint32_t validator_count);

        /**
         * @brief Withdraw accumulated rewards to wallet
         * @param amount Amount to withdraw (0 = withdraw all)
         * @param wallet_address Target wallet address for tracking
         * @return Amount withdrawn (0 if insufficient balance)
         */
        double withdraw(double amount, const std::string &wallet_address);

        /**
         * @brief Get current purse balance
         */
        double get_balance() const;

        /**
         * @brief Get complete purse state
         */
        PurseState get_state() const;

        /**
         * @brief Get recent reward history
         * @param limit Maximum number of entries (default 100)
         */
        std::vector<RewardEntry> get_recent_rewards(size_t limit = 100) const;

        /**
         * @brief Get total rewards earned since creation
         */
        double get_lifetime_earned() const;

        /**
         * @brief Get total blocks validated
         */
        uint64_t get_blocks_validated() const;

        /**
         * @brief Force save current state to disk
         * @return true if save successful
         */
        bool save();

        /**
         * @brief Check if purse file exists and is valid
         */
        bool is_valid() const;

        /**
         * @brief Reset purse (dangerous - clears all data)
         */
        void reset();

        /**
         * @brief Link validator rewards to a wallet address
         * @param wallet_address Destination wallet for auto-accumulation
         * @return true if linked successfully
         */
        bool link_wallet(const std::string &wallet_address);

        /**
         * @brief Get linked wallet address
         */
        std::string get_linked_wallet() const;

        /**
         * @brief Enable/disable auto-sweep to linked wallet
         * @param enabled True to enable auto-sweep
         * @param threshold Amount threshold (0 = always auto-sweep)
         */
        void set_auto_sweep(bool enabled, double threshold = 0.0);

        /**
         * @brief Check if auto-sweep is enabled and should trigger
         */
        bool should_auto_sweep() const;

        /**
         * @brief Validate reward percentage against network cap
         * @return true if percentage is within network limits
         */
        static bool validate_percentage(double percentage);

        /**
         * @brief Get network maximum allowed percentage
         */
        static double get_network_max_percentage();

    private:
        std::string purse_path_;
        double rewards_percentage_;
        PurseState state_;
        mutable std::mutex mutex_;
        bool dirty_; // Track if state needs saving

        // File operations
        bool load_from_disk();
        bool save_to_disk();
        bool create_backup();
        bool restore_from_backup();

        // JSON serialization
        std::string serialize_state() const;
        bool deserialize_state(const std::string &json_data);

        // Utilities
        uint64_t get_current_timestamp() const;
        void add_recent_reward(const RewardEntry &entry);
        void mark_dirty();
    };
}
