#include "pisecured/config.hpp"
#include "pisecured/daemon.hpp"
#include "release_update.hpp"
#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>

static std::atomic<bool> g_should_stop{false};

static void handle_signal(int)
{
    g_should_stop = true;
}

static void print_usage()
{
    std::cout << "pisecured [--validate-only] [--host 0.0.0.0] [--port 3144] [--p2p-port 3141]\n"
              << "          [--peer HOST:PORT] [--datadir PATH] [--no-update-check]\n"
              << "Set PISECURE_NODE_ID to a unique name on every machine.\n"
              << "Do not reuse pisecure-pi5-validator except on that Pi.\n"
              << "Coordinated defense stays off unless PISECURE_SENTINEL=1.\n";
}

int main(int argc, char *argv[])
{
    using namespace pisecured;

    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        if (arg == "-h" || arg == "--help")
        {
            print_usage();
            return 0;
        }
    }

    if (argc >= 3 && std::string(argv[1]) == "update" && std::string(argv[2]) == "download")
    {
        const auto report = pisecure_update::check_release(PISECURE_RELEASE);
        std::cout << report.line << std::endl;
        if (report.kind != pisecure_update::Report::Kind::Newer)
        {
            return report.kind == pisecure_update::Report::Kind::Skipped ? 0 : 0;
        }
        std::string err;
        if (!pisecure_update::download_member(report, "pisecured", "/tmp/pisecured", err))
        {
            std::cerr << err << std::endl;
            return 1;
        }
        pisecure_update::print_daemon_install(report.tag);
        return 0;
    }

    Config cfg = load_config(argc, argv);

    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);

    Daemon daemon(cfg);
    if (!daemon.start())
    {
        std::cerr << "Failed to start pisecured\n";
        return 1;
    }

    while (!g_should_stop.load())
    {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    daemon.stop();
    return 0;
}
