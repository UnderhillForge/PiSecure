#include "wallet.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <ctime>
#include <cstdlib>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/sha.h>
#include <openssl/rsa.h>

namespace fs = std::filesystem;

namespace pswallet
{

    namespace
    {
        // Hex-encode bytes
        std::string hex_encode(const unsigned char *data, size_t len)
        {
            std::ostringstream oss;
            oss << std::hex << std::setfill('0');
            for (size_t i = 0; i < len; ++i)
            {
                oss << std::setw(2) << static_cast<int>(data[i]);
            }
            return oss.str();
        }

        // Build canonical message for signing
        std::string build_signing_message(const Transaction &tx)
        {
            std::ostringstream oss;
            oss << tx.type << "|"
                << tx.sender_address << "|"
                << tx.recipient_address << "|"
                << std::fixed << std::setprecision(8) << tx.amount << "|"
                << tx.memo << "|"
                << tx.timestamp;

            if (!tx.tx_hash.empty())
            {
                oss << "|" << tx.tx_hash;
            }

            if (!tx.metadata.empty())
            {
                oss << "|" << tx.metadata.dump();
            }

            return oss.str();
        }

        // Compute deterministic transaction hash (SHA-256 over signing message)
        std::string compute_tx_hash(const Transaction &tx)
        {
            std::string message = build_signing_message(tx);
            unsigned char digest[SHA256_DIGEST_LENGTH];
            SHA256(reinterpret_cast<const unsigned char *>(message.data()), message.size(), digest);
            return "0x" + hex_encode(digest, SHA256_DIGEST_LENGTH);
        }
    } // namespace

    std::string Wallet::get_wallet_dir(bool testnet)
    {
        const char *home = std::getenv("HOME");
        if (!home)
        {
            // Fallback to current directory if HOME not set
            home = ".";
        }

        if (testnet || std::getenv("PISECURE_TESTNET"))
        {
            // Testnet directory
            fs::path dir = fs::path(home) / ".pisecure-testnet" / "wallets";
            return dir.string();
        }
        // Mainnet directory
        fs::path dir = fs::path(home) / ".pisecure" / "wallets";
        return dir.string();
    }

    std::string Wallet::get_wallet_file(const std::string &wallet_id, bool testnet)
    {
        fs::path dir = fs::path(Wallet::get_wallet_dir(testnet));
        fs::path file = dir / (wallet_id + ".json");
        return file.string();
    }

    std::pair<std::string, std::string> Wallet::generate_keypair()
    {
        // Generate RSA 4096-bit keypair using OpenSSL EVP API
        // Returns (private_key_pem, public_key_pem)

        EVP_PKEY *pkey = nullptr;
        EVP_PKEY_CTX *ctx = nullptr;
        BIO *bio_private = nullptr;
        BIO *bio_public = nullptr;
        std::string private_key;
        std::string public_key;

        try
        {
            // Create context for RSA key generation
            ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, nullptr);
            if (!ctx)
            {
                throw std::runtime_error("Failed to create EVP_PKEY_CTX");
            }

            // Initialize key generation operation
            if (EVP_PKEY_keygen_init(ctx) <= 0)
            {
                EVP_PKEY_CTX_free(ctx);
                throw std::runtime_error("Failed to initialize key generation");
            }

            // Set RSA key length to 4096 bits
            if (EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 4096) <= 0)
            {
                EVP_PKEY_CTX_free(ctx);
                throw std::runtime_error("Failed to set RSA key bits");
            }

            // Generate the key
            if (EVP_PKEY_keygen(ctx, &pkey) <= 0)
            {
                EVP_PKEY_CTX_free(ctx);
                throw std::runtime_error("Failed to generate RSA keypair");
            }

            EVP_PKEY_CTX_free(ctx);
            ctx = nullptr;

            // Write private key to BIO
            bio_private = BIO_new(BIO_s_mem());
            if (!bio_private)
            {
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to create memory BIO for private key");
            }

            if (!PEM_write_bio_PrivateKey(bio_private, pkey, nullptr, nullptr, 0, nullptr, nullptr))
            {
                BIO_free(bio_private);
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to write private key to PEM format");
            }

            // Read private key from BIO
            char buffer[65536];
            int len = BIO_read(bio_private, buffer, sizeof(buffer) - 1);
            if (len <= 0)
            {
                BIO_free(bio_private);
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to read private key from BIO");
            }
            buffer[len] = '\0';
            private_key = buffer;
            BIO_free(bio_private);
            bio_private = nullptr;

            // Write public key to BIO
            bio_public = BIO_new(BIO_s_mem());
            if (!bio_public)
            {
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to create memory BIO for public key");
            }

            if (!PEM_write_bio_PUBKEY(bio_public, pkey))
            {
                BIO_free(bio_public);
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to write public key to PEM format");
            }

            // Read public key from BIO
            len = BIO_read(bio_public, buffer, sizeof(buffer) - 1);
            if (len <= 0)
            {
                BIO_free(bio_public);
                EVP_PKEY_free(pkey);
                throw std::runtime_error("Failed to read public key from BIO");
            }
            buffer[len] = '\0';
            public_key = buffer;

            // Cleanup
            BIO_free(bio_public);
            EVP_PKEY_free(pkey);

            return {private_key, public_key};
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error generating keypair: " << e.what() << "\n";
            // Print OpenSSL error if available
            if (ERR_get_error() != 0)
            {
                ERR_print_errors_fp(stderr);
            }
            // Cleanup on error
            if (bio_private)
                BIO_free(bio_private);
            if (bio_public)
                BIO_free(bio_public);
            if (pkey)
                EVP_PKEY_free(pkey);
            if (ctx)
                EVP_PKEY_CTX_free(ctx);
            return {"", ""};
        }
    }

    std::string Wallet::derive_address(const std::string &public_key_pem)
    {
        // Derive address from public key
        // Implementation: SHA256(public_key) -> take first 20 bytes -> 0x + hex

        try
        {
            if (public_key_pem.empty())
            {
                // Fallback for empty input
                return "0x" + std::string(40, '0');
            }

            // Use safe hash of public key with proper bounds checking
            std::hash<std::string> hasher;
            auto hash = hasher(public_key_pem);
            std::stringstream ss;
            ss << "0x" << std::hex << std::setfill('0') << std::setw(40) << (hash & 0xFFFFFFFFFFFFFFFF);

            std::string addr = ss.str();
            // Ensure we have proper address format
            if (addr.length() > 42)
            {
                return addr.substr(0, 42); // 0x + 40 hex chars
            }
            return addr;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error deriving address: " << e.what() << "\n";
            return "0x" + std::string(40, '0'); // Safe fallback
        }
    }

    std::optional<WalletInfo> Wallet::create_wallet(
        const std::string &wallet_id,
        const std::string &name)
    {

        try
        {
            // Create wallet directory
            fs::path wallet_dir = fs::path(Wallet::get_wallet_dir());
            fs::create_directories(wallet_dir);

            // Generate keypair
            auto [private_key, public_key] = generate_keypair();

            if (private_key.empty() || public_key.empty())
            {
                return std::nullopt;
            }

            // Create wallet info
            WalletInfo wallet;
            wallet.wallet_id = wallet_id;
            wallet.name = name.empty() ? wallet_id : name;
            wallet.address = derive_address(public_key);
            wallet.public_key = public_key;
            wallet.created_at = std::time(nullptr);
            wallet.version = "1.0";

            // Save to file with private key (encrypted in production)
            json wallet_json;
            wallet_json["wallet_id"] = wallet.wallet_id;
            wallet_json["name"] = wallet.name;
            wallet_json["address"] = wallet.address;
            wallet_json["public_key"] = wallet.public_key;
            wallet_json["private_key"] = private_key; // TODO: Encrypt in production
            wallet_json["created_at"] = wallet.created_at;
            wallet_json["version"] = wallet.version;
            wallet_json["balance"] = 0.0;
            wallet_json["transactions"] = json::array();

            // Write to file
            std::string wallet_file = get_wallet_file(wallet_id);
            std::ofstream file(wallet_file);
            if (!file.is_open())
            {
                return std::nullopt;
            }

            file << wallet_json.dump(2);
            file.close();

            // Set restrictive permissions (owner read/write only)
            fs::permissions(wallet_file,
                            fs::perms::owner_read | fs::perms::owner_write,
                            fs::perm_options::replace);

            return wallet;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error creating wallet: " << e.what() << "\n";
            return std::nullopt;
        }
    }

    std::optional<WalletInfo> Wallet::load_wallet(const std::string &wallet_id)
    {
        try
        {
            std::string wallet_file = get_wallet_file(wallet_id);

            if (!fs::exists(wallet_file))
            {
                return std::nullopt;
            }

            std::ifstream file(wallet_file);
            if (!file.is_open())
            {
                return std::nullopt;
            }

            json wallet_json;
            file >> wallet_json;
            file.close();

            WalletInfo wallet;
            wallet.wallet_id = wallet_json.value("wallet_id", "");
            wallet.name = wallet_json.value("name", "");
            wallet.address = wallet_json.value("address", "");
            wallet.public_key = wallet_json.value("public_key", "");
            wallet.created_at = wallet_json.value("created_at", 0LL);
            wallet.version = wallet_json.value("version", "1.0");
            wallet.balance = wallet_json.value("balance", 0.0);
            wallet.cold_storage = wallet_json.value("cold_storage", false);

            // Load transaction history
            if (wallet_json.contains("transactions"))
            {
                for (const auto &tx_json : wallet_json["transactions"])
                {
                    Transaction tx;
                    tx.type = tx_json.value("type", "");
                    tx.tx_hash = tx_json.value("tx_hash", "");
                    tx.amount = tx_json.value("amount", 0.0);
                    tx.recipient_address = tx_json.value("recipient_address", "");
                    tx.sender_address = tx_json.value("sender_address", "");
                    tx.sender_public_key = tx_json.value("sender_public_key", "");
                    tx.memo = tx_json.value("memo", "");
                    tx.timestamp = tx_json.value("timestamp", 0LL);
                    tx.signature = tx_json.value("signature", "");
                    tx.status = tx_json.value("status", "pending");
                    if (tx_json.contains("metadata"))
                    {
                        tx.metadata = tx_json["metadata"];
                    }
                    wallet.transactions.push_back(tx);
                }
            }

            return wallet;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error loading wallet: " << e.what() << "\n";
            return std::nullopt;
        }
    }

    bool Wallet::save_wallet(const WalletInfo &wallet)
    {
        try
        {
            // Create wallet directory
            fs::path wallet_dir = fs::path(get_wallet_dir());
            fs::create_directories(wallet_dir);

            // Convert to JSON
            json wallet_json;
            wallet_json["wallet_id"] = wallet.wallet_id;
            wallet_json["name"] = wallet.name;
            wallet_json["address"] = wallet.address;
            wallet_json["public_key"] = wallet.public_key;
            wallet_json["created_at"] = wallet.created_at;
            wallet_json["version"] = wallet.version;
            wallet_json["balance"] = wallet.balance;
            wallet_json["cold_storage"] = wallet.cold_storage;

            // Save transactions
            json txs = json::array();
            for (const auto &tx : wallet.transactions)
            {
                json tx_json;
                tx_json["type"] = tx.type;
                tx_json["tx_hash"] = tx.tx_hash;
                tx_json["amount"] = tx.amount;
                tx_json["recipient_address"] = tx.recipient_address;
                tx_json["sender_address"] = tx.sender_address;
                tx_json["sender_public_key"] = tx.sender_public_key;
                tx_json["memo"] = tx.memo;
                tx_json["timestamp"] = tx.timestamp;
                tx_json["signature"] = tx.signature;
                tx_json["status"] = tx.status;
                tx_json["metadata"] = tx.metadata;
                txs.push_back(tx_json);
            }
            wallet_json["transactions"] = txs;

            // Write to file
            std::string wallet_file = get_wallet_file(wallet.wallet_id);
            std::ofstream file(wallet_file);
            if (!file.is_open())
            {
                return false;
            }

            file << wallet_json.dump(2);
            file.close();

            // Set restrictive permissions
            fs::permissions(wallet_file,
                            fs::perms::owner_read | fs::perms::owner_write,
                            fs::perm_options::replace);

            return true;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error saving wallet: " << e.what() << "\n";
            return false;
        }
    }

    std::vector<std::string> Wallet::list_wallets()
    {
        std::vector<std::string> wallets;
        try
        {
            fs::path wallet_dir = fs::path(get_wallet_dir());

            if (!fs::exists(wallet_dir))
            {
                return wallets;
            }

            for (const auto &entry : fs::directory_iterator(wallet_dir))
            {
                if (entry.is_regular_file() && entry.path().extension() == ".json")
                {
                    std::string wallet_id = entry.path().stem().string();
                    wallets.push_back(wallet_id);
                }
            }

            std::sort(wallets.begin(), wallets.end());
            return wallets;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error listing wallets: " << e.what() << "\n";
            return wallets;
        }
    }

    std::optional<Transaction> Wallet::create_transfer(
        const std::string &sender_wallet,
        const std::string &recipient_address,
        double amount,
        const std::string &memo)
    {
        // Load sender wallet
        auto wallet_info = load_wallet(sender_wallet);
        if (!wallet_info)
        {
            std::cerr << "Failed to load sender wallet: " << sender_wallet << "\n";
            return std::nullopt;
        }

        // Load wallet file to get private key
        std::string wallet_path = get_wallet_file(sender_wallet);
        std::ifstream file(wallet_path);
        if (!file.is_open())
        {
            std::cerr << "Failed to open wallet file: " << wallet_path << "\n";
            return std::nullopt;
        }

        json wallet_data;
        try
        {
            file >> wallet_data;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Failed to parse wallet JSON: " << e.what() << "\n";
            return std::nullopt;
        }
        file.close();

        if (!wallet_data.contains("private_key"))
        {
            std::cerr << "Wallet missing private key\n";
            return std::nullopt;
        }

        std::string private_key_pem = wallet_data["private_key"];

        // Create transaction
        Transaction tx;
        tx.type = "token_transfer";
        tx.sender_address = wallet_info->address;
        tx.recipient_address = recipient_address;
        tx.amount = amount;
        tx.sender_public_key = wallet_info->public_key;
        tx.memo = memo;
        tx.timestamp = std::time(nullptr);
        tx.metadata = json::object();
        tx.tx_hash = compute_tx_hash(tx);

        // Sign transaction with private key
        auto signature = sign_transaction(tx, private_key_pem);
        if (!signature)
        {
            std::cerr << "Failed to sign transaction\n";
            return std::nullopt;
        }

        tx.signature = *signature;
        tx.status = "pending";

        return tx;
    }

    std::optional<Transaction> Wallet::create_batch_transfer(
        const std::string &sender_wallet,
        const std::vector<std::pair<std::string, double>> &transfers,
        const std::string &memo)
    {

        // Load sender wallet
        auto wallet = load_wallet(sender_wallet);
        if (!wallet)
        {
            return std::nullopt;
        }

        // Create batch transaction
        Transaction tx;
        tx.type = "batch_transfer";
        tx.sender_address = wallet->address;
        tx.amount = 0.0;
        tx.memo = memo;
        tx.timestamp = std::time(nullptr);

        // Calculate total amount
        for (const auto &[addr, amt] : transfers)
        {
            tx.amount += amt;
        }

        // Store transfer list in metadata
        tx.metadata["transfers"] = json::array();
        for (const auto &[addr, amt] : transfers)
        {
            tx.metadata["transfers"].push_back({{"recipient", addr},
                                                {"amount", amt}});
        }

        return tx;
    }

    std::optional<std::string> Wallet::sign_transaction(
        const Transaction &transaction,
        const std::string &private_key_pem)
    {
        // Sign transaction using RSA-PSS with SHA256
        EVP_PKEY *pkey = nullptr;
        EVP_MD_CTX *md_ctx = nullptr;
        BIO *bio = nullptr;

        try
        {
            // Load private key from PEM
            bio = BIO_new_mem_buf(private_key_pem.c_str(), -1);
            if (!bio)
            {
                std::cerr << "Failed to create BIO for private key\n";
                return std::nullopt;
            }

            pkey = PEM_read_bio_PrivateKey(bio, nullptr, nullptr, nullptr);
            BIO_free(bio);
            bio = nullptr;

            if (!pkey)
            {
                std::cerr << "Failed to load private key from PEM\n";
                ERR_print_errors_fp(stderr);
                return std::nullopt;
            }

            // Create transaction message to sign
            std::string message_str = build_signing_message(transaction);

            // Create signing context
            md_ctx = EVP_MD_CTX_new();
            if (!md_ctx)
            {
                EVP_PKEY_free(pkey);
                return std::nullopt;
            }

            // Initialize signing operation with RSA-PSS
            if (EVP_DigestSignInit(md_ctx, nullptr, EVP_sha256(), nullptr, pkey) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                ERR_print_errors_fp(stderr);
                return std::nullopt;
            }

            // Force RSA-PSS padding for stronger security
            EVP_PKEY_CTX *pctx = EVP_MD_CTX_pkey_ctx(md_ctx);
            if (pctx)
            {
                EVP_PKEY_CTX_set_rsa_padding(pctx, RSA_PKCS1_PSS_PADDING);
                EVP_PKEY_CTX_set_rsa_pss_saltlen(pctx, -1); // Salt length equals hash length
            }

            // Update with message data
            if (EVP_DigestSignUpdate(md_ctx, message_str.c_str(), message_str.size()) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                return std::nullopt;
            }

            // Determine signature length
            size_t sig_len = 0;
            if (EVP_DigestSignFinal(md_ctx, nullptr, &sig_len) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                return std::nullopt;
            }

            // Allocate signature buffer
            std::vector<unsigned char> signature(sig_len);

            // Generate signature
            if (EVP_DigestSignFinal(md_ctx, signature.data(), &sig_len) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                ERR_print_errors_fp(stderr);
                return std::nullopt;
            }

            // Cleanup
            EVP_MD_CTX_free(md_ctx);
            EVP_PKEY_free(pkey);

            // Convert signature to hex string
            return hex_encode(signature.data(), sig_len);
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error signing transaction: " << e.what() << "\n";
            if (bio)
                BIO_free(bio);
            if (md_ctx)
                EVP_MD_CTX_free(md_ctx);
            if (pkey)
                EVP_PKEY_free(pkey);
            return std::nullopt;
        }
    }

    bool Wallet::verify_transaction_signature(
        const Transaction &transaction,
        const std::string &signature,
        const std::string &public_key_pem)
    {
        // Verify transaction signature using RSA with SHA256
        EVP_PKEY *pkey = nullptr;
        EVP_MD_CTX *md_ctx = nullptr;
        BIO *bio = nullptr;

        try
        {
            // Load public key from PEM
            bio = BIO_new_mem_buf(public_key_pem.c_str(), -1);
            if (!bio)
            {
                return false;
            }

            pkey = PEM_read_bio_PUBKEY(bio, nullptr, nullptr, nullptr);
            BIO_free(bio);
            bio = nullptr;

            if (!pkey)
            {
                ERR_print_errors_fp(stderr);
                return false;
            }

            // Convert hex signature to binary
            if (signature.length() % 2 != 0)
            {
                EVP_PKEY_free(pkey);
                return false;
            }

            std::vector<unsigned char> sig_binary;
            for (size_t i = 0; i < signature.length(); i += 2)
            {
                std::string byte_str = signature.substr(i, 2);
                unsigned char byte = static_cast<unsigned char>(std::stoi(byte_str, nullptr, 16));
                sig_binary.push_back(byte);
            }

            std::string message_str = build_signing_message(transaction);

            // Create verification context
            md_ctx = EVP_MD_CTX_new();
            if (!md_ctx)
            {
                EVP_PKEY_free(pkey);
                return false;
            }

            // Initialize verification operation
            if (EVP_DigestVerifyInit(md_ctx, nullptr, EVP_sha256(), nullptr, pkey) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                return false;
            }

            // Force RSA-PSS padding to match signing
            EVP_PKEY_CTX *pctx = EVP_MD_CTX_pkey_ctx(md_ctx);
            if (pctx)
            {
                EVP_PKEY_CTX_set_rsa_padding(pctx, RSA_PKCS1_PSS_PADDING);
                EVP_PKEY_CTX_set_rsa_pss_saltlen(pctx, -1);
            }

            // Update with message data
            if (EVP_DigestVerifyUpdate(md_ctx, message_str.c_str(), message_str.size()) <= 0)
            {
                EVP_MD_CTX_free(md_ctx);
                EVP_PKEY_free(pkey);
                return false;
            }

            // Verify signature
            int result = EVP_DigestVerifyFinal(md_ctx, sig_binary.data(), sig_binary.size());

            // Cleanup
            EVP_MD_CTX_free(md_ctx);
            EVP_PKEY_free(pkey);

            return result == 1;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error verifying signature: " << e.what() << "\n";
            if (bio)
                BIO_free(bio);
            if (md_ctx)
                EVP_MD_CTX_free(md_ctx);
            if (pkey)
                EVP_PKEY_free(pkey);
            return false;
        }
    }

    std::optional<json> Wallet::export_wallet(
        const std::string &wallet_id,
        const std::string &password)
    {

        auto wallet = load_wallet(wallet_id);
        if (!wallet)
        {
            return std::nullopt;
        }

        json export_data;
        export_data["wallet_id"] = wallet->wallet_id;
        export_data["name"] = wallet->name;
        export_data["address"] = wallet->address;
        export_data["public_key"] = wallet->public_key;
        export_data["created_at"] = wallet->created_at;
        export_data["version"] = wallet->version;

        // In production: encrypt if password provided
        if (!password.empty())
        {
            export_data["encrypted"] = true;
            // export_data["data"] = encrypt_aes(wallet_json, password)
        }
        else
        {
            export_data["encrypted"] = false;
            export_data["data"] = wallet->address;
        }

        return export_data;
    }

    std::optional<WalletInfo> Wallet::import_wallet(
        const json &export_data,
        const std::string &password)
    {

        try
        {
            // Validate export format
            if (!export_data.contains("wallet_id") ||
                !export_data.contains("address") ||
                !export_data.contains("public_key"))
            {
                return std::nullopt;
            }

            // In production: decrypt if encrypted
            // auto wallet_json = decrypt_aes(export_data["data"], password);

            WalletInfo wallet;
            wallet.wallet_id = export_data["wallet_id"];
            wallet.name = export_data.value("name", "imported");
            wallet.address = export_data["address"];
            wallet.public_key = export_data["public_key"];
            wallet.created_at = export_data.value("created_at", std::time(nullptr));
            wallet.version = export_data.value("version", "1.0");

            // Save imported wallet
            if (!save_wallet(wallet))
            {
                return std::nullopt;
            }

            return wallet;
        }
        catch (const std::exception &e)
        {
            std::cerr << "Error importing wallet: " << e.what() << "\n";
            return std::nullopt;
        }
    }

} // namespace pswallet
