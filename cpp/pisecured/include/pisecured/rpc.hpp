#pragma once

#include "config.hpp"
#include "storage.hpp"
#include "p2p.hpp"
#include <thread>
#include <atomic>
#include <memory>
#include <nlohmann/json.hpp>

namespace pisecured
{
    using json = nlohmann::json;

    // Forward declare daemon components
    class Storage;
    class P2PServer;
    class ValidatorPurse;
    class ThreatDetector;

    class RPC
    {
    public:
        RPC() = default;

        // Lifecycle
        bool start(const Config &cfg, Storage *storage, P2PServer *p2p, ValidatorPurse *purse, ThreatDetector *threats);
        void stop();

        // JSON-RPC request handler
        json handle_request(const json &request);

    private:
        std::atomic<bool> running_{false};
        std::thread worker_;
        int rpc_port_ = 3144;

        // Component references
        Storage *storage_ = nullptr;
        P2PServer *p2p_ = nullptr;
        ValidatorPurse *purse_ = nullptr;
        ThreatDetector *threats_ = nullptr;

        void run_loop();
        int create_server_socket(int port);

        // JSON-RPC 2.0 Method Handlers
        json method_getblockcount(const json &params);
        json method_getblock(const json &params);
        json method_getheader(const json &params);
        json method_gettransaction(const json &params);
        json method_sendtransaction(const json &params);
        json method_getmempool(const json &params);
        json method_getpeers(const json &params);
        json method_getnetworkstats(const json &params);
        json method_getthreats(const json &params);
        json method_reportthreat(const json &params);
        json method_getvalidatorstats(const json &params);
        json method_getbucketstatus(const json &params);
        json method_submitblock(const json &params);
        json method_getblocktemplate(const json &params);

        // Error responses
        json error_response(int code, const std::string &message, const json &id = nullptr);
        json success_response(const json &result, const json &id = nullptr);
    };
}
