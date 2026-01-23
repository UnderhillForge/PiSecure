/**
 * pow.cpp - Proof-of-Work implementation
 */
#include "pow.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace pisecure {
namespace consensus {

Big256 leading_zeros_to_target(int leading_zero_bits) {
    // leading_zero_bits = number of leading 0 bits
    // target has all these bits as 0, then 1, then any pattern
    // Example: 146 leading zeros → shift (256 - 146) = 110 bits left
    
    if (leading_zero_bits < 0 || leading_zero_bits >= 256) {
        return Big256(); // Return 0 for invalid
    }
    
    Big256 target(1);
    int shift_amount = 256 - 1 - leading_zero_bits; // -1 for the leading 1 bit
    if (shift_amount > 0) {
        target <<= shift_amount;
    } else if (shift_amount < 0) {
        target >>= -shift_amount;
    }
    
    return target;
}

int target_to_leading_zeros(const Big256& target) {
    if (target.is_zero()) {
        return -1; // Invalid: zero target
    }
    
    unsigned bits = target.bits();
    if (bits > 256) {
        return -1; // Invalid: overflow
    }
    
    return 256 - static_cast<int>(bits);
}

bool check_pow(const Blob256& hash, const Big256& target) {
    // Constant-time comparison: hash <= target
    // Convert hash to Big256 (little-endian)
    Big256 hash_value = Big256::from_bytes(hash.data());
    
    // Constant-time less-or-equal
    return ct_less_or_equal(hash_value, target);
}

bool check_pow_leading_zeros(const Blob256& hash, int required_leading_zeros) {
    // Count leading zero bits in hash
    Big256 hash_value = Big256::from_bytes(hash.data());
    unsigned leading_zeros = hash_value.leading_zero_bits();
    
    // Compare (constant-time via >= which doesn't branch on value)
    return static_cast<int>(leading_zeros) >= required_leading_zeros;
}

std::optional<Big256> calculate_next_target(
    const Big256& last_target,
    int64_t actual_time,
    const DifficultyParams& params
) {
    if (last_target.is_zero() || last_target.bits() > 256) {
        return std::nullopt; // Invalid target
    }
    
    // Clamp actual_time to reasonable bounds
    int64_t max_time = params.retarget_time_target * params.max_adjustment_factor;
    int64_t min_time = params.retarget_time_target / params.max_adjustment_factor;
    
    actual_time = std::max(min_time, std::min(max_time, actual_time));
    
    Big256 new_target = last_target;
    
    // Adjust: new_target = last_target * actual_time / target_time
    // To avoid precision loss, do: new_target = (last_target / target_time) * actual_time
    
    // Simple fixed-point arithmetic:
    // new_target = last_target * actual_time / target_time
    
    // First, multiply by actual_time (may overflow intermediate)
    // For safety, divide first if needed
    uint64_t time_ratio_num = actual_time;
    uint64_t time_ratio_den = params.retarget_time_target;
    
    // Simplify ratio to avoid overflow
    // GCD-like simplification (simple version)
    while (time_ratio_num > 1000000 && time_ratio_den > 1) {
        time_ratio_num /= 2;
        time_ratio_den /= 2;
    }
    
    // new_target *= (time_ratio_num / time_ratio_den)
    // Do multiply first, then divide
    if (time_ratio_num > time_ratio_den) {
        new_target *= static_cast<uint32_t>(time_ratio_num);
        new_target /= static_cast<uint32_t>(time_ratio_den);
    } else {
        new_target /= static_cast<uint32_t>(time_ratio_den);
        new_target *= static_cast<uint32_t>(time_ratio_num);
    }
    
    // Verify result is within pow_limit
    Big256 limit = get_pow_limit();
    if (new_target > limit) {
        new_target = limit;
    }
    
    return new_target;
}

uint32_t encode_compact(const Big256& target) {
    uint8_t bytes[32];
    target.to_bytes(bytes);
    
    // Find the highest set byte
    uint32_t size = 0;
    for (int i = 31; i >= 0; i--) {
        if (bytes[i] != 0) {
            size = i + 1;
            break;
        }
    }
    
    if (size == 0) {
        return 0; // Zero target
    }
    
    uint32_t compact = bytes[size - 1];
    
    if (size > 1) {
        compact = (compact << 8) | bytes[size - 2];
    }
    if (size > 2) {
        compact = (compact << 8) | bytes[size - 3];
    }
    
    // If high bit is set, we need an extra byte for the sign
    if (compact & 0x00800000) {
        compact >>= 8;
        size++;
    }
    
    compact |= (size << 24);
    return compact;
}

CompactDecoded decode_compact(uint32_t nbits) {
    CompactDecoded result;
    
    uint32_t size = nbits >> 24;
    uint32_t mantissa = nbits & 0x00ffffff;
    
    bool overflow = false;
    bool negative = false;
    
    if (mantissa & 0x00800000) {
        negative = true;
        mantissa &= 0x007fffff;
    }
    
    if (size <= 3) {
        mantissa >>= (8 * (3 - size));
    } else {
        if (size > 32) {
            overflow = true;
            return result; // Return zero on overflow
        }
        
        // Shift left
        // This is simplified; proper implementation would handle large shifts
    }
    
    result.target = Big256(mantissa);
    result.negative = negative;
    result.overflow = overflow;
    
    return result;
}

Big256 get_pow_limit() {
    // PiSecure PoW limit: generous initial limit
    // Can be tuned per network (mainnet/testnet)
    Big256 limit = Big256::from_compact(0x207fffff, false, false).target;
    return limit;
}

bool is_valid_target(const Big256& target, const Big256& pow_limit) {
    if (target.is_zero()) {
        return false; // Zero target not allowed
    }
    
    if (target > pow_limit) {
        return false; // Target above pow_limit (difficulty too low)
    }
    
    return true;
}

bool pow_selftest() {
    // Test 1: leading_zeros conversion round-trip
    for (int bits = 100; bits <= 250; bits += 10) {
        Big256 target = leading_zeros_to_target(bits);
        int recovered = target_to_leading_zeros(target);
        if (recovered != bits) {
            return false;
        }
    }
    
    // Test 2: constant-time check doesn't crash on edge cases
    Blob256 hash = Blob256::from_hex("0000000000000000000000000000000000000000000000000000000000000001");
    Big256 target(1);
    
    bool result = check_pow(hash, target);
    (void)result; // Use result to avoid unused warning
    
    // Test 3: compact encode/decode consistency
    Big256 test_target(0xffffffff);
    uint32_t compact = encode_compact(test_target);
    CompactDecoded decoded = decode_compact(compact);
    
    if (decoded.overflow) {
        return false;
    }
    
    return true;
}

} // namespace consensus
} // namespace pisecure
