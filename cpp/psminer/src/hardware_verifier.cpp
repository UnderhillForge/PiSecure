#include "hardware_verifier.hpp"
#include <fstream>
#include <sstream>
#include <regex>
#include <ctime>
#include <fcntl.h>
#include <unistd.h>

namespace psminer
{

    HardwareVerifier::HardwareVerifier()
    {
        read_cpuinfo();
    }

    bool HardwareVerifier::verify()
    {
        if (verified_)
            return true;

        // Multiple verification checks
        bool cpuinfo_ok = read_cpuinfo();
        bool bcm_ok = verify_bcm_chip();
        bool rng_ok = verify_hardware_rng();
        bool vc_ok = verify_videocore();

        // Require at least CPU serial + one other check
        verified_ = cpuinfo_ok && !serial_.empty() && (bcm_ok || rng_ok || vc_ok);

        return verified_;
    }

    bool HardwareVerifier::read_cpuinfo()
    {
        std::ifstream cpuinfo("/proc/cpuinfo");
        if (!cpuinfo.is_open())
            return false;

        std::string line;
        std::regex serial_regex(R"(Serial\s*:\s*([0-9a-fA-F]+))");
        std::regex hardware_regex(R"(Hardware\s*:\s*(.+))");
        std::regex revision_regex(R"(Revision\s*:\s*([0-9a-fA-F]+))");
        std::smatch match;

        while (std::getline(cpuinfo, line))
        {
            if (std::regex_search(line, match, serial_regex))
            {
                serial_ = match[1].str();
            }
            else if (std::regex_search(line, match, hardware_regex))
            {
                std::string hw = match[1].str();
                if (hw.find("BCM") != std::string::npos)
                {
                    model_ = hw;
                }
            }
            else if (std::regex_search(line, match, revision_regex))
            {
                revision_ = std::stoul(match[1].str(), nullptr, 16);
            }
        }

        return !serial_.empty() && !model_.empty();
    }

    bool HardwareVerifier::verify_bcm_chip()
    {
        // Check for BCM GPIO memory-mapped registers
        const char *gpio_paths[] = {
            "/dev/gpiomem",
            "/dev/gpiochip0",
            "/sys/class/gpio"};

        for (const char *path : gpio_paths)
        {
            if (access(path, F_OK) == 0)
            {
                return true;
            }
        }

        return false;
    }

    bool HardwareVerifier::verify_hardware_rng()
    {
        int fd = open("/dev/hwrng", O_RDONLY);
        if (fd < 0)
            return false;

        uint8_t test_buf[32];
        ssize_t bytes_read = read(fd, test_buf, sizeof(test_buf));
        close(fd);

        if (bytes_read != sizeof(test_buf))
            return false;

        // Basic entropy check: not all zeros
        bool has_entropy = false;
        for (size_t i = 0; i < sizeof(test_buf); i++)
        {
            if (test_buf[i] != 0)
            {
                has_entropy = true;
                break;
            }
        }

        return has_entropy;
    }

    bool HardwareVerifier::verify_videocore()
    {
        // Check for VideoCore mailbox interface
        return access("/dev/vcio", F_OK) == 0 ||
               access("/dev/vchiq", F_OK) == 0;
    }

    int HardwareVerifier::get_cpu_temp_c() const
    {
        std::ifstream temp_file("/sys/class/thermal/thermal_zone0/temp");
        if (!temp_file.is_open())
            return 0;

        int temp_millidegrees = 0;
        temp_file >> temp_millidegrees;
        return temp_millidegrees / 1000;
    }

    int HardwareVerifier::get_gpu_temp_c() const
    {
        // Read from VideoCore mailbox (implementation in videocore_mailbox.cpp)
        // For now, use CPU temp as fallback
        return get_cpu_temp_c();
    }

    int HardwareVerifier::get_cpu_freq_mhz() const
    {
        std::ifstream freq_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq");
        if (!freq_file.is_open())
            return 0;

        int freq_khz = 0;
        freq_file >> freq_khz;
        return freq_khz / 1000;
    }

    int HardwareVerifier::get_throttle_status() const
    {
        // Read throttle status from VideoCore
        // Bit 0: under-voltage
        // Bit 1: arm frequency capped
        // Bit 2: currently throttled
        // Bit 16: under-voltage has occurred
        // Bit 17: arm frequency capping has occurred
        // Bit 18: throttling has occurred
        return 0; // TODO: implement via videocore mailbox
    }

    HardwareVerifier::Fingerprint HardwareVerifier::get_fingerprint() const
    {
        Fingerprint fp;
        fp.serial = serial_;
        fp.model = model_;
        fp.revision = revision_;
        fp.timestamp = static_cast<uint64_t>(std::time(nullptr));

        // Read entropy from hardware RNG
        int fd = open("/dev/hwrng", O_RDONLY);
        if (fd >= 0)
        {
            read(fd, fp.entropy, sizeof(fp.entropy));
            close(fd);
        }
        else
        {
            // Fallback: zero entropy (will be rejected by strict verification)
            std::memset(fp.entropy, 0, sizeof(fp.entropy));
        }

        return fp;
    }

} // namespace psminer
