#include "pisecured/config.hpp"
#include "pisecured/daemon.hpp"
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

int main(int argc, char *argv[])
{
    using namespace pisecured;

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
