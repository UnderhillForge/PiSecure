#pragma once

#include "config.hpp"
#include "storage.hpp"
#include "p2p.hpp"
#include "rpc.hpp"
#include "ws_server.hpp"
#include "validator_purse.hpp"
#include <atomic>
#include <thread>
#include <memory>

namespace pisecured
{
    class Daemon
    {
    public:
        explicit Daemon(const Config &cfg);
        ~Daemon();

        bool start();
        void stop();

        // Validator rewards access
        ValidatorPurse *get_validator_purse() { return validator_purse_.get(); }
        Storage *get_storage() { return &storage_; }
        P2PServer *get_p2p_server() { return &p2p_; }

    private:
        Config config_;
        Storage storage_;
        P2PServer p2p_;
        RPC rpc_;
        WebSocketServer ws_;
        std::unique_ptr<ValidatorPurse> validator_purse_;
        std::atomic<bool> running_{false};
    };
}
