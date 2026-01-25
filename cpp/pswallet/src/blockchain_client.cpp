#include "blockchain_client.hpp"
#include <curl/curl.h>
#include <iostream>
#include <sstream>
#include <regex>
#include <thread>

namespace pswallet
{

    // Curl callback for HTTP responses
    static size_t curl_write_callback(void *contents, size_t size, size_t nmemb, std::string *userp)
    {
        userp->append((char *)contents, size * nmemb);
        return size * nmemb;
    }

    BlockchainClient::BlockchainClient(const std::string &node_url, int timeout)
        : node_url_(node_url), timeout_(timeout) {}

    std::optional<double> BlockchainClient::get_balance(const std::string &wallet_address)
    {
        if (!is_valid_address(wallet_address))
        {
            return std::nullopt;
        }

        std::map<std::string, std::string> params;
        params["wallet_id"] = wallet_address;

        auto response = http_get("/api/wallet/balance", params);
        if (!response)
        {
            return std::nullopt;
        }

        try
        {
            if (response->contains("balance"))
            {
                return response->at("balance").get<double>();
            }
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error parsing balance: " << e.what() << "\n";
        }

        return std::nullopt;
    }

    std::optional<std::vector<json>> BlockchainClient::get_transactions(
        const std::string &wallet_address,
        int limit)
    {

        if (!is_valid_address(wallet_address))
        {
            return std::nullopt;
        }

        std::map<std::string, std::string> params;
        params["wallet_id"] = wallet_address;
        params["limit"] = std::to_string(limit);

        auto response = http_get("/api/wallet/transactions", params);
        if (!response)
        {
            return std::nullopt;
        }

        try
        {
            std::vector<json> transactions;

            if (response->is_array())
            {
                for (const auto &tx : *response)
                {
                    transactions.push_back(tx);
                }
            }
            else if (response->contains("transactions"))
            {
                for (const auto &tx : response->at("transactions"))
                {
                    transactions.push_back(tx);
                }
            }

            return transactions;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error parsing transactions: " << e.what() << "\n";
        }

        return std::nullopt;
    }

    std::optional<std::string> BlockchainClient::submit_transaction(const json &transaction)
    {
        // Validate transaction first
        std::string error = validate_transaction(transaction);
        if (!error.empty())
        {
            std::cerr << "Transaction validation error: " << error << "\n";
            return std::nullopt;
        }

        auto response = http_post("/api/v1/transactions", transaction);
        if (!response)
        {
            return std::nullopt;
        }

        try
        {
            if (response->contains("tx_hash"))
            {
                return response->at("tx_hash").get<std::string>();
            }
            else if (response->contains("hash"))
            {
                return response->at("hash").get<std::string>();
            }
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error parsing submission response: " << e.what() << "\n";
        }

        return std::nullopt;
    }

    std::optional<json> BlockchainClient::get_chain_info()
    {
        auto response = http_get("/api/v1/chain");
        return response;
    }

    std::optional<std::vector<json>> BlockchainClient::get_pending_transactions()
    {
        auto response = http_get("/api/v1/transactions/pending");
        if (!response)
        {
            return std::nullopt;
        }

        try
        {
            std::vector<json> transactions;

            if (response->is_array())
            {
                for (const auto &tx : *response)
                {
                    transactions.push_back(tx);
                }
            }
            else if (response->contains("transactions"))
            {
                for (const auto &tx : response->at("transactions"))
                {
                    transactions.push_back(tx);
                }
            }

            return transactions;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error parsing pending transactions: " << e.what() << "\n";
        }

        return std::nullopt;
    }

    std::string BlockchainClient::validate_transaction(const json &transaction)
    {
        // Check required fields
        if (!transaction.contains("type"))
        {
            return "Missing 'type' field";
        }

        std::string tx_type = transaction["type"];

        if (tx_type == "token_transfer")
        {
            if (!transaction.contains("sender_address"))
            {
                return "Missing 'sender_address' for token_transfer";
            }
            if (!transaction.contains("recipient_address"))
            {
                return "Missing 'recipient_address' for token_transfer";
            }
            if (!transaction.contains("amount"))
            {
                return "Missing 'amount' for token_transfer";
            }
            if (!transaction.contains("signature"))
            {
                return "Missing 'signature' for token_transfer";
            }
            if (!transaction.contains("tx_hash"))
            {
                return "Missing 'tx_hash' for token_transfer";
            }
            if (!transaction.contains("timestamp"))
            {
                return "Missing 'timestamp' for token_transfer";
            }
            if (!transaction.contains("sender_public_key"))
            {
                return "Missing 'sender_public_key' for token_transfer";
            }

            // Validate addresses
            std::string sender = transaction["sender_address"];
            std::string recipient = transaction["recipient_address"];
            if (!is_valid_address(sender))
            {
                return "Invalid sender address format";
            }
            if (!is_valid_address(recipient))
            {
                return "Invalid recipient address format";
            }

            // Validate amount
            double amount = transaction["amount"];
            if (amount <= 0)
            {
                return "Amount must be greater than zero";
            }

            // Basic tx_hash format check (0x + 64 hex)
            std::string tx_hash = transaction["tx_hash"];
            if (tx_hash.size() != 66 || tx_hash.rfind("0x", 0) != 0)
            {
                return "Invalid tx_hash format";
            }
        }

        return ""; // Valid
    }

    std::optional<double> BlockchainClient::get_transaction_fee(
        double amount,
        const std::string &tx_type)
    {

        // Default fee calculation
        double base_fee = 0.01;
        if (tx_type == "batch_transfer")
        {
            base_fee = 0.02;
        }
        else if (tx_type == "smart_contract")
        {
            base_fee = 0.05;
        }

        double percentage_fee = amount * 0.001; // 0.1% of amount

        return base_fee + percentage_fee;
    }

    bool BlockchainClient::is_valid_address(const std::string &address)
    {
        // Valid address: 0x followed by 40 hex characters
        if (address.length() != 42)
        {
            return false;
        }
        if (address.substr(0, 2) != "0x")
        {
            return false;
        }

        // Check if remaining chars are hex
        for (size_t i = 2; i < address.length(); ++i)
        {
            char c = address[i];
            if (!((c >= '0' && c <= '9') ||
                  (c >= 'a' && c <= 'f') ||
                  (c >= 'A' && c <= 'F')))
            {
                return false;
            }
        }

        return true;
    }

    std::optional<bool> BlockchainClient::wallet_exists(const std::string &wallet_address)
    {
        auto balance = get_balance(wallet_address);
        return balance.has_value(); // If we can query balance, wallet exists
    }

    int BlockchainClient::stream_transactions(
        const std::string &wallet_address,
        std::function<void(const json &)> callback)
    {

        int stream_id = next_stream_id_++;
        active_streams_[stream_id] = wallet_address;

        // Start stream in background thread
        std::thread([this, stream_id, wallet_address, callback]()
                    {
        while (active_streams_.count(stream_id) > 0) {
            auto transactions = get_pending_transactions();
            if (transactions) {
                for (const auto& tx : *transactions) {
                    // Filter for this wallet if specified
                    if (!wallet_address.empty()) {
                        if (tx.contains("sender_address") && 
                            tx["sender_address"] == wallet_address) {
                            callback(tx);
                        } else if (tx.contains("recipient_address") &&
                                   tx["recipient_address"] == wallet_address) {
                            callback(tx);
                        }
                    } else {
                        callback(tx);
                    }
                }
            }
            
            std::this_thread::sleep_for(std::chrono::seconds(2));
        } })
            .detach();

        return stream_id;
    }

    void BlockchainClient::cancel_stream(int stream_id)
    {
        active_streams_.erase(stream_id);
    }

    std::optional<json> BlockchainClient::get_node_status()
    {
        auto response = http_get("/api/v1/node/status");
        return response;
    }

    std::optional<json> BlockchainClient::http_get(
        const std::string &endpoint,
        const std::map<std::string, std::string> &params)
    {

        std::string url = build_url(endpoint, params);

        CURL *curl = curl_easy_init();
        if (!curl)
        {
            return std::nullopt;
        }

        std::string response_str;

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_str);
        curl_easy_setopt(curl, CURLOPT_FAILONERROR, 1L);

        CURLcode res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK)
        {
            return std::nullopt;
        }

        try
        {
            return json::parse(response_str);
        }
        catch (const std::exception &e)
        {
            std::cerr << "JSON parse error: " << e.what() << "\n";
            return std::nullopt;
        }
    }

    std::optional<json> BlockchainClient::http_post(
        const std::string &endpoint,
        const json &data)
    {

        std::string url = node_url_ + endpoint;
        std::string data_str = data.dump();

        CURL *curl = curl_easy_init();
        if (!curl)
        {
            return std::nullopt;
        }

        std::string response_str;
        struct curl_slist *headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");

        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data_str.c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_str);
        curl_easy_setopt(curl, CURLOPT_FAILONERROR, 1L);

        CURLcode res = curl_easy_perform(curl);

        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK)
        {
            return std::nullopt;
        }

        try
        {
            return json::parse(response_str);
        }
        catch (const std::exception &e)
        {
            std::cerr << "JSON parse error: " << e.what() << "\n";
            return std::nullopt;
        }
    }

    std::string BlockchainClient::build_url(
        const std::string &endpoint,
        const std::map<std::string, std::string> &params) const
    {

        std::string url = node_url_ + endpoint;

        if (!params.empty())
        {
            url += "?";
            bool first = true;
            for (const auto &[key, value] : params)
            {
                if (!first)
                    url += "&";
                url += key + "=" + value;
                first = false;
            }
        }

        return url;
    }

} // namespace pswallet
