#include "monitor_tui.hpp"
#include <chrono>
#include <thread>
#include <iomanip>
#include <sstream>
#include <cstring>

namespace psminer
{

    MonitorTUI::MonitorTUI(const Miner &miner)
        : miner_(miner)
    {
        initscr();
        cbreak();
        noecho();
        nodelay(stdscr, TRUE);
        keypad(stdscr, TRUE);
        curs_set(0);

        init_colors();
        init_windows();
    }

    MonitorTUI::~MonitorTUI()
    {
        cleanup();
    }

    void MonitorTUI::init_colors()
    {
        if (has_colors())
        {
            start_color();
            init_pair(COLOR_HEADER, COLOR_WHITE, COLOR_BLUE);
            init_pair(COLOR_SUCCESS, COLOR_GREEN, COLOR_BLACK);
            init_pair(COLOR_WARNING, COLOR_YELLOW, COLOR_BLACK);
            init_pair(COLOR_ERROR, COLOR_RED, COLOR_BLACK);
            init_pair(COLOR_INFO, COLOR_CYAN, COLOR_BLACK);
            init_pair(COLOR_HIGHLIGHT, COLOR_BLACK, COLOR_WHITE);
        }
    }

    void MonitorTUI::init_windows()
    {
        getmaxyx(stdscr, term_height_, term_width_);

        int row = 0;

        // Header (3 lines)
        win_header_ = newwin(3, term_width_, row, 0);
        row += 3;

        // Stats (8 lines)
        win_stats_ = newwin(8, term_width_ / 2, row, 0);

        // Hardware (8 lines, right side)
        win_hardware_ = newwin(8, term_width_ / 2, row, term_width_ / 2);
        row += 8;

        // Network (6 lines)
        win_network_ = newwin(6, term_width_, row, 0);
        row += 6;

        // Log (remaining space - 3 for help)
        int log_height = term_height_ - row - 3;
        if (log_height > 0)
        {
            win_log_ = newwin(log_height, term_width_, row, 0);
            row += log_height;
        }

        // Help (3 lines at bottom)
        win_help_ = newwin(3, term_width_, row, 0);
    }

    void MonitorTUI::cleanup()
    {
        if (win_header_)
            delwin(win_header_);
        if (win_stats_)
            delwin(win_stats_);
        if (win_hardware_)
            delwin(win_hardware_);
        if (win_network_)
            delwin(win_network_);
        if (win_log_)
            delwin(win_log_);
        if (win_help_)
            delwin(win_help_);

        endwin();
    }

    void MonitorTUI::run()
    {
        running_ = true;

        while (running_ && miner_.is_running())
        {
            update_display();
            handle_input();
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }

    void MonitorTUI::stop()
    {
        running_ = false;
    }

    void MonitorTUI::draw_header()
    {
        if (!win_header_)
            return;

        werase(win_header_);
        wbkgd(win_header_, COLOR_PAIR(COLOR_HEADER));

        // Title
        mvwprintw(win_header_, 1, 2, "PiSecure Hardware-Verified Miner v0.1.0");

        // Status indicator
        const auto &stats = miner_.stats();
        if (stats.hardware_verified)
        {
            wattron(win_header_, COLOR_PAIR(COLOR_SUCCESS));
            mvwprintw(win_header_, 1, term_width_ - 25, "[HW VERIFIED]");
            wattroff(win_header_, COLOR_PAIR(COLOR_SUCCESS));
        }

        wrefresh(win_header_);
    }

    void MonitorTUI::draw_stats()
    {
        if (!win_stats_)
            return;

        werase(win_stats_);
        box(win_stats_, 0, 0);
        mvwprintw(win_stats_, 0, 2, "[ Mining Statistics ]");

        const auto &stats = miner_.stats();

        // Format numbers
        auto format_si = [](uint64_t val) -> std::string
        {
            if (val >= 1000000000)
                return std::to_string(val / 1000000000) + "G";
            if (val >= 1000000)
                return std::to_string(val / 1000000) + "M";
            if (val >= 1000)
                return std::to_string(val / 1000) + "K";
            return std::to_string(val);
        };

        int row = 2;
        mvwprintw(win_stats_, row++, 2, "Hashrate:   %8.2f MH/s", stats.hashrate_mhs.load());
        mvwprintw(win_stats_, row++, 2, "Hashes:     %12s", format_si(stats.hashes_computed).c_str());
        mvwprintw(win_stats_, row++, 2, "Blocks:     %12llu",
                  static_cast<unsigned long long>(stats.blocks_found.load()));
        mvwprintw(win_stats_, row++, 2, "Difficulty: %12u", stats.current_difficulty.load());

        // Uptime
        uint64_t uptime = stats.uptime_seconds;
        uint64_t hours = uptime / 3600;
        uint64_t mins = (uptime % 3600) / 60;
        uint64_t secs = uptime % 60;
        mvwprintw(win_stats_, row++, 2, "Uptime:     %02llu:%02llu:%02llu",
                  static_cast<unsigned long long>(hours),
                  static_cast<unsigned long long>(mins),
                  static_cast<unsigned long long>(secs));

        wrefresh(win_stats_);
    }

    void MonitorTUI::draw_hardware()
    {
        if (!win_hardware_)
            return;

        werase(win_hardware_);
        box(win_hardware_, 0, 0);
        mvwprintw(win_hardware_, 0, 2, "[ Hardware Status ]");

        const auto &stats = miner_.stats();

        int row = 2;

        // CPU temperature with color coding
        int cpu_temp = stats.cpu_temp_c;
        wattron(win_hardware_, COLOR_PAIR(
                                   cpu_temp > 80 ? COLOR_ERROR : cpu_temp > 70 ? COLOR_WARNING
                                                                               : COLOR_SUCCESS));
        mvwprintw(win_hardware_, row++, 2, "CPU Temp:  %3d°C", cpu_temp);
        wattroff(win_hardware_, COLOR_PAIR(COLOR_SUCCESS));
        wattroff(win_hardware_, COLOR_PAIR(COLOR_WARNING));
        wattroff(win_hardware_, COLOR_PAIR(COLOR_ERROR));

        // GPU temperature
        int gpu_temp = stats.gpu_temp_c;
        wattron(win_hardware_, COLOR_PAIR(
                                   gpu_temp > 80 ? COLOR_ERROR : gpu_temp > 70 ? COLOR_WARNING
                                                                               : COLOR_SUCCESS));
        mvwprintw(win_hardware_, row++, 2, "GPU Temp:  %3d°C", gpu_temp);
        wattroff(win_hardware_, COLOR_PAIR(COLOR_SUCCESS));
        wattroff(win_hardware_, COLOR_PAIR(COLOR_WARNING));
        wattroff(win_hardware_, COLOR_PAIR(COLOR_ERROR));

        // CPU frequency
        mvwprintw(win_hardware_, row++, 2, "CPU Freq:  %4d MHz", stats.cpu_freq_mhz.load());

        // Throttle status
        int throttle = stats.throttle_status;
        if (throttle != 0)
        {
            wattron(win_hardware_, COLOR_PAIR(COLOR_WARNING));
            mvwprintw(win_hardware_, row++, 2, "Throttled: YES (0x%04X)", throttle);
            wattroff(win_hardware_, COLOR_PAIR(COLOR_WARNING));
        }
        else
        {
            mvwprintw(win_hardware_, row++, 2, "Throttled: NO");
        }

        wrefresh(win_hardware_);
    }

    void MonitorTUI::draw_network()
    {
        if (!win_network_)
            return;

        werase(win_network_);
        box(win_network_, 0, 0);
        mvwprintw(win_network_, 0, 2, "[ Network Status ]");

        int row = 2;
        mvwprintw(win_network_, row++, 2, "Status: Connected");
        mvwprintw(win_network_, row++, 2, "Peers:  3 active");
        mvwprintw(win_network_, row++, 2, "Height: 12,345");

        wrefresh(win_network_);
    }

    void MonitorTUI::draw_log()
    {
        if (!win_log_)
            return;

        werase(win_log_);
        box(win_log_, 0, 0);
        mvwprintw(win_log_, 0, 2, "[ Activity Log ]");

        // Display recent log entries
        int max_lines = getmaxy(win_log_) - 2;
        int start_idx = log_buffer_.size() > static_cast<size_t>(max_lines)
                            ? log_buffer_.size() - max_lines
                            : 0;

        for (size_t i = start_idx; i < log_buffer_.size(); i++)
        {
            mvwprintw(win_log_, 1 + i - start_idx, 2, "%s", log_buffer_[i].c_str());
        }

        wrefresh(win_log_);
    }

    void MonitorTUI::draw_help()
    {
        if (!win_help_)
            return;

        werase(win_help_);
        box(win_help_, 0, 0);

        mvwprintw(win_help_, 1, 2, "[Q] Quit  [R] Refresh  [H] Help  [P] Pause");

        wrefresh(win_help_);
    }

    void MonitorTUI::handle_input()
    {
        int ch = getch();
        if (ch == ERR)
            return;

        switch (ch)
        {
        case 'q':
        case 'Q':
            running_ = false;
            break;
        case 'r':
        case 'R':
            // Force refresh
            break;
        case KEY_RESIZE:
            // Handle terminal resize
            getmaxyx(stdscr, term_height_, term_width_);
            cleanup();
            init_windows();
            break;
        }
    }

    void MonitorTUI::update_display()
    {
        clear();
        draw_header();
        draw_stats();
        draw_hardware();
        draw_network();
        draw_log();
        draw_help();
        refresh();
    }

} // namespace psminer
