#pragma once

#include <string>
#include <optional>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace pswallet
{

    /**
     * Blockchain API client for wallet operations
     */
    class BlockchainClient
    {
    public:
        /**
         * Create client with blockchain node URL
         * @param node_url Blockchain API URL (e.g., http://localhost:3142)
         * @param timeout Request timeout in seconds
         */
        BlockchainClient(const std::string &node_url, int timeout = 10);

        /**
         * Get wallet balance from blockchain
         * @param wallet_address Wallet address to query
         * @return Balance in tokens or empty on error
         */
        std::optional<double> get_balance(const std::string &wallet_address);

        /**
         * Get wallet transaction history
         * @param wallet_address Wallet address
         * @param limit Maximum transactions to return (default: 50)
         * @return List of transactions or empty on error
         */
        std::optional<std::vector<json>> get_transactions(
            const std::string &wallet_address,
            int limit = 50);

        /**
         * Submit transaction to blockchain
         * @param transaction Transaction JSON to submit
         * @return Transaction hash or empty on error
         */
        std::optional<std::string> submit_transaction(const json &transaction);

        /**
         * Get blockchain info
         * @return Blockchain info or empty on error
         */
        std::optional<json> get_chain_info();

        /**
         * Get pending transactions
         * @return List of pending transactions or empty on error
         */
        std::optional<std::vector<json>> get_pending_transactions();

        /**
         * Validate transaction format
         * @param transaction Transaction to validate
         * @return Error message or empty if valid
         */
        static std::string validate_transaction(const json &transaction);

        /**
         * Get transaction fee for amount and type
         * @param amount Transaction amount
         * @param tx_type Transaction type ("token_transfer", "batch_transfer", etc.)
         * @return Fee amount
         */
        std::optional<double> get_transaction_fee(
            double amount,
            const std::string &tx_type = "token_transfer");

        /**
         * Check if address is valid
         * @param address Address to validate
         * @return True if valid 0x-prefixed hex address
         */
        static bool is_valid_address(const std::string &address);

        /**
         * Check if wallet exists on blockchain
         * @param wallet_address Wallet address to check
         * @return True if wallet has any transactions
         */
        std::optional<bool> wallet_exists(const std::string &wallet_address);

        /**
         * Stream transactions (websocket)
         * @param wallet_address Watch this address (or empty for all)
         * @param callback Callback for new transactions
         * @return Connection handle
         */
        int stream_transactions(
            const std::string &wallet_address,
            std::function<void(const json &)> callback);

        /**
         * Cancel stream subscription
         * @param stream_id Stream handle from stream_transactions
         */
        void cancel_stream(int stream_id);

        /**
         * Get current node status
         * @return Node status or empty on error
         */
        std::optional<json> get_node_status();

    private:
        std::string node_url_;
        int timeout_;
        std::map<int, std::string> active_streams_;
        int next_stream_id_ = 0;

        /**
         * Make HTTP GET request
         * @param endpoint API endpoint path
         * @param params Query parameters
         * @return Response JSON or empty on error
         */
        std::optional<json> http_get(
            const std::string &endpoint,
            const std::map<std::string, std::string> &params = {});

        /**
         * Make HTTP POST request
         * @param endpoint API endpoint path
         * @param data Request body as JSON
         * @return Response JSON or empty on error
         */
        std::optional<json> http_post(const std::string &endpoint, const json &data);

        /**
         * Build full URL from endpoint and parameters
         * @param endpoint API endpoint
         * @param params Query parameters
         * @return Full URL
         */
        std::string build_url(const std::string &endpoint,
                              const std::map<std::string, std::string> &params = {}) const;
    };

} // namespace pswallet
