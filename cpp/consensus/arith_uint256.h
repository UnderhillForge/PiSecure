/**
 * arith_uint256.h - 256-bit integer arithmetic for consensus math
 * Inspired by Bitcoin Core: src/arith_uint256.h
 * Stores as 8 x 32-bit little-endian limbs
 */
#ifndef PISECURE_CONSENSUS_ARITH_UINT256_H
#define PISECURE_CONSENSUS_ARITH_UINT256_H

#include <cstdint>
#include <cstring>
#include <string>

namespace pisecure {
namespace consensus {

/**
 * 256-bit unsigned integer for proof-of-work and difficulty math
 * Internal representation: 8 x 32-bit little-endian limbs
 * Supports: arithmetic, shifts, comparisons, leading-zero counting
 */
class Big256 {
public:
    static constexpr size_t WIDTH = 8; // 8 x 32-bit limbs
    static constexpr size_t BYTES = 32;
    
    /**
     * Construct as zero
     */
    Big256();
    
    /**
     * Construct from single uint64
     */
    explicit Big256(uint64_t val);
    
    /**
     * Create from bytes (little-endian)
     */
    static Big256 from_bytes(const uint8_t data[32]);
    
    /**
     * Create from compact difficulty encoding (Bitcoin-style)
     * Returns {value, negative, overflow}
     */
    static Big256 from_compact(uint32_t nbits, bool& neg, bool& overflow);
    
    /**
     * Output to bytes (little-endian)
     */
    void to_bytes(uint8_t out[32]) const;
    
    /**
     * Convert to compact representation
     */
    uint32_t get_compact(bool negative = false) const;
    
    /**
     * Arithmetic operations
     */
    Big256& operator+=(const Big256& b);
    Big256& operator-=(const Big256& b);
    Big256& operator*=(uint32_t b);
    Big256& operator/=(uint32_t b);
    
    /**
     * Bit shifts
     */
    Big256& operator>>=(int bits);
    Big256& operator<<=(int bits);
    
    /**
     * Comparisons
     */
    bool operator==(const Big256& b) const;
    bool operator!=(const Big256& b) const { return !(*this == b); }
    bool operator<(const Big256& b) const;
    bool operator<=(const Big256& b) const;
    bool operator>(const Big256& b) const;
    bool operator>=(const Big256& b) const;
    
    /**
     * Check if zero
     */
    bool is_zero() const;
    
    /**
     * Check if negative (used for some consensus rules)
     */
    bool is_negative() const;
    
    /**
     * Count leading zero bits (leading zeros from MSB)
     */
    unsigned leading_zero_bits() const;
    
    /**
     * Count total bits (position of highest 1 bit + 1)
     */
    unsigned bits() const;
    
    /**
     * Set to zero
     */
    void set_zero();
    
    /**
     * Raw limb access (for optimization)
     */
    uint32_t* data() { return limbs_; }
    const uint32_t* data() const { return limbs_; }

private:
    uint32_t limbs_[WIDTH];
};

/**
 * Constant-time comparison helpers
 */
bool ct_equal(const Big256& a, const Big256& b);
bool ct_less_or_equal(const Big256& a, const Big256& b);

} // namespace consensus
} // namespace pisecure

#endif // PISECURE_CONSENSUS_ARITH_UINT256_H
