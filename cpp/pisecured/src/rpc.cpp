#include "pisecured/rpc.hpp"
#include "pisecured/storage.hpp"
#include "pisecured/p2p.hpp"
#include "pisecured/validator_purse.hpp"
#include <iostream>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <string.h>

namespace pisecured
{
    bool RPC::start(const Config &cfg, Storage *storage, P2PServer *p2p, ValidatorPurse *purse, ThreatDetector *threats)
    {
        if (running_.exchange(true))
        {
            return false;
        }

        storage_ = storage;
        p2p_ = p2p;
        purse_ = purse;
        threats_ = threats;
        rpc_port_ = cfg.rpc_port;

        worker_ = std::thread(&RPC::run_loop, this);
        return true;
    }

    void RPC::stop()
    {
        if (!running_.exchange(false))
        {
            return;
        }
        if (worker_.joinable())
        {
            worker_.join();
        }
    }

    void RPC::run_loop()
    {
        // Create TCP socket for JSON-RPC 2.0 HTTP server
        int server_socket = create_server_socket(rpc_port_);
        if (server_socket < 0)
        {
            std::cerr << "[RPC] Failed to create server socket on port " << rpc_port_ << std::endl;
            return;
        }

        std::cout << "[RPC] Server listening on port " << rpc_port_ << " (JSON-RPC 2.0)" << std::endl;

        while (running_)
        {
            struct sockaddr_in client_addr;
            socklen_t client_len = sizeof(client_addr);
            int client_socket = accept(server_socket, (struct sockaddr *)&client_addr, &client_len);

            if (client_socket < 0)
            {
                continue;
            }

            // Handle HTTP request (simple single-threaded for now)
            char buffer[4096];
            ssize_t bytes = read(client_socket, buffer, sizeof(buffer) - 1);
            if (bytes > 0)
            {
                buffer[bytes] = '\0';

                // Parse HTTP body (naive extraction)
                std::string request_str(buffer);
                size_t body_start = request_str.find("\r\n\r\n");
                if (body_start != std::string::npos)
                {
                    body_start += 4;
                    std::string json_body = request_str.substr(body_start);

                    try
                    {
                        json request_json = json::parse(json_body);
                        json response = handle_request(request_json);

                        // HTTP response
                        std::string response_str = response.dump();
                        std::string http_response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ";
                        http_response += std::to_string(response_str.length());
                        http_response += "\r\n\r\n";
                        http_response += response_str;

                        write(client_socket, http_response.c_str(), http_response.length());
                    }
                    catch (const std::exception &e)
                    {
                        std::cerr << "[RPC] JSON parse error: " << e.what() << std::endl;
                        json error = error_response(-32700, "Parse error");
                        std::string error_str = error.dump();
                        std::string http_error = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: ";
                        http_error += std::to_string(error_str.length());
                        http_error += "\r\n\r\n";
                        http_error += error_str;
                        write(client_socket, http_error.c_str(), http_error.length());
                    }
                }
            }

            close(client_socket);
        }

        close(server_socket);
    }

    int RPC::create_server_socket(int port)
    {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0)
        {
            return -1;
        }

        int opt = 1;
        setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK); // Only localhost
        addr.sin_port = htons(port);

        if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0)
        {
            close(sock);
            return -1;
        }

        if (listen(sock, 5) < 0)
        {
            close(sock);
            return -1;
        }

        return sock;
    }

    json RPC::handle_request(const json &request)
    {
        // Validate JSON-RPC 2.0 request
        if (!request.contains("jsonrpc") || request["jsonrpc"] != "2.0")
        {
            return error_response(-32600, "Invalid Request");
        }

        if (!request.contains("method"))
        {
            return error_response(-32600, "Invalid Request");
        }

        std::string method = request["method"];
        json params = request.contains("params") ? request["params"] : json::array();
        json id = request.contains("id") ? request["id"] : nullptr;

        // Dispatch to method handlers
        try
        {
            if (method == "getblockcount")
                return success_response(method_getblockcount(params), id);
            else if (method == "getblock")
                return success_response(method_getblock(params), id);
            else if (method == "getheader")
                return success_response(method_getheader(params), id);
            else if (method == "gettransaction")
                return success_response(method_gettransaction(params), id);
            else if (method == "sendtransaction")
                return success_response(method_sendtransaction(params), id);
            else if (method == "getmempool")
                return success_response(method_getmempool(params), id);
            else if (method == "getpeers")
                return success_response(method_getpeers(params), id);
            else if (method == "getnetworkstats")
                return success_response(method_getnetworkstats(params), id);
            else if (method == "getthreats")
                return success_response(method_getthreats(params), id);
            else if (method == "reportthreat")
                return success_response(method_reportthreat(params), id);
            else if (method == "getvalidatorstats")
                return success_response(method_getvalidatorstats(params), id);
            else if (method == "getbucketstatus" || method == "getpursestatus")
                return success_response(method_getbucketstatus(params), id);
            else if (method == "submitblock")
                return success_response(method_submitblock(params), id);
            else if (method == "getblocktemplate")
                return success_response(method_getblocktemplate(params), id);
            else
                return error_response(-32601, "Method not found", id);
        }
        catch (const std::exception &e)
        {
            return error_response(-32603, std::string("Internal error: ") + e.what(), id);
        }
    }

    // ========== Blockchain Query Methods ==========

    json RPC::method_getblockcount(const json &params)
    {
        if (!storage_)
            return json::object();

        json result;
        result["count"] = storage_->get_best_height();
        result["timestamp"] = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000;
        return result;
    }

    json RPC::method_getblock(const json &params)
    {
        if (!storage_ || params.empty())
            throw std::runtime_error("Missing block hash parameter");

        std::string hash_str = params[0].get<std::string>();
        if (hash_str.length() != 64)
            throw std::runtime_error("Invalid block hash length");

        // Convert hex string to array
        std::array<uint8_t, 32> hash;
        for (size_t i = 0; i < 32; i++)
        {
            hash[i] = std::stoi(hash_str.substr(i * 2, 2), nullptr, 16);
        }

        auto header = storage_->get_header_by_hash(hash);
        if (!header)
            throw std::runtime_error("Block not found");

        json result;
        result["hash"] = hash_str;
        result["height"] = header->height;
        result["version"] = header->version;
        result["timestamp"] = header->timestamp;
        result["difficulty"] = header->difficulty;
        result["nonce"] = header->nonce;
        return result;
    }

    json RPC::method_getheader(const json &params)
    {
        if (!storage_ || params.empty())
            throw std::runtime_error("Missing height parameter");

        uint32_t height = params[0].get<uint32_t>();
        auto header = storage_->get_header_by_height(height);
        if (!header)
            throw std::runtime_error("Header not found");

        json result;
        result["height"] = header->height;
        result["timestamp"] = header->timestamp;
        result["difficulty"] = header->difficulty;
        result["version"] = header->version;
        return result;
    }

    json RPC::method_gettransaction(const json &params)
    {
        if (!storage_ || params.empty())
            throw std::runtime_error("Missing transaction hash parameter");

        std::string hash_str = params[0].get<std::string>();
        std::array<uint8_t, 32> hash;
        for (size_t i = 0; i < 32; i++)
        {
            hash[i] = std::stoi(hash_str.substr(i * 2, 2), nullptr, 16);
        }

        auto tx = storage_->get_transaction(hash);
        if (!tx)
            throw std::runtime_error("Transaction not found");

        json result;
        result["hash"] = hash_str;
        result["timestamp"] = tx->timestamp;
        result["fee"] = tx->fee;
        result["size"] = tx->data.size();
        return result;
    }

    json RPC::method_sendtransaction(const json &params)
    {
        if (!storage_ || params.empty())
            throw std::runtime_error("Missing transaction data");

        // Placeholder for transaction relay
        json result;
        result["status"] = "accepted";
        result["message"] = "Transaction will be relayed to network";
        return result;
    }

    json RPC::method_getmempool(const json &params)
    {
        if (!storage_)
            return json::array();

        auto mempool = storage_->get_mempool_transactions(100);
        json result = json::array();

        for (const auto &tx : mempool)
        {
            json tx_obj;
            tx_obj["fee"] = tx.fee;
            tx_obj["size"] = tx.data.size();
            result.push_back(tx_obj);
        }

        return result;
    }

    // ========== Network Diagnostics ==========

    json RPC::method_getpeers(const json &params)
    {
        if (!p2p_)
            return json::array();

        // This would require exposing peer list from P2PServer
        // For now, return placeholder
        json result = json::array();
        return result;
    }

    json RPC::method_getnetworkstats(const json &params)
    {
        json result;
        result["active_connections"] = 0;
        result["inbound_connections"] = 0;
        result["outbound_connections"] = 0;
        result["network_uptime_seconds"] = 0;
        result["bytes_received"] = 0;
        result["bytes_sent"] = 0;
        result["protocol_version"] = 1;
        result["testnet"] = false;
        return result;
    }

    // ========== Threat Reporting ==========

    json RPC::method_getthreats(const json &params)
    {
        if (!threats_)
            return json::array();

        // Get recent threats (last hour by default)
        uint64_t time_window = params.empty() ? 3600 : params[0].get<uint64_t>();
        auto threat_list = threats_->getRecentThreats(time_window);

        json result = json::array();
        for (const auto &threat : threat_list)
        {
            json threat_obj;
            threat_obj["type"] = threat.threatType;
            threat_obj["ip"] = threat.sourceIP;
            threat_obj["severity"] = threat.confidenceScore;
            threat_obj["timestamp"] = threat.timestamp;
            result.push_back(threat_obj);
        }

        return result;
    }

    json RPC::method_reportthreat(const json &params)
    {
        if (!threats_ || params.empty())
            throw std::runtime_error("Missing threat details");

        ThreatAlert alert;
        alert.threatType = params.contains("type") ? params["type"].get<std::string>() : "unknown";
        alert.sourceIP = params.contains("ip") ? params["ip"].get<uint32_t>() : 0;
        alert.timestamp = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000;
        alert.confidenceScore = params.contains("severity") ? params["severity"].get<double>() : 0.5;

        threats_->recordThreat(alert);

        json result;
        result["status"] = "recorded";
        result["threat_id"] = alert.threatType;
        return result;
    }

    // ========== Validator Stats ==========

    json RPC::method_getvalidatorstats(const json &params)
    {
        if (!purse_)
            throw std::runtime_error("Validator purse not available");

        json result;
        result["linked_wallet"] = purse_->get_linked_wallet();
        result["auto_sweep_enabled"] = purse_->should_auto_sweep();
        result["total_rewards_percentage"] = 0.01; // From config
        return result;
    }

    json RPC::method_getbucketstatus(const json &params)
    {
        if (!purse_)
            throw std::runtime_error("Validator bucket not available");

        json result;
        result["current_balance"] = purse_->get_balance();
        result["lifetime_earned"] = purse_->get_lifetime_earned();
        result["linked_wallet"] = purse_->get_linked_wallet();
        result["auto_sweep_enabled"] = purse_->should_auto_sweep();
        return result;
    }

    json RPC::method_submitblock(const json &params)
    {
        if (!storage_ || !p2p_ || params.size() < 3)
            throw std::runtime_error("Missing block submission parameters (nonce, hash, data)");

        uint32_t nonce = params[0].get<uint32_t>();
        std::string hash_str = params[1].get<std::string>();
        json block_data = params[2];

        // TODO: Validate block and add to storage
        // For now, accept and relay to P2P network

        json result;
        result["status"] = "accepted";
        result["hash"] = hash_str;
        result["message"] = "Block will be validated and relayed to network";

        return result;
    }

    json RPC::method_getblocktemplate(const json &params)
    {
        if (!storage_)
            throw std::runtime_error("Storage not available");

        // Get current best block
        uint32_t height = storage_->get_best_height();
        auto best_hash = storage_->get_best_block_hash();

        // Generate template for next block
        json result;
        result["height"] = height + 1;
        result["prev_block_hash"] = ""; // Convert best_hash to hex string
        result["timestamp"] = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000;
        result["difficulty"] = 146; // Current network difficulty
        result["version"] = 1;

        return result;
    }

    // ========== Error & Success Responses ==========

    json RPC::error_response(int code, const std::string &message, const json &id)
    {
        json response;
        response["jsonrpc"] = "2.0";
        response["error"]["code"] = code;
        response["error"]["message"] = message;
        if (!id.is_null())
        {
            response["id"] = id;
        }
        return response;
    }

    json RPC::success_response(const json &result, const json &id)
    {
        json response;
        response["jsonrpc"] = "2.0";
        response["result"] = result;
        if (!id.is_null())
        {
            response["id"] = id;
        }
        return response;
    }
}
