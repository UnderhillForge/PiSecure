/**
 * endian.h - Explicit byte order handling for PiSecure
 * Inspired by Bitcoin Core: src/compat/endian.h
 */
#ifndef PISECURE_UTIL_ENDIAN_H
#define PISECURE_UTIL_ENDIAN_H

#include <cstdint>
#include <cstring>

namespace pisecure {
namespace util {

/**
 * Explicit big-endian 32-bit read
 */
inline uint32_t read_be32(const uint8_t* data) {
    return (static_cast<uint32_t>(data[0]) << 24) |
           (static_cast<uint32_t>(data[1]) << 16) |
           (static_cast<uint32_t>(data[2]) << 8) |
           (static_cast<uint32_t>(data[3]));
}

/**
 * Explicit little-endian 32-bit read
 */
inline uint32_t read_le32(const uint8_t* data) {
    return (static_cast<uint32_t>(data[0])) |
           (static_cast<uint32_t>(data[1]) << 8) |
           (static_cast<uint32_t>(data[2]) << 16) |
           (static_cast<uint32_t>(data[3]) << 24);
}

/**
 * Explicit big-endian 32-bit write
 */
inline void write_be32(uint8_t* data, uint32_t val) {
    data[0] = (val >> 24) & 0xff;
    data[1] = (val >> 16) & 0xff;
    data[2] = (val >> 8) & 0xff;
    data[3] = val & 0xff;
}

/**
 * Explicit little-endian 32-bit write
 */
inline void write_le32(uint8_t* data, uint32_t val) {
    data[0] = val & 0xff;
    data[1] = (val >> 8) & 0xff;
    data[2] = (val >> 16) & 0xff;
    data[3] = (val >> 24) & 0xff;
}

/**
 * Explicit big-endian 64-bit read
 */
inline uint64_t read_be64(const uint8_t* data) {
    return (static_cast<uint64_t>(read_be32(data)) << 32) |
           (static_cast<uint64_t>(read_be32(data + 4)));
}

/**
 * Explicit big-endian 64-bit write
 */
inline void write_be64(uint8_t* data, uint64_t val) {
    write_be32(data, (val >> 32) & 0xffffffff);
    write_be32(data + 4, val & 0xffffffff);
}

} // namespace util
} // namespace pisecure

#endif // PISECURE_UTIL_ENDIAN_H
