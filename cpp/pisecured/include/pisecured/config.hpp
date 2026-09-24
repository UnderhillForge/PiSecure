#pragma once

#include <string>
#include <vector>
#include <filesystem>

namespace pisecured
{
    // Maximum validator rewards percentage allowed by the network (5%)
    constexpr double MAX_VALIDATOR_REWARDS_PERCENTAGE = 0.05;

    struct Config
    {
        std::filesystem::path datadir;
        std::filesystem::path conf_file;
        std::string rpc_bind = "0.0.0.0";
        int rpc_port = 3144;
        // WebSocket RPC (Phase 3)
        std::string ws_bind = "0.0.0.0";
        int ws_port = 3144;
        bool ws_enabled = true;              // Replace HTTP by default
        bool http_enabled = false;           // Disable HTTP fallback by default
        bool ws_tls = false;                 // Enable TLS for WebSocket
        std::filesystem::path tls_cert_path; // PEM cert
        std::filesystem::path tls_key_path;  // PEM key
        std::string p2p_bind = "0.0.0.0";
        int p2p_port = 3141;
        std::vector<std::string> peers;
        bool testnet = false;
        bool validate_only = false;
        bool daemonize = false;
        bool no_update_check = false;
        bool apply_update = false;
        int max_peers = 32;
        bool hybrid_storage = true;

        // Validator rewards
        bool validator_rewards_enabled = true;
        double validator_rewards_percentage = 0.01;  // 1% of block reward
        std::string validator_wallet_address = "";   // Linked wallet for rewards
        std::filesystem::path validator_bucket_path; // Validator bucket path
    };

    Config load_config(int argc, char *argv[]);
    std::filesystem::path default_datadir(bool testnet);
}
