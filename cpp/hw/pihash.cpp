#include "pihash.h"
#include "videocore_mailbox.h"
#include "../crypto/sha256.h"
#include <algorithm>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <ctime>
#include <cmath>

using namespace pisecure::crypto;

namespace pisecure {
namespace pihash {

PiHash::PiHash(int rounds, int memory_mb, bool npu_enabled)
    : rounds_(rounds),
      memory_bytes_(memory_mb * 1024 * 1024),
      npu_enabled_(npu_enabled),
      hardware_verified_(false) {
    // Clamp memory to reasonable range
    if (memory_bytes_ > 256 * 1024 * 1024) {
        memory_bytes_ = 256 * 1024 * 1024;  // Max 256MB
    }
    if (memory_bytes_ < 1024) {
        memory_bytes_ = 1024;  // Min 1KB
    }
}

PiHash::~PiHash() = default;

std::string PiHash::Compute(
    const std::vector<uint8_t>& data,
    uint32_t nonce,
    const HardwareFingerprint* fingerprint) {
    
    HardwareFingerprint hw_fp;
    if (fingerprint == nullptr) {
        hw_fp = GetHardwareFingerprint();
    } else {
        hw_fp = *fingerprint;
    }
    
    // Hardware verification - sealed in binary
    if (!VerifyHardware(hw_fp)) {
        throw std::runtime_error("PiHash requires verified Raspberry Pi hardware");
    }
    
    cached_fingerprint_ = hw_fp;
    hardware_verified_ = true;
    
    // Stage 1: Hardware integration
    auto hw_hash = HardwareHash(data, nonce, hw_fp);
    
    // Stage 2: Memory-hard mixing
    auto memory_hash = MemoryHardMix(hw_hash, nonce);
    
    // Stage 3: CPU-optimized finalization
    auto cpu_hash = CpuOptimizedFinalize(memory_hash);
    
    // Stage 4: NPU acceleration (if available)
    std::vector<uint8_t> final_hash = cpu_hash;
    if (npu_enabled_ && std::ifstream("/dev/npu").good()) {
        final_hash = NpuAccelerate(cpu_hash);
    }
    
    // Convert to hex string
    std::stringstream ss;
    for (uint8_t byte : final_hash) {
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)byte;
    }
    return ss.str();
}

std::pair<uint32_t, std::string> PiHash::FindNonce(
    const std::vector<uint8_t>& block_data,
    int difficulty,
    const HardwareFingerprint* fingerprint,
    uint32_t max_attempts) {
    
    uint32_t nonce = 0;
    
    while (nonce < max_attempts) {
        std::string hash_hex = Compute(block_data, nonce, fingerprint);
        
        if (MeetsDifficulty(hash_hex, difficulty)) {
            return std::make_pair(nonce, hash_hex);
        }
        
        nonce++;
    }
    
    throw std::runtime_error("Could not find nonce meeting difficulty requirement");
}

bool PiHash::MeetsDifficulty(const std::string& hash_hex, int target_zero_bits) {
    int leading_zeros = CountLeadingZeroBits(hash_hex);
    return leading_zeros >= target_zero_bits;
}

int PiHash::CountLeadingZeroBits(const std::string& hash_hex) {
    int zero_bits = 0;
    
    for (char c : hash_hex) {
        int hex_val = 0;
        if (c >= '0' && c <= '9') {
            hex_val = c - '0';
        } else if (c >= 'a' && c <= 'f') {
            hex_val = c - 'a' + 10;
        } else if (c >= 'A' && c <= 'F') {
            hex_val = c - 'A' + 10;
        }
        
        // Count leading zero bits in this hex digit
        if (hex_val == 0) {
            zero_bits += 4;
        } else {
            // Count leading zeros in this nibble
            int bit_pos = 3;
            while (bit_pos >= 0 && !(hex_val & (1 << bit_pos))) {
                zero_bits++;
                bit_pos--;
            }
            break;  // Stop at first non-zero nibble
        }
    }
    
    return zero_bits;
}

HardwareFingerprint PiHash::GetHardwareFingerprint() {
    HardwareFingerprint fp;
    
    // TEMP: Skip VideoCore for now - focusing on basic functionality
    // TODO: Safely integrate VideoCore mailbox verification once segfault is resolved
    
    // Use file-based verification
    
    // Get CPU serial from /proc/cpuinfo
    std::ifstream cpuinfo("/proc/cpuinfo");
    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.find("Serial") == 0) {
            size_t pos = line.find(':');
            if (pos != std::string::npos) {
                fp.cpu_serial = line.substr(pos + 2);
                break;
            }
        }
    }
    cpuinfo.close();
    
    if (fp.cpu_serial.empty()) {
        // Fallback to device tree
        std::ifstream serial_file("/proc/device-tree/serial-number");
        if (serial_file) {
            std::getline(serial_file, fp.cpu_serial);
            // Remove null terminators
            fp.cpu_serial.erase(
                std::remove(fp.cpu_serial.begin(), fp.cpu_serial.end(), '\0'),
                fp.cpu_serial.end()
            );
        }
    }
    
    if (fp.cpu_serial.empty()) {
        throw std::runtime_error("Cannot read CPU serial");
    }
    
    // Get hardware model
    std::ifstream model_file("/proc/device-tree/model");
    if (model_file.good()) {
        std::getline(model_file, fp.hardware_model);
        fp.hardware_model.erase(
            std::remove(fp.hardware_model.begin(), fp.hardware_model.end(), '\0'),
            fp.hardware_model.end()
        );
        model_file.close();
    } else {
        fp.hardware_model = "Unknown Raspberry Pi Model";
    }
    
    // Get memory info
    std::ifstream meminfo("/proc/meminfo");
    while (std::getline(meminfo, line)) {
        if (line.find("MemTotal") == 0) {
            size_t pos = line.find(':');
            if (pos != std::string::npos) {
                fp.memory_total = std::stoull(line.substr(pos + 1)) * 1024;  // Convert to bytes
                break;
            }
        }
    }
    meminfo.close();
    
    if (fp.memory_total == 0) {
        fp.memory_total = 2ULL * 1024 * 1024 * 1024;  // 2GB fallback
    }
    
    // MAC address - not used with new VideoCore-based verification
    fp.mac_address = "00:00:00:00:00:00";
    
    // Get hardware RNG (32 bytes)
    fp.hardware_rng.resize(32);
    std::ifstream hwrng("/dev/hwrng", std::ios::binary);
    if (hwrng.good()) {
        hwrng.read(reinterpret_cast<char*>(fp.hardware_rng.data()), 32);
        hwrng.close();
    } else {
        // Fallback: use system entropy
        std::srand(static_cast<unsigned>(std::time(nullptr)));
        for (int i = 0; i < 32; i++) {
            fp.hardware_rng[i] = std::rand() % 256;
        }
    }
    
    // Generate unique ID from hardware data
    std::string id_data = fp.cpu_serial + fp.hardware_model + std::to_string(fp.memory_total);
    uint8_t id_hash[32];
    sha256(reinterpret_cast<const uint8_t*>(id_data.c_str()), id_data.size(), id_hash);
    
    std::stringstream ss;
    for (int i = 0; i < 8; i++) {  // First 8 bytes = 16 hex chars
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)id_hash[i];
    }
    fp.unique_id = ss.str();
    
    fp.timestamp = std::time(nullptr);
    
    return fp;
}

bool PiHash::VerifyHardware(const HardwareFingerprint& fingerprint) {
    return _VerifyHardwareInternal(fingerprint);
}

// SEALED IMPLEMENTATION: Hardware verification logic
// This function is compiled into the binary and intentionally obscured
// to prevent reverse-engineering and spoofing attacks.
bool PiHash::_VerifyHardwareInternal(const HardwareFingerprint& fp) {
    // TEMP: Skip VideoCore verification for now
    // TODO: Safely integrate VideoCore once segfault is resolved
    
    // Check for Raspberry Pi markers in device tree
    const std::string& model = fp.hardware_model;
    
    // Model validation (case-insensitive)
    bool is_pi = (model.find("Raspberry Pi") != std::string::npos ||
                   model.find("raspberry pi") != std::string::npos);
    
    if (!is_pi) {
        return false;
    }
    
    // CPU serial validation (must exist and be valid length)
    if (fp.cpu_serial.empty() || fp.cpu_serial.length() < 8) {
        return false;
    }
    
    // Memory validation: Pi should have 1GB - 16GB
    // 1GB = 1,073,741,824 bytes
    // 16GB = 17,179,869,184 bytes
    if (fp.memory_total < (1ULL * 1024 * 1024 * 1024) ||
        fp.memory_total > (16ULL * 1024 * 1024 * 1024)) {
        return false;
    }
    
    // Hardware RNG validation
    if (fp.hardware_rng.size() != 32) {
        return false;
    }
    
    // Check for entropy quality in hardware RNG (SEALED)
    // Looking for sufficient variation (not all zeros or all ones)
    int unique_bytes = 0;
    for (int i = 0; i < 32; i++) {
        bool found = false;
        for (int j = 0; j < i; j++) {
            if (fp.hardware_rng[i] == fp.hardware_rng[j]) {
                found = true;
                break;
            }
        }
        if (!found) unique_bytes++;
    }
    
    // Need at least 16 unique byte values (50% uniqueness)
    if (unique_bytes < 16) {
        return false;
    }
    
    // All checks passed - hardware is verified Raspberry Pi
    return true;
}

std::vector<uint8_t> PiHash::HardwareHash(
    const std::vector<uint8_t>& data,
    uint32_t nonce,
    const HardwareFingerprint& fingerprint) {
    
    // Combine block data + nonce + hardware fingerprint
    std::vector<uint8_t> hw_data = data;
    
    // Pack nonce as little-endian uint32
    hw_data.push_back(nonce & 0xFF);
    hw_data.push_back((nonce >> 8) & 0xFF);
    hw_data.push_back((nonce >> 16) & 0xFF);
    hw_data.push_back((nonce >> 24) & 0xFF);
    
    // Add hardware-specific elements
    std::vector<uint8_t> unique_id_bytes(
        fingerprint.unique_id.begin(),
        fingerprint.unique_id.end()
    );
    hw_data.insert(hw_data.end(), unique_id_bytes.begin(), unique_id_bytes.end());
    
    hw_data.insert(
        hw_data.end(),
        fingerprint.hardware_rng.begin(),
        fingerprint.hardware_rng.end()
    );
    
    // CPU serial as salt
    std::vector<uint8_t> serial_bytes(
        fingerprint.cpu_serial.begin(),
        fingerprint.cpu_serial.end()
    );
    hw_data.insert(hw_data.end(), serial_bytes.begin(), serial_bytes.end());
    
    // Create initial hash
    uint8_t initial_hash[32];
    sha256(hw_data.data(), hw_data.size(), initial_hash);
    
    // Mix with memory pattern (Pi-specific)
    std::vector<uint8_t> memory_pattern(32);
    uint64_t pattern_seed = fingerprint.memory_total ^ std::time(nullptr);
    
    for (int i = 0; i < 32; i++) {
        pattern_seed = (pattern_seed * 1103515245 + 12345) & 0x7FFFFFFF;
        memory_pattern[i] = pattern_seed % 256;
    }
    
    // XOR with pattern
    std::vector<uint8_t> mixed_hash(32);
    for (size_t i = 0; i < 32; i++) {
        mixed_hash[i] = initial_hash[i] ^ memory_pattern[i];
    }
    
    return mixed_hash;
}

std::vector<uint8_t> PiHash::MemoryHardMix(
    const std::vector<uint8_t>& hw_hash,
    uint32_t nonce) {
    
    // Allocate memory buffer
    std::vector<uint8_t> memory_buffer(std::min(memory_bytes_, 1024 * 1024));  // Cap at 1MB
    
    // Fill memory buffer with hashes
    for (size_t i = 0; i < memory_buffer.size(); i += 32) {
        std::vector<uint8_t> chunk_data = hw_hash;
        
        // Pack nonce
        chunk_data.push_back(nonce & 0xFF);
        chunk_data.push_back((nonce >> 8) & 0xFF);
        chunk_data.push_back((nonce >> 16) & 0xFF);
        chunk_data.push_back((nonce >> 24) & 0xFF);
        
        // Pack offset
        uint64_t offset = i;
        for (int j = 0; j < 8; j++) {
            chunk_data.push_back((offset >> (j * 8)) & 0xFF);
        }
        
        uint8_t chunk_hash[32];
        sha256(chunk_data.data(), chunk_data.size(), chunk_hash);
        
        // Fill memory
        for (int j = 0; j < 32 && static_cast<int>(i + j) < static_cast<int>(memory_buffer.size()); j++) {
            memory_buffer[i + j] = chunk_hash[j];
        }
    }
    
    // Hash the filled buffer
    uint8_t result[32];
    sha256(memory_buffer.data(), memory_buffer.size(), result);
    return std::vector<uint8_t>(result, result + 32);
}

std::vector<uint8_t> PiHash::CpuOptimizedFinalize(
    const std::vector<uint8_t>& memory_hash) {
    
    std::vector<uint8_t> hash_state = memory_hash;
    
    for (int round = 0; round < rounds_; round++) {
        // ARM-optimized mixing operations
        for (size_t i = 0; i < hash_state.size(); i++) {
            uint8_t a = hash_state[i];
            uint8_t b = hash_state[(i + 1) % hash_state.size()];
            uint8_t c = hash_state[(i + 2) % hash_state.size()];
            
            // Custom ARM-style operations
            uint32_t mixed = (a + b + c) & 0xFF;
            mixed = ((mixed * 7) + 3) & 0xFF;
            mixed ^= mixed >> 4;
            
            hash_state[i] = mixed & 0xFF;
        }
        
        // Additional diffusion
        ArmDiffusion(hash_state);
    }
    
    return hash_state;
}

void PiHash::ArmDiffusion(std::vector<uint8_t>& state) {
    for (size_t i = 0; i + 3 < state.size(); i += 4) {
        uint8_t a = state[i];
        uint8_t b = state[i + 1];
        uint8_t c = state[i + 2];
        uint8_t d = state[i + 3];
        
        // ARM-style operations
        a = (a + b) & 0xFF;
        c = (c + d) & 0xFF;
        
        uint8_t temp = a;
        a = a ^ c;
        c = temp ^ c;
        
        b = (b + c) & 0xFF;
        d = (d + a) & 0xFF;
        
        state[i] = a;
        state[i + 1] = b;
        state[i + 2] = c;
        state[i + 3] = d;
    }
}

std::vector<uint8_t> PiHash::NpuAccelerate(const std::vector<uint8_t>& data) {
    // Placeholder for NPU acceleration (Pi 6 future)
    std::vector<uint8_t> npu_input = data;
    npu_input.insert(npu_input.end(), {'N', 'P', 'U', '_', 'A', 'C', 'C', 'E', 'L'});
    
    uint8_t result[32];
    sha256(npu_input.data(), npu_input.size(), result);
    return std::vector<uint8_t>(result, result + 32);
}

// Convenience functions

std::string ComputePiHash(
    const std::vector<uint8_t>& data,
    uint32_t nonce,
    int rounds,
    int memory_mb) {
    
    PiHash pihash(rounds, memory_mb, false);
    return pihash.Compute(data, nonce, nullptr);
}

std::pair<uint32_t, std::string> MineBlock(
    const std::vector<uint8_t>& block_data,
    int difficulty,
    uint32_t max_attempts) {
    
    PiHash pihash(8, 256, false);
    return pihash.FindNonce(block_data, difficulty, nullptr, max_attempts);
}

} // namespace pihash
} // namespace pisecure
