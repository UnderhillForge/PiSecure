#include "pisecured/ws_server.hpp"
#include "pisecured/chain_rpc.hpp"
#include <iostream>
#include <cstring>
#include <algorithm>

namespace pisecured
{
    using json = nlohmann::json;

    // Global instance pointer for lightweight cross-component notifications
    static WebSocketServer *g_ws_instance = nullptr;

    static int lws_protocol_callback(struct lws *wsi,
                                     enum lws_callback_reasons reason,
                                     void *user,
                                     void *in,
                                     size_t len)
    {
        return WebSocketServer::callback_pisecure(wsi, reason, user, in, len);
    }

    WebSocketServer::~WebSocketServer()
    {
        stop();
    }

    bool WebSocketServer::start(const Config &cfg, Storage *storage, P2PServer *p2p, ValidatorPurse *purse)
    {
        if (running_.exchange(true))
            return false;
        storage_ = storage;
        p2p_ = p2p;
        purse_ = purse;
        port_ = cfg.ws_port;
        bind_addr_ = cfg.ws_bind;
        use_tls_ = cfg.ws_tls;
        tls_cert_ = cfg.tls_cert_path;
        tls_key_ = cfg.tls_key_path;

        // Set global instance
        g_ws_instance = this;

        worker_ = std::thread(&WebSocketServer::run_loop, this);
        return true;
    }

    void WebSocketServer::stop()
    {
        if (!running_.exchange(false))
            return;
        if (context_)
        {
            lws_context_destroy(context_);
            context_ = nullptr;
        }
        if (worker_.joinable())
            worker_.join();
        // Clean up connection tracking
        {
            std::lock_guard<std::mutex> lock(conns_mutex_);
            conns_.clear();
        }

        // Clear global instance
        g_ws_instance = nullptr;
    }

    void WebSocketServer::run_loop()
    {
        lws_context_creation_info info;
        memset(&info, 0, sizeof(info));

        static const struct lws_protocols protocols[] = {
            {"pisecure", lws_protocol_callback, sizeof(WsConnData), 4096},
            {NULL, NULL, 0, 0}};

        info.port = port_;
        info.protocols = protocols;
        info.options = LWS_SERVER_OPTION_DO_SSL_GLOBAL_INIT;
        info.iface = bind_addr_.c_str();

        if (use_tls_ && !tls_cert_.empty() && !tls_key_.empty())
        {
            // Keep local strings alive during context creation
            static std::string cert_str;
            static std::string key_str;
            cert_str = tls_cert_.string();
            key_str = tls_key_.string();
            info.ssl_cert_filepath = cert_str.c_str();
            info.ssl_private_key_filepath = key_str.c_str();
        }

        context_ = lws_create_context(&info);
        if (!context_)
        {
            std::cerr << "[WS] Failed to create libwebsockets context on port " << port_ << std::endl;
            return;
        }

        std::cout << "[WS] WebSocket server listening on ws" << (use_tls_ ? "s" : "")
                  << "://" << bind_addr_ << ":" << port_ << " (libwebsockets)" << std::endl;

        while (running_)
        {
            lws_service(context_, 50);
        }
    }

    int WebSocketServer::callback_pisecure(struct lws *wsi,
                                           enum lws_callback_reasons reason,
                                           void *user,
                                           void *in,
                                           size_t len)
    {
        auto *ud = reinterpret_cast<WsConnData *>(user);
        switch (reason)
        {
        case LWS_CALLBACK_ESTABLISHED:
            ud->wsi = wsi;
            // Track connection
            if (g_ws_instance)
            {
                std::lock_guard<std::mutex> lock(g_ws_instance->conns_mutex_);
                g_ws_instance->conns_.push_back(ud);
            }
            break;
        case LWS_CALLBACK_RECEIVE:
            try
            {
                std::string msg(reinterpret_cast<const char *>(in), len);
                auto req = json::parse(msg);
                auto resp = handle_request(req,
                                           g_ws_instance ? g_ws_instance->storage_ : nullptr,
                                           g_ws_instance ? g_ws_instance->p2p_ : nullptr,
                                           g_ws_instance ? g_ws_instance->purse_ : nullptr,
                                           ud);
                send_json(wsi, resp);

                // If it's a subscription, optionally send a snapshot for the topic
                std::string method = req.value("method", "");
                if (method == "subscribe")
                {
                    json params = req.value("params", json::array());
                    std::string topic = params.is_array() && !params.empty() ? params[0].get<std::string>() : "";
                    if (g_ws_instance)
                    {
                        if (topic == "bucket" && g_ws_instance->purse_)
                        {
                            auto st = g_ws_instance->purse_->get_state();
                            json bucket_obj = {
                                {"balance", st.total_balance},
                                {"lifetime_earned", st.lifetime_earned},
                                {"lifetime_withdrawn", st.lifetime_withdrawn},
                                {"blocks_validated", st.blocks_validated},
                                {"last_block_height", st.last_block_height},
                                {"last_updated", st.last_updated},
                                {"wallet", st.linked_wallet_address}};
                            json msg_out = {{"jsonrpc", "2.0"}, {"method", "bucket"}, {"params", bucket_obj}};
                            send_json(wsi, msg_out);
                        }
                        else if (topic == "blocks" && g_ws_instance->storage_)
                        {
                            // Send a minimal tip snapshot
                            uint32_t tip = g_ws_instance->storage_->get_best_height();
                            json block_obj = {{"type", "tip"}, {"height", tip}};
                            json msg_out = {{"jsonrpc", "2.0"}, {"method", "block"}, {"params", block_obj}};
                            send_json(wsi, msg_out);
                        }
                    }
                }
            }
            catch (const std::exception &e)
            {
                json err;
                err["jsonrpc"] = "2.0";
                err["error"]["code"] = -32700;
                err["error"]["message"] = std::string("Parse error: ") + e.what();
                send_json(wsi, err);
            }
            break;
        case LWS_CALLBACK_SERVER_WRITEABLE:
            // No-op; we write immediately upon requests
            break;
        case LWS_CALLBACK_CLOSED:
            // Remove from connection tracking
            if (g_ws_instance)
            {
                std::lock_guard<std::mutex> lock(g_ws_instance->conns_mutex_);
                auto &vec = g_ws_instance->conns_;
                vec.erase(std::remove(vec.begin(), vec.end(), ud), vec.end());
            }
            break;
        default:
            break;
        }
        return 0;
    }

    bool WebSocketServer::send_json(lws *wsi, const json &obj)
    {
        auto s = obj.dump();
        size_t len = s.size();
        std::vector<unsigned char> buf(LWS_PRE + len);
        memcpy(buf.data() + LWS_PRE, s.data(), len);
        int n = lws_write(wsi, buf.data() + LWS_PRE, len, LWS_WRITE_TEXT);
        return n >= 0;
    }

    json WebSocketServer::handle_request(json req, Storage *storage, P2PServer *p2p, ValidatorPurse *purse, WsConnData *ud)
    {
        json id = req.contains("id") ? req["id"] : nullptr;
        json result;

        if (!req.contains("jsonrpc") || req["jsonrpc"] != "2.0")
        {
            return {
                {"jsonrpc", "2.0"},
                {"error", {{"code", -32600}, {"message", "Invalid Request"}}},
                {"id", id}};
        }

        std::string method = req.value("method", "");
        json params = req.value("params", json::array());

        try
        {
            if (method == "subscribe")
            {
                std::string topic = params.is_array() && !params.empty() ? params[0].get<std::string>() : "";
                if (topic == "blocks")
                    ud->sub_blocks = true;
                else if (topic == "threats")
                    ud->sub_threats = true;
                else if (topic == "bucket")
                    ud->sub_bucket = true;
                result["status"] = "subscribed";
                result["topic"] = topic;
            }
            else if (method == "ping")
            {
                result["status"] = "pong";
            }
            else if (method == "getblockcount")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result["count"] = storage->get_best_height();
            }
            else if (method == "getnetworkstats")
            {
                if (!storage || !p2p)
                    throw std::runtime_error("components not available");
                result["best_height"] = storage->get_best_height();
                result["peer_count"] = static_cast<uint32_t>(p2p->getPeerCount());
            }
            else if (method == "getpeers")
            {
                if (!p2p)
                    throw std::runtime_error("p2p not available");
                result["count"] = static_cast<uint32_t>(p2p->getPeerCount());
                result["self"] = {{"address", p2p->reachableHost()}, {"port", p2p->listenPort()}, {"host", "pisecure.local"}};
            }
            else if (method == "getthreats")
            {
                if (!p2p)
                    throw std::runtime_error("p2p not available");
                auto threats = p2p->getNetworkThreats();
                json arr = json::array();
                for (const auto &t : threats)
                {
                    uint32_t ip_be = t.sourceIP;
                    uint8_t a = (ip_be >> 24) & 0xFF;
                    uint8_t b = (ip_be >> 16) & 0xFF;
                    uint8_t c = (ip_be >> 8) & 0xFF;
                    uint8_t d = ip_be & 0xFF;
                    std::string ip_str = std::to_string(a) + "." + std::to_string(b) + "." + std::to_string(c) + "." + std::to_string(d);
                    arr.push_back({{"type", t.threatType},
                                   {"severity", t.severity},
                                   {"source_ip", ip_str},
                                   {"timestamp", t.timestamp},
                                   {"details", t.details},
                                   {"reporting_node_id", t.reportingNodeId},
                                   {"confidence", t.confidenceScore}});
                }
                result["threats"] = arr;
            }
            else if (method == "reportthreat")
            {
                if (!p2p)
                    throw std::runtime_error("p2p not available");
                std::string type = params.size() > 0 ? params[0].get<std::string>() : "unknown";
                std::string severity = params.size() > 1 ? params[1].get<std::string>() : "low";
                std::string source_ip = params.size() > 2 ? params[2].get<std::string>() : "0.0.0.0";
                std::string details = params.size() > 3 ? params[3].get<std::string>() : "";
                uint32_t ip = 0;
                unsigned a, b, c, d;
                if (sscanf(source_ip.c_str(), "%u.%u.%u.%u", &a, &b, &c, &d) == 4)
                {
                    ip = (a << 24) | (b << 16) | (c << 8) | d;
                }
                ThreatAlert alert{type, severity, ip, (uint64_t)std::time(nullptr), details, "local", 0.8};
                p2p->broadcastThreatAlert(alert);
                result["status"] = "recorded";
            }
            else if (method == "getvalidatorstats")
            {
                if (!purse)
                    throw std::runtime_error("validator bucket not available");
                result["linked_wallet"] = purse->get_linked_wallet();
                result["auto_sweep_enabled"] = purse->should_auto_sweep();
            }
            else if (method == "getbucketstatus")
            {
                if (!purse)
                    throw std::runtime_error("validator bucket not available");
                result["current_balance"] = purse->get_balance();
                result["lifetime_earned"] = purse->get_lifetime_earned();
                result["linked_wallet"] = purse->get_linked_wallet();
                result["auto_sweep_enabled"] = purse->should_auto_sweep();
            }
            else if (method == "getblock")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_getblock(*storage, params);
            }
            else if (method == "getheader")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_getheader(*storage, params);
            }
            else if (method == "listunspent")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_listunspent(*storage, params);
            }
            else if (method == "gettransaction")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                if (params.empty())
                    throw std::runtime_error("gettransaction requires tx hash parameter");
                result["found"] = false;
                result["hash"] = "placeholder_tx_hash";
            }
            else if (method == "getmempool")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_getmempool(*storage);
            }
            else if (method == "sendtransaction")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_sendtransaction(*storage, params);
            }
            else if (method == "getblocktemplate")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                result = rpc_getblocktemplate(*storage, params);
            }
            else if (method == "submitblock")
            {
                if (!storage)
                    throw std::runtime_error("storage not available");
                // Validation does not depend on this host being a Pi, and does not mine.
                result = rpc_submitblock(*storage, p2p, params);
            }
            else if (method == "pinsregister")
            {
                // PiNS service registration stub (Phase 3)
                std::string service_name = params.size() > 0 ? params[0].get<std::string>() : "unknown";
                std::string service_host = params.size() > 1 ? params[1].get<std::string>() : "localhost";
                int service_port = params.size() > 2 ? params[2].get<int>() : 0;
                result["service"] = service_name;
                result["registered"] = true;
                result["endpoint"] = service_host + ":" + std::to_string(service_port);
            }
            else if (method == "pinsresolve")
            {
                // PiNS name resolution stub (Phase 3)
                std::string service_name = params.size() > 0 ? params[0].get<std::string>() : "unknown";
                result["service"] = service_name;
                result["endpoint"] = "localhost:9999"; // Placeholder
                result["found"] = false;
            }
            else
            {
                // Unsupported method
                return {
                    {"jsonrpc", "2.0"},
                    {"error", {{"code", -32601}, {"message", "Method not found"}}},
                    {"id", id}};
            }
        }
        catch (const std::exception &e)
        {
            return {
                {"jsonrpc", "2.0"},
                {"error", {{"code", -32603}, {"message", std::string("Internal error: ") + e.what()}}},
                {"id", id}};
        }

        return {
            {"jsonrpc", "2.0"},
            {"result", result},
            {"id", id}};
    }

    void WebSocketServer::broadcast_threat(const json &threat_obj)
    {
        std::lock_guard<std::mutex> lock(conns_mutex_);
        for (auto *ud : conns_)
        {
            if (ud->sub_threats && ud->wsi)
            {
                json msg = {{"jsonrpc", "2.0"}, {"method", "threat"}, {"params", threat_obj}};
                send_json(ud->wsi, msg);
            }
        }
    }

    void WebSocketServer::broadcast_bucket_update(const json &bucket_obj)
    {
        std::lock_guard<std::mutex> lock(conns_mutex_);
        for (auto *ud : conns_)
        {
            if (ud->sub_bucket && ud->wsi)
            {
                json msg = {{"jsonrpc", "2.0"}, {"method", "bucket"}, {"params", bucket_obj}};
                send_json(ud->wsi, msg);
            }
        }
    }

    void WebSocketServer::broadcast_block(const json &block_obj)
    {
        std::lock_guard<std::mutex> lock(conns_mutex_);
        for (auto *ud : conns_)
        {
            if (ud->sub_blocks && ud->wsi)
            {
                json msg = {{"jsonrpc", "2.0"}, {"method", "block"}, {"params", block_obj}};
                send_json(ud->wsi, msg);
            }
        }
    }

    WebSocketServer *WebSocketServer::instance()
    {
        return g_ws_instance;
    }
}
