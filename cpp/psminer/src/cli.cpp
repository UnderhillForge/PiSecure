#include "cli.hpp"
#include "pins_resolver.hpp"
#include <iostream>
#include <cstring>
#include <cstdlib>

namespace psminer
{

    void print_version()
    {
        std::cout << "psminer v0.1.0\n"
                  << "PiSecure Hardware-Verified Mining Client for Raspberry Pi\n"
                  << "Built: " << __DATE__ << " " << __TIME__ << "\n"
                  << "Copyright (c) 2026 PiSecure Project\n";
    }

    void print_help(const char *program_name)
    {
        std::cout << R"(Usage: )" << program_name << R"( [OPTIONS]

PiSecure hardware-verified mining client for Raspberry Pi.

Required:
  -w, --wallet NAME_OR_ADDRESS
                             Wallet address or PiNS name (e.g., myname.pi)
                             PiNS names are resolved via blockchain

Optional:
  -u, --url URL              Blockchain node URL (default: http://localhost:3142)
  -d, --data-dir PATH        Data directory (default: /var/lib/pisecure)
  -t, --threads N            Number of mining threads (default: 1)
      --difficulty N         Target difficulty (default: 146)
      --testnet              Use testnet instead of mainnet
  
Hardware Tuning:
      --rounds N             PiHash computation rounds (default: 8)
      --memory MB            PiHash memory buffer in MB (default: 256)
      --npu                  Enable NPU acceleration (Pi 6+)

Display:
      --no-tui               Disable TUI monitor (use plain output)
  -v, --verbose              Verbose output
      --daemon               Run as background daemon

Other:
  -h, --help                 Show this help message
      --version              Show version information

Examples:
  # Mine using wallet address
  psminer -w 0x1234567890abcdef...

  # Mine using PiNS name (automatically resolved)
  psminer -w myname.pi

  # Multi-threaded mining
  psminer -w myname.pi -t 4

  # Testnet mining
  psminer -w myname.pi --testnet

  # High-performance mining (Pi 5)
  psminer -w myname.pi -t 4 --rounds 8 --memory 512

For more information, visit: https://github.com/UnderhillForge/PiSecure
)";
    }

    bool parse_args(int argc, char **argv, Config &config)
    {
        bool wallet_set = false;

        for (int i = 1; i < argc; i++)
        {
            std::string arg = argv[i];

            if (arg == "-h" || arg == "--help")
            {
                print_help(argv[0]);
                return false;
            }
            else if (arg == "--version")
            {
                print_version();
                return false;
            }
            else if (arg == "-w" || arg == "--wallet")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --wallet requires an address\n";
                    return false;
                }
                config.wallet_address = argv[++i];
                wallet_set = true;
            }
            else if (arg == "-u" || arg == "--url")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --url requires a URL\n";
                    return false;
                }
                config.blockchain_url = argv[++i];
            }
            else if (arg == "-d" || arg == "--data-dir")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --data-dir requires a path\n";
                    return false;
                }
                config.data_dir = argv[++i];
            }
            else if (arg == "-t" || arg == "--threads")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --threads requires a number\n";
                    return false;
                }
                config.threads = std::atoi(argv[++i]);
                if (config.threads == 0)
                    config.threads = 1;
            }
            else if (arg == "--difficulty")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --difficulty requires a number\n";
                    return false;
                }
                config.difficulty = std::atoi(argv[++i]);
            }
            else if (arg == "--rounds")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --rounds requires a number\n";
                    return false;
                }
                config.pihash_rounds = std::atoi(argv[++i]);
            }
            else if (arg == "--memory")
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Error: --memory requires a number (MB)\n";
                    return false;
                }
                config.pihash_memory_mb = std::atoi(argv[++i]);
            }
            else if (arg == "--npu")
            {
                config.npu_enabled = true;
            }
            else if (arg == "--testnet")
            {
                config.testnet = true;
            }
            else if (arg == "--no-tui")
            {
                config.monitor_tui = false;
            }
            else if (arg == "-v" || arg == "--verbose")
            {
                config.verbose = true;
            }
            else if (arg == "--daemon")
            {
                config.daemon = true;
                config.monitor_tui = false; // Daemon mode disables TUI
            }
            else
            {
                std::cerr << "Error: Unknown option '" << arg << "'\n";
                std::cerr << "Use --help for usage information\n";
                return false;
            }
        }

        // Validate required options
        if (!wallet_set)
        {
            std::cerr << "Error: Wallet address is required\n";
            std::cerr << "Use: " << argv[0] << " -w YOUR_WALLET_ADDRESS\n";
            return false;
        }

        // Handle PiNS name resolution
        config.wallet_name = config.wallet_address; // Store original input
        if (PiNSResolver::is_pins_name(config.wallet_address))
        {
            if (config.verbose)
            {
                std::cout << "Resolving PiNS name: " << config.wallet_address << "\n";
            }

            PiNSResolver resolver(config.blockchain_url);
            auto resolved = resolver.resolve(config.wallet_address);

            if (resolved)
            {
                config.resolved_address = resolved.value();
                config.wallet_address = config.resolved_address;
                if (config.verbose)
                {
                    std::cout << "Resolved to: " << config.resolved_address << "\n";
                }
            }
            else
            {
                std::cerr << "Error: Could not resolve PiNS name '"
                          << config.wallet_name << "'\n";
                std::cerr << "Make sure:\n";
                std::cerr << "  1. The name is registered on the blockchain\n";
                std::cerr << "  2. The blockchain node URL is accessible\n";
                std::cerr << "  3. PiNS resolution is enabled on the network\n";
                return false;
            }
        }
        else if (!PiNSResolver::is_wallet_address(config.wallet_address))
        {
            std::cerr << "Error: Invalid wallet address or PiNS name: "
                      << config.wallet_address << "\n";
            std::cerr << "Expected format:\n";
            std::cerr << "  - Wallet address: 0x followed by 40 hex characters\n";
            std::cerr << "  - PiNS name: alphanumeric with dots and hyphens (e.g., myname.pi)\n";
            return false;
        }

        // Validate configuration
        if (config.threads > 16)
        {
            std::cerr << "Warning: High thread count (" << config.threads
                      << ") may reduce efficiency\n";
        }

        if (config.pihash_memory_mb < 1 || config.pihash_memory_mb > 1024)
        {
            std::cerr << "Error: PiHash memory must be between 1-1024 MB\n";
            return false;
        }

        return true;
    }

} // namespace psminer
