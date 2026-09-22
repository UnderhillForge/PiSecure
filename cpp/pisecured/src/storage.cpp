#include "pisecured/storage.hpp"
#include <fstream>
#include <iostream>
#include <algorithm>
#include <regex>
#include <cstdio>

namespace pisecured
{
    Storage::Storage(std::filesystem::path datadir)
        : datadir_(std::move(datadir))
    {
    }

    bool Storage::init(const std::filesystem::path &datadir, bool testnet, bool /*hybrid_storage*/)
    {
        datadir_ = datadir;
        blocks_path_ = datadir_ / "blocks";
        try
        {
            std::filesystem::create_directories(blocks_path_);
            if (!scan_existing())
            {
                return false;
            }
            return true;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Storage init error: " << e.what() << "\n";
            return false;
        }
    }

    bool Storage::rotate_if_needed(uint64_t upcoming_bytes)
    {
        if (current_file_size_ + upcoming_bytes <= kMaxBlockFileSize)
        {
            return true;
        }

        ++current_file_;
        current_file_size_ = 0;
        return true;
    }

    bool Storage::append_block(const std::vector<uint8_t> &block_bytes)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        uint64_t frame_size = sizeof(uint32_t) + block_bytes.size();
        if (!rotate_if_needed(frame_size))
        {
            return false;
        }

        std::filesystem::path blk_file = file_path(current_file_);
        std::ofstream out(blk_file, std::ios::binary | std::ios::app);
        if (!out.is_open())
        {
            std::cerr << "Failed to open block file " << blk_file << "\n";
            return false;
        }

        uint32_t len = static_cast<uint32_t>(block_bytes.size());
        uint64_t offset = current_file_size_;
        out.write(reinterpret_cast<const char *>(&len), sizeof(len));
        out.write(reinterpret_cast<const char *>(block_bytes.data()), block_bytes.size());
        current_file_size_ += sizeof(len) + block_bytes.size();

        index_.push_back({current_file_, offset, len});
        ++next_index_;
        return true;
    }

    std::optional<std::vector<uint8_t>> Storage::read_block(uint64_t index)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        if (index >= index_.size())
        {
            return std::nullopt;
        }

        const BlockPos &pos = index_[static_cast<size_t>(index)];
        std::filesystem::path blk_file = file_path(pos.file);
        std::ifstream in(blk_file, std::ios::binary);
        if (!in.is_open())
        {
            return std::nullopt;
        }

        in.seekg(static_cast<std::streamoff>(pos.offset), std::ios::beg);
        uint32_t len = 0;
        in.read(reinterpret_cast<char *>(&len), sizeof(len));
        if (!in || len != pos.size)
        {
            return std::nullopt;
        }

        std::vector<uint8_t> buf(len);
        in.read(reinterpret_cast<char *>(buf.data()), len);
        if (!in)
        {
            return std::nullopt;
        }
        return buf;
    }

    std::filesystem::path Storage::file_path(uint32_t file_index) const
    {
        char name[32];
        std::snprintf(name, sizeof(name), "blk%05u.dat", file_index);
        return blocks_path_ / name;
    }

    bool Storage::scan_existing()
    {
        index_.clear();
        current_file_ = 0;
        current_file_size_ = 0;
        next_index_ = 0;

        // Find existing blk*.dat files and sort
        std::vector<std::filesystem::path> files;
        std::regex blk_regex(R"(blk(\d{5})\.dat)");
        for (auto &entry : std::filesystem::directory_iterator(blocks_path_))
        {
            if (!entry.is_regular_file())
                continue;
            auto fname = entry.path().filename().string();
            if (std::regex_match(fname, blk_regex))
            {
                files.push_back(entry.path());
            }
        }

        std::sort(files.begin(), files.end());

        for (const auto &file : files)
        {
            std::ifstream in(file, std::ios::binary);
            if (!in.is_open())
            {
                continue;
            }

            std::error_code size_ec;
            const uint64_t file_bytes = std::filesystem::file_size(file, size_ec);
            if (size_ec)
            {
                continue;
            }
            // Legacy files can start with a non-length prefix. Step until a
            // uint32 length fits and the payload begins with '{'.
            uint64_t offset = 0;
            while (offset + sizeof(uint32_t) <= file_bytes)
            {
                in.clear();
                in.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
                uint32_t len = 0;
                in.read(reinterpret_cast<char *>(&len), sizeof(len));
                if (!in)
                {
                    break;
                }
                const uint64_t frame_end = offset + sizeof(uint32_t) + static_cast<uint64_t>(len);
                char first = 0;
                if (len > 0 && frame_end <= file_bytes)
                {
                    in.read(&first, 1);
                }
                if (len > 0 && frame_end <= file_bytes && in && first == '{')
                {
                    BlockPos pos;
                    std::string fname = file.filename().string();
                    int fnum = std::stoi(fname.substr(3, 5));
                    pos.file = static_cast<uint32_t>(fnum);
                    pos.offset = offset;
                    pos.size = len;
                    index_.push_back(pos);
                    ++next_index_;
                    offset = frame_end;
                    continue;
                }
                ++offset;
            }

            // Track last file size
            std::error_code ec;
            auto fsize = std::filesystem::file_size(file, ec);
            if (!ec)
            {
                current_file_size_ = fsize;
                std::string fname = file.filename().string();
                int fnum = std::stoi(fname.substr(3, 5));
                current_file_ = static_cast<uint32_t>(fnum);
            }
        }

        // If no files, ensure blk00000.dat exists
        if (files.empty())
        {
            current_file_ = 0;
            current_file_size_ = 0;
            std::ofstream create(file_path(0), std::ios::binary | std::ios::app);
        }

        return true;
    }

    // Hash-based block storage and lookups
    bool Storage::store_block_with_header(const std::array<uint8_t, 32> &hash, const BlockHeader &header, const std::vector<uint8_t> &block_data)
    {
        if (!append_block(block_data))
        {
            return false;
        }

        std::lock_guard<std::mutex> lock(io_mutex_);
        uint64_t block_index = next_index_ - 1;
        hash_to_index_[hash] = block_index;
        headers_cache_[hash] = header;

        // Update best chain if this block extends it
        if (header.height >= height_to_hash_.size())
        {
            height_to_hash_.resize(header.height + 1);
        }
        height_to_hash_[header.height] = hash;

        if (header.height > best_height_)
        {
            best_height_ = header.height;
            best_block_hash_ = hash;
        }

        return true;
    }

    std::optional<std::vector<uint8_t>> Storage::get_block_by_hash(const std::array<uint8_t, 32> &hash)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        auto it = hash_to_index_.find(hash);
        if (it == hash_to_index_.end())
        {
            return std::nullopt;
        }

        // Temporarily unlock for read_block (which locks internally)
        uint64_t index = it->second;
        io_mutex_.unlock();
        auto result = read_block(index);
        io_mutex_.lock();
        return result;
    }

    std::optional<BlockHeader> Storage::get_header_by_hash(const std::array<uint8_t, 32> &hash)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        auto it = headers_cache_.find(hash);
        if (it == headers_cache_.end())
        {
            return std::nullopt;
        }
        return it->second;
    }

    std::optional<BlockHeader> Storage::get_header_by_height(uint32_t height)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        if (height >= height_to_hash_.size())
        {
            return std::nullopt;
        }
        const auto &hash = height_to_hash_[height];
        auto it = headers_cache_.find(hash);
        if (it == headers_cache_.end())
        {
            return std::nullopt;
        }
        return it->second;
    }

    std::array<uint8_t, 32> Storage::get_best_block_hash() const
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        return best_block_hash_;
    }

    uint32_t Storage::get_best_height() const
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        return best_height_;
    }

    std::vector<std::array<uint8_t, 32>> Storage::get_block_locator_hashes()
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        std::vector<std::array<uint8_t, 32>> locator;

        // Bitcoin-style exponential backoff: include recent blocks, then skip exponentially
        uint32_t step = 1;
        uint32_t height = best_height_;

        while (height > 0 && locator.size() < 10)
        {
            if (height < height_to_hash_.size())
            {
                locator.push_back(height_to_hash_[height]);
            }

            if (height < step)
                break;

            height -= step;

            // After 10 blocks, increase step exponentially
            if (locator.size() > 10)
            {
                step *= 2;
            }
        }

        // Always include genesis (height 0)
        if (!height_to_hash_.empty())
        {
            locator.push_back(height_to_hash_[0]);
        }

        return locator;
    }

    // Mempool operations
    bool Storage::add_transaction(const Transaction &tx)
    {
        std::lock_guard<std::mutex> lock(mempool_mutex_);
        mempool_[tx.hash] = tx;
        return true;
    }

    std::optional<Transaction> Storage::get_transaction(const std::array<uint8_t, 32> &hash)
    {
        std::lock_guard<std::mutex> lock(mempool_mutex_);
        auto it = mempool_.find(hash);
        if (it == mempool_.end())
        {
            return std::nullopt;
        }
        return it->second;
    }

    bool Storage::has_transaction(const std::array<uint8_t, 32> &hash)
    {
        std::lock_guard<std::mutex> lock(mempool_mutex_);
        return mempool_.count(hash) > 0;
    }

    std::vector<Transaction> Storage::get_mempool_transactions(size_t max_count)
    {
        std::lock_guard<std::mutex> lock(mempool_mutex_);
        std::vector<Transaction> txs;
        txs.reserve(std::min(mempool_.size(), max_count));

        for (const auto &[hash, tx] : mempool_)
        {
            txs.push_back(tx);
            if (txs.size() >= max_count)
                break;
        }

        return txs;
    }

    void Storage::remove_transaction(const std::array<uint8_t, 32> &hash)
    {
        std::lock_guard<std::mutex> lock(mempool_mutex_);
        mempool_.erase(hash);
    }

    // Block validation
    bool Storage::validate_block_header(const BlockHeader &header, const BlockHeader *prev_header)
    {
        // Basic sanity checks
        if (header.timestamp == 0)
        {
            return false;
        }

        // If we have previous header, verify chain linkage
        if (prev_header)
        {
            if (header.prevBlockHash != prev_header->hash)
            {
                return false;
            }

            if (header.height != prev_header->height + 1)
            {
                return false;
            }

            // Timestamp should be greater than previous
            if (header.timestamp <= prev_header->timestamp)
            {
                return false;
            }
        }

        return true;
    }

    bool Storage::validate_block_pow(const std::array<uint8_t, 32> &hash, uint32_t difficulty)
    {
        // Count leading zero bits
        int zero_bits = 0;
        for (size_t i = 0; i < 32; ++i)
        {
            if (hash[i] == 0)
            {
                zero_bits += 8;
            }
            else
            {
                // Count leading zeros in this byte
                uint8_t byte = hash[i];
                while ((byte & 0x80) == 0 && zero_bits < 256)
                {
                    zero_bits++;
                    byte <<= 1;
                }
                break;
            }
        }

        return zero_bits >= static_cast<int>(difficulty);
    }

    namespace
    {
        std::string utxo_key(const std::array<uint8_t, 32> &txid, uint32_t vout)
        {
            static const char *hexd = "0123456789abcdef";
            std::string key(64, '0');
            for (size_t i = 0; i < 32; ++i)
            {
                key[i * 2] = hexd[txid[i] >> 4];
                key[i * 2 + 1] = hexd[txid[i] & 0x0f];
            }
            key.push_back(':');
            key += std::to_string(vout);
            return key;
        }
    }

    bool Storage::has_tip() const
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        return !height_to_hash_.empty();
    }

    uint32_t Storage::tip_difficulty() const
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        if (height_to_hash_.empty())
        {
            return 0;
        }
        auto it = headers_cache_.find(best_block_hash_);
        if (it == headers_cache_.end())
        {
            return 0;
        }
        return it->second.difficulty;
    }

    bool Storage::index_existing_block(uint64_t index, const BlockHeader &header)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        if (index >= next_index_)
        {
            return false;
        }
        hash_to_index_[header.hash] = index;
        headers_cache_[header.hash] = header;
        if (header.height >= height_to_hash_.size())
        {
            height_to_hash_.resize(static_cast<size_t>(header.height) + 1);
        }
        height_to_hash_[header.height] = header.hash;
        if (header.height > best_height_ || best_block_hash_ == std::array<uint8_t, 32>{})
        {
            best_height_ = header.height;
            best_block_hash_ = header.hash;
        }
        return true;
    }

    bool Storage::utxo_available(const std::array<uint8_t, 32> &txid, uint32_t vout, uint64_t &value) const
    {
        std::lock_guard<std::mutex> lock(utxo_mutex_);
        auto it = utxo_.find(utxo_key(txid, vout));
        if (it == utxo_.end())
        {
            return false;
        }
        value = it->second.first;
        return true;
    }

    bool Storage::apply_utxos(const std::vector<UtxoSpend> &spends, const std::vector<UtxoCredit> &credits)
    {
        std::lock_guard<std::mutex> lock(utxo_mutex_);
        for (const auto &spend : spends)
        {
            if (utxo_.find(utxo_key(spend.txid, spend.vout)) == utxo_.end())
            {
                return false;
            }
        }
        for (const auto &credit : credits)
        {
            if (utxo_.find(utxo_key(credit.txid, credit.vout)) != utxo_.end())
            {
                return false;
            }
        }
        for (const auto &spend : spends)
        {
            utxo_.erase(utxo_key(spend.txid, spend.vout));
        }
        for (const auto &credit : credits)
        {
            utxo_[utxo_key(credit.txid, credit.vout)] = {credit.value, credit.address};
        }
        return true;
    }

    std::vector<Storage::UtxoEntry> Storage::list_utxos(const std::string &address) const
    {
        std::lock_guard<std::mutex> lock(utxo_mutex_);
        std::vector<UtxoEntry> rows;
        for (const auto &item : utxo_)
        {
            if (!address.empty() && item.second.second != address)
            {
                continue;
            }
            const auto colon = item.first.rfind(':');
            if (colon == std::string::npos)
            {
                continue;
            }
            UtxoEntry row;
            row.txid_hex = item.first.substr(0, colon);
            row.vout = static_cast<uint32_t>(std::stoul(item.first.substr(colon + 1)));
            row.units = item.second.first;
            row.address = item.second.second;
            rows.push_back(row);
        }
        return rows;
    }

    std::optional<uint64_t> Storage::block_index(const std::array<uint8_t, 32> &hash) const
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        auto it = hash_to_index_.find(hash);
        if (it == hash_to_index_.end())
        {
            return std::nullopt;
        }
        return it->second;
    }
}
