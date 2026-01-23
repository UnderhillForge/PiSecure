/**
 * uint256.h - 256-bit opaque byte container for hashes
 * Inspired by Bitcoin Core: src/uint256.h
 */
#ifndef PISECURE_CONSENSUS_UINT256_H
#define PISECURE_CONSENSUS_UINT256_H

#include <cstdint>
#include <cstring>
#include <string>
#include <array>

namespace pisecure {
namespace consensus {

/**
 * 256-bit opaque fixed-size container for hashes
 * Stores as 32 bytes in network (big-endian) byte order
 * Comparisons are little-endian for consensus (like Bitcoin)
 */
class Blob256 {
public:
    static constexpr size_t SIZE = 32;
    
    /**
     * Create from 32-byte array
     */
    static Blob256 from_bytes(const uint8_t data[32]) {
        Blob256 b;
        std::memcpy(b.data_.data(), data, SIZE);
        return b;
    }
    
    /**
     * Create from hex string (must be exactly 64 hex chars)
     * Returns all-zeros on parse error
     */
    static Blob256 from_hex(const std::string& hex);
    
    /**
     * Output to 32-byte array
     */
    void to_bytes(uint8_t out[32]) const {
        std::memcpy(out, data_.data(), SIZE);
    }
    
    /**
     * Convert to hex string (lowercase, 64 chars)
     */
    std::string to_hex() const;
    
    /**
     * Raw byte access
     */
    const uint8_t* data() const { return data_.data(); }
    uint8_t* data() { return data_.data(); }
    
    /**
     * Comparison for sorting/maps
     * Returns: <0 if this < other, 0 if equal, >0 if this > other
     * Comparison is in little-endian (consensus order)
     */
    int compare(const Blob256& other) const;
    
    /**
     * Equality
     */
    bool operator==(const Blob256& other) const;
    bool operator!=(const Blob256& other) const { return !(*this == other); }
    
    /**
     * Ordering for consensus
     */
    bool operator<(const Blob256& other) const { return compare(other) < 0; }
    bool operator<=(const Blob256& other) const { return compare(other) <= 0; }
    bool operator>(const Blob256& other) const { return compare(other) > 0; }
    bool operator>=(const Blob256& other) const { return compare(other) >= 0; }
    
    /**
     * Check if all zeros
     */
    bool is_zero() const;

private:
    std::array<uint8_t, SIZE> data_ = {};
};

} // namespace consensus
} // namespace pisecure

#endif // PISECURE_CONSENSUS_UINT256_H
