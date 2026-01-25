#include "cli.hpp"
#include <iostream>
#include <iomanip>
#include <cstring>

namespace psvalidator
{
    void CLI::print_version()
    {
        std::cout << "psvalidator v1.0.0 - PiSecure Universal Validator\n";
        std::cout << "Platform-agnostic blockchain validator for earning rewards\n";
    }

    void CLI::print_banner()
    {
        std::cout << R"(
╔═══════════════════════════════════════════════════════════╗
║                     PSVALIDATOR                           ║
║           Platform-Agnostic Blockchain Validator          ║
╚═══════════════════════════════════════════════════════════╝
)" << "\n";
    }

    void CLI::print_validation_info()
    {
        std::cout << R"(
UNIVERSAL VALIDATION (No Pi Hardware Required)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

psvalidator validates blocks and transactions on ANY platform:
  • Works on Mac, Windows, Linux, Raspberry Pi
  • Validates proof-of-work (zero bit counting only)
  • Validates transaction signatures and structure
  • Earns 1% of block rewards for validation
  • No hardware verification required

Mining vs Validation:
  • Mining: Requires Raspberry Pi hardware (PiHash algorithm)
  • Validation: Works on any platform (SHA256 + XOR only)
  
Earn rewards by helping secure the network through validation!
)" << "\n";
    }

    void CLI::print_help(const char *program_name)
    {
        print_banner();
        print_validation_info();

        std::cout << "USAGE:\n";
        std::cout << "  " << program_name << " [OPTIONS]\n\n";

        std::cout << "OPTIONS:\n";
        std::cout << "  --wallet ADDRESS       Wallet address for validator rewards (required)\n";
        std::cout << "  --daemon-url URL       pisecured WebSocket URL (default: ws://127.0.0.1:3142)\n";
        std::cout << "  --testnet              Connect to testnet instead of mainnet\n";
        std::cout << "  --daemon               Run in background daemon mode (no TUI)\n";
        std::cout << "  --no-tui               Disable TUI, use simple CLI output\n";
        std::cout << "  --threads N            Number of validation threads (default: 4)\n";
        std::cout << "  --poll-interval MS     Polling interval in milliseconds (default: 1000)\n";
        std::cout << "  --verbose              Enable verbose logging\n";
        std::cout << "  --version              Show version information\n";
        std::cout << "  --help                 Show this help message\n\n";

        std::cout << "EXAMPLES:\n";
        std::cout << "  # Start with TUI (default)\n";
        std::cout << "  " << program_name << " --wallet pisecure_wallet_abc123\n\n";

        std::cout << "  # Run in background daemon mode\n";
        std::cout << "  " << program_name << " --wallet pisecure_wallet_abc123 --daemon\n\n";

        std::cout << "  # Connect to remote daemon\n";
        std::cout << "  " << program_name << " --wallet pisecure_wallet_abc123 --daemon-url ws://192.168.1.100:3142\n\n";

        std::cout << "  # Testnet validation\n";
        std::cout << "  " << program_name << " --wallet pisecure_wallet_test123 --testnet\n\n";

        std::cout << "MODES:\n";
        std::cout << "  1. TUI Mode (default): Interactive terminal UI with real-time stats\n";
        std::cout << "  2. CLI Mode (--no-tui): Simple text output with periodic updates\n";
        std::cout << "  3. Daemon Mode (--daemon): Background process, logs to stdout\n\n";

        std::cout << "REWARDS:\n";
        std::cout << "  Validators earn 1% of each block reward distributed among all active validators.\n";
        std::cout << "  Rewards accumulate in the validator bucket and can be swept to your wallet.\n\n";

        std::cout << "For more information, visit: https://github.com/UnderhillForge/PiSecure\n";
    }

    bool CLI::parse_args(int argc, char **argv, Config &config)
    {
        for (int i = 1; i < argc; i++)
        {
            std::string arg = argv[i];

            if (arg == "--help" || arg == "-h")
            {
                print_help(argv[0]);
                return false;
            }
            else if (arg == "--version")
            {
                print_version();
                return false;
            }
            else if (arg == "--wallet" && i + 1 < argc)
            {
                config.wallet_address = argv[++i];
            }
            else if (arg == "--daemon-url" && i + 1 < argc)
            {
                config.daemon_url = argv[++i];
            }
            else if (arg == "--testnet")
            {
                config.testnet = true;
            }
            else if (arg == "--daemon")
            {
                config.daemon = true;
                config.monitor_tui = false;
            }
            else if (arg == "--no-tui")
            {
                config.monitor_tui = false;
            }
            else if (arg == "--threads" && i + 1 < argc)
            {
                config.validation_threads = std::stoi(argv[++i]);
            }
            else if (arg == "--poll-interval" && i + 1 < argc)
            {
                config.poll_interval_ms = std::stoi(argv[++i]);
            }
            else if (arg == "--verbose" || arg == "-v")
            {
                config.verbose = true;
            }
            else
            {
                std::cerr << "Unknown option: " << arg << "\n";
                std::cerr << "Use --help for usage information\n";
                return false;
            }
        }

        // Validate required arguments
        if (config.wallet_address.empty())
        {
            std::cerr << "Error: --wallet ADDRESS is required\n";
            std::cerr << "Use --help for usage information\n";
            return false;
        }

        return true;
    }

    int CLI::execute_command(const std::string &command, const Config &config)
    {
        // For now, psvalidator only has the main validation mode
        // Future: could add commands like "status", "rewards", etc.
        return 0;
    }

    void CLI::print_status(const Config &config)
    {
        std::cout << "Validator Configuration:\n";
        std::cout << "  Wallet: " << config.wallet_address << "\n";
        std::cout << "  Daemon: " << config.daemon_url << "\n";
        std::cout << "  Network: " << (config.testnet ? "testnet" : "mainnet") << "\n";
        std::cout << "  Threads: " << config.validation_threads << "\n";
        std::cout << "  Mode: " << (config.daemon ? "daemon" : (config.monitor_tui ? "TUI" : "CLI")) << "\n";
    }

} // namespace psvalidator
