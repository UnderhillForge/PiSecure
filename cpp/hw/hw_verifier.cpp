/**
 * hw_verifier.cpp - Hardware Verification Implementation
 */
#include "hw_verifier.h"

#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <cstring>
#include <cmath>
#include <fstream>
#include <sstream>
#include <chrono>
#include <algorithm>

namespace pisecure {
namespace hw {

// BCM peripheral base addresses (vary by Pi model)
constexpr uint32_t BCM2835_PERI_BASE = 0x20000000; // Pi 1, Zero
constexpr uint32_t BCM2836_PERI_BASE = 0x3F000000; // Pi 2, 3
constexpr uint32_t BCM2711_PERI_BASE = 0xFE000000; // Pi 4
constexpr uint64_t BCM2712_PERI_BASE = 0x1F00000000ULL; // Pi 5 (64-bit)

constexpr size_t PERI_MAP_SIZE = 0x1000000; // 16MB

// Revision code mappings (subset - full list extensive)
struct RevisionMapping {
    uint32_t code;
    PiModel model;
};

static const RevisionMapping REVISION_MAP[] = {
    {0x900092, PiModel::PI_ZERO},
    {0x900093, PiModel::PI_ZERO},
    {0x920093, PiModel::PI_ZERO},
    {0x9000C1, PiModel::PI_ZERO_W},
    {0x902120, PiModel::PI_ZERO_2W},
    {0xa02082, PiModel::PI_3_B},
    {0xa020d3, PiModel::PI_3_B_PLUS},
    {0xa22082, PiModel::PI_3_B},
    {0xa32082, PiModel::PI_3_B},
    {0xc03111, PiModel::PI_4_B},
    {0xc03112, PiModel::PI_4_B},
    {0xd03114, PiModel::PI_4_B},
    {0xc04170, PiModel::PI_5},
    {0xd04170, PiModel::PI_5},
};

// ============================================================================
// BCMPeripheralAccess Implementation
// ============================================================================

BCMPeripheralAccess::BCMPeripheralAccess()
    : fd_(-1)
    , mapped_base_(nullptr)
    , mapped_size_(0)
    , peripheral_base_(0)
    , mapped_(false)
{
}

BCMPeripheralAccess::~BCMPeripheralAccess() {
    if (mapped_base_ && mapped_base_ != MAP_FAILED) {
        munmap(mapped_base_, mapped_size_);
    }
    if (fd_ >= 0) {
        close(fd_);
    }
}

uint32_t BCMPeripheralAccess::detect_peripheral_base() {
    // Try to detect from /proc/device-tree/soc/ranges
    std::ifstream ranges("/proc/device-tree/soc/ranges", std::ios::binary);
    if (ranges.is_open()) {
        uint32_t addr;
        ranges.read(reinterpret_cast<char*>(&addr), sizeof(addr));
        if (!ranges.fail()) {
            // Big-endian to native
            addr = __builtin_bswap32(addr);
            if (addr == BCM2835_PERI_BASE || addr == BCM2836_PERI_BASE ||
                addr == BCM2711_PERI_BASE) {
                return addr;
            }
        }
    }

    // Fallback: check /proc/cpuinfo for model hints
    std::ifstream cpuinfo("/proc/cpuinfo");
    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.find("Revision") != std::string::npos) {
            size_t pos = line.find(':');
            if (pos != std::string::npos) {
                std::string rev = line.substr(pos + 1);
                rev.erase(0, rev.find_first_not_of(" \t"));
                uint32_t rev_code = std::stoul(rev, nullptr, 16);

                // Pi 5: BCM2712
                if ((rev_code & 0xFFFF00) == 0xc04100 || (rev_code & 0xFFFF00) == 0xd04100) {
                    return BCM2712_PERI_BASE;
                }
                // Pi 4: BCM2711
                if ((rev_code & 0xFFFF00) == 0xc03100 || (rev_code & 0xFFFF00) == 0xd03100) {
                    return BCM2711_PERI_BASE;
                }
                // Pi 2/3: BCM2836/2837
                if ((rev_code & 0xFF0000) == 0xa00000 || (rev_code & 0xFF0000) == 0xa20000) {
                    return BCM2836_PERI_BASE;
                }
                // Pi 1/Zero: BCM2835
                return BCM2835_PERI_BASE;
            }
        }
    }

    // Default to BCM2836 (most common)
    return BCM2836_PERI_BASE;
}

bool BCMPeripheralAccess::open() {
    if (mapped_) {
        return true;
    }

    peripheral_base_ = detect_peripheral_base();

    // Try /dev/mem (requires root)
    fd_ = ::open("/dev/mem", O_RDONLY | O_SYNC);
    if (fd_ < 0) {
        // Try /dev/gpiomem (non-root GPIO access)
        fd_ = ::open("/dev/gpiomem", O_RDONLY | O_SYNC);
        if (fd_ < 0) {
            return false;
        }
        peripheral_base_ = 0; // gpiomem is pre-mapped to GPIO base
    }

    mapped_size_ = PERI_MAP_SIZE;
    mapped_base_ = mmap(
        nullptr,
        mapped_size_,
        PROT_READ,
        MAP_SHARED,
        fd_,
        peripheral_base_
    );

    if (mapped_base_ == MAP_FAILED) {
        close(fd_);
        fd_ = -1;
        return false;
    }

    mapped_ = true;
    return true;
}

std::optional<uint32_t> BCMPeripheralAccess::read_register(uint32_t offset) {
    if (!mapped_ || !mapped_base_ || mapped_base_ == MAP_FAILED) {
        return std::nullopt;
    }

    if (offset >= mapped_size_) {
        return std::nullopt;
    }

    volatile uint32_t* reg = reinterpret_cast<volatile uint32_t*>(
        static_cast<char*>(mapped_base_) + offset
    );
    return *reg;
}

// ============================================================================
// HardwareVerifier Implementation
// ============================================================================

HardwareVerifier::HardwareVerifier() {
}

std::string HardwareVerifier::read_cpuinfo_field(const std::string& field_name) {
    std::ifstream cpuinfo("/proc/cpuinfo");
    std::string line;

    while (std::getline(cpuinfo, line)) {
        if (line.find(field_name) == 0) {
            size_t colon = line.find(':');
            if (colon != std::string::npos) {
                std::string value = line.substr(colon + 1);
                // Trim whitespace
                value.erase(0, value.find_first_not_of(" \t"));
                value.erase(value.find_last_not_of(" \t\r\n") + 1);
                return value;
            }
        }
    }
    return "";
}

std::string HardwareVerifier::get_cpu_serial() {
    return read_cpuinfo_field("Serial");
}

std::string HardwareVerifier::get_board_revision() {
    return read_cpuinfo_field("Revision");
}

PiModel HardwareVerifier::detect_pi_model(const std::string& revision) {
    if (revision.empty()) {
        return PiModel::UNKNOWN;
    }

    try {
        uint32_t rev_code = std::stoul(revision, nullptr, 16);

        // Check known revision mappings
        for (const auto& mapping : REVISION_MAP) {
            if (mapping.code == rev_code) {
                return mapping.model;
            }
        }

        // Decode new-style revision (bits 23:4)
        if (rev_code & 0x800000) {
            uint32_t type = (rev_code >> 4) & 0xFF;
            switch (type) {
                case 0x00: return PiModel::PI_1_A;
                case 0x01: return PiModel::PI_1_B;
                case 0x02: return PiModel::PI_1_A_PLUS;
                case 0x03: return PiModel::PI_1_B_PLUS;
                case 0x04: return PiModel::PI_2_B;
                case 0x08: return PiModel::PI_3_B;
                case 0x09: return PiModel::PI_ZERO;
                case 0x0a: return PiModel::PI_CM4;
                case 0x0c: return PiModel::PI_ZERO_W;
                case 0x0d: return PiModel::PI_3_B_PLUS;
                case 0x0e: return PiModel::PI_3_A_PLUS;
                case 0x11: return PiModel::PI_4_B;
                case 0x13: return PiModel::PI_400;
                case 0x14: return PiModel::PI_CM4;
                case 0x17: return PiModel::PI_5;
                default: return PiModel::UNKNOWN;
            }
        }
    } catch (...) {
        return PiModel::UNKNOWN;
    }

    return PiModel::UNKNOWN;
}

bool HardwareVerifier::check_hwrng_available() {
    return access("/dev/hwrng", R_OK) == 0;
}

uint32_t HardwareVerifier::detect_soc_id() {
    // Try to read from BCM registers (if accessible)
    if (bcm_access_.open()) {
        // Read SoC identification register (implementation varies by SoC)
        // This is a simplified check - real implementation would probe specific registers
        auto reg = bcm_access_.read_register(0);
        if (reg.has_value()) {
            // Heuristic: non-zero register suggests real hardware
            return reg.value();
        }
    }
    return 0;
}

bool HardwareVerifier::timing_based_vm_detection() {
    // Measure RDTSC variance - VMs have higher jitter
    constexpr int NUM_SAMPLES = 100;
    std::vector<uint64_t> deltas;
    deltas.reserve(NUM_SAMPLES);

    for (int i = 0; i < NUM_SAMPLES; i++) {
        auto t1 = std::chrono::high_resolution_clock::now();
        // Tiny delay
        volatile int x = 0;
        for (int j = 0; j < 10; j++) x++;
        auto t2 = std::chrono::high_resolution_clock::now();

        auto delta = std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count();
        deltas.push_back(delta);
    }

    // Calculate variance
    double mean = 0;
    for (auto d : deltas) mean += d;
    mean /= deltas.size();

    double variance = 0;
    for (auto d : deltas) {
        double diff = d - mean;
        variance += diff * diff;
    }
    variance /= deltas.size();

    // VMs typically have variance > 1000ns^2
    return variance > 1000.0;
}

bool HardwareVerifier::check_hypervisor_hints() {
    // Check /proc/cpuinfo for hypervisor flag
    std::string flags = read_cpuinfo_field("flags");
    if (flags.find("hypervisor") != std::string::npos) {
        return true;
    }

    // Check /sys/hypervisor
    struct stat st;
    if (stat("/sys/hypervisor", &st) == 0) {
        return true;
    }

    return false;
}

bool HardwareVerifier::detect_virtualization() {
    // Multiple heuristics for VM detection
    if (check_hypervisor_hints()) {
        return true;
    }

    if (timing_based_vm_detection()) {
        return true;
    }

    // Check DMI/BIOS strings (x86-centric, but useful)
    std::ifstream sys_vendor("/sys/class/dmi/id/sys_vendor");
    if (sys_vendor.is_open()) {
        std::string vendor;
        std::getline(sys_vendor, vendor);
        if (vendor.find("QEMU") != std::string::npos ||
            vendor.find("VirtualBox") != std::string::npos ||
            vendor.find("VMware") != std::string::npos) {
            return true;
        }
    }

    return false;
}

HardwareInfo HardwareVerifier::verify_hardware() {
    // Return cached result if available
    if (cached_info_.has_value()) {
        return cached_info_.value();
    }

    HardwareInfo info = {};
    info.is_genuine_pi = false;
    info.model = PiModel::UNKNOWN;

    // Get CPU serial
    info.cpu_serial = get_cpu_serial();
    if (info.cpu_serial.empty() || info.cpu_serial == "0000000000000000") {
        info.model = PiModel::NOT_PI;
        info.error_message = "No CPU serial - not a Raspberry Pi";
        cached_info_ = info;
        return info;
    }

    // Get board revision
    info.board_revision = get_board_revision();
    if (info.board_revision.empty()) {
        info.model = PiModel::NOT_PI;
        info.error_message = "No board revision - not a Raspberry Pi";
        cached_info_ = info;
        return info;
    }

    // Detect model
    info.model = detect_pi_model(info.board_revision);
    if (info.model == PiModel::UNKNOWN) {
        info.error_message = "Unknown Pi model from revision: " + info.board_revision;
        cached_info_ = info;
        return info;
    }

    // Check virtualization
    info.virtualized = detect_virtualization();
    if (info.virtualized) {
        info.error_message = "Running in virtualized environment";
        info.is_genuine_pi = false;
        cached_info_ = info;
        return info;
    }

    // Check hwrng
    info.has_hwrng = check_hwrng_available();

    // Detect SoC
    info.soc_id = detect_soc_id();

    // Success: genuine Pi detected
    info.is_genuine_pi = true;
    info.error_message = "";

    cached_info_ = info;
    return info;
}

double HardwareVerifier::calculate_entropy(const uint8_t* data, size_t len) {
    if (len == 0) return 0.0;

    // Count byte frequencies
    uint32_t freq[256] = {0};
    for (size_t i = 0; i < len; i++) {
        freq[data[i]]++;
    }

    // Shannon entropy: -sum(p * log2(p))
    double entropy = 0.0;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            double p = static_cast<double>(freq[i]) / len;
            entropy -= p * std::log2(p);
        }
    }

    return entropy;
}

double HardwareVerifier::chi_square_test(const uint8_t* data, size_t len) {
    if (len == 0) return 0.0;

    uint32_t freq[256] = {0};
    for (size_t i = 0; i < len; i++) {
        freq[data[i]]++;
    }

    double expected = static_cast<double>(len) / 256.0;
    double chi_sq = 0.0;

    for (int i = 0; i < 256; i++) {
        double diff = freq[i] - expected;
        chi_sq += (diff * diff) / expected;
    }

    return chi_sq;
}

EntropyQuality HardwareVerifier::read_entropy(size_t num_bytes, int timeout_ms) {
    EntropyQuality quality = {};
    quality.sufficient = false;
    quality.sample_size = 0;

    if (!check_hwrng_available()) {
        quality.failure_reason = "/dev/hwrng not available";
        return quality;
    }

    int fd = ::open("/dev/hwrng", O_RDONLY);
    if (fd < 0) {
        quality.failure_reason = "Failed to open /dev/hwrng";
        return quality;
    }

    std::vector<uint8_t> buffer(num_bytes);
    ssize_t bytes_read = read(fd, buffer.data(), num_bytes);
    close(fd);

    if (bytes_read <= 0) {
        quality.failure_reason = "Failed to read from /dev/hwrng";
        return quality;
    }

    quality.sample_size = bytes_read;

    // Calculate entropy metrics
    quality.bits_per_byte = calculate_entropy(buffer.data(), bytes_read);
    quality.chi_square = chi_square_test(buffer.data(), bytes_read);

    // Chi-square critical value for 255 df at p=0.05: ~293
    // Acceptable range: ~200-350 (allows some variance)
    quality.uniformity_ok = (quality.chi_square >= 200.0 && quality.chi_square <= 350.0);

    // Good entropy: >7.5 bits/byte, uniform distribution
    quality.sufficient = (quality.bits_per_byte >= 7.5 && quality.uniformity_ok);

    if (!quality.sufficient) {
        if (quality.bits_per_byte < 7.5) {
            quality.failure_reason = "Low entropy: " + std::to_string(quality.bits_per_byte) + " bits/byte";
        } else {
            quality.failure_reason = "Non-uniform distribution (chi-square: " + std::to_string(quality.chi_square) + ")";
        }
    }

    return quality;
}

bool HardwareVerifier::is_mining_capable() {
    auto info = verify_hardware();
    return info.is_genuine_pi && !info.virtualized;
}

std::string HardwareVerifier::model_name(PiModel model) {
    switch (model) {
        case PiModel::PI_ZERO: return "Raspberry Pi Zero";
        case PiModel::PI_ZERO_W: return "Raspberry Pi Zero W";
        case PiModel::PI_ZERO_2W: return "Raspberry Pi Zero 2 W";
        case PiModel::PI_1_A: return "Raspberry Pi 1 Model A";
        case PiModel::PI_1_B: return "Raspberry Pi 1 Model B";
        case PiModel::PI_1_A_PLUS: return "Raspberry Pi 1 Model A+";
        case PiModel::PI_1_B_PLUS: return "Raspberry Pi 1 Model B+";
        case PiModel::PI_2_B: return "Raspberry Pi 2 Model B";
        case PiModel::PI_3_B: return "Raspberry Pi 3 Model B";
        case PiModel::PI_3_B_PLUS: return "Raspberry Pi 3 Model B+";
        case PiModel::PI_3_A_PLUS: return "Raspberry Pi 3 Model A+";
        case PiModel::PI_4_B: return "Raspberry Pi 4 Model B";
        case PiModel::PI_400: return "Raspberry Pi 400";
        case PiModel::PI_CM4: return "Raspberry Pi Compute Module 4";
        case PiModel::PI_5: return "Raspberry Pi 5";
        case PiModel::PI_CM5: return "Raspberry Pi Compute Module 5";
        case PiModel::NOT_PI: return "Not a Raspberry Pi";
        case PiModel::UNKNOWN:
        default: return "Unknown";
    }
}

bool HardwareVerifier::selftest() {
    HardwareVerifier verifier;

    // Test 1: Can read cpuinfo fields
    std::string serial = verifier.get_cpu_serial();
    std::string revision = verifier.get_board_revision();

    // Test 2: Hardware verification runs without crashing
    HardwareInfo info = verifier.verify_hardware();
    (void)info; // Suppress unused warning

    // Test 3: Entropy reading (may fail on non-Pi, that's ok)
    EntropyQuality quality = verifier.read_entropy(16, 100);
    (void)quality;

    // Test 4: Model name function
    std::string name = model_name(PiModel::PI_5);
    if (name != "Raspberry Pi 5") {
        return false;
    }

    return true;
}

} // namespace hw
} // namespace pisecure
