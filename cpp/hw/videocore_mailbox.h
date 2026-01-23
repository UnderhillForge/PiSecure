#pragma once

#include <cstdint>
#include <vector>
#include <string>

namespace pisecure {
namespace hw {

/**
 * VideoCore Mailbox Property Interface for Raspberry Pi Hardware Verification
 * 
 * Direct communication with GPU firmware for strong anti-emulation checks.
 * Queries the closed-source VideoCore firmware which is difficult to emulate.
 */

class VideoCoreMailbox {
public:
    /**
     * Initialize mailbox interface (/dev/mem access)
     * Returns false if /dev/mem unavailable (non-Pi or permission denied)
     */
    bool initialize();
    
    /**
     * Get board serial number from VideoCore (OTP-stored unique ID)
     * Returns empty string if unavailable
     */
    std::string get_board_serial();
    
    /**
     * Get GPU temperature in Celsius
     * Returns 0 if unavailable (indicates emulation or missing sensor)
     */
    uint32_t get_gpu_temperature();
    
    /**
     * Get ARM clock rate in Hz
     * Returns 0 if unavailable
     */
    uint32_t get_arm_clock_rate();
    
    /**
     * Get throttling status (bitfield indicating under-voltage, throttling, etc.)
     * Returns 0 if unavailable
     */
    uint32_t get_throttling_status();
    
    /**
     * Get firmware revision (unique per firmware build)
     * Returns empty string if unavailable
     */
    std::string get_firmware_revision();
    
    /**
     * Clean up resources
     */
    void cleanup();
    
private:
    volatile uint32_t* mailbox_ptr_ = nullptr;
    int devmem_fd_ = -1;
    
    /**
     * Send mailbox query and wait for response
     * @param buffer Aligned 16-byte buffer with property tags
     * @return Response code (0x80000000 = success)
     */
    uint32_t mailbox_send(uint32_t* buffer);
    
    /**
     * Wait for mailbox status
     * @param ready_mask Bitmask to check (0x40000000 for empty, 0x80000000 for full)
     */
    void mailbox_wait(uint32_t ready_mask);
};

/**
 * Hardware verification result combining VideoCore mailbox data
 */
struct VideoCoreVerification {
    bool is_valid = false;
    bool is_pi_hardware = false;
    std::string board_serial;
    uint32_t gpu_temperature = 0;
    uint32_t arm_clock_rate = 0;
    uint32_t throttling_status = 0;
    std::string firmware_revision;
    std::string error_message;
};

/**
 * Perform comprehensive hardware verification using VideoCore mailbox
 * @return Verification result with detailed hardware data
 */
VideoCoreVerification verify_with_videocore();

} // namespace hw
} // namespace pisecure
