#include "cli.hpp"
#include <iostream>
#include <cstdlib>
#include <cstring>

using namespace pswallet;

int main(int argc, char *argv[])
{
    try
    {
        // Require at least program name and command
        if (argc < 2)
        {
            CLI::print_help(argv[0]);
            return 1;
        }

        // Handle global flags that don't need a command
        for (int i = 1; i < argc; ++i)
        {
            std::string arg = argv[i];
            if (arg == "--version")
            {
                CLI::print_version();
                return 0;
            }
            else if (arg == "-h" || arg == "--help")
            {
                CLI::print_help(argv[0]);
                return 0;
            }
        }

        // Get command from argv[1] (first positional argument after program name)
        std::string command = argv[1];

        CLIConfig config;

        // Parse all arguments first (using command to interpret positionals)
        if (!CLI::parse_args(argc, argv, config, command))
        {
            return 0; // Help or version displayed
        }

        if (command.empty())
        {
            CLI::print_help(argv[0]);
            return 1;
        }

        // Execute the command with the parsed configuration
        return CLI::execute_command(command, config);
    }
    catch (const std::exception &e)
    {
        std::cerr << "Fatal error: " << e.what() << "\n";
        return 1;
    }
    catch (...)
    {
        std::cerr << "Unknown fatal error\n";
        return 1;
    }
}
