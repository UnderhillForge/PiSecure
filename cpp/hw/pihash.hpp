#pragma once

#include <string>
#include <cstdint>
#include <vector>

// PiHash mining algorithm interface
// This wraps the actual implementation from ../hw/pihash.cpp

class PiHash
{
public:
    PiHash(uint32_t rounds = 8, uint32_t memory_mb = 256, bool npu_enabled = false);
    ~PiHash();

    // Compute PiHash for given data and nonce
    std::string compute(
        const uint8_t *data,
        size_t data_len,
        uint32_t nonce,
        void *hardware_fingerprint // nullptr = auto-detect
    );

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

// Helper function to check hash difficulty
bool hash_meets_difficulty(const std::string &hash_hex, uint32_t target_zero_bits);
