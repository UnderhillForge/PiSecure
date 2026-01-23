/**
 * pow.h - Proof-of-Work consensus logic
 * Inspired by Bitcoin Core: src/pow.cpp
 * 
 * PiSecure uses leading-zero bit difficulty; adapters to/from compact target.
 * All target comparisons are constant-time to prevent timing attacks.
 */
#ifndef PISECURE_CONSENSUS_POW_H
#define PISECURE_CONSENSUS_POW_H

#include "uint256.h"
#include "arith_uint256.h"
#include <cstdint>
#include <optional>

namespace pisecure {
namespace consensus {

/**
 * PiSecure difficulty parameters
 */
struct DifficultyParams {
    // Current leading-zero bit requirement
    int leading_zero_bits = 146;
    
    // Retarget window (blocks)
    int retarget_blocks = 2016;
    
    // Retarget time target (seconds, e.g., 14 days in seconds for Bitcoin)
    int64_t retarget_time_target = 1209600;
    
    // Min/max difficulty adjustment per period
    int min_adjustment_factor = 1;  // Can't go below 1x
    int max_adjustment_factor = 4;  // Can't go above 4x
};

/**
 * Convert leading-zero bit count to Big256 target
 * Example: leading_zero_bits=146 → target has 146 leading zeros in binary
 */
Big256 leading_zeros_to_target(int leading_zero_bits);

/**
 * Convert Big256 target back to leading-zero bit count
 * Returns -1 if target is invalid (e.g., all zeros)
 */
int target_to_leading_zeros(const Big256& target);

/**
 * Check proof-of-work: constant-time comparison of hash vs target
 * Returns true if hash <= target (hash has enough leading zeros)
 * 
 * All branches and memory access are constant-time w.r.t. hash/target values
 */
bool check_pow(const Blob256& hash, const Big256& target);

/**
 * Check PoW using leading-zero bit requirement directly
 * Counts leading zero bits in hash, compares to difficulty
 */
bool check_pow_leading_zeros(const Blob256& hash, int required_leading_zeros);

/**
 * Adaptive difficulty: calculate next target based on block time history
 * 
 * Input:
 *   - last_target: current target (or Big256(1) for first adjustment)
 *   - actual_time: actual time taken for retarget_blocks blocks (seconds)
 *   - params: difficulty parameters
 * 
 * Output:
 *   - new target bounded by min/max adjustment factors
 *   - returns std::nullopt if adjustment fails (invalid input)
 */
std::optional<Big256> calculate_next_target(
    const Big256& last_target,
    int64_t actual_time,
    const DifficultyParams& params
);

/**
 * Compact difficulty encoding (Bitcoin-style)
 * 
 * nbits format: 0xMMEEEEEE
 *   MM = exponent (bytes of mantissa)
 *   EEEEEE = mantissa (3 bytes)
 * 
 * Value = mantissa * 2^(8 * (exponent - 3))
 * 
 * Encode Big256 → uint32_t compact
 */
uint32_t encode_compact(const Big256& target);

/**
 * Decode compact → Big256
 * Returns {target, negative, overflow}
 */
struct CompactDecoded {
    Big256 target;
    bool negative = false;
    bool overflow = false;
};

CompactDecoded decode_compact(uint32_t nbits);

/**
 * Get PoW limit (maximum difficulty = minimum target)
 * In Bitcoin: 0x00000000FFFF0000000000000000000000000000000000000000000000000000
 * For PiSecure: can be customized
 */
Big256 get_pow_limit();

/**
 * Validate that a target is within allowed range
 */
bool is_valid_target(const Big256& target, const Big256& pow_limit);

/**
 * Self-test: verify constant-time properties, encode/decode consistency
 * Returns true if all tests pass
 */
bool pow_selftest();

} // namespace consensus
} // namespace pisecure

#endif // PISECURE_CONSENSUS_POW_H
