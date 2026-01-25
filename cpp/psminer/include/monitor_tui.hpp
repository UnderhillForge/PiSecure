#pragma once

#include "miner.hpp"
#include <ncurses.h>
#include <memory>
#include <atomic>

namespace psminer {

class MonitorTUI {
public:
    explicit MonitorTUI(const Miner& miner);
    ~MonitorTUI();
    
    // Start the TUI (blocking)
    void run();
    
    // Stop the TUI
    void stop();
    
private:
    void init_colors();
    void init_windows();
    void cleanup();
    
    void draw_header();
    void draw_stats();
    void draw_hardware();
    void draw_network();
    void draw_log();
    void draw_help();
    
    void handle_input();
    void update_display();
    
    const Miner& miner_;
    std::atomic<bool> running_{true};
    
    // ncurses windows
    WINDOW* win_header_ = nullptr;
    WINDOW* win_stats_ = nullptr;
    WINDOW* win_hardware_ = nullptr;
    WINDOW* win_network_ = nullptr;
    WINDOW* win_log_ = nullptr;
    WINDOW* win_help_ = nullptr;
    
    // Layout dimensions
    int term_height_ = 0;
    int term_width_ = 0;
    
    // Log buffer
    std::vector<std::string> log_buffer_;
    static constexpr size_t MAX_LOG_LINES = 100;
    
    // Colors
    enum ColorPair {
        COLOR_HEADER = 1,
        COLOR_SUCCESS = 2,
        COLOR_WARNING = 3,
        COLOR_ERROR = 4,
        COLOR_INFO = 5,
        COLOR_HIGHLIGHT = 6
    };
};

} // namespace psminer
