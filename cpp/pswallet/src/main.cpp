#include "release_update.hpp"

#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>

#include <nlohmann/json.hpp>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <termios.h>
#include <unistd.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using json = nlohmann::json;

namespace
{
    struct PassOpt
    {
        bool from_flag = false;
        std::string value;
    };

    PassOpt g_pass;
    bool g_dry_run = false;
    bool g_no_update_check = false;

    void maybe_check_update()
    {
        if (g_no_update_check)
        {
            return;
        }
        if (const char *env = std::getenv("PISECURE_NO_UPDATE"))
        {
            const std::string flag = env;
            if (flag == "1" || flag == "true" || flag == "TRUE" || flag == "yes")
            {
                return;
            }
        }
        try
        {
            const auto report = pisecure_update::check_release(PISECURE_RELEASE);
            std::cerr << report.line << "\n";
            if (report.kind != pisecure_update::Report::Kind::Newer)
            {
                return;
            }
            if (!isatty(STDIN_FILENO))
            {
                return;
            }
            std::cerr << "Download pswallet " << report.tag << "? [y/N] " << std::flush;
            std::string answer;
            if (!std::getline(std::cin, answer))
            {
                return;
            }
            if (answer != "y" && answer != "Y")
            {
                return;
            }
            std::string err;
            if (!pisecure_update::download_member(report, "pswallet", "/tmp/pswallet", err))
            {
                std::cerr << err << "\n";
                return;
            }
            pisecure_update::print_wallet_install();
        }
        catch (const std::exception &)
        {
            std::cerr << "update check skipped\n";
        }
    }

    constexpr uint64_t kScryptN = 16384;
    constexpr uint64_t kScryptR = 8;
    constexpr uint64_t kScryptP = 1;
    std::string data_dir()
    {
        const char *env = std::getenv("PISECURE_DATA_DIR");
        if (env != nullptr && env[0] != '\0')
        {
            return env;
        }
        return "/var/lib/pisecure";
    }

    std::string ws_host()
    {
        const char *env = std::getenv("PISECURED_HOST");
        std::string host = (env != nullptr && env[0] != '\0') ? env : "127.0.0.1";
        if (host == "0.0.0.0" || host == "::")
        {
            host = "127.0.0.1";
        }
        return host;
    }

    int ws_port()
    {
        const char *env = std::getenv("PISECURED_PORT");
        if (env == nullptr || env[0] == '\0')
        {
            return 3144;
        }
        return std::atoi(env);
    }

    std::string hex_of(const uint8_t *data, size_t n)
    {
        static const char *hexd = "0123456789abcdef";
        std::string out(n * 2, '0');
        for (size_t i = 0; i < n; ++i)
        {
            out[i * 2] = hexd[data[i] >> 4];
            out[i * 2 + 1] = hexd[data[i] & 0x0f];
        }
        return out;
    }

    bool decode_hex(const std::string &hex, std::vector<uint8_t> &out)
    {
        if (hex.size() % 2 != 0)
        {
            return false;
        }
        auto nybble = [](char c) -> int
        {
            if (c >= '0' && c <= '9')
                return c - '0';
            if (c >= 'a' && c <= 'f')
                return c - 'a' + 10;
            if (c >= 'A' && c <= 'F')
                return c - 'A' + 10;
            return -1;
        };
        out.clear();
        for (size_t i = 0; i < hex.size(); i += 2)
        {
            const int hi = nybble(hex[i]);
            const int lo = nybble(hex[i + 1]);
            if (hi < 0 || lo < 0)
            {
                return false;
            }
            out.push_back(static_cast<uint8_t>((hi << 4) | lo));
        }
        return true;
    }

    std::string fold_name(std::string name)
    {
        for (char &c : name)
        {
            if (c >= 'A' && c <= 'Z')
            {
                c = static_cast<char>(c - 'A' + 'a');
            }
        }
        return name;
    }

    bool valid_shortname(const std::string &name)
    {
        if (name.size() < 2 || name.size() > 32)
        {
            return false;
        }
        const char first = name[0];
        if (!((first >= 'A' && first <= 'Z') || (first >= 'a' && first <= 'z')))
        {
            return false;
        }
        for (char c : name)
        {
            const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
            if (!ok)
            {
                return false;
            }
        }
        return true;
    }

    bool is_reserved_name(const std::string &name)
    {
        const std::string folded = fold_name(name);
        static const char *reserved[] = {"foundation", "validator", "stakers", "loans", "genesis", "pisecure", "operator"};
        for (const char *item : reserved)
        {
            if (folded == item)
            {
                return true;
            }
        }
        return false;
    }

    std::string normalize_ps1(std::string text)
    {
        if (text.size() != 67)
        {
            return {};
        }
        for (char &c : text)
        {
            if (c >= 'A' && c <= 'Z')
            {
                c = static_cast<char>(c - 'A' + 'a');
            }
        }
        if (text.compare(0, 3, "ps1") != 0)
        {
            return {};
        }
        for (size_t i = 3; i < text.size(); ++i)
        {
            const char c = text[i];
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            {
                return {};
            }
        }
        return text;
    }

    std::string ps1_of_pubkey(const uint8_t pub[32])
    {
        uint8_t dig[32];
        SHA256(pub, 32, dig);
        return "ps1" + hex_of(dig, 32);
    }

    std::string b64(const uint8_t *data, size_t len)
    {
        static const char *table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        std::string out;
        for (size_t i = 0; i < len; i += 3)
        {
            unsigned n = static_cast<unsigned>(data[i]) << 16;
            if (i + 1 < len)
            {
                n |= static_cast<unsigned>(data[i + 1]) << 8;
            }
            if (i + 2 < len)
            {
                n |= static_cast<unsigned>(data[i + 2]);
            }
            out.push_back(table[(n >> 18) & 63]);
            out.push_back(table[(n >> 12) & 63]);
            out.push_back(i + 1 < len ? table[(n >> 6) & 63] : '=');
            out.push_back(i + 2 < len ? table[n & 63] : '=');
        }
        return out;
    }

    bool send_all(int fd, const uint8_t *data, size_t n)
    {
        size_t off = 0;
        while (off < n)
        {
            const ssize_t wrote = ::send(fd, data + off, n - off, 0);
            if (wrote <= 0)
            {
                return false;
            }
            off += static_cast<size_t>(wrote);
        }
        return true;
    }

    bool recv_some(int fd, std::string &buf)
    {
        char tmp[4096];
        const ssize_t got = ::recv(fd, tmp, sizeof(tmp), 0);
        if (got <= 0)
        {
            return false;
        }
        buf.append(tmp, tmp + got);
        return true;
    }

    bool ws_call(const std::string &method, const json &params, json &result, std::string &err)
    {
        const std::string host = ws_host();
        const int port = ws_port();
        int fd = ::socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0)
        {
            err = "socket failed";
            return false;
        }
        timeval tv{};
        tv.tv_sec = 15;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<uint16_t>(port));
        if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1)
        {
            ::close(fd);
            err = "wallet speaks to " + host + ":" + std::to_string(port);
            return false;
        }
        if (connect(fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) != 0)
        {
            ::close(fd);
            err = "cannot connect to ws://" + host + ":" + std::to_string(port);
            return false;
        }
        uint8_t raw_key[16];
        if (RAND_bytes(raw_key, sizeof(raw_key)) != 1)
        {
            ::close(fd);
            err = "random failed";
            return false;
        }
        const std::string key = b64(raw_key, sizeof(raw_key));
        std::ostringstream req;
        req << "GET / HTTP/1.1\r\n"
            << "Host: " << host << ":" << port << "\r\n"
            << "Upgrade: websocket\r\n"
            << "Connection: Upgrade\r\n"
            << "Sec-WebSocket-Key: " << key << "\r\n"
            << "Sec-WebSocket-Version: 13\r\n\r\n";
        const std::string handshake = req.str();
        if (!send_all(fd, reinterpret_cast<const uint8_t *>(handshake.data()), handshake.size()))
        {
            ::close(fd);
            err = "websocket handshake failed";
            return false;
        }
        std::string buf;
        while (buf.find("\r\n\r\n") == std::string::npos)
        {
            if (!recv_some(fd, buf))
            {
                ::close(fd);
                err = "websocket handshake failed";
                return false;
            }
        }
        if (buf.find(" 101 ") == std::string::npos)
        {
            ::close(fd);
            err = "websocket handshake failed";
            return false;
        }
        buf.erase(0, buf.find("\r\n\r\n") + 4);

        const json body = {{"jsonrpc", "2.0"}, {"id", 1}, {"method", method}, {"params", params}};
        const std::string payload = body.dump();
        uint8_t mask[4];
        RAND_bytes(mask, sizeof(mask));
        std::vector<uint8_t> frame;
        frame.push_back(0x81);
        const size_t n = payload.size();
        if (n < 126)
        {
            frame.push_back(static_cast<uint8_t>(0x80 | n));
        }
        else if (n <= 0xffff)
        {
            frame.push_back(0x80 | 126);
            frame.push_back(static_cast<uint8_t>((n >> 8) & 0xff));
            frame.push_back(static_cast<uint8_t>(n & 0xff));
        }
        else
        {
            frame.push_back(0x80 | 127);
            for (int shift = 56; shift >= 0; shift -= 8)
            {
                frame.push_back(static_cast<uint8_t>((n >> shift) & 0xff));
            }
        }
        frame.insert(frame.end(), mask, mask + 4);
        for (size_t i = 0; i < n; ++i)
        {
            frame.push_back(static_cast<uint8_t>(payload[i]) ^ mask[i % 4]);
        }
        if (!send_all(fd, frame.data(), frame.size()))
        {
            ::close(fd);
            err = "websocket send failed";
            return false;
        }

        while (true)
        {
            if (buf.size() < 2 && !recv_some(fd, buf))
            {
                ::close(fd);
                err = "websocket read failed";
                return false;
            }
            if (buf.size() < 2)
            {
                continue;
            }
            const uint8_t b0 = static_cast<uint8_t>(buf[0]);
            const uint8_t b1 = static_cast<uint8_t>(buf[1]);
            size_t header = 2;
            uint64_t len = b1 & 0x7f;
            if (len == 126)
            {
                header += 2;
            }
            else if (len == 127)
            {
                header += 8;
            }
            if (buf.size() < header && !recv_some(fd, buf))
            {
                ::close(fd);
                err = "websocket read failed";
                return false;
            }
            if (buf.size() < header)
            {
                continue;
            }
            size_t cursor = 2;
            if ((b1 & 0x7f) == 126)
            {
                len = (static_cast<uint8_t>(buf[2]) << 8) | static_cast<uint8_t>(buf[3]);
                cursor = 4;
            }
            else if ((b1 & 0x7f) == 127)
            {
                len = 0;
                for (int i = 0; i < 8; ++i)
                {
                    len = (len << 8) | static_cast<uint8_t>(buf[2 + i]);
                }
                cursor = 10;
            }
            if ((b1 & 0x80) != 0)
            {
                header += 4;
            }
            if (buf.size() < header + len)
            {
                if (!recv_some(fd, buf))
                {
                    ::close(fd);
                    err = "websocket read failed";
                    return false;
                }
                continue;
            }
            std::string text = buf.substr(header, static_cast<size_t>(len));
            buf.erase(0, header + static_cast<size_t>(len));
            const uint8_t opcode = b0 & 0x0f;
            if (opcode == 0x8)
            {
                ::close(fd);
                err = "websocket closed";
                return false;
            }
            if (opcode != 0x1)
            {
                continue;
            }
            ::close(fd);
            json reply = json::parse(text);
            if (reply.contains("error"))
            {
                err = reply["error"].value("message", "rpc error");
                return false;
            }
            result = reply.value("result", json::object());
            return true;
        }
    }

    std::string wallet_path(const std::string &address)
    {
        return data_dir() + "/wallets/" + address + ".json";
    }

    std::string read_file_maybe_sudo(const std::string &path, bool &ok)
    {
        std::ifstream in(path);
        if (in)
        {
            std::stringstream buf;
            buf << in.rdbuf();
            ok = true;
            return buf.str();
        }
        const std::string cmd = "sudo -n cat '" + path + "' 2>/dev/null";
        FILE *pipe = popen(cmd.c_str(), "r");
        if (pipe == nullptr)
        {
            ok = false;
            return {};
        }
        std::string out;
        char tmp[512];
        while (fgets(tmp, sizeof(tmp), pipe) != nullptr)
        {
            out += tmp;
        }
        ok = pclose(pipe) == 0 && !out.empty();
        return out;
    }

    bool write_privileged(const std::string &dest, const std::string &contents, const char *mode)
    {
        char path[] = "/tmp/pisecure-wallet-XXXXXX";
        const int fd = mkstemp(path);
        if (fd < 0)
        {
            return false;
        }
        const ssize_t wrote = ::write(fd, contents.data(), contents.size());
        ::close(fd);
        if (wrote < 0 || static_cast<size_t>(wrote) != contents.size())
        {
            ::unlink(path);
            return false;
        }
        const std::string cmd = std::string("sudo -n install -o pisecure -g pisecure -m ") + mode + " '" + path + "' '" + dest + "'";
        const int rc = std::system(cmd.c_str());
        ::unlink(path);
        return rc == 0;
    }

    struct Key
    {
        std::string address;
        std::string public_hex;
        std::string secret_hex;
    };

    struct EchoOff
    {
        termios saved{};
        bool active = false;
        EchoOff()
        {
            if (!isatty(STDIN_FILENO) || tcgetattr(STDIN_FILENO, &saved) != 0)
            {
                return;
            }
            termios next = saved;
            next.c_lflag &= ~tcflag_t(ECHO);
            active = tcsetattr(STDIN_FILENO, TCSANOW, &next) == 0;
        }
        ~EchoOff()
        {
            if (active)
            {
                tcsetattr(STDIN_FILENO, TCSANOW, &saved);
            }
        }
    };

    std::string prompt_passphrase(std::string &err)
    {
        if (!isatty(STDIN_FILENO))
        {
            err = "passphrase required";
            return {};
        }
        std::cerr << "passphrase: " << std::flush;
        std::string line;
        {
            EchoOff hidden;
            if (!std::getline(std::cin, line))
            {
                err = "passphrase required";
                return {};
            }
        }
        std::cerr << "\n";
        if (line.empty())
        {
            err = "passphrase required";
            return {};
        }
        return line;
    }

    std::string passphrase_for(bool required, std::string &err)
    {
        if (g_pass.from_flag)
        {
            if (g_pass.value.empty())
            {
                err = "passphrase required";
                return {};
            }
            return g_pass.value;
        }
        if (const char *env = std::getenv("PISECURE_WALLET_PASS"))
        {
            if (env[0] != '\0')
            {
                return env;
            }
        }
        if (!required)
        {
            return {};
        }
        return prompt_passphrase(err);
    }

    bool scrypt_key(const std::string &pass, const uint8_t *salt, size_t salt_len, uint8_t out[32])
    {
        return EVP_PBE_scrypt(pass.data(), pass.size(), salt, salt_len, kScryptN, kScryptR, kScryptP, 64ull * 1024ull * 1024ull, out, 32) == 1;
    }

    bool seal_seed(const std::string &pass, const std::string &public_hex, const std::vector<uint8_t> &seed, json &enc, std::string &err)
    {
        if (seed.size() != 32)
        {
            err = "spending key is not ed25519";
            return false;
        }
        uint8_t salt[16];
        uint8_t nonce[12];
        uint8_t key[32];
        if (RAND_bytes(salt, sizeof(salt)) != 1 || RAND_bytes(nonce, sizeof(nonce)) != 1 || !scrypt_key(pass, salt, sizeof(salt), key))
        {
            err = "could not encrypt spending key";
            return false;
        }
        EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
        uint8_t ct[32];
        uint8_t tag[16];
        int len = 0;
        int final_len = 0;
        const bool ok = ctx != nullptr &&
                        EVP_EncryptInit_ex(ctx, EVP_chacha20_poly1305(), nullptr, nullptr, nullptr) == 1 &&
                        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_IVLEN, 12, nullptr) == 1 &&
                        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key, nonce) == 1 &&
                        EVP_EncryptUpdate(ctx, nullptr, &len, reinterpret_cast<const uint8_t *>(public_hex.data()), static_cast<int>(public_hex.size())) == 1 &&
                        EVP_EncryptUpdate(ctx, ct, &len, seed.data(), 32) == 1 &&
                        EVP_EncryptFinal_ex(ctx, ct + len, &final_len) == 1 &&
                        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_GET_TAG, 16, tag) == 1;
        EVP_CIPHER_CTX_free(ctx);
        OPENSSL_cleanse(key, sizeof(key));
        if (!ok || len + final_len != 32)
        {
            err = "could not encrypt spending key";
            return false;
        }
        std::vector<uint8_t> packed(ct, ct + 32);
        packed.insert(packed.end(), tag, tag + 16);
        enc = {{"kdf", "scrypt"},
               {"kdf_n", kScryptN},
               {"kdf_r", kScryptR},
               {"kdf_p", kScryptP},
               {"cipher", "chacha20poly1305"},
               {"salt", hex_of(salt, sizeof(salt))},
               {"nonce", hex_of(nonce, sizeof(nonce))},
               {"ciphertext", hex_of(packed.data(), packed.size())}};
        return true;
    }

    bool open_seed(const std::string &pass, const std::string &public_hex, const json &enc, std::string &secret_hex, std::string &err)
    {
        if (!enc.is_object() || enc.value("kdf", "") != "scrypt" || enc.value("cipher", "") != "chacha20poly1305")
        {
            err = "spending key is not ed25519";
            return false;
        }
        std::vector<uint8_t> salt;
        std::vector<uint8_t> nonce;
        std::vector<uint8_t> packed;
        if (!decode_hex(enc.value("salt", ""), salt) || salt.size() != 16 || !decode_hex(enc.value("nonce", ""), nonce) || nonce.size() != 12 || !decode_hex(enc.value("ciphertext", ""), packed) || packed.size() != 48)
        {
            err = "spending key is not ed25519";
            return false;
        }
        uint8_t key[32];
        const uint64_t n = enc.value("kdf_n", kScryptN);
        const uint64_t r = enc.value("kdf_r", kScryptR);
        const uint64_t p = enc.value("kdf_p", kScryptP);
        if (EVP_PBE_scrypt(pass.data(), pass.size(), salt.data(), salt.size(), n, r, p, 64ull * 1024ull * 1024ull, key, 32) != 1)
        {
            err = "wrong passphrase";
            return false;
        }
        EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
        uint8_t plain[32];
        int len = 0;
        int final_len = 0;
        const bool ok = ctx != nullptr &&
                        EVP_DecryptInit_ex(ctx, EVP_chacha20_poly1305(), nullptr, nullptr, nullptr) == 1 &&
                        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_IVLEN, 12, nullptr) == 1 &&
                        EVP_DecryptInit_ex(ctx, nullptr, nullptr, key, nonce.data()) == 1 &&
                        EVP_DecryptUpdate(ctx, nullptr, &len, reinterpret_cast<const uint8_t *>(public_hex.data()), static_cast<int>(public_hex.size())) == 1 &&
                        EVP_DecryptUpdate(ctx, plain, &len, packed.data(), 32) == 1 &&
                        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_TAG, 16, packed.data() + 32) == 1 &&
                        EVP_DecryptFinal_ex(ctx, plain + len, &final_len) == 1;
        EVP_CIPHER_CTX_free(ctx);
        OPENSSL_cleanse(key, sizeof(key));
        if (!ok)
        {
            OPENSSL_cleanse(plain, sizeof(plain));
            err = "wrong passphrase";
            return false;
        }
        secret_hex = hex_of(plain, 32);
        OPENSSL_cleanse(plain, sizeof(plain));
        return true;
    }

    bool write_wallet_doc(const std::string &path, const json &doc, std::string &err)
    {
        if (doc.contains("secret_key"))
        {
            err = "refusing to write plaintext secret_key";
            return false;
        }
        if (!write_privileged(path, doc.dump(2) + "\n", "0600"))
        {
            err = "could not write " + path;
            return false;
        }
        return true;
    }

    bool read_wallet_doc(const std::string &address, json &doc, std::string &err)
    {
        bool ok = false;
        const std::string raw = read_file_maybe_sudo(wallet_path(address), ok);
        if (!ok)
        {
            err = "no spending key for " + address;
            return false;
        }
        try
        {
            doc = json::parse(raw);
        }
        catch (const std::exception &)
        {
            err = "spending key for " + address + " is not ed25519";
            return false;
        }
        if (!doc.is_object() || doc.value("scheme", "") != "ed25519" || !doc.contains("public_key") || !doc["public_key"].is_string())
        {
            err = "spending key for " + address + " is not ed25519";
            return false;
        }
        return true;
    }

    bool load_key(const std::string &address, Key &key, std::string &err)
    {
        json doc;
        if (!read_wallet_doc(address, doc, err))
        {
            return false;
        }
        key.address = address;
        key.public_hex = doc["public_key"].get<std::string>();
        const bool enc = doc.contains("secret_key_enc");
        const bool plain = doc.contains("secret_key") && doc["secret_key"].is_string();
        if (enc)
        {
            const std::string pass = passphrase_for(true, err);
            if (pass.empty())
            {
                if (err.empty())
                {
                    err = "passphrase required";
                }
                return false;
            }
            if (!open_seed(pass, key.public_hex, doc["secret_key_enc"], key.secret_hex, err))
            {
                return false;
            }
            return true;
        }
        if (!plain)
        {
            err = "no spending key for " + address;
            return false;
        }
        key.secret_hex = doc["secret_key"].get<std::string>();
        return true;
    }

    bool ed25519_sign(const std::string &secret_hex, const std::string &message, std::string &sig_hex, std::string &err)
    {
        std::vector<uint8_t> seed;
        if (!decode_hex(secret_hex, seed) || seed.size() != 32)
        {
            err = "spending key is not ed25519";
            return false;
        }
        EVP_PKEY *pkey = EVP_PKEY_new_raw_private_key(EVP_PKEY_ED25519, nullptr, seed.data(), seed.size());
        if (pkey == nullptr)
        {
            err = "spending key is not ed25519";
            return false;
        }
        EVP_MD_CTX *ctx = EVP_MD_CTX_new();
        uint8_t sig[64];
        size_t siglen = sizeof(sig);
        const bool ok = ctx != nullptr && EVP_DigestSignInit(ctx, nullptr, nullptr, nullptr, pkey) == 1 &&
                        EVP_DigestSign(ctx, sig, &siglen, reinterpret_cast<const uint8_t *>(message.data()), message.size()) == 1 &&
                        siglen == 64;
        EVP_MD_CTX_free(ctx);
        EVP_PKEY_free(pkey);
        if (!ok)
        {
            err = "signature invalid";
            return false;
        }
        sig_hex = hex_of(sig, 64);
        return true;
    }

    std::string spend_payload(const json &tx)
    {
        json inputs = json::array();
        for (const auto &in : tx["inputs"])
        {
            inputs.push_back({{"prev_txid", in["prev_txid"]}, {"vout", in["vout"]}});
        }
        json outputs = json::array();
        for (const auto &out : tx["outputs"])
        {
            outputs.push_back({{"address", out["address"]}, {"value", out["value"]}});
        }
        json body = {{"fee", tx["fee"]}, {"inputs", inputs}, {"outputs", outputs}, {"version", tx["version"]}};
        if (tx.value("type", "") == "register")
        {
            body["type"] = "register";
            body["name"] = tx["name"];
            body["address"] = tx["address"];
        }
        return body.dump();
    }

    bool sign_tx(json &tx, const Key &key, std::string &err)
    {
        std::string sig;
        if (!ed25519_sign(key.secret_hex, spend_payload(tx), sig, err))
        {
            return false;
        }
        for (auto &in : tx["inputs"])
        {
            in["public_key"] = key.public_hex;
            in["signature"] = sig;
        }
        return true;
    }

    bool parse_314st(const std::string &text, uint64_t &units, std::string &err)
    {
        if (text.empty() || text[0] == '-')
        {
            err = "amount must be 314ST, for example 0.050";
            return false;
        }
        std::string whole;
        std::string frac;
        const auto dot = text.find('.');
        if (dot == std::string::npos)
        {
            whole = text;
        }
        else
        {
            whole = text.substr(0, dot);
            frac = text.substr(dot + 1);
        }
        if (whole.empty())
        {
            whole = "0";
        }
        if (frac.size() > 3)
        {
            err = "amount must be 314ST, for example 0.050";
            return false;
        }
        while (frac.size() < 3)
        {
            frac.push_back('0');
        }
        auto digits = [](const std::string &s)
        {
            for (char c : s)
            {
                if (c < '0' || c > '9')
                {
                    return false;
                }
            }
            return true;
        };
        if (!digits(whole) || !digits(frac))
        {
            err = "amount must be 314ST, for example 0.050";
            return false;
        }
        units = std::stoull(whole) * 1000ull + std::stoull(frac);
        if (units == 0)
        {
            err = "amount must be greater than 0";
            return false;
        }
        return true;
    }

    bool rpc(const std::string &method, const json &params, json &result, std::string &err)
    {
        try
        {
            return ws_call(method, params, result, err);
        }
        catch (const std::exception &ex)
        {
            err = ex.what();
            return false;
        }
    }

    std::string resolve_address(const std::string &text, std::string &err)
    {
        const std::string ps1 = normalize_ps1(text);
        if (!ps1.empty())
        {
            return ps1;
        }
        json result;
        if (!rpc("namelookup", json{{"name", text}}, result, err))
        {
            return {};
        }
        if (result.value("found", true) == false || !result.contains("address"))
        {
            err.clear();
            return text;
        }
        return result["address"].get<std::string>();
    }

    struct Coin
    {
        std::string txid;
        uint32_t vout = 0;
        uint64_t units = 0;
    };

    bool coins_for(const std::string &address, std::vector<Coin> &coins, std::string &err)
    {
        json listed;
        if (!rpc("listunspent", json{{"address", address}}, listed, err))
        {
            return false;
        }
        for (const auto &row : listed.value("utxos", json::array()))
        {
            Coin coin;
            coin.txid = row.value("txid", "");
            coin.vout = row.value("vout", 0u);
            coin.units = row.value("units", 0ull);
            if (!coin.txid.empty() && coin.units > 0)
            {
                coins.push_back(coin);
            }
        }
        json pool;
        if (!rpc("getmempool", json::object(), pool, err))
        {
            return false;
        }
        std::vector<std::pair<std::string, uint32_t>> spent;
        const auto txs = pool.value("transactions", json::array());
        for (const auto &tx : txs)
        {
            for (const auto &in : tx.value("inputs", json::array()))
            {
                spent.emplace_back(in.value("prev_txid", ""), in.value("vout", 0u));
            }
        }
        coins.erase(std::remove_if(coins.begin(), coins.end(), [&](const Coin &coin)
                                   {
                                       for (const auto &item : spent)
                                       {
                                           if (item.first == coin.txid && item.second == coin.vout)
                                           {
                                               return true;
                                           }
                                       }
                                       return false;
                                   }),
                    coins.end());
        for (const auto &tx : txs)
        {
            const std::string txid = tx.value("txid", "");
            uint32_t vout = 0;
            for (const auto &out : tx.value("outputs", json::array()))
            {
                if (out.value("address", "") == address)
                {
                    bool used = false;
                    for (const auto &item : spent)
                    {
                        if (item.first == txid && item.second == vout)
                        {
                            used = true;
                        }
                    }
                    for (const auto &have : coins)
                    {
                        if (have.txid == txid && have.vout == vout)
                        {
                            used = true;
                        }
                    }
                    if (!used)
                    {
                        Coin coin;
                        coin.txid = txid;
                        coin.vout = vout;
                        coin.units = out.value("value", 0ull);
                        if (coin.units > 0 && !coin.txid.empty())
                        {
                            coins.push_back(coin);
                        }
                    }
                }
                ++vout;
            }
        }
        err.clear();
        return true;
    }

    int cmd_create()
    {
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_ED25519, nullptr);
        EVP_PKEY *pkey = nullptr;
        if (ctx == nullptr || EVP_PKEY_keygen_init(ctx) != 1 || EVP_PKEY_keygen(ctx, &pkey) != 1)
        {
            EVP_PKEY_CTX_free(ctx);
            std::cerr << "could not create an ed25519 key\n";
            return 1;
        }
        EVP_PKEY_CTX_free(ctx);
        uint8_t seed[32];
        uint8_t pub[32];
        size_t slen = sizeof(seed);
        size_t plen = sizeof(pub);
        if (EVP_PKEY_get_raw_private_key(pkey, seed, &slen) != 1 || EVP_PKEY_get_raw_public_key(pkey, pub, &plen) != 1 || slen != 32 || plen != 32)
        {
            EVP_PKEY_free(pkey);
            std::cerr << "could not create an ed25519 key\n";
            return 1;
        }
        EVP_PKEY_free(pkey);
        const std::string address = ps1_of_pubkey(pub);
        const std::string public_hex = hex_of(pub, 32);
        std::string err;
        const std::string pass = passphrase_for(true, err);
        if (pass.empty())
        {
            OPENSSL_cleanse(seed, sizeof(seed));
            std::cerr << (err.empty() ? "passphrase required" : err) << "\n";
            return 1;
        }
        json enc;
        std::vector<uint8_t> raw_seed(seed, seed + 32);
        OPENSSL_cleanse(seed, sizeof(seed));
        if (!seal_seed(pass, public_hex, raw_seed, enc, err))
        {
            OPENSSL_cleanse(raw_seed.data(), raw_seed.size());
            std::cerr << err << "\n";
            return 1;
        }
        OPENSSL_cleanse(raw_seed.data(), raw_seed.size());
        json doc = {{"address", address}, {"scheme", "ed25519"}, {"public_key", public_hex}, {"secret_key_enc", enc}};
        const std::string path = wallet_path(address);
        if (!write_wallet_doc(path, doc, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::cout << address << "\n"
                  << path << "\n";
        return 0;
    }

    int cmd_encrypt(const std::string &who)
    {
        std::string err;
        const std::string address = resolve_address(who, err);
        if (address.empty())
        {
            std::cerr << err << "\n";
            return 1;
        }
        json doc;
        if (!read_wallet_doc(address, doc, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        const bool plain = doc.contains("secret_key") && doc["secret_key"].is_string();
        if (!plain)
        {
            if (doc.contains("secret_key_enc"))
            {
                std::cout << "already encrypted\n";
                return 0;
            }
            std::cerr << "no spending key for " << address << "\n";
            return 1;
        }
        const std::string pass = passphrase_for(true, err);
        if (pass.empty())
        {
            std::cerr << (err.empty() ? "passphrase required" : err) << "\n";
            return 1;
        }
        std::vector<uint8_t> seed;
        if (!decode_hex(doc["secret_key"].get<std::string>(), seed) || seed.size() != 32)
        {
            std::cerr << "spending key is not ed25519\n";
            return 1;
        }
        json enc;
        const std::string public_hex = doc["public_key"].get<std::string>();
        if (!seal_seed(pass, public_hex, seed, enc, err))
        {
            OPENSSL_cleanse(seed.data(), seed.size());
            std::cerr << err << "\n";
            return 1;
        }
        OPENSSL_cleanse(seed.data(), seed.size());
        doc.erase("secret_key");
        doc["secret_key_enc"] = enc;
        if (!write_wallet_doc(wallet_path(address), doc, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::cout << wallet_path(address) << "\n";
        return 0;
    }

    int cmd_list()
    {
        const std::string dir = data_dir() + "/wallets";
        const std::string cmd = "sudo -n ls -1 '" + dir + "'";
        FILE *pipe = popen(cmd.c_str(), "r");
        if (pipe == nullptr)
        {
            std::cerr << "cannot list " << dir << "\n";
            return 1;
        }
        char line[512];
        while (fgets(line, sizeof(line), pipe) != nullptr)
        {
            std::string name = line;
            while (!name.empty() && (name.back() == '\n' || name.back() == '\r'))
            {
                name.pop_back();
            }
            if (name.size() > 5 && name.substr(name.size() - 5) == ".json")
            {
                std::cout << name.substr(0, name.size() - 5) << "\n";
            }
        }
        pclose(pipe);
        return 0;
    }

    int cmd_balance(const std::string &who)
    {
        std::string err;
        const std::string address = resolve_address(who, err);
        if (address.empty())
        {
            std::cerr << err << "\n";
            return 1;
        }
        json result;
        if (!rpc("listunspent", json{{"address", address}}, result, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::cout << result.value("amount", "0.000") << " 314ST\n";
        return 0;
    }

    int cmd_utxos(const std::string &who)
    {
        std::string err;
        const std::string address = resolve_address(who, err);
        if (address.empty())
        {
            std::cerr << err << "\n";
            return 1;
        }
        json result;
        if (!rpc("listunspent", json{{"address", address}}, result, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::cout << address << " " << result.value("amount", "0.000") << " 314ST\n";
        for (const auto &row : result.value("utxos", json::array()))
        {
            std::cout << row.value("txid", "") << " " << row.value("vout", 0) << " " << row.value("amount", "") << "\n";
        }
        return 0;
    }

    int cmd_info(const std::string &who)
    {
        std::string err;
        json result;
        if (!rpc("namelookup", json{{"name", who}}, result, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        if (result.value("found", true) == false)
        {
            const std::string ps1 = normalize_ps1(who);
            if (!ps1.empty())
            {
                json by_addr;
                if (!rpc("namelookup", json{{"address", ps1}}, by_addr, err))
                {
                    std::cerr << err << "\n";
                    return 1;
                }
                std::cout << by_addr.dump() << "\n"
                          << wallet_path(ps1) << "\n";
                return 0;
            }
            std::cout << result.dump() << "\n";
            return 0;
        }
        std::cout << result.dump() << "\n";
        if (result.contains("address"))
        {
            std::cout << wallet_path(result["address"].get<std::string>()) << "\n";
        }
        return 0;
    }

    bool write_grant(const std::string &name, const std::string &ps1, std::string &err)
    {
        const std::string path = data_dir() + "/names.json";
        bool ok = false;
        json doc = {{"reserved_bind", json::array()}, {"names", json::array()}};
        const std::string raw = read_file_maybe_sudo(path, ok);
        if (ok)
        {
            try
            {
                doc = json::parse(raw);
            }
            catch (const std::exception &)
            {
                err = "names.json is not json";
                return false;
            }
        }
        if (!doc.contains("reserved_bind") || !doc["reserved_bind"].is_array())
        {
            doc["reserved_bind"] = json::array();
        }
        const std::string folded = fold_name(name);
        bool replaced = false;
        for (auto &row : doc["reserved_bind"])
        {
            if (row.is_object() && fold_name(row.value("name", "")) == folded)
            {
                row["name"] = name;
                row["address"] = ps1;
                replaced = true;
            }
        }
        if (!replaced)
        {
            doc["reserved_bind"].push_back({{"name", name}, {"address", ps1}});
        }
        if (!write_privileged(path, doc.dump(2) + "\n", "0644"))
        {
            err = "could not write " + path;
            return false;
        }
        return true;
    }

    int cmd_register(const std::string &name, const std::string &ps1_in, bool grant)
    {
        const std::string ps1 = normalize_ps1(ps1_in);
        if (!valid_shortname(name) || ps1.empty())
        {
            std::cerr << "usage: pswallet register NAME ps1...\n";
            return 1;
        }
        if (is_reserved_name(name) && !grant)
        {
            std::cerr << "name is reserved\n";
            return 1;
        }
        if (grant && !is_reserved_name(name))
        {
            std::cerr << "grant is only for a reserved name\n";
            return 1;
        }
        std::string err;
        if (grant && !write_grant(name, ps1, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        Key key;
        if (!load_key(ps1, key, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::vector<Coin> coins;
        if (!coins_for(ps1, coins, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        const Coin *chosen = nullptr;
        for (const auto &coin : coins)
        {
            if (coin.units >= 2)
            {
                chosen = &coin;
                break;
            }
        }
        if (chosen == nullptr)
        {
            std::cerr << ps1 << " has no coin covering the 1 unit register fee\n";
            return 1;
        }
        json tx = {
            {"version", 1},
            {"type", "register"},
            {"name", name},
            {"address", ps1},
            {"fee", 1},
            {"inputs", json::array({{{"prev_txid", chosen->txid}, {"vout", chosen->vout}}})},
            {"outputs", json::array({{{"address", ps1}, {"value", chosen->units - 1}}})},
        };
        if (!sign_tx(tx, key, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        json result;
        if (!rpc("sendtransaction", tx, result, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        if (result.value("status", "") != "accepted")
        {
            std::cerr << result.value("reason", "register rejected") << "\n";
            return 1;
        }
        std::cout << result.value("txid", "") << "\n";
        return 0;
    }

    int cmd_send(const std::string &src, const std::string &dst, const std::string &amount, const std::string &fee_text)
    {
        std::string err;
        uint64_t pay = 0;
        uint64_t fee = 0;
        if (!parse_314st(amount, pay, err) || !parse_314st(fee_text, fee, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        const std::string src_addr = resolve_address(src, err);
        if (src_addr.empty())
        {
            std::cerr << err << "\n";
            return 1;
        }
        const std::string dst_addr = resolve_address(dst, err);
        if (dst_addr.empty())
        {
            std::cerr << err << "\n";
            return 1;
        }
        Key key;
        if (!load_key(src_addr, key, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::vector<Coin> coins;
        if (!coins_for(src_addr, coins, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        std::sort(coins.begin(), coins.end(), [](const Coin &a, const Coin &b)
                  { return a.units > b.units; });
        std::vector<Coin> chosen;
        uint64_t sum = 0;
        for (const auto &coin : coins)
        {
            if (sum >= pay + fee)
            {
                break;
            }
            chosen.push_back(coin);
            sum += coin.units;
        }
        if (sum < pay + fee)
        {
            if (g_dry_run)
            {
                std::string sig;
                if (!ed25519_sign(key.secret_hex, src_addr, sig, err))
                {
                    std::cerr << err << "\n";
                    return 1;
                }
                std::cout << "signed\n";
                return 0;
            }
            std::cerr << src << " has no coin covering " << amount << " 314ST plus fee " << fee_text << "\n";
            return 1;
        }
        const uint64_t change = sum - pay - fee;
        json inputs = json::array();
        for (const auto &coin : chosen)
        {
            inputs.push_back({{"prev_txid", coin.txid}, {"vout", coin.vout}});
        }
        json outputs = json::array({{{"address", dst_addr}, {"value", pay}}});
        if (change > 0)
        {
            outputs.push_back({{"address", src_addr}, {"value", change}});
        }
        json tx = {
            {"version", 1},
            {"fee", fee},
            {"inputs", inputs},
            {"outputs", outputs},
        };
        if (!sign_tx(tx, key, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        if (g_dry_run)
        {
            std::cout << "signed\n";
            return 0;
        }
        json result;
        if (!rpc("sendtransaction", tx, result, err))
        {
            std::cerr << err << "\n";
            return 1;
        }
        if (result.value("status", "") != "accepted")
        {
            std::cerr << result.value("reason", "send rejected") << "\n";
            return 1;
        }
        std::cout << result.value("txid", "") << "\n";
        return 0;
    }

    void usage()
    {
        std::cerr << "pswallet talks to ws://127.0.0.1:3144\n"
                  << "  create\n"
                  << "  encrypt NAME [--passphrase TEXT]\n"
                  << "  register NAME ps1... [--grant]\n"
                  << "  list\n"
                  << "  info NAME|ps1\n"
                  << "  balance NAME|ps1\n"
                  << "  utxos NAME|ps1\n"
                  << "  send SRC DST AMOUNT [--fee 0.001] [--dry-run]\n"
                  << "Amounts are 314ST. 0.001 is 1 unit.\n"
                  << "A tty prompt or PISECURE_WALLET_PASS unlocks secret_key_enc.\n";
    }
}

int main(int argc, char **argv)
{
    std::vector<std::string> positional;
    bool grant = false;
    std::string fee = "0.001";
    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h")
        {
            usage();
            return 0;
        }
        if (arg == "--version")
        {
            std::cout << "pswallet " PSWALLET_VERSION "\n";
            return 0;
        }
        if (arg == "--grant")
        {
            grant = true;
            continue;
        }
        if (arg == "--dry-run")
        {
            g_dry_run = true;
            continue;
        }
        if (arg == "--no-update-check")
        {
            g_no_update_check = true;
            continue;
        }
        if (arg == "--fee" && i + 1 < argc)
        {
            fee = argv[++i];
            continue;
        }
        if (arg == "--passphrase" && i + 1 < argc)
        {
            g_pass.from_flag = true;
            g_pass.value = argv[++i];
            continue;
        }
        positional.push_back(arg);
    }
    if (positional.empty())
    {
        usage();
        return 1;
    }
    const std::string cmd = positional[0];
    try
    {
        if (cmd == "create" && positional.size() == 1)
        {
            maybe_check_update();
            return cmd_create();
        }
        if (cmd == "encrypt" && positional.size() == 2)
        {
            return cmd_encrypt(positional[1]);
        }
        if (cmd == "list" && positional.size() == 1)
        {
            maybe_check_update();
            return cmd_list();
        }
        if (cmd == "balance" && positional.size() == 2)
        {
            maybe_check_update();
            return cmd_balance(positional[1]);
        }
        if (cmd == "utxos" && positional.size() == 2)
        {
            return cmd_utxos(positional[1]);
        }
        if (cmd == "info" && positional.size() == 2)
        {
            return cmd_info(positional[1]);
        }
        if (cmd == "register" && positional.size() == 3)
        {
            return cmd_register(positional[1], positional[2], grant);
        }
        if (cmd == "send" && positional.size() == 4)
        {
            maybe_check_update();
            return cmd_send(positional[1], positional[2], positional[3], fee);
        }
    }
    catch (const std::exception &ex)
    {
        std::cerr << ex.what() << "\n";
        return 1;
    }
    usage();
    return 1;
}
