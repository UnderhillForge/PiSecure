#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace psminer
{

    // CLI Configuration
    struct Config
    {
        std::string wallet_address;
        std::string wallet_name;      // Original name or address provided by user
        std::string resolved_address; // Final address (resolved from PiNS if needed)
        std::string blockchain_url = "http://localhost:3142";
        std::string data_dir = "/var/lib/pisecure";

        uint32_t threads = 1;
        uint32_t difficulty = 146;
        uint32_t max_nonce = 0xFFFFFFFF;

        bool testnet = false;
        bool monitor_tui = true;
        bool verbose = false;
        bool daemon = false;

        // Hardware tuning
        uint32_t pihash_rounds = 8;
        uint32_t pihash_memory_mb = 256;
        bool npu_enabled = false;
    };

    // Parse command-line arguments
    bool parse_args(int argc, char **argv, Config &config);

    // Print help message
    void print_help(const char *program_name);

    // Print version information
    void print_version();

} // namespace psminer
