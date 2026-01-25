#pragma once

#include <string>
#include <cstdint>

namespace psminer {

// Hardware verification for Raspberry Pi
class HardwareVerifier {
public:
    HardwareVerifier();
    
    // Verify this is genuine Raspberry Pi hardware
    bool verify();
    
    // Get hardware information
    std::string get_model() const { return model_; }
    std::string get_serial() const { return serial_; }
    uint32_t get_revision() const { return revision_; }
    
    // Hardware monitoring
    int get_cpu_temp_c() const;
    int get_gpu_temp_c() const;
    int get_cpu_freq_mhz() const;
    int get_throttle_status() const;
    
    // Hardware fingerprint for PiHash
    struct Fingerprint {
        std::string serial;
        std::string model;
        uint32_t revision;
        uint64_t timestamp;
        uint8_t entropy[32];  // From hardware RNG
    };
    
    Fingerprint get_fingerprint() const;
    
private:
    bool read_cpuinfo();
    bool verify_bcm_chip();
    bool verify_hardware_rng();
    bool verify_videocore();
    
    std::string model_;
    std::string serial_;
    uint32_t revision_ = 0;
    bool verified_ = false;
};

} // namespace psminer
