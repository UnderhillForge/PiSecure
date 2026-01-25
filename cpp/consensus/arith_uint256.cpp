/**
 * arith_uint256.cpp - 256-bit arithmetic implementation
 */
#include "arith_uint256.h"
#include "../util/endian.h"
#include <algorithm>
#include <climits>

namespace pisecure {
namespace consensus {

Big256::Big256() {
    std::memset(limbs_, 0, sizeof(limbs_));
}

Big256::Big256(uint64_t val) {
    std::memset(limbs_, 0, sizeof(limbs_));
    limbs_[0] = val & 0xffffffff;
    limbs_[1] = (val >> 32) & 0xffffffff;
}

Big256 Big256::from_bytes(const uint8_t data[32]) {
    Big256 b;
    for (size_t i = 0; i < WIDTH; i++) {
        b.limbs_[i] = util::read_le32(data + i * 4);
    }
    return b;
}

Big256 Big256::from_compact(uint32_t nbits, bool& neg, bool& overflow) {
    Big256 b;
    neg = false;
    overflow = false;
    
    uint32_t nShift = (nbits >> 24) & 0xff;
    uint32_t dDiff = 0x00ffffff;
    
    if (nShift <= 3) {
        b.limbs_[0] = (nbits & dDiff) >> (8 * (3 - nShift));
    } else {
        if (nShift >= 32) {
            overflow = true;
            return b;
        }
        b.limbs_[nShift >> 2] = (nbits & 0x00ffffff);
        if ((nbits & 0x00800000) != 0) {
            neg = true;
        }
    }
    
    return b;
}

void Big256::to_bytes(uint8_t out[32]) const {
    for (size_t i = 0; i < WIDTH; i++) {
        util::write_le32(out + i * 4, limbs_[i]);
    }
}

uint32_t Big256::get_compact(bool negative) const {
    uint32_t nSize = (bits() + 7) / 8;
    uint32_t nCompact = 0;
    
    if (nSize <= 3) {
        nCompact = (limbs_[0] & 0xffffff) << (8 * (3 - nSize));
    } else {
        nCompact = (limbs_[nSize / 4 - 1] & 0xffffff);
        if (nSize % 4 != 0) {
            nCompact >>= (8 * (4 - nSize % 4));
        }
    }
    
    if (nCompact & 0x00800000) {
        nCompact >>= 8;
        nSize--;
    }
    
    if (negative) {
        nCompact |= 0x00800000;
    }
    
    nCompact |= (nSize << 24);
    return nCompact;
}

Big256& Big256::operator+=(const Big256& b) {
    uint64_t carry = 0;
    for (size_t i = 0; i < WIDTH; i++) {
        uint64_t sum = carry + static_cast<uint64_t>(limbs_[i]) + b.limbs_[i];
        limbs_[i] = static_cast<uint32_t>(sum);
        carry = sum >> 32;
    }
    return *this;
}

Big256& Big256::operator-=(const Big256& b) {
    int64_t borrow = 0;
    for (size_t i = 0; i < WIDTH; i++) {
        int64_t diff = borrow + static_cast<int64_t>(limbs_[i]) - b.limbs_[i];
        limbs_[i] = static_cast<uint32_t>(diff);
        borrow = diff >> 32;
    }
    return *this;
}

Big256& Big256::operator*=(uint32_t b) {
    uint64_t carry = 0;
    for (size_t i = 0; i < WIDTH; i++) {
        uint64_t prod = carry + static_cast<uint64_t>(limbs_[i]) * b;
        limbs_[i] = static_cast<uint32_t>(prod);
        carry = prod >> 32;
    }
    return *this;
}

Big256& Big256::operator/=(uint32_t b) {
    uint64_t rem = 0;
    for (int i = WIDTH - 1; i >= 0; i--) {
        uint64_t dividend = (rem << 32) | limbs_[i];
        limbs_[i] = static_cast<uint32_t>(dividend / b);
        rem = dividend % b;
    }
    return *this;
}

Big256& Big256::operator>>=(int bits) {
    if (bits >= 256) {
        std::memset(limbs_, 0, sizeof(limbs_));
        return *this;
    }
    
    int limb_shift = bits / 32;
    int bit_shift = bits % 32;
    
    if (limb_shift > 0) {
        for (size_t i = 0; i < WIDTH - limb_shift; i++) {
            limbs_[i] = limbs_[i + limb_shift];
        }
        std::memset(limbs_ + WIDTH - limb_shift, 0, limb_shift * 4);
    }
    
    if (bit_shift > 0) {
        for (size_t i = 0; i < WIDTH - 1; i++) {
            limbs_[i] = (limbs_[i] >> bit_shift) | (limbs_[i + 1] << (32 - bit_shift));
        }
        limbs_[WIDTH - 1] >>= bit_shift;
    }
    
    return *this;
}

Big256& Big256::operator<<=(int bits) {
    if (bits >= 256) {
        std::memset(limbs_, 0, sizeof(limbs_));
        return *this;
    }
    
    int limb_shift = bits / 32;
    int bit_shift = bits % 32;
    
    if (limb_shift > 0) {
        for (int i = WIDTH - 1; i >= limb_shift; i--) {
            limbs_[i] = limbs_[i - limb_shift];
        }
        std::memset(limbs_, 0, limb_shift * 4);
    }
    
    if (bit_shift > 0) {
        for (int i = WIDTH - 1; i > 0; i--) {
            limbs_[i] = (limbs_[i] << bit_shift) | (limbs_[i - 1] >> (32 - bit_shift));
        }
        limbs_[0] <<= bit_shift;
    }
    
    return *this;
}

bool Big256::operator==(const Big256& b) const {
    return std::memcmp(limbs_, b.limbs_, sizeof(limbs_)) == 0;
}

bool Big256::operator<(const Big256& b) const {
    for (int i = WIDTH - 1; i >= 0; i--) {
        if (limbs_[i] < b.limbs_[i]) return true;
        if (limbs_[i] > b.limbs_[i]) return false;
    }
    return false;
}

bool Big256::operator<=(const Big256& b) const {
    return *this < b || *this == b;
}

bool Big256::operator>(const Big256& b) const {
    return b < *this;
}

bool Big256::operator>=(const Big256& b) const {
    return b <= *this;
}

bool Big256::is_zero() const {
    for (size_t i = 0; i < WIDTH; i++) {
        if (limbs_[i] != 0) return false;
    }
    return true;
}

bool Big256::is_negative() const {
    return (limbs_[WIDTH - 1] & 0x80000000) != 0;
}

unsigned Big256::leading_zero_bits() const {
    unsigned bits = 0;
    for (int i = WIDTH - 1; i >= 0; i--) {
        if (limbs_[i] != 0) {
            uint32_t val = limbs_[i];
            for (int j = 31; j >= 0; j--) {
                if ((val & (1u << j)) != 0) break;
                bits++;
            }
            break;
        }
        bits += 32;
    }
    return bits;
}

unsigned Big256::bits() const {
    for (int i = WIDTH - 1; i >= 0; i--) {
        if (limbs_[i] != 0) {
            uint32_t val = limbs_[i];
            unsigned b = 1;
            while (val >>= 1) b++;
            return b + i * 32;
        }
    }
    return 0;
}

void Big256::set_zero() {
    std::memset(limbs_, 0, sizeof(limbs_));
}

bool ct_equal(const Big256& a, const Big256& b) {
    uint32_t result = 0;
    const uint32_t* a_data = a.data();
    const uint32_t* b_data = b.data();
    for (size_t i = 0; i < Big256::WIDTH; i++) {
        result |= a_data[i] ^ b_data[i];
    }
    return result == 0;
}

bool ct_less_or_equal(const Big256& a, const Big256& b) {
    // Constant-time comparison
    int eq = 1, lt = 0;
    const uint32_t* a_data = a.data();
    const uint32_t* b_data = b.data();
    
    for (int i = Big256::WIDTH - 1; i >= 0; i--) {
        uint32_t x = a_data[i], y = b_data[i];
        lt = (lt & eq) | ((x < y) ? 1 : (x > y) ? 0 : 0);
        eq &= (x == y) ? 1 : 0;
    }
    return lt | eq;
}

} // namespace consensus
} // namespace pisecure
