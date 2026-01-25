#include "cli.hpp"
#include "miner.hpp"
#include "monitor_tui.hpp"
#include "hardware_verifier.hpp"
#include <iostream>
#include <csignal>
#include <atomic>
#include <memory>
#include <thread>
#include <chrono>

std::atomic<bool> g_shutdown_requested{false};
std::unique_ptr<psminer::Miner> g_miner;

void signal_handler(int signal)
{
    if (signal == SIGINT || signal == SIGTERM)
    {
        std::cout << "\nShutdown requested...\n";
        g_shutdown_requested = true;
        if (g_miner)
        {
            g_miner->stop();
        }
    }
}

int main(int argc, char **argv)
{
    // Parse command-line arguments
    psminer::Config config;
    if (!psminer::parse_args(argc, argv, config))
    {
        return 1;
    }

    // Verify hardware (Raspberry Pi required)
    psminer::HardwareVerifier hw_verifier;
    if (!hw_verifier.verify())
    {
        std::cerr << "ERROR: PiSecure mining requires genuine Raspberry Pi hardware\n";
        std::cerr << "Detected: " << hw_verifier.get_model() << "\n";
        std::cerr << "\nFor validation on non-Pi platforms, use 'psvalid' instead.\n";
        return 1;
    }

    if (config.verbose)
    {
        std::cout << "Hardware verified: " << hw_verifier.get_model() << "\n";
        std::cout << "Serial: " << hw_verifier.get_serial() << "\n";
        std::cout << "Revision: 0x" << std::hex << hw_verifier.get_revision() << std::dec << "\n";
    }

    // Install signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    // Create miner instance
    g_miner = std::make_unique<psminer::Miner>(config);

    // Set up block callback
    g_miner->set_block_callback([&config](uint32_t nonce, const std::string &hash)
                                {
        if (!config.monitor_tui) {
            std::cout << "✓ Block found! Nonce: " << nonce << " Hash: " << hash << "\n";
        } });

    // Start mining
    if (!g_miner->start())
    {
        std::cerr << "Failed to start miner\n";
        return 1;
    }

    std::cout << "Mining started on " << config.threads << " thread(s)\n";
    std::cout << "Wallet: " << config.wallet_address << "\n";
    std::cout << "Network: " << (config.testnet ? "testnet" : "mainnet") << "\n";

    // Run TUI or simple loop
    if (config.monitor_tui && !config.daemon)
    {
        try
        {
            psminer::MonitorTUI tui(*g_miner);
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
        while (!g_shutdown_requested && g_miner->is_running())
        {
            std::this_thread::sleep_for(std::chrono::seconds(10));

            const auto &stats = g_miner->stats();
            std::cout << "[" << stats.uptime_seconds << "s] "
                      << "Hashrate: " << stats.hashrate_mhs << " MH/s | "
                      << "Blocks: " << stats.blocks_found << " | "
                      << "Hashes: " << stats.hashes_computed << "\n";
        }
    }

    // Cleanup
    g_miner->stop();
    std::cout << "Mining stopped. Final statistics:\n";

    const auto &stats = g_miner->stats();
    std::cout << "  Total hashes: " << stats.hashes_computed << "\n";
    std::cout << "  Blocks found: " << stats.blocks_found << "\n";
    std::cout << "  Uptime: " << stats.uptime_seconds << " seconds\n";
    std::cout << "  Avg hashrate: " << stats.hashrate_mhs << " MH/s\n";

    return 0;
}
