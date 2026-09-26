#pragma once

#include "config.hpp"
#include "storage.hpp"
#include "p2p.hpp"
#include "validator_purse.hpp"
#include <atomic>
#include <string>
#include <thread>
#include <vector>
#include <mutex>
#include <nlohmann/json.hpp>

// libwebsockets
#include <libwebsockets.h>

namespace pisecured
{
    using json = nlohmann::json;

    struct WsConnData
    {
        bool sub_blocks = false;
        bool sub_threats = false;
        bool sub_bucket = false;
        lws *wsi = nullptr;
        // libwebsockets allocates this struct with calloc, so the buffer is
        // created in ESTABLISHED and freed in CLOSED. skip drops the rest of
        // a message that already exceeded the cap, until its final fragment.
        std::string *rx = nullptr;
        bool skip = false;
    };

    class WebSocketServer
    {
    public:
        WebSocketServer() = default;
        ~WebSocketServer();

        bool start(const Config &cfg, Storage *storage, P2PServer *p2p, ValidatorPurse *purse);
        void stop();

        // Broadcast helpers
        void broadcast_threat(const json &threat_obj);
        void broadcast_bucket_update(const json &bucket_obj);
        void broadcast_block(const json &block_obj);

        // libwebsockets protocol callback (public for lws)
        static int callback_pisecure(struct lws *wsi,
                                     enum lws_callback_reasons reason,
                                     void *user,
                                     void *in,
                                     size_t len);

        // Global instance accessor (for lightweight event wiring)
        static WebSocketServer *instance();

    private:
        std::atomic<bool> running_{false};
        std::thread worker_;
        lws_context *context_ = nullptr;
        int port_ = 3144;
        bool use_tls_ = false;
        std::string bind_addr_ = "127.0.0.1";
        std::filesystem::path tls_cert_;
        std::filesystem::path tls_key_;

        Storage *storage_ = nullptr;
        P2PServer *p2p_ = nullptr;
        ValidatorPurse *purse_ = nullptr;

        std::vector<WsConnData *> conns_;
        std::mutex conns_mutex_;

        // Internal helpers
        void run_loop();
        static bool send_json(lws *wsi, const json &obj);
        static json handle_request(json req, Storage *storage, P2PServer *p2p, ValidatorPurse *purse, WsConnData *ud);
    };
}
