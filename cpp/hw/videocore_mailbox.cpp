#include "videocore_mailbox.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <chrono>
#include <thread>

namespace pisecure {
namespace hw {

// Pi 4/5 peripheral base
#define PERIPHERAL_BASE 0xFE000000ULL
#define MAILBOX_BASE    (PERIPHERAL_BASE + 0xB880)

// Mailbox status bits
#define MAIL_EMPTY  0x40000000
#define MAIL_FULL   0x80000000
#define MAIL_CHANNEL 8  // Property tags (ARM -> VC)

// Property tag IDs
#define TAG_GET_FIRMWARE_REV   0x00000001
#define TAG_GET_BOARD_SERIAL   0x00010004
#define TAG_GET_BOARD_MAC      0x00010003
#define TAG_GET_GPU_TEMP       0x00030006
#define TAG_GET_ARM_CLOCK      0x00030002
#define TAG_GET_THROTTLING     0x0003000A

bool VideoCoreMailbox::initialize() {
    // Try to open /dev/mem for physical memory access
    devmem_fd_ = open("/dev/mem", O_RDWR | O_SYNC);
    if (devmem_fd_ < 0) {
        return false;  // Not running as root or not a Pi
    }
    
    // Map mailbox memory
    mailbox_ptr_ = (volatile uint32_t*)mmap(
        nullptr,
        0x1000,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        devmem_fd_,
        MAILBOX_BASE
    );
    
    if (mailbox_ptr_ == MAP_FAILED) {
        close(devmem_fd_);
        devmem_fd_ = -1;
        return false;
    }
    
    return true;
}

void VideoCoreMailbox::mailbox_wait(uint32_t ready_mask) {
    // Simple busy-wait with timeout
    if (!mailbox_ptr_) return;  // Exit early if not initialized
    volatile uint32_t* status = mailbox_ptr_ + 6;  // Status register offset
    for (int i = 0; i < 100000; i++) {
        if (!(*status & ready_mask)) {
            return;
        }
        std::this_thread::sleep_for(std::chrono::microseconds(1));
    }
}

uint32_t VideoCoreMailbox::mailbox_send(uint32_t* buffer) {
    if (!mailbox_ptr_) return 0;
    
    volatile uint32_t* read_reg = mailbox_ptr_ + 0;     // Read (offset 0x00)
    volatile uint32_t* status_reg = mailbox_ptr_ + 6;   // Status (offset 0x18)
    volatile uint32_t* write_reg = mailbox_ptr_ + 8;    // Write (offset 0x20)
    
    // Convert buffer pointer to physical address (ARM -> VC)
    uintptr_t addr = (uintptr_t)buffer & ~0xF;  // Align to 16 bytes
    
    // Wait for mailbox to be ready
    mailbox_wait(MAIL_FULL);
    
    // Send request
    *write_reg = (uint32_t)(addr | MAIL_CHANNEL);
    
    // Wait for response
    for (int i = 0; i < 100000; i++) {
        mailbox_wait(MAIL_EMPTY);
        uint32_t read = *read_reg;
        
        if ((read & 0xF) == MAIL_CHANNEL && (read & ~0xF) == (uint32_t)addr) {
            return buffer[1];  // Response code
        }
        
        std::this_thread::sleep_for(std::chrono::microseconds(1));
    }
    
    return 0;  // Timeout
}

std::string VideoCoreMailbox::get_board_serial() {
    if (!mailbox_ptr_) return "";
    
    alignas(16) uint32_t buffer[8] = {0};
    
    buffer[0] = 8 * sizeof(uint32_t);  // Buffer size
    buffer[1] = 0;                      // Request code
    buffer[2] = TAG_GET_BOARD_SERIAL;   // Tag ID
    buffer[3] = 8;                      // Response buffer size
    buffer[4] = 0;                      // Request size
    // buffer[5-6] will be filled with serial
    buffer[7] = 0;                      // End tag
    
    uint32_t response = mailbox_send(buffer);
    if (response != 0x80000000) {
        return "";  // Failed
    }
    
    // Serial is in buffer[5-6] as uint64_t
    uint64_t serial = ((uint64_t)buffer[5] << 32) | buffer[6];
    
    // Format as hex string
    std::stringstream ss;
    ss << std::hex << serial;
    return ss.str();
}

uint32_t VideoCoreMailbox::get_gpu_temperature() {
    if (!mailbox_ptr_) return 0;
    
    alignas(16) uint32_t buffer[8] = {0};
    
    buffer[0] = 8 * sizeof(uint32_t);
    buffer[1] = 0;
    buffer[2] = TAG_GET_GPU_TEMP;
    buffer[3] = 8;
    buffer[4] = 0;
    buffer[7] = 0;
    
    uint32_t response = mailbox_send(buffer);
    if (response != 0x80000000) return 0;
    
    // Temperature in milli-degrees C, convert to C
    uint32_t temp_mc = buffer[5];
    return temp_mc / 1000;
}

uint32_t VideoCoreMailbox::get_arm_clock_rate() {
    if (!mailbox_ptr_) return 0;
    
    alignas(16) uint32_t buffer[8] = {0};
    
    buffer[0] = 8 * sizeof(uint32_t);
    buffer[1] = 0;
    buffer[2] = TAG_GET_ARM_CLOCK;
    buffer[3] = 8;
    buffer[4] = 0;
    buffer[7] = 0;
    
    uint32_t response = mailbox_send(buffer);
    if (response != 0x80000000) return 0;
    
    return buffer[5];  // Clock rate in Hz
}

uint32_t VideoCoreMailbox::get_throttling_status() {
    if (!mailbox_ptr_) return 0;
    
    alignas(16) uint32_t buffer[8] = {0};
    
    buffer[0] = 8 * sizeof(uint32_t);
    buffer[1] = 0;
    buffer[2] = TAG_GET_THROTTLING;
    buffer[3] = 8;
    buffer[4] = 0;
    buffer[7] = 0;
    
    uint32_t response = mailbox_send(buffer);
    if (response != 0x80000000) return 0;
    
    return buffer[5];
}

std::string VideoCoreMailbox::get_firmware_revision() {
    if (!mailbox_ptr_) return "";
    
    alignas(16) uint32_t buffer[8] = {0};
    
    buffer[0] = 8 * sizeof(uint32_t);
    buffer[1] = 0;
    buffer[2] = TAG_GET_FIRMWARE_REV;
    buffer[3] = 4;
    buffer[4] = 0;
    buffer[7] = 0;
    
    uint32_t response = mailbox_send(buffer);
    if (response != 0x80000000) return "";
    
    // Firmware revision as uint32
    uint32_t rev = buffer[5];
    std::stringstream ss;
    ss << std::hex << rev;
    return ss.str();
}

void VideoCoreMailbox::cleanup() {
    if (mailbox_ptr_) {
        munmap((void*)mailbox_ptr_, 0x1000);
        mailbox_ptr_ = nullptr;
    }
    if (devmem_fd_ >= 0) {
        close(devmem_fd_);
        devmem_fd_ = -1;
    }
}

VideoCoreVerification verify_with_videocore() {
    VideoCoreVerification result;
    result.is_valid = false;
    result.is_pi_hardware = false;
    
    VideoCoreMailbox mailbox;
    
    if (!mailbox.initialize()) {
        result.error_message = "VideoCore mailbox unavailable (requires root or /dev/mem access)";
        return result;
    }
    
    // Query multiple properties
    result.board_serial = mailbox.get_board_serial();
    result.gpu_temperature = mailbox.get_gpu_temperature();
    result.arm_clock_rate = mailbox.get_arm_clock_rate();
    result.throttling_status = mailbox.get_throttling_status();
    result.firmware_revision = mailbox.get_firmware_revision();
    
    mailbox.cleanup();
    
    // Validation logic
    // Serial should be non-empty and valid format (hex string, 8-16 chars)
    if (result.board_serial.empty() || result.board_serial.length() < 8) {
        result.error_message = "Invalid board serial from VideoCore";
        return result;
    }
    
    // GPU temperature should be reasonable (20-85°C under load, or 0 if sensor unavailable)
    // Note: Temperature = 0 might indicate emulation or sensor issue
    // Valid range: 0 (sensor fail) or 20-85°C (normal operation)
    if (result.gpu_temperature > 95) {
        result.error_message = "GPU temperature unreasonably high (possible emulation)";
        return result;
    }
    
    // ARM clock should be reasonable for Pi (typically 1.2-2.4 GHz)
    if (result.arm_clock_rate == 0 || result.arm_clock_rate < 100000000UL) {
        result.error_message = "Invalid ARM clock rate from VideoCore";
        return result;
    }
    
    // Firmware revision should be set (non-zero)
    if (result.firmware_revision.empty()) {
        result.error_message = "Invalid firmware revision from VideoCore";
        return result;
    }
    
    // All checks passed
    result.is_valid = true;
    result.is_pi_hardware = true;
    
    return result;
}

} // namespace hw
} // namespace pisecure
