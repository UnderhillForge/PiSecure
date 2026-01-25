#pragma once

#include <filesystem>
#include <mutex>
#include <vector>
#include <optional>
#include <cstdint>
#include <string>
#include <map>
#include <array>
#include <unordered_map>

namespace pisecured
{
    // Hash function for std::array<uint8_t, 32> to use in unordered_map
    struct Hash256
    {
        size_t operator()(const std::array<uint8_t, 32> &arr) const
        {
            size_t hash = 0;
            for (size_t i = 0; i < 8; ++i)
            {
                hash ^= static_cast<size_t>(arr[i]) << (i * 8);
            }
            return hash;
        }
    };

    struct BlockPos
    {
        uint32_t file = 0;   // blkNNNN.dat index
        uint64_t offset = 0; // byte offset within file
        uint32_t size = 0;   // block byte length
    };

    // Block header for headers-first sync
    struct BlockHeader
    {
        uint32_t version;
        std::array<uint8_t, 32> prevBlockHash;
        std::array<uint8_t, 32> merkleRoot;
        uint64_t timestamp;
        uint32_t difficulty;
        uint64_t nonce;
        std::array<uint8_t, 32> hash;
        uint32_t height;
    };

    // Transaction for mempool
    struct Transaction
    {
        std::array<uint8_t, 32> hash;
        std::vector<uint8_t> data;
        uint64_t timestamp;
        uint64_t fee;
    };

    // Simple binary block store (length-prefixed frames) inspired by Bitcoin blk*.dat pattern
    class Storage
    {
    public:
        Storage() = default;
        explicit Storage(std::filesystem::path datadir);

        bool init(const std::filesystem::path &datadir, bool testnet, bool hybrid_storage);
        bool append_block(const std::vector<uint8_t> &block_bytes);
        std::optional<std::vector<uint8_t>> read_block(uint64_t index);
        std::filesystem::path blocks_path() const { return blocks_path_; }
        uint64_t next_index() const { return next_index_; }

        // Hash-based block lookups
        bool store_block_with_header(const std::array<uint8_t, 32> &hash, const BlockHeader &header, const std::vector<uint8_t> &block_data);
        std::optional<std::vector<uint8_t>> get_block_by_hash(const std::array<uint8_t, 32> &hash);
        std::optional<BlockHeader> get_header_by_hash(const std::array<uint8_t, 32> &hash);
        std::optional<BlockHeader> get_header_by_height(uint32_t height);
        std::array<uint8_t, 32> get_best_block_hash() const;
        uint32_t get_best_height() const;
        std::vector<std::array<uint8_t, 32>> get_block_locator_hashes();

        // Mempool operations
        bool add_transaction(const Transaction &tx);
        std::optional<Transaction> get_transaction(const std::array<uint8_t, 32> &hash);
        bool has_transaction(const std::array<uint8_t, 32> &hash);
        std::vector<Transaction> get_mempool_transactions(size_t max_count = 1000);
        void remove_transaction(const std::array<uint8_t, 32> &hash);

        // Block validation
        bool validate_block_header(const BlockHeader &header, const BlockHeader *prev_header = nullptr);
        bool validate_block_pow(const std::array<uint8_t, 32> &hash, uint32_t difficulty);

    private:
        std::filesystem::path datadir_;
        std::filesystem::path blocks_path_;
        mutable std::mutex io_mutex_;
        mutable std::mutex mempool_mutex_;
        uint64_t next_index_ = 0;
        uint32_t current_file_ = 0;
        uint64_t current_file_size_ = 0;
        static constexpr uint64_t kMaxBlockFileSize = 128ULL * 1024ULL * 1024ULL; // 128 MiB per blk file
        std::vector<BlockPos> index_;                                             // in-memory block index (sequential blocks only)

        // Hash-based indexes
        std::unordered_map<std::array<uint8_t, 32>, uint64_t, Hash256> hash_to_index_;    // block hash -> index
        std::unordered_map<std::array<uint8_t, 32>, BlockHeader, Hash256> headers_cache_; // block hash -> header
        std::vector<std::array<uint8_t, 32>> height_to_hash_;                             // height -> best block hash
        std::array<uint8_t, 32> best_block_hash_{};                                       // tip of the chain
        uint32_t best_height_ = 0;

        // Mempool
        std::unordered_map<std::array<uint8_t, 32>, Transaction, Hash256> mempool_;

        bool rotate_if_needed(uint64_t upcoming_bytes);
        std::filesystem::path file_path(uint32_t file_index) const;
        bool scan_existing();
    };
}
