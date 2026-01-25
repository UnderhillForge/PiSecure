#pragma once

#include <string>
#include <map>
#include <vector>
#include <optional>
#include <memory>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace pswallet
{

    /**
     * Wallet transaction representation
     */
    struct Transaction
    {
        std::string type;               // "token_transfer", "batch_transfer", "smart_contract"
        std::string tx_hash;            // Blockchain transaction hash
        double amount = 0.0;            // Amount transferred
        std::string recipient_address;  // Recipient address
        std::string sender_address;     // Sender address
        std::string sender_public_key;  // Sender public key (PEM) for signature verification
        std::string memo;               // Optional memo
        long long timestamp = 0;        // Unix timestamp
        std::string signature;          // RSA PSS signature (hex)
        std::string status = "pending"; // "pending", "confirmed", "failed"
        json metadata;                  // Additional transaction data
    };

    /**
     * Wallet information
     */
    struct WalletInfo
    {
        std::string wallet_id;                 // Unique wallet ID
        std::string address;                   // Blockchain address (0x-prefixed)
        std::string public_key;                // PEM-encoded public key
        std::string name;                      // Display name
        double balance = 0.0;                  // Current balance (from blockchain)
        long long created_at = 0;              // Creation timestamp
        std::vector<Transaction> transactions; // Transaction history
        bool cold_storage = false;             // Cold storage flag
        std::string version = "1.0";           // Wallet version
    };

    /**
     * PiSecure cryptographic wallet
     */
    class Wallet
    {
    public:
        /**
         * Create a new wallet
         * @param wallet_id Unique wallet identifier
         * @param name Display name
         * @return Wallet info or error
         */
        static std::optional<WalletInfo> create_wallet(
            const std::string &wallet_id,
            const std::string &name = "");

        /**
         * Load wallet from file
         * @param wallet_id Wallet ID to load
         * @return Wallet info or empty if not found
         */
        static std::optional<WalletInfo> load_wallet(const std::string &wallet_id);

        /**
         * Save wallet to file
         * @param wallet Wallet to save
         * @return Success flag
         */
        static bool save_wallet(const WalletInfo &wallet);

        /**
         * List all available wallets
         * @return List of wallet IDs
         */
        static std::vector<std::string> list_wallets();

        /**
         * Create a transfer transaction
         * @param sender_wallet Sender wallet ID
         * @param recipient_address Recipient wallet address
         * @param amount Amount to transfer
         * @param memo Optional transaction memo
         * @return Signed transaction or error
         */
        static std::optional<Transaction> create_transfer(
            const std::string &sender_wallet,
            const std::string &recipient_address,
            double amount,
            const std::string &memo = "");

        /**
         * Create a batch transfer transaction
         * @param sender_wallet Sender wallet ID
         * @param transfers List of recipient->amount pairs
         * @param memo Optional memo
         * @return Signed batch transaction or error
         */
        static std::optional<Transaction> create_batch_transfer(
            const std::string &sender_wallet,
            const std::vector<std::pair<std::string, double>> &transfers,
            const std::string &memo = "");

        /**
         * Sign a transaction
         * @param transaction Transaction to sign
         * @param private_key_pem Private key in PEM format
         * @return Signature (hex) or empty
         */
        static std::optional<std::string> sign_transaction(
            const Transaction &transaction,
            const std::string &private_key_pem);

        /**
         * Verify transaction signature
         * @param transaction Transaction to verify
         * @param signature Signature (hex)
         * @param public_key_pem Public key in PEM format
         * @return True if signature is valid
         */
        static bool verify_transaction_signature(
            const Transaction &transaction,
            const std::string &signature,
            const std::string &public_key_pem);

        /**
         * Get wallet directory path
         * @param testnet Use testnet directory
         * @return Wallet directory path
         */
        static std::string get_wallet_dir(bool testnet = false);

        /**
         * Export wallet (with optional encryption)
         * @param wallet_id Wallet to export
         * @param password Optional password for encryption
         * @return Export data as JSON
         */
        static std::optional<json> export_wallet(
            const std::string &wallet_id,
            const std::string &password = "");

        /**
         * Import wallet from export
         * @param export_data Export JSON
         * @param password Password if encrypted
         * @return Imported wallet info or error
         */
        static std::optional<WalletInfo> import_wallet(
            const json &export_data,
            const std::string &password = "");

    private:
        /**
         * Get wallet file path
         * @param wallet_id Wallet ID
         * @param testnet Use testnet
         * @return File path
         */
        static std::string get_wallet_file(const std::string &wallet_id, bool testnet = false);

        /**
         * Generate RSA key pair
         * @return Pair of (private_key_pem, public_key_pem)
         */
        static std::pair<std::string, std::string> generate_keypair();

        /**
         * Get wallet address from public key
         * @param public_key_pem Public key in PEM format
         * @return Blockchain address (0x-prefixed)
         */
        static std::string derive_address(const std::string &public_key_pem);
    };

} // namespace pswallet
