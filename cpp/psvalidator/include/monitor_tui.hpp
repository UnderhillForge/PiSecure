#pragma once

#include "validator.hpp"
#include <string>
#include <vector>

namespace psvalidator
{
    /**
     * Terminal UI monitor for psvalidator
     * Shows real-time validation statistics and rewards
     */
    class MonitorTUI
    {
    public:
        explicit MonitorTUI(Validator &validator);
        ~MonitorTUI();

        // Run the TUI (blocking)
        void run();

    private:
        void init_display();
        void cleanup_display();
        void render();
        void handle_input();

        void draw_header();
        void draw_stats_panel();
        void draw_rewards_panel();
        void draw_network_panel();
        void draw_activity_log();
        void draw_footer();

        void add_log_entry(const std::string &message);

        Validator &validator_;
        bool running_{true};
        std::vector<std::string> activity_log_;
        static constexpr size_t kMaxLogEntries = 10;

        // Terminal dimensions
        int term_width_{80};
        int term_height_{24};
    };

} // namespace psvalidator
