#pragma once

#include <string>
#include <vector>
#include <map>
#include <optional>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace pswallet
{

    /**
     * CLI configuration
     */
    struct CLIConfig
    {
        // Global options
        bool testnet = false;     // Use testnet
        bool json_output = false; // JSON output format
        bool quiet = false;       // Suppress output
        bool verbose = false;     // Verbose logging
        std::string wallet_dir;   // Custom wallet directory
        std::string blockchain_url = "http://localhost:3142";

        // Wallet command options
        std::string wallet_id;     // Wallet ID for operations
        std::string wallet_name;   // Display name
        std::string password;      // Encryption password
        bool cold_storage = false; // Cold storage mode

        // Transaction options
        std::string recipient; // Transfer recipient
        double amount = 0.0;   // Transfer amount
        std::string memo;      // Transaction memo
        int tx_limit = 20;     // Transaction history limit
        std::string tx_file;   // Transaction file to process

        // Script/contract options
        std::string script_file;      // Smart contract file
        std::string contract_address; // Contract address
        json script_params;           // Script parameters
        bool dry_run = false;         // Simulate without submitting
    };

    /**
     * Command-line interface processor
     */
    class CLI
    {
    public:
        /**
         * Parse command-line arguments
         * @param argc Argument count
         * @param argv Argument values
         * @param config Output configuration
         * @return True if parsing succeeded
         */
        static bool parse_args(int argc, char *argv[], CLIConfig &config, const std::string &command);

        /**
         * Print help message
         * @param program Program name
         */
        static void print_help(const std::string &program);

        /**
         * Print version information
         */
        static void print_version();

        /**
         * Execute command
         * @param command Command name
         * @param config CLI configuration
         * @return Exit code (0 = success)
         */
        static int execute_command(const std::string &command, const CLIConfig &config);

        /**
         * Pretty print JSON output
         * @param data JSON to print
         * @param indent Indentation level
         */
        static void print_json(const json &data, int indent = 2);

        /**
         * Print colored table output
         * @param rows Table rows
         * @param headers Column headers
         */
        static void print_table(const std::vector<std::vector<std::string>> &rows,
                                const std::vector<std::string> &headers);

        /**
         * Get current command being executed
         */
        static std::string get_current_command();

    private:
        static std::string current_command_;

        /**
         * Process wallet commands (create, list, export, import, etc.)
         */
        static int handle_wallet_command(const std::string &subcommand, const CLIConfig &config);

        /**
         * Process transaction commands (send, history, create-tx, etc.)
         */
        static int handle_transaction_command(const std::string &subcommand, const CLIConfig &config);

        /**
         * Process blockchain queries (balance, chain-info, etc.)
         */
        static int handle_blockchain_command(const std::string &subcommand, const CLIConfig &config);

        /**
         * Process smart contract commands (run, validate, deploy, etc.)
         */
        static int handle_contract_command(const std::string &subcommand, const CLIConfig &config);

        /**
         * Print wallet info table
         */
        static void print_wallet_table(const std::vector<json> &wallets);

        /**
         * Print transaction history table
         */
        static void print_transaction_table(const std::vector<json> &transactions);

        /**
         * Prompt user for input
         * @param prompt Prompt text
         * @param password Hide input if true
         * @return User input
         */
        static std::string prompt_user(const std::string &prompt, bool password = false);

        /**
         * Confirm action with user
         * @param message Confirmation message
         * @return True if confirmed
         */
        static bool confirm(const std::string &message);
    };

} // namespace pswallet
