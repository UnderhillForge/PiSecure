#include "pisecured/ws_client.hpp"
#include <websocketpp/client.hpp>
#include <websocketpp/config/asio_no_tls_client.hpp>
#include <iostream>
#include <thread>

using websocketpp::lib::bind;
using websocketpp::lib::placeholders::_1;
using websocketpp::lib::placeholders::_2;

namespace pisecured
{
    typedef websocketpp::client<websocketpp::config::asio_client> ws_client;
    typedef websocketpp::config::asio_client::message_type::ptr message_ptr;

    // Internal WebSocket connection wrapper with managed thread
    struct WSClient::WSConnectionImpl
    {
        ws_client client;
        websocketpp::connection_hdl hdl;
        std::string response;
        bool response_received = false;
        std::mutex response_mutex;
        std::condition_variable response_cv;
        std::thread run_thread;
        std::atomic<bool> should_stop{false};

        ~WSConnectionImpl()
        {
            // Ensure thread is joined before destruction
            should_stop = true;
            try
            {
                client.stop_perpetual();
            }
            catch (...)
            {
            }
            if (run_thread.joinable())
            {
                run_thread.join();
            }
        }
    };

    WSClient::WSClient(const std::string &url)
        : url_(url), ws_(nullptr)
    {
    }

    WSClient::~WSClient()
    {
        disconnect();
    }

    bool WSClient::connect()
    {
        if (connected_)
            return true;

        try
        {
            auto conn = std::make_unique<WSConnectionImpl>();
            conn->client.clear_access_channels(websocketpp::log::alevel::all);
            conn->client.clear_error_channels(websocketpp::log::elevel::all);
            conn->client.init_asio();
            conn->client.start_perpetual();

            // Message handler
            conn->client.set_message_handler([conn_ptr = conn.get()](websocketpp::connection_hdl, message_ptr msg)
                                             {
                std::lock_guard<std::mutex> lock(conn_ptr->response_mutex);
                conn_ptr->response = msg->get_payload();
                conn_ptr->response_received = true;
                conn_ptr->response_cv.notify_one(); });

            // Connect
            websocketpp::lib::error_code ec;
            ws_client::connection_ptr con = conn->client.get_connection(url_, ec);

            if (ec)
            {
                std::cerr << "WebSocket connection init failed: " << ec.message() << std::endl;
                return false;
            }

            conn->hdl = con->get_handle();
            conn->client.connect(con);

            // Run client in managed thread with stop flag
            conn->run_thread = std::thread([conn_ptr = conn.get()]()
                                           { 
                            while (!conn_ptr->should_stop.load())
                            {
                                conn_ptr->client.run();
                            } });

            // Wait for connection (with timeout)
            std::this_thread::sleep_for(std::chrono::milliseconds(500));

            ws_ = std::move(conn);
            connected_ = true;
            return true;
        }
        catch (const std::exception &e)
        {
            std::cerr << "WebSocket connection exception: " << e.what() << std::endl;
            ws_.reset();
            return false;
        }
    }

    void WSClient::disconnect()
    {
        if (!connected_ || !ws_)
            return;

        connected_ = false;

        if (ws_)
        {
            try
            {
                // Signal thread to stop
                ws_->should_stop = true;
                ws_->client.close(ws_->hdl, websocketpp::close::status::normal, "Disconnect");
                ws_->client.stop_perpetual();

                // Thread cleanup happens in ~WSConnectionImpl destructor
                // unique_ptr will call destructor which joins the thread
            }
            catch (const std::exception &e)
            {
                std::cerr << "WebSocket disconnect error: " << e.what() << std::endl;
            }
        }

        ws_.reset(); // This destroys the unique_ptr, calling ~WSConnectionImpl
    }

    json WSClient::create_request(const std::string &method, const json &params)
    {
        json request;
        request["jsonrpc"] = "2.0";
        request["method"] = method;
        request["id"] = ++request_id_;

        if (!params.empty())
        {
            request["params"] = params;
        }

        return request;
    }

    std::optional<json> WSClient::send_request(const json &request)
    {
        if (!connected_ || !ws_)
            return std::nullopt;

        try
        {
            // Reset response state
            {
                std::lock_guard<std::mutex> lock(ws_->response_mutex);
                ws_->response.clear();
                ws_->response_received = false;
            }

            // Send request
            websocketpp::lib::error_code ec;
            ws_->client.send(ws_->hdl, request.dump(), websocketpp::frame::opcode::text, ec);

            if (ec)
            {
                std::cerr << "WebSocket send failed: " << ec.message() << std::endl;
                return std::nullopt;
            }

            // Wait for response with timeout
            std::unique_lock<std::mutex> lock(ws_->response_mutex);
            if (!ws_->response_cv.wait_for(lock, std::chrono::seconds(5),
                                           [this]
                                           { return ws_->response_received; }))
            {
                std::cerr << "WebSocket response timeout" << std::endl;
                return std::nullopt;
            }

            // Parse response
            json response = json::parse(ws_->response);

            if (response.contains("error"))
            {
                std::cerr << "RPC error: " << response["error"]["message"] << std::endl;
                return std::nullopt;
            }

            if (response.contains("result"))
            {
                return response["result"];
            }

            return response;
        }
        catch (const std::exception &e)
        {
            std::cerr << "WebSocket request exception: " << e.what() << std::endl;
            return std::nullopt;
        }
    }

    std::optional<json> WSClient::call(const std::string &method, const json &params)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        json request = create_request(method, params);
        return send_request(request);
    }

    std::optional<uint32_t> WSClient::get_block_count()
    {
        auto result = call("getblockcount");
        if (result && result->contains("count"))
        {
            return result->at("count").get<uint32_t>();
        }
        return std::nullopt;
    }

    std::optional<json> WSClient::get_block(const std::string &hash_or_height)
    {
        json params = json::array();
        params.push_back(hash_or_height);
        return call("getblock", params);
    }

    std::optional<json> WSClient::get_block_header(uint32_t height)
    {
        json params = json::array();
        params.push_back(height);
        return call("getheader", params);
    }

    std::optional<json> WSClient::get_network_stats()
    {
        return call("getnetworkstats");
    }

    std::optional<json> WSClient::get_mempool(size_t limit)
    {
        json params = json::array();
        params.push_back(limit);
        return call("getmempool", params);
    }

    std::optional<std::string> WSClient::submit_transaction(const json &tx_data)
    {
        json params = json::array();
        params.push_back(tx_data.dump());
        auto result = call("sendtransaction", params);

        if (result && result->contains("hash"))
        {
            return result->at("hash").get<std::string>();
        }
        return std::nullopt;
    }

    std::optional<json> WSClient::get_transaction(const std::string &tx_hash)
    {
        json params = json::array();
        params.push_back(tx_hash);
        return call("gettransaction", params);
    }

    std::optional<json> WSClient::get_block_template()
    {
        // This is a placeholder - actual implementation would require
        // a new RPC method on pisecured
        return call("getblocktemplate");
    }

    bool WSClient::submit_block(uint32_t nonce, const std::string &hash, const json &block_data)
    {
        json params = json::array();
        params.push_back(nonce);
        params.push_back(hash);
        params.push_back(block_data);

        auto result = call("submitblock", params);
        return result.has_value();
    }

    std::optional<json> WSClient::get_bucket_status()
    {
        return call("getbucketstatus");
    }

    std::optional<json> WSClient::get_validator_stats()
    {
        return call("getvalidatorstats");
    }

    void WSClient::subscribe(const std::string &channel, std::function<void(const json &)> callback)
    {
        json params = json::array();
        params.push_back(channel);
        call("subscribe", params);

        // TODO: Set up callback for async notifications
    }

    void WSClient::unsubscribe(const std::string &channel)
    {
        json params = json::array();
        params.push_back(channel);
        call("unsubscribe", params);
    }
}
