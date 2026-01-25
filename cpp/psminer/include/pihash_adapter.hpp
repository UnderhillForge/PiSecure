#pragma once

#include <string>
#include <cstdint>

namespace psminer
{

    // Adapter class for pisecure::pihash::PiHash
    class PiHashAdapter
    {
    public:
        PiHashAdapter(uint32_t rounds = 8, uint32_t memory_mb = 256, bool npu_enabled = false);
        ~PiHashAdapter();

        // Compute PiHash for given data and nonce
        std::string compute(
            const uint8_t *data,
            size_t data_len,
            uint32_t nonce,
            void *hardware_fingerprint = nullptr);

        // Find nonce that meets difficulty
        bool find_nonce(
            const uint8_t *data,
            size_t data_len,
            uint32_t difficulty,
            uint32_t max_nonce,
            uint32_t &out_nonce,
            std::string &out_hash);

    private:
        struct Impl;
        Impl *impl_;
    };

} // namespace psminer
