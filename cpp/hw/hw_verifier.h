/**
 * hw_verifier.h - Raspberry Pi Hardware Verification
 * 
 * Provides hardware-bound verification for PiSecure mining:
 * - BCM271x/2712 peripheral access (Pi-specific registers)
 * - /dev/hwrng entropy quality validation
 * - CPU serial and board revision detection
 * - Anti-virtualization heuristics
 * - Pi model identification (Pi 0 through Pi 5)
 * 
 * Security Model:
 * - Mining requires genuine Pi hardware (hardware-verified PiHash)
 * - Validation works on ANY platform (SHA-256 only, no hardware dependency)
 */

#ifndef PISECURE_HW_VERIFIER_H
#define PISECURE_HW_VERIFIER_H

#include <cstdint>
#include <string>
#include <vector>
#include <optional>

namespace pisecure {
namespace hw {

/**
 * Pi model enumeration (Zero through 5)
 */
enum class PiModel {
    UNKNOWN = 0,
    PI_ZERO,
    PI_ZERO_W,
    PI_ZERO_2W,
    PI_1_A,
    PI_1_B,
    PI_1_A_PLUS,
    PI_1_B_PLUS,
    PI_2_B,
    PI_3_B,
    PI_3_B_PLUS,
    PI_3_A_PLUS,
    PI_4_B,
    PI_400,
    PI_CM4,
    PI_5,
    PI_CM5,
    NOT_PI  // Running on non-Pi hardware (validation-only mode allowed)
};

/**
 * Hardware verification result
 */
struct HardwareInfo {
    bool is_genuine_pi;           // True if genuine Raspberry Pi detected
    PiModel model;                // Detected Pi model
    std::string cpu_serial;       // CPU serial from /proc/cpuinfo
    std::string board_revision;   // Board revision hex code
    uint32_t soc_id;              // BCM SoC identifier (2835/2836/2837/2711/2712)
    bool has_hwrng;               // /dev/hwrng available
    bool virtualized;             // Likely running in VM/container
    std::string error_message;    // Error details if verification fails
};

/**
 * Entropy quality assessment from /dev/hwrng
 */
struct EntropyQuality {
    bool sufficient;              // True if entropy meets quality threshold
    double bits_per_byte;         // Shannon entropy estimate (0-8)
    uint32_t sample_size;         // Bytes sampled
    double chi_square;            // Chi-square test statistic
    bool uniformity_ok;           // Byte distribution uniform
    std::string failure_reason;   // Reason if quality insufficient
};

/**
 * RAII wrapper for BCM peripheral mmap access
 */
class BCMPeripheralAccess {
public:
    BCMPeripheralAccess();
    ~BCMPeripheralAccess();

    // Delete copy/move (RAII resource)
    BCMPeripheralAccess(const BCMPeripheralAccess&) = delete;
    BCMPeripheralAccess& operator=(const BCMPeripheralAccess&) = delete;

    /**
     * Open BCM peripheral memory mapping
     * Returns true on success
     */
    bool open();

    /**
     * Read 32-bit register at offset
     */
    std::optional<uint32_t> read_register(uint32_t offset);

    /**
     * Check if successfully mapped
     */
    bool is_open() const { return mapped_; }

    /**
     * Get base address for current SoC
     */
    uint32_t get_peripheral_base() const { return peripheral_base_; }

private:
    int fd_;
    void* mapped_base_;
    size_t mapped_size_;
    uint32_t peripheral_base_;
    bool mapped_;

    /**
     * Detect BCM peripheral base address (varies by Pi model)
     */
    uint32_t detect_peripheral_base();
};

/**
 * Hardware Verifier - main interface
 */
class HardwareVerifier {
public:
    HardwareVerifier();
    ~HardwareVerifier() = default;

    /**
     * Perform comprehensive hardware verification
     * Returns HardwareInfo with detection results
     */
    HardwareInfo verify_hardware();

    /**
     * Read entropy from /dev/hwrng and assess quality
     * 
     * @param num_bytes Number of entropy bytes to read (default 32)
     * @param timeout_ms Timeout in milliseconds (default 1000)
     * @return Entropy quality assessment
     */
    EntropyQuality read_entropy(size_t num_bytes = 32, int timeout_ms = 1000);

    /**
     * Get CPU serial from /proc/cpuinfo
     */
    std::string get_cpu_serial();

    /**
     * Get board revision from /proc/cpuinfo
     */
    std::string get_board_revision();

    /**
     * Detect Pi model from revision code
     */
    PiModel detect_pi_model(const std::string& revision);

    /**
     * Check if running in virtualized environment
     * Uses timing attacks and hypervisor hints
     */
    bool detect_virtualization();

    /**
     * Validate hardware fingerprint for mining
     * Returns true only if genuine Pi hardware detected
     */
    bool is_mining_capable();

    /**
     * Get human-readable model name
     */
    static std::string model_name(PiModel model);

    /**
     * Self-test: verify hardware verifier is working
     */
    static bool selftest();

private:
    BCMPeripheralAccess bcm_access_;
    std::optional<HardwareInfo> cached_info_;

    /**
     * Parse /proc/cpuinfo for key-value pairs
     */
    std::string read_cpuinfo_field(const std::string& field_name);

    /**
     * Detect BCM SoC ID from peripheral access
     */
    uint32_t detect_soc_id();

    /**
     * Check /dev/hwrng availability
     */
    bool check_hwrng_available();

    /**
     * Calculate Shannon entropy for byte buffer
     */
    double calculate_entropy(const uint8_t* data, size_t len);

    /**
     * Perform chi-square uniformity test
     */
    double chi_square_test(const uint8_t* data, size_t len);

    /**
     * Timing-based virtualization detection
     * VMs have higher rdtsc variance
     */
    bool timing_based_vm_detection();

    /**
     * Check for hypervisor hints in /proc/cpuinfo
     */
    bool check_hypervisor_hints();
};

} // namespace hw
} // namespace pisecure

#endif // PISECURE_HW_VERIFIER_H
