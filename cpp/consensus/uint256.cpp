/**
 * uint256.cpp - Implementation of 256-bit opaque container
 */
#include "uint256.h"
#include <algorithm>
#include <cctype>
#include <cstdio>

namespace pisecure {
namespace consensus {

Blob256 Blob256::from_hex(const std::string& hex) {
    Blob256 b;
    if (hex.length() != 64) {
        return b; // Return zeros on error
    }
    
    for (size_t i = 0; i < 32; i++) {
        std::string byteStr = hex.substr(i * 2, 2);
        char* end;
        unsigned long val = strtoul(byteStr.c_str(), &end, 16);
        if (*end != '\0' || val > 0xff) {
            return Blob256(); // Return zeros on parse error
        }
        b.data_[i] = static_cast<uint8_t>(val);
    }
    return b;
}

std::string Blob256::to_hex() const {
    std::string result;
    result.reserve(64);
    for (size_t i = 0; i < SIZE; i++) {
        char buf[3];
        snprintf(buf, sizeof(buf), "%02x", data_[i]);
        result += buf;
    }
    return result;
}

int Blob256::compare(const Blob256& other) const {
    // Compare as little-endian (consensus order): compare from end to start
    for (int i = SIZE - 1; i >= 0; i--) {
        if (data_[i] < other.data_[i]) return -1;
        if (data_[i] > other.data_[i]) return 1;
    }
    return 0;
}

bool Blob256::operator==(const Blob256& other) const {
    return std::memcmp(data_.data(), other.data_.data(), SIZE) == 0;
}

bool Blob256::is_zero() const {
    for (size_t i = 0; i < SIZE; i++) {
        if (data_[i] != 0) return false;
    }
    return true;
}

} // namespace consensus
} // namespace pisecure
