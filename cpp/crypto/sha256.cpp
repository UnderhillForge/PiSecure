/**
 * sha256.cpp - SHA-256 implementation (validation only)
 * Based on Bitcoin Core patterns
 */
#include "sha256.h"
#include "../util/endian.h"
#include <cstring>

namespace pisecure {
namespace crypto {

// SHA-256 constants
static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

// SHA-256 initial state
static const uint32_t IV[8] = {
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
};

Sha256Ctx::Sha256Ctx() : bytes_(0), buffer_len_(0) {
    std::memcpy(state_, IV, sizeof(state_));
}

Sha256Ctx& Sha256Ctx::reset() {
    std::memcpy(state_, IV, sizeof(state_));
    bytes_ = 0;
    buffer_len_ = 0;
    return *this;
}

Sha256Ctx& Sha256Ctx::write(const uint8_t* data, size_t len) {
    while (len > 0) {
        size_t space = 64 - buffer_len_;
        size_t chunk = (len < space) ? len : space;
        std::memcpy(buffer_ + buffer_len_, data, chunk);
        buffer_len_ += chunk;
        data += chunk;
        len -= chunk;
        bytes_ += chunk;
        
        if (buffer_len_ == 64) {
            Transform(buffer_);
            buffer_len_ = 0;
        }
    }
    return *this;
}

void Sha256Ctx::Transform(const uint8_t* block) {
    uint32_t w[64];
    
    // Load message schedule
    for (int i = 0; i < 16; i++) {
        w[i] = util::read_be32(block + i * 4);
    }
    
    // Expand message schedule
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ((w[i-15] >> 7) | (w[i-15] << 25)) ^ ((w[i-15] >> 18) | (w[i-15] << 14)) ^ (w[i-15] >> 3);
        uint32_t s1 = ((w[i-2] >> 17) | (w[i-2] << 15)) ^ ((w[i-2] >> 19) | (w[i-2] << 13)) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    
    // Working variables
    uint32_t a = state_[0], b = state_[1], c = state_[2], d = state_[3];
    uint32_t e = state_[4], f = state_[5], g = state_[6], h = state_[7];
    
    // Main loop
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = ((e >> 6) | (e << 26)) ^ ((e >> 11) | (e << 21)) ^ ((e >> 25) | (e << 7));
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + S1 + ch + K[i] + w[i];
        uint32_t S0 = ((a >> 2) | (a << 30)) ^ ((a >> 13) | (a << 19)) ^ ((a >> 22) | (a << 10));
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = S0 + maj;
        
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    
    // Update state
    state_[0] += a;
    state_[1] += b;
    state_[2] += c;
    state_[3] += d;
    state_[4] += e;
    state_[5] += f;
    state_[6] += g;
    state_[7] += h;
}

void Sha256Ctx::finalize(uint8_t out[32]) {
    // Padding
    uint8_t pad[64];
    uint64_t bits = bytes_ * 8;
    size_t padlen = (bytes_ % 64 < 56) ? (56 - bytes_ % 64) : (120 - bytes_ % 64);
    
    pad[0] = 0x80;
    std::memset(pad + 1, 0, padlen - 1);
    util::write_be64(pad + padlen, bits);
    
    write(pad, padlen + 8);
    
    // Output
    for (int i = 0; i < 8; i++) {
        util::write_be32(out + i * 4, state_[i]);
    }
}

void sha256(const uint8_t* in, size_t len, uint8_t out[32]) {
    Sha256Ctx ctx;
    ctx.write(in, len).finalize(out);
}

void sha256d(const uint8_t* in, size_t len, uint8_t out[32]) {
    uint8_t tmp[32];
    sha256(in, len, tmp);
    sha256(tmp, 32, out);
}

void sha256d64(uint8_t* out, const uint8_t* in, size_t blocks) {
    for (size_t i = 0; i < blocks; i++) {
        sha256d(in + i * 64, 64, out + i * 32);
    }
}

} // namespace crypto
} // namespace pisecure
