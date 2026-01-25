#pragma once

#include "validator.hpp"
#include <string>

namespace psvalidator
{
    class CLI
    {
    public:
        static void print_version();
        static void print_help(const char *program_name);
        static bool parse_args(int argc, char **argv, Config &config);
        static int execute_command(const std::string &command, const Config &config);

    private:
        static void print_banner();
        static void print_validation_info();
        static void print_status(const Config &config);
    };

} // namespace psvalidator
