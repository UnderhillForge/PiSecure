#include "pisecured/config.hpp"
#include <cstdlib>
#include <iostream>
#include <filesystem>

namespace pisecured
{
    std::filesystem::path default_datadir(bool testnet)
    {
        const char *home = std::getenv("HOME");
        if (!home)
        {
            home = ".";
        }
        std::filesystem::path base = home;
        if (testnet || std::getenv("PISECURE_TESTNET"))
        {
            return base / ".pisecure-testnet";
        }
        return base / ".pisecure";
    }

    Config load_config(int argc, char *argv[])
    {
        Config cfg;
        cfg.datadir = default_datadir(false);

        // EnvironmentFile=/etc/pisecure/pisecure.env is applied by systemd
        // before exec. CLI flags below override these.
        if (const char *data_dir = std::getenv("PISECURE_DATA_DIR"))
        {
            if (data_dir[0] != '\0')
            {
                cfg.datadir = data_dir;
            }
        }
        if (const char *host = std::getenv("PISECURED_HOST"))
        {
            if (host[0] != '\0')
            {
                cfg.rpc_bind = host;
            }
        }
        if (const char *port = std::getenv("PISECURED_PORT"))
        {
            if (port[0] != '\0')
            {
                cfg.rpc_port = std::stoi(port);
            }
        }

        cfg.conf_file = cfg.datadir / "pisecured.conf";
        cfg.validator_bucket_path = cfg.datadir / "validator_bucket.json";
        cfg.ws_bind = cfg.rpc_bind;
        cfg.ws_port = cfg.rpc_port;

        bool explicit_validator_path = false;
        if (const char *no_update = std::getenv("PISECURE_NO_UPDATE"))
        {
            const std::string flag = no_update;
            if (flag == "1" || flag == "true" || flag == "TRUE" || flag == "yes")
            {
                cfg.no_update_check = true;
            }
        }

        for (int i = 1; i < argc; ++i)
        {
            std::string arg = argv[i];
            auto next = [&](const std::string &flag) -> std::string
            {
                if (i + 1 >= argc)
                {
                    std::cerr << "Missing value for " << flag << "\n";
                    return "";
                }
                return argv[++i];
            };

            if (arg == "--datadir")
            {
                cfg.datadir = next(arg);
                cfg.conf_file = cfg.datadir / "pisecured.conf";
                if (!explicit_validator_path)
                {
                    cfg.validator_bucket_path = cfg.datadir / "validator_bucket.json";
                }
            }
            else if (arg == "--host")
            {
                // Alias used by deploy/pisecured.service (ExecStart --host/--port).
                cfg.rpc_bind = next(arg);
                cfg.ws_bind = cfg.rpc_bind;
            }
            else if (arg == "--port")
            {
                int port = std::stoi(next(arg));
                cfg.rpc_port = port;
                cfg.ws_port = port;
            }
            else if (arg == "--conf")
            {
                cfg.conf_file = next(arg);
            }
            else if (arg == "--rpc-bind")
            {
                cfg.rpc_bind = next(arg);
                cfg.ws_bind = cfg.rpc_bind; // default WS bind mirrors RPC
            }
            else if (arg == "--rpc-port")
            {
                cfg.rpc_port = std::stoi(next(arg));
                cfg.ws_port = cfg.rpc_port; // default WS port mirrors RPC
            }
            else if (arg == "--p2p-bind")
            {
                cfg.p2p_bind = next(arg);
            }
            else if (arg == "--p2p-port")
            {
                cfg.p2p_port = std::stoi(next(arg));
            }
            else if (arg == "--peer")
            {
                cfg.peers.push_back(next(arg));
            }
            else if (arg == "--testnet")
            {
                cfg.testnet = true;
            }
            else if (arg == "--validate-only")
            {
                cfg.validate_only = true;
            }
            else if (arg == "--daemon")
            {
                cfg.daemonize = true;
            }
            else if (arg == "--maxpeers")
            {
                cfg.max_peers = std::stoi(next(arg));
            }
            else if (arg == "--no-hybrid-storage")
            {
                cfg.hybrid_storage = false;
            }
            else if (arg == "--no-update-check")
            {
                cfg.no_update_check = true;
            }
            else if (arg == "--apply-update" || arg.rfind("--apply-update=", 0) == 0)
            {
                std::string value = "yes";
                const auto eq = arg.find('=');
                if (eq != std::string::npos)
                {
                    value = arg.substr(eq + 1);
                }
                cfg.apply_update = !(value == "ask" || value == "log" || value == "0" || value == "no" || value == "false");
            }
            else if (arg == "--no-validator-rewards")
            {
                cfg.validator_rewards_enabled = false;
            }
            // WebSocket / TLS options (Phase 3)
            else if (arg == "--ws-bind")
            {
                cfg.ws_bind = next(arg);
            }
            else if (arg == "--ws-port")
            {
                cfg.ws_port = std::stoi(next(arg));
            }
            else if (arg == "--no-ws")
            {
                cfg.ws_enabled = false;
            }
            else if (arg == "--http-rpc")
            {
                cfg.http_enabled = true;
            }
            else if (arg == "--ws-tls")
            {
                cfg.ws_tls = true;
            }
            else if (arg == "--tls-cert")
            {
                cfg.tls_cert_path = next(arg);
            }
            else if (arg == "--tls-key")
            {
                cfg.tls_key_path = next(arg);
            }
            else if (arg == "--validator-rewards-percentage")
            {
                double pct = std::stod(next(arg));
                // Enforce network maximum (5%)
                if (pct > MAX_VALIDATOR_REWARDS_PERCENTAGE)
                {
                    std::cerr << "Warning: validator rewards percentage " << pct
                              << " exceeds network maximum "
                              << (MAX_VALIDATOR_REWARDS_PERCENTAGE * 100)
                              << "%\n";
                    cfg.validator_rewards_percentage = MAX_VALIDATOR_REWARDS_PERCENTAGE;
                }
                else if (pct > 0.0)
                {
                    cfg.validator_rewards_percentage = pct;
                }
            }
            else if (arg == "--validator-wallet")
            {
                cfg.validator_wallet_address = next(arg);
            }
            else if (arg == "--validator-bucket")
            {
                cfg.validator_bucket_path = next(arg);
                explicit_validator_path = true;
            }
            else if (arg == "-h" || arg == "--help")
            {
                continue;
            }
            else if (!arg.empty() && arg[0] == '-')
            {
                std::cerr << "Unknown option " << arg << "\n";
                std::exit(2);
            }
        }

        // Apply testnet datadir if flagged
        if (cfg.testnet)
        {
            cfg.datadir = default_datadir(true);
            cfg.conf_file = cfg.datadir / "pisecured.conf";
            if (!explicit_validator_path)
            {
                cfg.validator_bucket_path = cfg.datadir / "validator_bucket.json";
            }
            // Keep ws bind/port consistent with rpc by default in testnet
            cfg.ws_bind = cfg.rpc_bind;
            cfg.ws_port = cfg.rpc_port;
        }

        return cfg;
    }
}
