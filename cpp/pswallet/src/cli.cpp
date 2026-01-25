#include "cli.hpp"
#include "wallet.hpp"
#include "blockchain_client.hpp"
#include "smart_contract.hpp"
#include <iostream>
#include <iomanip>
#include <fstream>
#include <cstring>
#include <algorithm>
#include <termios.h>
#include <unistd.h>

namespace pswallet
{

    std::string CLI::current_command_;

    bool CLI::parse_args(int argc, char *argv[], CLIConfig &config, const std::string &command)
    {
        if (argc < 2)
        {
            print_help(argv[0]);
            return false;
        }

        // Process flags and options (starting from argv[2] to preserve command at argv[1])
        for (int i = 2; i < argc; ++i)
        {
            std::string arg = argv[i];

            if (arg == "--version")
            {
                print_version();
                return false;
            }
            else if (arg == "-h" || arg == "--help")
            {
                print_help(argv[0]);
                return false;
            }
            else if (arg == "--testnet")
            {
                config.testnet = true;
            }
            else if (arg == "-j" || arg == "--json")
            {
                config.json_output = true;
            }
            else if (arg == "-q" || arg == "--quiet")
            {
                config.quiet = true;
            }
            else if (arg == "-v" || arg == "--verbose")
            {
                config.verbose = true;
            }
            else if ((arg == "-u" || arg == "--url") && i + 1 < argc)
            {
                config.blockchain_url = argv[++i];
            }
            else if ((arg == "-d" || arg == "--wallet-dir") && i + 1 < argc)
            {
                config.wallet_dir = argv[++i];
            }
            else if ((arg == "-w" || arg == "--wallet") && i + 1 < argc)
            {
                config.wallet_id = argv[++i];
            }
            else if ((arg == "-r" || arg == "--recipient") && i + 1 < argc)
            {
                config.recipient = argv[++i];
            }
            else if ((arg == "-a" || arg == "--amount") && i + 1 < argc)
            {
                config.amount = std::stod(argv[++i]);
            }
            else if ((arg == "-m" || arg == "--memo") && i + 1 < argc)
            {
                config.memo = argv[++i];
            }
            else if ((arg == "-p" || arg == "--password") && i + 1 < argc)
            {
                config.password = argv[++i];
            }
            else if ((arg == "-s" || arg == "--script") && i + 1 < argc)
            {
                config.script_file = argv[++i];
            }
            else if (arg == "--dry-run")
            {
                config.dry_run = true;
            }
            else if (arg == "--cold-storage")
            {
                config.cold_storage = true;
            }
            else if (!arg.empty() && arg[0] != '-')
            {
                // Interpret positional arguments based on the current command
                if (command == "create")
                {
                    if (config.wallet_id.empty())
                    {
                        config.wallet_id = arg;
                        config.wallet_name = arg;
                    }
                    else if (config.wallet_name.empty())
                    {
                        config.wallet_name = arg;
                    }
                }
                else if (command == "info" || command == "export" ||
                         command == "import" || command == "delete" ||
                         command == "balance" || command == "history" ||
                         command == "pending")
                {
                    if (config.wallet_id.empty())
                    {
                        config.wallet_id = arg;
                    }
                }
                else if (command == "send")
                {
                    if (config.wallet_id.empty())
                    {
                        config.wallet_id = arg;
                    }
                    else if (config.recipient.empty())
                    {
                        config.recipient = arg;
                    }
                    else if (config.amount <= 0)
                    {
                        try
                        {
                            config.amount = std::stod(arg);
                        }
                        catch (const std::exception &)
                        {
                            std::cerr << "Error: amount must be numeric\n";
                            return false;
                        }
                    }
                    else if (config.memo.empty())
                    {
                        config.memo = arg;
                    }
                }
            }
        }

        return true;
    }

    void CLI::print_help(const std::string &program)
    {
        std::cout << "Usage: " << program << " [OPTIONS] COMMAND [ARGS]\n\n"
                  << "pswallet - PiSecure Wallet Manager and Smart Contract Engine\n\n"
                  << "Global Options:\n"
                  << "  --testnet              Use testnet (separate blockchain)\n"
                  << "  -j, --json             Output as JSON\n"
                  << "  -q, --quiet            Suppress informational output\n"
                  << "  -v, --verbose          Verbose output with details\n"
                  << "  -u, --url URL          Blockchain node URL (default: http://localhost:3142)\n"
                  << "  -d, --wallet-dir DIR   Custom wallet directory\n"
                  << "  -h, --help             Show this help message\n"
                  << "  --version              Show version information\n\n"
                  << "Wallet Commands:\n"
                  << "  create NAME            Create new wallet\n"
                  << "  list                   List all wallets\n"
                  << "  info WALLET_ID         Show wallet information\n"
                  << "  balance ADDRESS        Check wallet balance\n"
                  << "  export WALLET_ID       Export wallet (backup)\n"
                  << "  import FILE            Import wallet from backup\n"
                  << "  delete WALLET_ID       Delete wallet\n\n"
                  << "Transaction Commands:\n"
                  << "  send WALLET RECIPIENT AMOUNT\n"
                  << "                         Send tokens from wallet\n"
                  << "  history ADDRESS        Show transaction history\n"
                  << "  batch-send FILE        Send batch of transfers from file\n"
                  << "  pending                Show pending transactions\n\n"
                  << "Smart Contract Commands:\n"
                  << "  run-script FILE        Execute smart contract script\n"
                  << "  validate SCRIPT        Validate script syntax\n"
                  << "  deploy CONTRACT        Deploy contract\n"
                  << "  call CONTRACT FUNC     Call contract function\n\n"
                  << "Blockchain Commands:\n"
                  << "  chain-info             Show blockchain information\n"
                  << "  node-status            Show node status\n"
                  << "  peers                  Show connected peers\n\n"
                  << "Examples:\n"
                  << "  pswallet create mywallet\n"
                  << "  pswallet balance 0x1234...\n"
                  << "  pswallet send mywallet 0x5678... 100.0\n"
                  << "  pswallet run-script contract.ps\n";
    }

    void CLI::print_version()
    {
        std::cout << "pswallet 1.0.0\n"
                  << "PiSecure Wallet Manager and Smart Contract Engine\n"
                  << "Built for Raspberry Pi and Linux systems\n";
    }

    int CLI::execute_command(const std::string &command, const CLIConfig &config)
    {
        current_command_ = command;

        if (command.empty())
        {
            print_help("pswallet");
            return 1;
        }

        // Wallet commands
        if (command == "create")
        {
            return handle_wallet_command("create", config);
        }
        else if (command == "list")
        {
            return handle_wallet_command("list", config);
        }
        else if (command == "info")
        {
            return handle_wallet_command("info", config);
        }
        else if (command == "export")
        {
            return handle_wallet_command("export", config);
        }
        else if (command == "import")
        {
            return handle_wallet_command("import", config);
        }
        else if (command == "delete")
        {
            return handle_wallet_command("delete", config);
        }
        // Transaction commands
        else if (command == "balance")
        {
            return handle_blockchain_command("balance", config);
        }
        else if (command == "send")
        {
            return handle_transaction_command("send", config);
        }
        else if (command == "history")
        {
            return handle_transaction_command("history", config);
        }
        else if (command == "pending")
        {
            return handle_transaction_command("pending", config);
        }
        // Smart contract commands
        else if (command == "run-script" || command == "run")
        {
            return handle_contract_command("run", config);
        }
        else if (command == "validate")
        {
            return handle_contract_command("validate", config);
        }
        // Blockchain commands
        else if (command == "chain-info")
        {
            return handle_blockchain_command("chain-info", config);
        }
        else if (command == "node-status")
        {
            return handle_blockchain_command("node-status", config);
        }

        std::cerr << "Unknown command: " << command << "\n";
        return 1;
    }

    int CLI::handle_wallet_command(const std::string &subcommand, const CLIConfig &config)
    {
        if (subcommand == "create")
        {
            if (config.wallet_id.empty())
            {
                std::cerr << "Error: Wallet name required\n";
                return 1;
            }

            auto wallet = Wallet::create_wallet(config.wallet_id, config.wallet_name);
            if (!wallet)
            {
                std::cerr << "Error: Failed to create wallet\n";
                return 1;
            }

            if (config.json_output)
            {
                json output;
                output["wallet_id"] = wallet->wallet_id;
                output["address"] = wallet->address;
                output["name"] = wallet->name;
                print_json(output);
            }
            else if (!config.quiet)
            {
                std::cout << "✓ Created wallet: " << wallet->wallet_id << "\n"
                          << "  Address: " << wallet->address << "\n";
            }

            return 0;
        }

        if (subcommand == "list")
        {
            auto wallets = Wallet::list_wallets();

            if (wallets.empty())
            {
                if (!config.quiet)
                {
                    std::cout << "No wallets found\n";
                }
                return 0;
            }

            if (config.json_output)
            {
                json output = json::array();
                for (const auto &wallet_id : wallets)
                {
                    auto wallet = Wallet::load_wallet(wallet_id);
                    if (wallet)
                    {
                        json w;
                        w["wallet_id"] = wallet->wallet_id;
                        w["address"] = wallet->address;
                        w["name"] = wallet->name;
                        w["balance"] = wallet->balance;
                        output.push_back(w);
                    }
                }
                print_json(output);
            }
            else if (!config.quiet)
            {
                std::cout << "Wallets:\n";
                for (const auto &wallet_id : wallets)
                {
                    std::cout << "  " << wallet_id << "\n";
                }
            }

            return 0;
        }

        if (subcommand == "info")
        {
            if (config.wallet_id.empty())
            {
                std::cerr << "Error: Wallet ID required\n";
                return 1;
            }

            auto wallet = Wallet::load_wallet(config.wallet_id);
            if (!wallet)
            {
                std::cerr << "Error: Wallet not found\n";
                return 1;
            }

            if (config.json_output)
            {
                json output;
                output["wallet_id"] = wallet->wallet_id;
                output["address"] = wallet->address;
                output["name"] = wallet->name;
                output["balance"] = wallet->balance;
                output["created_at"] = wallet->created_at;
                output["transactions"] = wallet->transactions.size();
                print_json(output);
            }
            else if (!config.quiet)
            {
                std::cout << "Wallet: " << wallet->wallet_id << "\n"
                          << "  Name: " << wallet->name << "\n"
                          << "  Address: " << wallet->address << "\n"
                          << "  Balance: " << std::fixed << std::setprecision(2)
                          << wallet->balance << " 314ST\n"
                          << "  Transactions: " << wallet->transactions.size() << "\n";
            }

            return 0;
        }

        return 0;
    }

    int CLI::handle_transaction_command(const std::string &subcommand, const CLIConfig &config)
    {
        BlockchainClient client(config.blockchain_url);

        if (subcommand == "send")
        {
            if (config.wallet_id.empty() || config.recipient.empty() || config.amount <= 0)
            {
                std::cerr << "Error: wallet, recipient, and amount required\n";
                return 1;
            }

            auto tx = Wallet::create_transfer(config.wallet_id, config.recipient,
                                              config.amount, config.memo);
            if (!tx)
            {
                std::cerr << "Error: Failed to create transaction\n";
                return 1;
            }

            // Optional local verification before submission
            if (!Wallet::verify_transaction_signature(*tx, tx->signature, tx->sender_public_key))
            {
                std::cerr << "Error: Local signature verification failed\n";
                return 1;
            }

            if (!config.dry_run)
            {
                json tx_json = {
                    {"type", tx->type},
                    {"sender_address", tx->sender_address},
                    {"recipient_address", tx->recipient_address},
                    {"amount", tx->amount},
                    {"memo", tx->memo},
                    {"timestamp", tx->timestamp},
                    {"tx_hash", tx->tx_hash},
                    {"signature", tx->signature},
                    {"sender_public_key", tx->sender_public_key}};

                if (!tx->metadata.empty())
                {
                    tx_json["metadata"] = tx->metadata;
                }

                auto result = client.submit_transaction(tx_json);
                if (!result)
                {
                    std::cerr << "Error: Failed to submit transaction\n";
                    return 1;
                }

                if (config.json_output)
                {
                    json output;
                    output["tx_hash"] = *result;
                    output["amount"] = tx->amount;
                    output["recipient"] = tx->recipient_address;
                    output["sender"] = tx->sender_address;
                    print_json(output);
                }
                else if (!config.quiet)
                {
                    std::cout << "✓ Transaction submitted\n"
                              << "  TX: " << result->substr(0, 20) << "...\n";
                }
            }
            else
            {
                if (!config.quiet)
                {
                    std::cout << "✓ Dry run - transaction not submitted\n";
                }
            }

            return 0;
        }

        if (subcommand == "history")
        {
            if (config.wallet_id.empty())
            {
                std::cerr << "Error: Wallet address required\n";
                return 1;
            }

            auto transactions = client.get_transactions(config.wallet_id, config.tx_limit);
            if (!transactions)
            {
                std::cerr << "Error: Failed to retrieve transactions\n";
                return 1;
            }

            if (config.json_output)
            {
                print_json(json(*transactions));
            }
            else if (!config.quiet)
            {
                std::cout << "Transaction History (" << transactions->size() << " total):\n";
                for (const auto &tx : *transactions)
                {
                    std::cout << "  " << tx.value("type", "unknown") << ": "
                              << tx.value("amount", 0.0) << " 314ST\n";
                }
            }

            return 0;
        }

        return 0;
    }

    int CLI::handle_blockchain_command(const std::string &subcommand, const CLIConfig &config)
    {
        BlockchainClient client(config.blockchain_url);

        if (subcommand == "balance")
        {
            if (config.wallet_id.empty())
            {
                std::cerr << "Error: Wallet address required\n";
                return 1;
            }

            auto balance = client.get_balance(config.wallet_id);
            if (!balance)
            {
                std::cerr << "Error: Failed to get balance\n";
                return 1;
            }

            if (config.json_output)
            {
                json output;
                output["address"] = config.wallet_id;
                output["balance"] = *balance;
                print_json(output);
            }
            else if (!config.quiet)
            {
                std::cout << std::fixed << std::setprecision(2)
                          << *balance << " 314ST\n";
            }

            return 0;
        }

        if (subcommand == "chain-info")
        {
            auto info = client.get_chain_info();
            if (!info)
            {
                std::cerr << "Error: Failed to get chain info\n";
                return 1;
            }

            print_json(*info);
            return 0;
        }

        return 0;
    }

    int CLI::handle_contract_command(const std::string &subcommand, const CLIConfig &config)
    {
        if (subcommand == "run")
        {
            if (config.script_file.empty())
            {
                std::cerr << "Error: Script file required\n";
                return 1;
            }

            auto context = std::make_shared<ScriptContext>(
                config.wallet_id,
                config.contract_address);

            auto result = SmartContractEngine::execute_file(config.script_file, context);

            if (config.json_output)
            {
                print_json(result);
            }
            else if (!config.quiet)
            {
                if (result.contains("error"))
                {
                    std::cerr << "Error: " << result["error"] << "\n";
                    return 1;
                }

                std::cout << "✓ Script executed successfully\n";
                if (result.contains("output"))
                {
                    std::cout << "Output:\n";
                    print_json(result["output"], 2);
                }
            }

            return result.contains("error") ? 1 : 0;
        }

        if (subcommand == "validate")
        {
            if (config.script_file.empty())
            {
                std::cerr << "Error: Script file required\n";
                return 1;
            }

            std::ifstream file(config.script_file);
            std::stringstream buffer;
            buffer << file.rdbuf();

            std::string error = SmartContractEngine::validate_script(buffer.str());

            if (!error.empty())
            {
                if (config.json_output)
                {
                    json output;
                    output["valid"] = false;
                    output["error"] = error;
                    print_json(output);
                }
                else
                {
                    std::cerr << "✗ Validation failed: " << error << "\n";
                }
                return 1;
            }

            if (!config.quiet)
            {
                std::cout << "✓ Script is valid\n";
            }

            return 0;
        }

        return 0;
    }

    void CLI::print_json(const json &data, int indent)
    {
        std::cout << data.dump(indent) << "\n";
    }

    std::string CLI::get_current_command()
    {
        return current_command_;
    }

} // namespace pswallet
