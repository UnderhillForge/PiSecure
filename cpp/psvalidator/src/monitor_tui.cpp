#include "monitor_tui.hpp"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <ctime>
#include <sys/ioctl.h>
#include <unistd.h>
#include <termios.h>
#include <cstring>

namespace psvalidator
{
    MonitorTUI::MonitorTUI(Validator &validator)
        : validator_(validator)
    {
    }

    MonitorTUI::~MonitorTUI()
    {
        cleanup_display();
    }

    void MonitorTUI::init_display()
    {
        // Get terminal size
        struct winsize w;
        if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == 0)
        {
            term_height_ = w.ws_row;
            term_width_ = w.ws_col;
        }

        // Clear screen
        std::cout << "\033[2J\033[H";
        std::cout.flush();
    }

    void MonitorTUI::cleanup_display()
    {
        // Clear screen and reset cursor
        std::cout << "\033[2J\033[H";
        std::cout.flush();
    }

    void MonitorTUI::run()
    {
        init_display();

        // Set up callbacks
        validator_.set_block_callback([this](uint32_t height, const std::string &hash, bool valid)
                                      {
            std::stringstream ss;
            ss << "[Block #" << height << "] " 
               << (valid ? "✓ Valid" : "✗ Invalid") 
               << " - " << hash.substr(0, 16) << "...";
            add_log_entry(ss.str()); });

        validator_.set_reward_callback([this](double amount, uint32_t block_height)
                                       {
            std::stringstream ss;
            ss << "[Reward] Earned " << std::fixed << std::setprecision(4) 
               << amount << " tokens at block #" << block_height;
            add_log_entry(ss.str()); });

        while (running_ && validator_.is_running())
        {
            render();
            handle_input();
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }

        cleanup_display();
    }

    void MonitorTUI::render()
    {
        // Clear screen
        std::cout << "\033[H";

        draw_header();
        draw_stats_panel();
        draw_rewards_panel();
        draw_network_panel();
        draw_activity_log();
        draw_footer();

        std::cout.flush();
    }

    void MonitorTUI::draw_header()
    {
        std::cout << "╔════════════════════════════════════════════════════════════════════════════╗\n";
        std::cout << "║                         PSVALIDATOR - VALIDATION MONITOR                   ║\n";
        std::cout << "╚════════════════════════════════════════════════════════════════════════════╝\n";
        std::cout << "\n";
    }

    void MonitorTUI::draw_stats_panel()
    {
        const auto &stats = validator_.stats();

        std::cout << "┌─ VALIDATION STATISTICS ───────────────────────────────────────────────────┐\n";
        std::cout << "│ Blocks Validated:       " << std::setw(12) << stats.blocks_validated << "                                   │\n";
        std::cout << "│ Transactions Validated: " << std::setw(12) << stats.transactions_validated << "                                   │\n";
        std::cout << "│ Invalid Blocks:         " << std::setw(12) << stats.invalid_blocks_detected << "                                   │\n";
        std::cout << "│ Invalid Transactions:   " << std::setw(12) << stats.invalid_transactions_detected << "                                   │\n";

        // Calculate uptime
        uint64_t uptime = stats.uptime_seconds;
        uint32_t hours = uptime / 3600;
        uint32_t minutes = (uptime % 3600) / 60;
        uint32_t seconds = uptime % 60;

        std::cout << "│ Uptime:                 "
                  << std::setfill('0') << std::setw(2) << hours << ":"
                  << std::setw(2) << minutes << ":"
                  << std::setw(2) << seconds << std::setfill(' ')
                  << "                                          │\n";

        std::cout << "│ Current Height:         " << std::setw(12) << stats.current_height << "                                   │\n";
        std::cout << "└────────────────────────────────────────────────────────────────────────────┘\n";
        std::cout << "\n";
    }

    void MonitorTUI::draw_rewards_panel()
    {
        const auto &stats = validator_.stats();

        std::cout << "┌─ VALIDATOR REWARDS ───────────────────────────────────────────────────────┐\n";
        std::cout << "│ Total Earned:           "
                  << std::fixed << std::setprecision(4) << std::setw(12)
                  << stats.total_rewards_earned << " tokens                            │\n";
        std::cout << "│ Current Bucket:         "
                  << std::fixed << std::setprecision(4) << std::setw(12)
                  << stats.current_bucket_balance << " tokens                            │\n";
        std::cout << "│ Reward Rate:            1% of block rewards                                │\n";
        std::cout << "└────────────────────────────────────────────────────────────────────────────┘\n";
        std::cout << "\n";
    }

    void MonitorTUI::draw_network_panel()
    {
        const auto &stats = validator_.stats();

        std::cout << "┌─ NETWORK STATUS ──────────────────────────────────────────────────────────┐\n";
        std::cout << "│ Daemon Connection:      "
                  << (stats.connected_to_daemon ? "✓ Connected" : "✗ Disconnected")
                  << "                                         │\n";
        std::cout << "│ Peer Count:             " << std::setw(12) << stats.peer_count << "                                   │\n";
        std::cout << "└────────────────────────────────────────────────────────────────────────────┘\n";
        std::cout << "\n";
    }

    void MonitorTUI::draw_activity_log()
    {
        std::cout << "┌─ RECENT ACTIVITY ─────────────────────────────────────────────────────────┐\n";

        // Show last N log entries
        size_t start = activity_log_.size() > kMaxLogEntries ? activity_log_.size() - kMaxLogEntries : 0;
        for (size_t i = start; i < activity_log_.size(); i++)
        {
            std::cout << "│ " << std::left << std::setw(76) << activity_log_[i] << " │\n";
        }

        // Fill remaining lines
        for (size_t i = activity_log_.size(); i < kMaxLogEntries; i++)
        {
            std::cout << "│" << std::string(78, ' ') << "│\n";
        }

        std::cout << "└────────────────────────────────────────────────────────────────────────────┘\n";
        std::cout << "\n";
    }

    void MonitorTUI::draw_footer()
    {
        std::cout << "Press 'q' to quit | 'r' to refresh | Platform: Universal (No Pi Required)\n";
    }

    void MonitorTUI::handle_input()
    {
        // Non-blocking input check
        struct termios oldt, newt;
        tcgetattr(STDIN_FILENO, &oldt);
        newt = oldt;
        newt.c_lflag &= ~(ICANON | ECHO);
        tcsetattr(STDIN_FILENO, TCSANOW, &newt);

        fd_set set;
        struct timeval timeout;
        FD_ZERO(&set);
        FD_SET(STDIN_FILENO, &set);
        timeout.tv_sec = 0;
        timeout.tv_usec = 100000; // 100ms timeout

        int rv = select(STDIN_FILENO + 1, &set, nullptr, nullptr, &timeout);
        if (rv > 0)
        {
            char c;
            if (read(STDIN_FILENO, &c, 1) > 0)
            {
                if (c == 'q' || c == 'Q')
                {
                    running_ = false;
                }
                else if (c == 'r' || c == 'R')
                {
                    init_display(); // Force full refresh
                }
            }
        }

        tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    }

    void MonitorTUI::add_log_entry(const std::string &message)
    {
        // Add timestamp
        auto now = std::time(nullptr);
        auto tm = *std::localtime(&now);
        std::stringstream ss;
        ss << std::put_time(&tm, "%H:%M:%S") << " " << message;

        activity_log_.push_back(ss.str());

        // Keep only last kMaxLogEntries * 2 entries in memory
        if (activity_log_.size() > kMaxLogEntries * 2)
        {
            activity_log_.erase(activity_log_.begin());
        }
    }

} // namespace psvalidator
