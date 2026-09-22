#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>
#include <cstring>

namespace pisecure {
namespace pihash {

/**
 * PiHash: Hardware-verified mining algorithm for Raspberry Pi
 * 
 * CRITICAL SECURITY NOTICE:
 * This implementation contains hardware verification logic
 * that is compiled into binary form to prevent reverse-engineering.
 * The exact verification algorithms and thresholds are intentionally
 * obscured to protect the network from ASIC emulation and spoofing.
 * 
 * DO NOT expose the verification logic details in Python wrappers.
 */

struct HardwareFingerprint {
    std::string cpu_serial;
    std::string hardware_model;
    std::string mac_address;
    uint64_t memory_total;
    std::vector<uint8_t> hardware_rng;
    std::string unique_id;
    uint64_t timestamp;
    
    // VideoCore GPU firmware verification (enhanced anti-emulation)
    bool videocore_verified = false;
    uint32_t gpu_temperature = 0;
    uint32_t arm_clock_rate = 0;
    uint32_t throttling_status = 0;
    std::string firmware_revision;
};

class PiHash {
public:
    /**
     * Create PiHash instance
     * 
     * @param rounds Number of computational rounds (affects difficulty)
     * @param memory_mb Memory buffer size in MB (1-256)
     * @param npu_enabled Enable NPU acceleration if available
     */
    PiHash(int rounds = 1, int memory_mb = 1, bool npu_enabled = false);
    
    ~PiHash();
    
    /**
     * Compute PiHash digest with hardware verification
     * 
     * @param data Block data to hash
     * @param nonce Mining nonce
     * @param fingerprint Optional hardware fingerprint
     * @return Hexadecimal hash string
     * @throws std::runtime_error if hardware verification fails
     */
    std::string Compute(
        const std::vector<uint8_t>& data,
        uint32_t nonce,
        const HardwareFingerprint* fingerprint = nullptr
    );
    
    /**
     * Find nonce meeting difficulty requirement
     * 
     * @param block_data Block data to mine
     * @param difficulty Target leading zero bits
     * @param fingerprint Optional hardware fingerprint
     * @param max_attempts Maximum nonces to try (default 2^32)
     * @return Pair of (nonce, hash_hex) meeting difficulty
     * @throws std::runtime_error if no nonce found
     */
    std::pair<uint32_t, std::string> FindNonce(
        const std::vector<uint8_t>& block_data,
        int difficulty,
        const HardwareFingerprint* fingerprint = nullptr,
        uint32_t max_attempts = 0xFFFFFFFF
    );
    
    /**
     * Check if hash meets zero-bit difficulty requirement
     * 
     * @param hash_hex Hexadecimal hash string
     * @param target_zero_bits Required leading zero bits
     * @return True if hash meets difficulty
     */
    static bool MeetsDifficulty(const std::string& hash_hex, int target_zero_bits);
    
    /**
     * Get system hardware fingerprint
     * 
     * @return HardwareFingerprint structure
     * @throws std::runtime_error if fingerprinting fails
     */
    static HardwareFingerprint GetHardwareFingerprint();
    
    /**
     * Verify hardware is genuine Raspberry Pi
     * 
     * @param fingerprint Hardware fingerprint to verify
     * @return True if verified
     * 
     * IMPLEMENTATION DETAIL: Verification logic is intentionally
     * obscured within compiled binary to prevent spoofing.
     */
    static bool VerifyHardware(const HardwareFingerprint& fingerprint);

    /**
     * Portable digest: MemoryHardMix then CpuOptimizedFinalize.
     * Does not read VideoCore, mailbox, or a hardware fingerprint.
     * nonce_low is the MemoryHardMix nonce argument (low 32 bits).
     */
    std::vector<uint8_t> MixFinalize(const std::vector<uint8_t>& preimage, uint32_t nonce_low);
    
private:
    int rounds_;
    int memory_bytes_;
    bool npu_enabled_;
    bool hardware_verified_;
    HardwareFingerprint cached_fingerprint_;
    
    // Stage 1: Hardware integration
    std::vector<uint8_t> HardwareHash(
        const std::vector<uint8_t>& data,
        uint32_t nonce,
        const HardwareFingerprint& fingerprint
    );
    
    // Stage 2: Memory-hard mixing
    std::vector<uint8_t> MemoryHardMix(
        const std::vector<uint8_t>& hw_hash,
        uint32_t nonce
    );
    
    // Stage 3: CPU-optimized finalization
    std::vector<uint8_t> CpuOptimizedFinalize(
        const std::vector<uint8_t>& memory_hash
    );
    
    // Stage 4: NPU acceleration (placeholder)
    std::vector<uint8_t> NpuAccelerate(const std::vector<uint8_t>& data);
    
    // Helper: ARM diffusion operation
    void ArmDiffusion(std::vector<uint8_t>& state);
    
    // Helper: Count leading zero bits in hash
    static int CountLeadingZeroBits(const std::string& hash_hex);
    
    // Internal hardware verification (sealed in binary)
    static bool _VerifyHardwareInternal(const HardwareFingerprint& fp);
};

/**
 * Convenience function to compute PiHash
 * 
 * @param data Data to hash
 * @param nonce Mining nonce
 * @param rounds Computational rounds
 * @param memory_mb Memory buffer size
 * @return Hexadecimal hash string
 */
std::string ComputePiHash(
    const std::vector<uint8_t>& data,
    uint32_t nonce = 0,
    int rounds = 8,
    int memory_mb = 256
);

/**
 * Find mining nonce (convenience function)
 * 
 * @param block_data Block to mine
 * @param difficulty Target zero bits
 * @param max_attempts Maximum attempts
 * @return Pair of (nonce, hash) meeting difficulty
 */
std::pair<uint32_t, std::string> MineBlock(
    const std::vector<uint8_t>& block_data,
    int difficulty,
    uint32_t max_attempts = 0xFFFFFFFF
);

} // namespace pihash
} // namespace pisecure
