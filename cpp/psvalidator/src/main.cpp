#include "cli.hpp"
#include "validator.hpp"
#include "monitor_tui.hpp"
#include <iostream>
#include <csignal>
#include <atomic>
#include <memory>
#include <thread>
#include <chrono>

std::atomic<bool> g_shutdown_requested{false};
std::unique_ptr<psvalidator::Validator> g_validator;

void signal_handler(int signal)
{
    if (signal == SIGINT || signal == SIGTERM)
    {
        std::cout << "\nShutdown requested...\n";
        g_shutdown_requested = true;
        if (g_validator)
        {
            g_validator->stop();
        }
    }
}

int main(int argc, char **argv)
{
    // Parse command-line arguments
    psvalidator::Config config;
    if (!psvalidator::CLI::parse_args(argc, argv, config))
    {
        return 1;
    }

    // Install signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    // Print configuration
    if (config.verbose || !config.monitor_tui)
    {
        psvalidator::CLI::print_version();
        std::cout << "\nStarting validator...\n";
        std::cout << "  Wallet: " << config.wallet_address << "\n";
        std::cout << "  Daemon: " << config.daemon_url << "\n";
        std::cout << "  Network: " << (config.testnet ? "testnet" : "mainnet") << "\n";
        std::cout << "  Mode: " << (config.daemon ? "daemon" : (config.monitor_tui ? "TUI" : "CLI")) << "\n";
        std::cout << "\n";
    }

    // Create validator instance
    g_validator = std::make_unique<psvalidator::Validator>(config);

    // Start validation
    if (!g_validator->start())
    {
        std::cerr << "Failed to start validator\n";
        return 1;
    }

    std::cout << "Validation started\n";
    std::cout << "Platform: Universal (Works on any system - No Pi hardware required)\n";
    std::cout << "Earning: 1% of block rewards distributed among all validators\n\n";

    // Run TUI or simple loop
    if (config.monitor_tui && !config.daemon)
    {
        try
        {
            psvalidator::MonitorTUI tui(*g_validator);
            tui.run(); // Blocking
        }
        catch (const std::exception &e)
        {
            std::cerr << "TUI error: " << e.what() << "\n";
            std::cerr << "Falling back to daemon mode...\n";
            config.daemon = true;
        }
    }

    if (config.daemon || !config.monitor_tui)
    {
        // Simple status output loop
        while (!g_shutdown_requested && g_validator->is_running())
        {
            std::this_thread::sleep_for(std::chrono::seconds(10));

            const auto &stats = g_validator->stats();

            if (!config.daemon)
            {
                std::cout << "[" << stats.uptime_seconds << "s] "
                          << "Height: " << stats.current_height << " | "
                          << "Validated: " << stats.blocks_validated << " blocks, "
                          << stats.transactions_validated << " txs | "
                          << "Rewards: " << std::fixed << std::setprecision(4)
                          << stats.total_rewards_earned << " tokens\n";
            }
        }
    }

    // Cleanup
    g_validator->stop();
    std::cout << "\nValidation stopped. Final statistics:\n";

    const auto &stats = g_validator->stats();
    std::cout << "  Blocks validated: " << stats.blocks_validated << "\n";
    std::cout << "  Transactions validated: " << stats.transactions_validated << "\n";
    std::cout << "  Invalid blocks detected: " << stats.invalid_blocks_detected << "\n";
    std::cout << "  Invalid transactions detected: " << stats.invalid_transactions_detected << "\n";
    std::cout << "  Total rewards earned: " << std::fixed << std::setprecision(4)
              << stats.total_rewards_earned << " tokens\n";
    std::cout << "  Uptime: " << stats.uptime_seconds << " seconds\n";

    return 0;
}
