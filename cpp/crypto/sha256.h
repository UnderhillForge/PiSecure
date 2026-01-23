/**
 * sha256.h - Incremental SHA-256 context (validation only, not mining)
 * Inspired by Bitcoin Core: src/crypto/sha256.h, CSHA256 class
 */
#ifndef PISECURE_CRYPTO_SHA256_H
#define PISECURE_CRYPTO_SHA256_H

#include <cstdint>
#include <cstring>

namespace pisecure {
namespace crypto {

/**
 * Incremental SHA-256 hasher (no dynamic allocation)
 * Used for validation tasks: transaction/block hashing, merkle trees
 * NOT used in mining (PiHash is mining-exclusive)
 */
class Sha256Ctx {
public:
    Sha256Ctx();
    
    /**
     * Add data to hash computation
     */
    Sha256Ctx& write(const uint8_t* data, size_t len);
    
    /**
     * Finalize and output 32-byte digest
     */
    void finalize(uint8_t out[32]);
    
    /**
     * Reset to initial state for reuse
     */
    Sha256Ctx& reset();
    
    /**
     * Get current byte count
     */
    uint64_t get_bytes() const { return bytes_; }

private:
    uint32_t state_[8];      // SHA-256 state vector
    uint64_t bytes_;         // Total bytes hashed
    uint8_t buffer_[64];     // Input buffer
    size_t buffer_len_;      // Current buffer usage
    
    /**
     * Process one 512-bit (64-byte) block
     */
    void Transform(const uint8_t* block);
};

/**
 * Single-shot SHA-256 hash
 */
void sha256(const uint8_t* in, size_t len, uint8_t out[32]);

/**
 * Single-shot double-SHA-256 (SHA256(SHA256(x)))
 */
void sha256d(const uint8_t* in, size_t len, uint8_t out[32]);

/**
 * Batch double-SHA-256 for multiple 64-byte inputs (validation throughput)
 * Not used in mining; for merkle tree / bulk validation
 */
void sha256d64(uint8_t* out, const uint8_t* in, size_t blocks);

} // namespace crypto
} // namespace pisecure

#endif // PISECURE_CRYPTO_SHA256_H
