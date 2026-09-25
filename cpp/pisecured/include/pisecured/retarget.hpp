#pragma once

#include <cstdint>

namespace pisecured
{
    // Leading-zero bits after the activation height. One retarget uses the
    // last 10 timestamps (9 gaps) and cannot move work by more than 4x.
    constexpr uint32_t kRetargetMinBits = 2;
    constexpr uint32_t kRetargetMaxBits = 24;
    constexpr uint64_t kRetargetTargetSeconds = 540;

    inline uint32_t round_log2(uint64_t value)
    {
        if (value <= 1)
        {
            return 0;
        }
        uint32_t floor = 0;
        uint64_t shifted = value;
        while (shifted > 1)
        {
            shifted >>= 1;
            ++floor;
        }
        const uint64_t base = 1ull << floor;
        // Nearest integer to log2: round up at 2^(n+0.5) = base * sqrt(2).
        const unsigned __int128 squared = static_cast<unsigned __int128>(value) * value;
        const unsigned __int128 half = static_cast<unsigned __int128>(base) * base * 2;
        if (squared >= half)
        {
            return floor + 1;
        }
        return floor;
    }

    // elapsed is time[tip] - time[tip-9]. Non-positive elapsed keeps bits.
    inline uint32_t retarget_difficulty_bits(uint32_t bits, int64_t elapsed)
    {
        if (bits < kRetargetMinBits)
        {
            bits = kRetargetMinBits;
        }
        if (bits > kRetargetMaxBits)
        {
            bits = kRetargetMaxBits;
        }
        if (elapsed <= 0)
        {
            return bits;
        }
        uint64_t span = static_cast<uint64_t>(elapsed);
        const uint64_t min_span = kRetargetTargetSeconds / 4;
        const uint64_t max_span = kRetargetTargetSeconds * 4;
        if (span < min_span)
        {
            span = min_span;
        }
        if (span > max_span)
        {
            span = max_span;
        }
        const uint64_t work = 1ull << bits;
        uint64_t next_work = work * kRetargetTargetSeconds / span;
        const uint64_t min_work = work / 4;
        const uint64_t max_work = work * 4;
        if (next_work < min_work)
        {
            next_work = min_work;
        }
        if (next_work > max_work)
        {
            next_work = max_work;
        }
        if (next_work < 1)
        {
            next_work = 1;
        }
        uint32_t next_bits = round_log2(next_work);
        if (next_bits < kRetargetMinBits)
        {
            next_bits = kRetargetMinBits;
        }
        if (next_bits > kRetargetMaxBits)
        {
            next_bits = kRetargetMaxBits;
        }
        return next_bits;
    }
}
