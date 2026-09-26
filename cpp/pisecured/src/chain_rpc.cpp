#include "pisecured/chain_rpc.hpp"
#include "pisecured/retarget.hpp"
#include "pisecured/p2p.hpp"
#include "pihash.h"

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <unordered_set>
#include <utility>

namespace pisecured
{
    namespace
    {
        constexpr uint64_t kMaxTxBytes = 100000;

        json rejected(const std::string &reason)
        {
            return json{{"status", "rejected"}, {"reason", reason}};
        }

        void append_u16(std::vector<uint8_t> &out, uint16_t v)
        {
            out.push_back(static_cast<uint8_t>(v & 0xff));
            out.push_back(static_cast<uint8_t>((v >> 8) & 0xff));
        }

        void append_u32(std::vector<uint8_t> &out, uint32_t v)
        {
            for (int i = 0; i < 4; ++i)
            {
                out.push_back(static_cast<uint8_t>((v >> (8 * i)) & 0xff));
            }
        }

        void append_u64(std::vector<uint8_t> &out, uint64_t v)
        {
            for (int i = 0; i < 8; ++i)
            {
                out.push_back(static_cast<uint8_t>((v >> (8 * i)) & 0xff));
            }
        }

        void append_bytes(std::vector<uint8_t> &out, const uint8_t *data, size_t n)
        {
            out.insert(out.end(), data, data + n);
        }

        void append_str(std::vector<uint8_t> &out, const char *s)
        {
            out.insert(out.end(), s, s + std::strlen(s));
        }

        std::array<uint8_t, 32> sha256(const std::vector<uint8_t> &data)
        {
            std::array<uint8_t, 32> dig{};
            SHA256(data.data(), data.size(), dig.data());
            return dig;
        }

        std::array<uint8_t, 32> sha256_pair(const std::array<uint8_t, 32> &a, const std::array<uint8_t, 32> &b)
        {
            std::vector<uint8_t> buf;
            buf.reserve(64);
            append_bytes(buf, a.data(), 32);
            append_bytes(buf, b.data(), 32);
            return sha256(buf);
        }

        std::string to_hex(const std::array<uint8_t, 32> &dig)
        {
            static const char *hexd = "0123456789abcdef";
            std::string s(64, '0');
            for (size_t i = 0; i < 32; ++i)
            {
                s[i * 2] = hexd[dig[i] >> 4];
                s[i * 2 + 1] = hexd[dig[i] & 0x0f];
            }
            return s;
        }

        bool from_hex(const std::string &hex, std::array<uint8_t, 32> &out)
        {
            if (hex.size() != 64)
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
            for (size_t i = 0; i < 32; ++i)
            {
                int hi = nybble(hex[i * 2]);
                int lo = nybble(hex[i * 2 + 1]);
                if (hi < 0 || lo < 0)
                {
                    return false;
                }
                out[i] = static_cast<uint8_t>((hi << 4) | lo);
            }
            return true;
        }

        bool is_zero(const std::array<uint8_t, 32> &d)
        {
            for (uint8_t b : d)
            {
                if (b != 0)
                {
                    return false;
                }
            }
            return true;
        }

        uint64_t now_seconds()
        {
            return static_cast<uint64_t>(std::chrono::system_clock::now().time_since_epoch().count() / 1000000000LL);
        }

        bool official_pi_model(const std::string &model)
        {
            if (model.empty() || model.size() > 128)
            {
                return false;
            }
            if (model.find("Zero") != std::string::npos)
            {
                return false;
            }
            static const char *prefixes[] = {
                "Raspberry Pi 2",
                "Raspberry Pi 3",
                "Raspberry Pi 4",
                "Raspberry Pi 5",
            };
            for (const char *prefix : prefixes)
            {
                if (model.compare(0, std::strlen(prefix), prefix) == 0)
                {
                    return true;
                }
            }
            return false;
        }

        struct TxIn
        {
            std::array<uint8_t, 32> prev{};
            uint32_t vout = 0;
            std::string signature_hex;
            std::string public_key_hex;
        };

        struct TxOut
        {
            uint64_t value = 0;
            std::string address;
        };

        struct Tx
        {
            uint32_t version = 1;
            bool coinbase = false;
            bool reg = false;
            uint32_t height = 0;
            uint64_t fee = 0;
            std::string name;
            std::string reg_address;
            std::vector<TxIn> inputs;
            std::vector<TxOut> outputs;
            std::array<uint8_t, 32> txid{};
        };

        // TX1 || u32 ver || u8 type || inputs || outputs || u64 fee || u32 height
        std::vector<uint8_t> canonical_tx(const Tx &tx)
        {
            std::vector<uint8_t> out;
            append_str(out, "TX1");
            append_u32(out, tx.version);
            out.push_back(tx.coinbase ? 1 : 0);
            append_u32(out, static_cast<uint32_t>(tx.inputs.size()));
            for (const auto &in : tx.inputs)
            {
                append_bytes(out, in.prev.data(), 32);
                append_u32(out, in.vout);
            }
            append_u32(out, static_cast<uint32_t>(tx.outputs.size()));
            for (const auto &o : tx.outputs)
            {
                append_u64(out, o.value);
                append_u16(out, static_cast<uint16_t>(o.address.size()));
                out.insert(out.end(), o.address.begin(), o.address.end());
            }
            append_u64(out, tx.fee);
            append_u32(out, tx.coinbase ? tx.height : 0);
            // Register fields are appended only. A spend's preimage stays TX1.
            if (tx.reg)
            {
                append_str(out, "REG1");
                append_u16(out, static_cast<uint16_t>(tx.name.size()));
                out.insert(out.end(), tx.name.begin(), tx.name.end());
                append_u16(out, static_cast<uint16_t>(tx.reg_address.size()));
                out.insert(out.end(), tx.reg_address.begin(), tx.reg_address.end());
            }
            return out;
        }

        std::array<uint8_t, 32> txid_of(const Tx &tx)
        {
            return sha256(canonical_tx(tx));
        }

        std::array<uint8_t, 32> merkle_root(const std::vector<std::array<uint8_t, 32>> &ids_in)
        {
            std::vector<std::array<uint8_t, 32>> ids = ids_in;
            if (ids.empty())
            {
                return {};
            }
            while (ids.size() > 1)
            {
                if (ids.size() % 2 == 1)
                {
                    ids.push_back(ids.back());
                }
                std::vector<std::array<uint8_t, 32>> next;
                for (size_t i = 0; i < ids.size(); i += 2)
                {
                    next.push_back(sha256_pair(ids[i], ids[i + 1]));
                }
                ids.swap(next);
            }
            return ids[0];
        }

        std::vector<uint8_t> header_preimage(const char *domain,
                                             uint32_t version,
                                             const std::array<uint8_t, 32> &prev,
                                             const std::array<uint8_t, 32> &merkle,
                                             uint64_t timestamp,
                                             uint32_t difficulty,
                                             uint64_t nonce,
                                             const std::string &model,
                                             const std::array<uint8_t, 32> &serial_commitment)
        {
            std::vector<uint8_t> pre;
            append_str(pre, domain);
            append_u32(pre, version);
            append_bytes(pre, prev.data(), 32);
            append_bytes(pre, merkle.data(), 32);
            append_u64(pre, timestamp);
            append_u32(pre, difficulty);
            append_u64(pre, nonce);
            append_u16(pre, static_cast<uint16_t>(model.size()));
            pre.insert(pre.end(), model.begin(), model.end());
            append_bytes(pre, serial_commitment.data(), 32);
            return pre;
        }

        // Height 1–4. One SHA-256 over the PiHash1 preimage.
        std::array<uint8_t, 32> pihash_v1(uint32_t version,
                                           const std::array<uint8_t, 32> &prev,
                                           const std::array<uint8_t, 32> &merkle,
                                           uint64_t timestamp,
                                           uint32_t difficulty,
                                           uint64_t nonce,
                                           const std::string &model,
                                           const std::array<uint8_t, 32> &serial_commitment)
        {
            return sha256(header_preimage("PiHash1", version, prev, merkle, timestamp, difficulty, nonce, model, serial_commitment));
        }

        // Height 5+. Same preimage with domain PiHash2, then PiHash::MixFinalize.
        std::array<uint8_t, 32> pihash_v2(uint32_t version,
                                           const std::array<uint8_t, 32> &prev,
                                           const std::array<uint8_t, 32> &merkle,
                                           uint64_t timestamp,
                                           uint32_t difficulty,
                                           uint64_t nonce,
                                           const std::string &model,
                                           const std::array<uint8_t, 32> &serial_commitment)
        {
            const auto pre = header_preimage("PiHash2", version, prev, merkle, timestamp, difficulty, nonce, model, serial_commitment);
            pisecure::pihash::PiHash hasher(1, 32, false);
            const auto mixed = hasher.MixFinalize(pre, static_cast<uint32_t>(nonce));
            std::array<uint8_t, 32> out{};
            const size_t n = std::min(out.size(), mixed.size());
            for (size_t i = 0; i < n; ++i)
            {
                out[i] = mixed[i];
            }
            return out;
        }

        json as_object_param(const json &params)
        {
            if (params.is_object())
            {
                return params;
            }
            if (params.is_array() && !params.empty())
            {
                if (params[0].is_object())
                {
                    return params[0];
                }
                if (params[0].is_string())
                {
                    try
                    {
                        json parsed = json::parse(params[0].get<std::string>());
                        if (parsed.is_object())
                        {
                            return parsed;
                        }
                    }
                    catch (const std::exception &)
                    {
                    }
                }
            }
            return json();
        }

        std::string wallet_from_params(const json &params)
        {
            if (params.is_array() && params.size() == 1 && params[0].is_string())
            {
                return params[0].get<std::string>();
            }
            json obj = as_object_param(params);
            if (obj.is_object())
            {
                if (obj.contains("wallet") && obj["wallet"].is_string())
                {
                    return obj["wallet"].get<std::string>();
                }
                if (obj.contains("miner") && obj["miner"].is_string())
                {
                    return obj["miner"].get<std::string>();
                }
            }
            return "";
        }

        bool parse_outputs(const json &arr, std::vector<TxOut> &outputs, std::string &reason)
        {
            if (!arr.is_array() || arr.empty())
            {
                reason = "transaction output invalid";
                return false;
            }
            for (const auto &item : arr)
            {
                if (!item.is_object() || !item.contains("address") || !item["address"].is_string() || !item.contains("value") || !item["value"].is_number_unsigned())
                {
                    reason = "transaction output invalid";
                    return false;
                }
                TxOut out;
                out.address = item["address"].get<std::string>();
                out.value = item["value"].get<uint64_t>();
                if (out.address.empty() || out.address.size() > 256 || out.value == 0)
                {
                    reason = "transaction output invalid";
                    return false;
                }
                outputs.push_back(out);
            }
            return true;
        }

        bool parse_inputs(const json &arr, std::vector<TxIn> &inputs, std::string &reason)
        {
            if (!arr.is_array())
            {
                reason = "malformed transaction";
                return false;
            }
            for (const auto &item : arr)
            {
                if (!item.is_object() || !item.contains("prev_txid") || !item["prev_txid"].is_string() || !item.contains("vout") || !item["vout"].is_number_unsigned())
                {
                    reason = "malformed transaction";
                    return false;
                }
                TxIn in;
                if (!from_hex(item["prev_txid"].get<std::string>(), in.prev))
                {
                    reason = "malformed transaction";
                    return false;
                }
                in.vout = item["vout"].get<uint32_t>();
                if (item.contains("signature") && item["signature"].is_string())
                {
                    in.signature_hex = item["signature"].get<std::string>();
                }
                if (item.contains("public_key") && item["public_key"].is_string())
                {
                    in.public_key_hex = item["public_key"].get<std::string>();
                }
                inputs.push_back(in);
            }
            return true;
        }

        json tx_to_json(const Tx &tx)
        {
            json inputs = json::array();
            for (const auto &in : tx.inputs)
            {
                json one = {{"prev_txid", to_hex(in.prev)}, {"vout", in.vout}};
                if (!in.signature_hex.empty())
                {
                    one["signature"] = in.signature_hex;
                }
                if (!in.public_key_hex.empty())
                {
                    one["public_key"] = in.public_key_hex;
                }
                inputs.push_back(one);
            }
            json outputs = json::array();
            for (const auto &o : tx.outputs)
            {
                outputs.push_back({{"address", o.address}, {"value", o.value}});
            }
            json doc = {
                {"txid", to_hex(tx.txid)},
                {"version", tx.version},
                {"inputs", inputs},
                {"outputs", outputs},
                {"fee", tx.fee},
                {"spendable", !tx.inputs.empty()},
                {"signed", !tx.inputs.empty() && std::all_of(tx.inputs.begin(), tx.inputs.end(), [](const TxIn &in)
                                                             { return !in.signature_hex.empty(); })},
                {"size", canonical_tx(tx).size()},
            };
            if (tx.reg)
            {
                doc["type"] = "register";
                doc["name"] = tx.name;
                doc["address"] = tx.reg_address;
            }
            return doc;
        }

        bool parse_user_tx(const json &obj, Tx &tx, std::string &reason)
        {
            if (!obj.is_object())
            {
                reason = "malformed transaction";
                return false;
            }
            // The signed record, public key and signature included. Checked
            // before the input walk, the balance check, and the signature check.
            if (obj.dump().size() > kMaxTxJsonBytes)
            {
                reason = "tx too large";
                return false;
            }
            if (!obj.contains("version") || !obj["version"].is_number_unsigned() || obj["version"].get<uint32_t>() != 1)
            {
                reason = "malformed transaction";
                return false;
            }
            if (!obj.contains("fee") || !obj["fee"].is_number_unsigned())
            {
                reason = "fee too low";
                return false;
            }
            tx.version = 1;
            tx.coinbase = false;
            tx.height = 0;
            tx.reg = false;
            tx.name.clear();
            tx.reg_address.clear();
            tx.fee = obj["fee"].get<uint64_t>();
            if (tx.fee < 1)
            {
                reason = "fee too low";
                return false;
            }
            if (obj.contains("type") && obj["type"].is_string())
            {
                if (obj["type"].get<std::string>() != "register")
                {
                    reason = "malformed transaction";
                    return false;
                }
                if (!obj.contains("name") || !obj["name"].is_string() || !obj.contains("address") || !obj["address"].is_string())
                {
                    reason = "name invalid";
                    return false;
                }
                tx.reg = true;
                tx.name = obj["name"].get<std::string>();
                tx.reg_address = obj["address"].get<std::string>();
                if (tx.reg_address.size() == 67)
                {
                    std::string prefix = tx.reg_address.substr(0, 3);
                    for (char &c : prefix)
                    {
                        if (c >= 'A' && c <= 'Z')
                        {
                            c = static_cast<char>(c - 'A' + 'a');
                        }
                    }
                    if (prefix == "ps1")
                    {
                        std::string hex = tx.reg_address.substr(3);
                        for (char &c : hex)
                        {
                            if (c >= 'A' && c <= 'F')
                            {
                                c = static_cast<char>(c - 'A' + 'a');
                            }
                        }
                        tx.reg_address = "ps1" + hex;
                    }
                }
            }
            if (!obj.contains("inputs") || !obj.contains("outputs"))
            {
                reason = "malformed transaction";
                return false;
            }
            if (obj["inputs"].is_array() && obj["inputs"].size() > kMaxTxInputs)
            {
                reason = "tx too large";
                return false;
            }
            if (!parse_inputs(obj["inputs"], tx.inputs, reason))
            {
                return false;
            }
            if (!parse_outputs(obj["outputs"], tx.outputs, reason))
            {
                return false;
            }
            auto raw = canonical_tx(tx);
            if (raw.size() > kMaxTxBytes)
            {
                reason = "tx too large";
                return false;
            }
            tx.txid = sha256(raw);
            return true;
        }

        struct Emission
        {
            uint64_t subsidy = kSubsidyUnits;
            uint64_t miner_subsidy = kSubsidyUnits - kValidatorUnits;
            uint64_t fee = 0;
            uint64_t miner_fee = 0;
            uint64_t stakers = 0;
            uint64_t loans = 0;
            uint64_t foundation = 0;
            uint64_t burn = 0;

            uint64_t miner_cap() const { return miner_subsidy + miner_fee; }
        };

        uint64_t subsidy_units_for(uint32_t height)
        {
            return height >= kDifficultyActivationHeight ? kSubsidyUnitsAfterActivation : kSubsidyUnits;
        }

        Emission emission_for(uint32_t height, uint64_t fee)
        {
            Emission e;
            e.subsidy = subsidy_units_for(height);
            e.miner_subsidy = e.subsidy - kValidatorUnits;
            e.fee = fee;
            e.miner_fee = fee * 60 / 100;
            e.stakers = fee * 20 / 100;
            e.loans = fee * 8 / 100;
            e.foundation = fee * 7 / 100;
            e.burn = fee - (e.miner_fee + e.stakers + e.loans + e.foundation);
            return e;
        }

        struct CbOut
        {
            std::string role;
            std::string address;
            uint64_t units = 0;
        };

        Tx coinbase_from(uint32_t height, const std::vector<CbOut> &outs)
        {
            Tx tx;
            tx.version = 1;
            tx.coinbase = true;
            tx.height = height;
            tx.fee = 0;
            for (const auto &o : outs)
            {
                if (o.units == 0)
                {
                    continue;
                }
                TxOut out;
                out.address = o.address;
                out.value = o.units;
                tx.outputs.push_back(out);
            }
            tx.txid = txid_of(tx);
            return tx;
        }

        std::vector<CbOut> template_coinbase(const std::string &wallet, const Emission &e)
        {
            std::vector<CbOut> outs;
            outs.push_back(CbOut{"miner", wallet, e.miner_cap()});
            outs.push_back(CbOut{"validator", "validator", kValidatorUnits});
            if (e.stakers > 0)
            {
                outs.push_back(CbOut{"stakers", "stakers", e.stakers});
            }
            if (e.loans > 0)
            {
                outs.push_back(CbOut{"loans", "loans", e.loans});
            }
            if (e.foundation > 0)
            {
                outs.push_back(CbOut{"foundation", kFoundationPayout, e.foundation});
            }
            return outs;
        }

        std::string units_314st(uint64_t units)
        {
            char buf[32];
            std::snprintf(buf, sizeof(buf), "%llu.%03llu",
                          static_cast<unsigned long long>(units / 1000),
                          static_cast<unsigned long long>(units % 1000));
            return buf;
        }

        json coinbase_body(const std::string &wallet, uint32_t height, const Emission &e, const Tx &cb, const std::vector<CbOut> &outs)
        {
            json outputs = json::array();
            for (const auto &o : outs)
            {
                if (o.units == 0)
                {
                    continue;
                }
                outputs.push_back({{"role", o.role},
                                   {"address", o.address},
                                   {"units", o.units},
                                   {"amount", units_314st(o.units)}});
            }
            return json{
                {"wallet", wallet},
                {"height", height},
                {"txid", to_hex(cb.txid)},
                {"unit", "0.001 314ST"},
                {"subsidy", units_314st(e.subsidy)},
                {"subsidy_units", e.subsidy},
                {"outputs", outputs},
                {"fee_units", e.fee},
                {"shares_units", {{"miner", e.miner_fee}, {"stakers", e.stakers}, {"loans", e.loans}, {"foundation", e.foundation}, {"burn", e.burn}}},
            };
        }

        uint32_t clamp_difficulty(uint32_t bits)
        {
            if (bits < kMinDifficultyBits)
            {
                return kMinDifficultyBits;
            }
            if (bits > kMaxDifficultyBits)
            {
                return kMaxDifficultyBits;
            }
            return bits;
        }

        // 60s target. One step per block, never outside 2–4 leading-zero bits.
        // Used for every block at or before the activation height.
        uint32_t next_difficulty_legacy(Storage &storage)
        {
            if (!storage.has_tip())
            {
                return kInitialDifficultyBits;
            }
            uint32_t tip_bits = storage.tip_difficulty();
            uint32_t diff = clamp_difficulty(tip_bits == 0 ? kInitialDifficultyBits : tip_bits);
            auto tip = storage.get_header_by_hash(storage.get_best_block_hash());
            if (!tip || tip->height < 2)
            {
                return diff;
            }
            auto parent = storage.get_header_by_height(tip->height - 1);
            if (!parent || tip->timestamp <= parent->timestamp)
            {
                return diff;
            }
            const uint64_t interval = tip->timestamp - parent->timestamp;
            if (interval < kTargetBlockSeconds && diff < kMaxDifficultyBits)
            {
                ++diff;
            }
            else if (interval > kTargetBlockSeconds && diff > kMinDifficultyBits)
            {
                --diff;
            }
            return diff;
        }

        // Last 10 timestamps, 9 gaps, 540s target, 4x clamp, bits 2–24.
        uint32_t next_difficulty_window(Storage &storage)
        {
            if (!storage.has_tip())
            {
                return kInitialDifficultyBits;
            }
            const uint32_t tip_bits = storage.tip_difficulty();
            uint32_t bits = tip_bits == 0 ? kInitialDifficultyBits : tip_bits;
            if (bits < kRetargetMinBits)
            {
                bits = kRetargetMinBits;
            }
            if (bits > kRetargetMaxBits)
            {
                bits = kRetargetMaxBits;
            }
            auto tip = storage.get_header_by_hash(storage.get_best_block_hash());
            if (!tip || tip->height < 10)
            {
                return bits;
            }
            auto older = storage.get_header_by_height(tip->height - 9);
            if (!older)
            {
                return bits;
            }
            const int64_t elapsed = static_cast<int64_t>(tip->timestamp) - static_cast<int64_t>(older->timestamp);
            return retarget_difficulty_bits(bits, elapsed);
        }

        uint32_t next_difficulty(Storage &storage)
        {
            const uint32_t next_height = storage.has_tip() ? storage.get_best_height() + 1 : 1;
            if (next_height < kDifficultyActivationHeight)
            {
                return next_difficulty_legacy(storage);
            }
            return next_difficulty_window(storage);
        }

        bool units_of(const json &item, uint64_t &units)
        {
            if (item.contains("units") && item["units"].is_number_unsigned())
            {
                units = item["units"].get<uint64_t>();
                return true;
            }
            if (item.contains("value") && item["value"].is_number_unsigned())
            {
                units = item["value"].get<uint64_t>();
                return true;
            }
            return false;
        }

        std::vector<Tx> mempool_txs(Storage &storage)
        {
            std::vector<Tx> txs;
            for (const auto &stored : storage.get_mempool_transactions(1000))
            {
                try
                {
                    json obj = json::parse(stored.data.begin(), stored.data.end());
                    Tx tx;
                    std::string reason;
                    if (!parse_user_tx(obj, tx, reason))
                    {
                        continue;
                    }
                    tx.txid = stored.hash;
                    txs.push_back(std::move(tx));
                }
                catch (const std::exception &)
                {
                }
            }
            std::vector<Tx> ordered;
            std::vector<char> used(txs.size(), 0);
            bool progress = true;
            while (ordered.size() < txs.size() && progress)
            {
                progress = false;
                for (size_t i = 0; i < txs.size(); ++i)
                {
                    if (used[i] != 0)
                    {
                        continue;
                    }
                    bool waiting = false;
                    for (const auto &in : txs[i].inputs)
                    {
                        for (size_t j = 0; j < txs.size(); ++j)
                        {
                            if (i == j || used[j] != 0)
                            {
                                continue;
                            }
                            if (txs[j].txid == in.prev)
                            {
                                waiting = true;
                            }
                        }
                    }
                    if (!waiting)
                    {
                        used[i] = 1;
                        ordered.push_back(txs[i]);
                        progress = true;
                    }
                }
            }
            for (size_t i = 0; i < txs.size(); ++i)
            {
                if (used[i] == 0)
                {
                    ordered.push_back(txs[i]);
                }
            }
            return ordered;
        }

        bool find_outpoint(Storage &storage, const std::array<uint8_t, 32> &prev, uint32_t vout, uint64_t &value, std::string &owner, const std::vector<Tx> *prior);

        bool check_spendable(Storage &storage, const Tx &tx, std::string &reason, const std::vector<Tx> *prior = nullptr)
        {
            if (tx.inputs.empty())
            {
                reason = "transaction inputs missing";
                return false;
            }
            uint64_t input_value = 0;
            for (const auto &in : tx.inputs)
            {
                if (prior != nullptr)
                {
                    for (const auto &earlier : *prior)
                    {
                        for (const auto &spent : earlier.inputs)
                        {
                            if (spent.vout == in.vout && spent.prev == in.prev)
                            {
                                reason = "unknown input";
                                return false;
                            }
                        }
                    }
                }
                uint64_t value = 0;
                std::string owner;
                if (!find_outpoint(storage, in.prev, in.vout, value, owner, prior))
                {
                    reason = "unknown input";
                    return false;
                }
                input_value += value;
            }
            uint64_t output_value = 0;
            for (const auto &o : tx.outputs)
            {
                output_value += o.value;
            }
            if (output_value + tx.fee > input_value)
            {
                reason = "insufficient funds";
                return false;
            }
            return true;
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
            out.reserve(hex.size() / 2);
            for (size_t i = 0; i < hex.size(); i += 2)
            {
                int hi = nybble(hex[i]);
                int lo = nybble(hex[i + 1]);
                if (hi < 0 || lo < 0)
                {
                    return false;
                }
                out.push_back(static_cast<uint8_t>((hi << 4) | lo));
            }
            return true;
        }

        std::string lower_hex(std::string hex)
        {
            for (char &c : hex)
            {
                if (c >= 'A' && c <= 'F')
                {
                    c = static_cast<char>(c - 'A' + 'a');
                }
            }
            return hex;
        }

        std::mutex g_challenge_mu;
        std::unordered_set<std::string> g_challenges;

        std::string issue_challenge()
        {
            std::array<uint8_t, 32> raw{};
            if (RAND_bytes(raw.data(), static_cast<int>(raw.size())) != 1)
            {
                return {};
            }
            const std::string hex = to_hex(raw);
            std::lock_guard<std::mutex> lock(g_challenge_mu);
            g_challenges.insert(hex);
            return hex;
        }

        bool challenge_was_issued(const std::string &hex)
        {
            std::lock_guard<std::mutex> lock(g_challenge_mu);
            return g_challenges.find(hex) != g_challenges.end();
        }

        void retire_challenge(const std::string &hex)
        {
            std::lock_guard<std::mutex> lock(g_challenge_mu);
            g_challenges.erase(hex);
        }

        bool pi_serial_text(const std::string &serial)
        {
            if (serial.empty() || serial.size() > 64)
            {
                return false;
            }
            for (unsigned char c : serial)
            {
                if (c == 0)
                {
                    return false;
                }
                const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
                if (!hex)
                {
                    return false;
                }
            }
            return true;
        }

        bool address_filename(const std::string &address)
        {
            if (address.empty() || address.size() > 128)
            {
                return false;
            }
            for (char c : address)
            {
                const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-';
                if (!ok)
                {
                    return false;
                }
            }
            return true;
        }

        // Bound Ed25519 public key, or false when no key file exists.
        bool bound_public_key(const std::filesystem::path &datadir, const std::string &address, std::string &public_hex)
        {
            if (!address_filename(address))
            {
                return false;
            }
            const auto path = datadir / "wallets" / (address + ".json");
            std::ifstream in(path);
            if (!in)
            {
                return false;
            }
            try
            {
                json doc = json::parse(in);
                if (!doc.is_object() || doc.value("scheme", "") != "ed25519" || !doc.contains("public_key") || !doc["public_key"].is_string())
                {
                    return false;
                }
                public_hex = lower_hex(doc["public_key"].get<std::string>());
                std::vector<uint8_t> raw;
                return decode_hex(public_hex, raw) && raw.size() == 32;
            }
            catch (const std::exception &)
            {
                return false;
            }
        }

        bool is_long_address(const std::string &address)
        {
            if (address.size() != 67 || address.compare(0, 3, "ps1") != 0)
            {
                return false;
            }
            for (size_t i = 3; i < address.size(); ++i)
            {
                const char c = address[i];
                const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                if (!hex)
                {
                    return false;
                }
            }
            return true;
        }

        std::string long_address(const std::vector<uint8_t> &pubkey)
        {
            return "ps1" + to_hex(sha256(pubkey));
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

        std::string canonical_name(const std::string &name)
        {
            // Reserved checks stay case-insensitive. The stored spelling is the one registered.
            return name;
        }

        struct NameRec
        {
            std::string name;
            std::string address;
            std::string kind;
            std::string txid;
        };

        std::mutex g_name_mu;
        std::vector<NameRec> g_names;

        NameRec *find_name_locked(const std::string &name)
        {
            const std::string folded = fold_name(name);
            for (auto &rec : g_names)
            {
                if (fold_name(rec.name) == folded)
                {
                    return &rec;
                }
            }
            return nullptr;
        }

        NameRec *find_address_locked(const std::string &address)
        {
            for (auto &rec : g_names)
            {
                if (rec.address == address)
                {
                    return &rec;
                }
            }
            return nullptr;
        }

        bool remember_name(const std::string &name, const std::string &address, const std::string &kind, const std::string &txid, bool overwrite, std::string &reason)
        {
            if (!valid_shortname(name) || !is_long_address(address))
            {
                reason = "name invalid";
                return false;
            }
            const std::string shown = canonical_name(name);
            std::lock_guard<std::mutex> lock(g_name_mu);
            if (NameRec *by_addr = find_address_locked(address))
            {
                if (fold_name(by_addr->name) != fold_name(shown))
                {
                    reason = "name is taken";
                    return false;
                }
            }
            if (NameRec *existing = find_name_locked(shown))
            {
                if (existing->address == address)
                {
                    if (!txid.empty())
                    {
                        existing->txid = txid;
                    }
                    if (!kind.empty())
                    {
                        existing->kind = kind;
                    }
                    return true;
                }
                if (!overwrite)
                {
                    reason = "name is taken";
                    return false;
                }
                existing->address = address;
                existing->kind = kind;
                existing->txid = txid;
                existing->name = shown;
                return true;
            }
            g_names.push_back(NameRec{shown, address, kind, txid});
            return true;
        }

        json name_snapshot_unlocked()
        {
            json rows = json::array();
            for (const auto &rec : g_names)
            {
                json row = {{"name", rec.name}, {"address", rec.address}, {"kind", rec.kind}};
                if (!rec.txid.empty())
                {
                    row["txid"] = rec.txid;
                }
                rows.push_back(row);
            }
            return rows;
        }

        void save_names(const std::filesystem::path &datadir)
        {
            json reserved = json::array();
            json names = json::array();
            {
                std::lock_guard<std::mutex> lock(g_name_mu);
                for (const auto &rec : g_names)
                {
                    if (rec.kind == "reserved_bind")
                    {
                        reserved.push_back({{"name", rec.name}, {"address", rec.address}});
                    }
                    else
                    {
                        json row = {{"name", rec.name}, {"address", rec.address}};
                        if (!rec.txid.empty())
                        {
                            row["txid"] = rec.txid;
                        }
                        names.push_back(row);
                    }
                }
            }
            json doc = {{"reserved_bind", reserved}, {"names", names}};
            const auto path = datadir / "names.json";
            const auto tmp = datadir / "names.json.tmp";
            {
                std::ofstream out(tmp, std::ios::trunc);
                if (!out)
                {
                    std::cerr << "names.json write failed\n";
                    return;
                }
                out << doc.dump(2) << "\n";
            }
            std::error_code ec;
            std::filesystem::rename(tmp, path, ec);
            if (ec)
            {
                std::cerr << "names.json rename failed\n";
            }
        }

        void absorb_name_record(const json &row, bool chain)
        {
            if (!row.is_object() || !row.contains("name") || !row["name"].is_string() || !row.contains("address") || !row["address"].is_string())
            {
                return;
            }
            std::string address = row["address"].get<std::string>();
            if (is_long_address(address))
            {
                address = "ps1" + lower_hex(address.substr(3));
            }
            std::string kind = "register";
            if (row.contains("kind") && row["kind"].is_string() && row["kind"].get<std::string>() == "reserved_bind")
            {
                kind = "reserved_bind";
            }
            else if (is_reserved_name(row["name"].get<std::string>()))
            {
                kind = "reserved_bind";
            }
            const std::string txid = row.value("txid", std::string());
            std::string reason;
            remember_name(row["name"].get<std::string>(), address, kind, txid, chain, reason);
        }

        void load_names_file(const std::filesystem::path &datadir)
        {
            std::ifstream in(datadir / "names.json");
            if (!in)
            {
                return;
            }
            try
            {
                json doc = json::parse(in);
                if (doc.contains("reserved_bind") && doc["reserved_bind"].is_array())
                {
                    for (const auto &row : doc["reserved_bind"])
                    {
                        json copy = row;
                        copy["kind"] = "reserved_bind";
                        absorb_name_record(copy, false);
                    }
                }
                if (doc.contains("names") && doc["names"].is_array())
                {
                    for (const auto &row : doc["names"])
                    {
                        absorb_name_record(row, false);
                    }
                }
            }
            catch (const std::exception &)
            {
            }
        }

        bool grant_matches(const std::filesystem::path &datadir, const std::string &name, const std::string &address)
        {
            std::ifstream in(datadir / "names.json");
            if (!in)
            {
                return false;
            }
            try
            {
                json doc = json::parse(in);
                if (!doc.contains("reserved_bind") || !doc["reserved_bind"].is_array())
                {
                    return false;
                }
                for (const auto &row : doc["reserved_bind"])
                {
                    if (!row.is_object() || !row.contains("name") || !row["name"].is_string() || !row.contains("address") || !row["address"].is_string())
                    {
                        continue;
                    }
                    std::string bound = row["address"].get<std::string>();
                    if (is_long_address(bound))
                    {
                        bound = "ps1" + lower_hex(bound.substr(3));
                    }
                    if (fold_name(row["name"].get<std::string>()) == fold_name(name) && bound == address)
                    {
                        std::string reason;
                        remember_name(name, address, "reserved_bind", "", false, reason);
                        return true;
                    }
                }
            }
            catch (const std::exception &)
            {
            }
            return false;
        }

        bool lookup_name(const std::string &query, std::string &address, std::string &shown, std::string &kind)
        {
            std::lock_guard<std::mutex> lock(g_name_mu);
            if (NameRec *rec = find_name_locked(query))
            {
                address = rec->address;
                shown = rec->name;
                kind = rec->kind;
                return true;
            }
            return false;
        }

        bool lookup_ps1(const std::string &address, std::string &shown, std::string &kind)
        {
            std::lock_guard<std::mutex> lock(g_name_mu);
            if (NameRec *rec = find_address_locked(address))
            {
                shown = rec->name;
                kind = rec->kind;
                return true;
            }
            return false;
        }

        bool resolve_miner(const std::string &wallet, std::string &shown, std::string &payout, std::string &reason)
        {
            if (wallet.empty() || wallet.size() > 256)
            {
                reason = "wallet or miner address required";
                return false;
            }
            if (wallet.size() == 67)
            {
                std::string prefix = wallet.substr(0, 3);
                for (char &c : prefix)
                {
                    if (c >= 'A' && c <= 'Z')
                    {
                        c = static_cast<char>(c - 'A' + 'a');
                    }
                }
                std::string hex = wallet.substr(3);
                for (char &c : hex)
                {
                    if (c >= 'A' && c <= 'F')
                    {
                        c = static_cast<char>(c - 'A' + 'a');
                    }
                }
                const std::string ps1 = prefix + hex;
                if (prefix == "ps1" && is_long_address(ps1))
                {
                    shown = ps1;
                    payout = ps1;
                    return true;
                }
            }
            if (!valid_shortname(wallet))
            {
                reason = "unknown shortname";
                return false;
            }
            std::string kind;
            if (!lookup_name(wallet, payout, shown, kind))
            {
                reason = "unknown shortname";
                return false;
            }
            return true;
        }

        void resolve_output_names(Tx &tx)
        {
            bool changed = false;
            for (auto &out : tx.outputs)
            {
                std::string address;
                std::string shown;
                std::string kind;
                if (lookup_name(out.address, address, shown, kind) && address != out.address)
                {
                    out.address = address;
                    changed = true;
                }
            }
            if (changed)
            {
                tx.txid = txid_of(tx);
            }
        }

        bool admit_register(Storage &storage, const Tx &tx, std::string &reason, bool local_policy, const std::vector<Tx> *prior)
        {
            if (!tx.reg)
            {
                return true;
            }
            if (!valid_shortname(tx.name))
            {
                reason = "name invalid";
                return false;
            }
            if (!is_long_address(tx.reg_address))
            {
                reason = "address does not match signer";
                return false;
            }
            for (const auto &in : tx.inputs)
            {
                uint64_t value = 0;
                std::string owner;
                if (!find_outpoint(storage, in.prev, in.vout, value, owner, prior))
                {
                    reason = "unknown input";
                    return false;
                }
                if (owner != tx.reg_address)
                {
                    reason = "address does not match signer";
                    return false;
                }
                std::vector<uint8_t> pubkey;
                if (!decode_hex(in.public_key_hex, pubkey) || long_address(pubkey) != tx.reg_address)
                {
                    reason = "address does not match signer";
                    return false;
                }
            }
            std::string existing;
            std::string shown;
            std::string kind;
            if (lookup_name(tx.name, existing, shown, kind) && existing != tx.reg_address)
            {
                reason = "name is taken";
                return false;
            }
            if (is_reserved_name(tx.name))
            {
                if (local_policy && !grant_matches(storage.datadir(), tx.name, tx.reg_address))
                {
                    reason = "name is reserved";
                    return false;
                }
            }
            return true;
        }

        bool find_outpoint(Storage &storage, const std::array<uint8_t, 32> &prev, uint32_t vout, uint64_t &value, std::string &owner, const std::vector<Tx> *prior)
        {
            if (storage.utxo_available(prev, vout, value) && storage.utxo_address(prev, vout, owner))
            {
                return true;
            }
            if (prior == nullptr)
            {
                return false;
            }
            for (const auto &tx : *prior)
            {
                if (tx.txid != prev || vout >= tx.outputs.size())
                {
                    continue;
                }
                value = tx.outputs[vout].value;
                owner = tx.outputs[vout].address;
                return true;
            }
            return false;
        }

        void absorb_block_names(const json &block)
        {
            if (block.contains("txs") && block["txs"].is_array())
            {
                for (const auto &txj : block["txs"])
                {
                    if (!txj.is_object() || txj.value("type", "") != "register")
                    {
                        continue;
                    }
                    absorb_name_record(txj, true);
                }
            }
            if (block.contains("names") && block["names"].is_array())
            {
                for (const auto &row : block["names"])
                {
                    absorb_name_record(row, true);
                }
            }
        }

        json snapshot_including(const std::vector<Tx> &txs)
        {
            json rows;
            {
                std::lock_guard<std::mutex> lock(g_name_mu);
                rows = name_snapshot_unlocked();
            }
            for (const auto &tx : txs)
            {
                if (!tx.reg)
                {
                    continue;
                }
                bool found = false;
                for (auto &row : rows)
                {
                    if (fold_name(row.value("name", "")) == fold_name(tx.name))
                    {
                        row["name"] = canonical_name(tx.name);
                        row["address"] = tx.reg_address;
                        row["kind"] = is_reserved_name(tx.name) ? "reserved_bind" : "register";
                        row["txid"] = to_hex(tx.txid);
                        found = true;
                    }
                }
                if (!found)
                {
                    rows.push_back({{"name", canonical_name(tx.name)},
                                    {"address", tx.reg_address},
                                    {"kind", is_reserved_name(tx.name) ? "reserved_bind" : "register"},
                                    {"txid", to_hex(tx.txid)}});
                }
            }
            return rows;
        }

        // Canonical UTF-8 JSON of the tx with signature fields removed. Keys are sorted.
        std::string sign_payload(const Tx &tx)
        {
            json inputs = json::array();
            for (const auto &in : tx.inputs)
            {
                inputs.push_back({{"prev_txid", to_hex(in.prev)}, {"vout", in.vout}});
            }
            json outputs = json::array();
            for (const auto &o : tx.outputs)
            {
                outputs.push_back({{"address", o.address}, {"value", o.value}});
            }
            json body = {{"fee", tx.fee}, {"inputs", inputs}, {"outputs", outputs}, {"version", tx.version}};
            if (tx.reg)
            {
                body["type"] = "register";
                body["name"] = tx.name;
                body["address"] = tx.reg_address;
            }
            return body.dump();
        }

        bool ed25519_verify(const std::vector<uint8_t> &pubkey, const std::vector<uint8_t> &sig, const std::string &message)
        {
            if (pubkey.size() != 32 || sig.size() != 64)
            {
                return false;
            }
            EVP_PKEY *key = EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519, nullptr, pubkey.data(), pubkey.size());
            if (key == nullptr)
            {
                return false;
            }
            EVP_MD_CTX *ctx = EVP_MD_CTX_new();
            const int init_ok = ctx != nullptr && EVP_DigestVerifyInit(ctx, nullptr, nullptr, nullptr, key) == 1;
            const int ok = init_ok && EVP_DigestVerify(ctx, sig.data(), sig.size(), reinterpret_cast<const unsigned char *>(message.data()), message.size()) == 1;
            EVP_MD_CTX_free(ctx);
            EVP_PKEY_free(key);
            return ok;
        }

        bool verify_input_signatures(Storage &storage, const Tx &tx, std::string &reason, bool require_local_key, const std::vector<Tx> *prior = nullptr)
        {
            if (tx.inputs.empty())
            {
                reason = "transaction inputs missing";
                return false;
            }
            const std::string message = sign_payload(tx);
            for (const auto &in : tx.inputs)
            {
                uint64_t value = 0;
                std::string owner;
                if (!find_outpoint(storage, in.prev, in.vout, value, owner, prior))
                {
                    reason = "unknown input";
                    return false;
                }
                const bool ps1_owner = is_long_address(owner);
                std::string bound;
                const bool have_local = bound_public_key(storage.datadir(), owner, bound);
                if (require_local_key && !have_local && !ps1_owner)
                {
                    reason = "address has no spending key";
                    return false;
                }
                if (in.signature_hex.empty())
                {
                    // Miner RPC still rejects. A synced historical block may
                    // predate signatures; the PiHash and model checks still run.
                    // A ps1 output always needs a signature.
                    if (require_local_key || ps1_owner)
                    {
                        reason = "signature missing";
                        return false;
                    }
                    continue;
                }
                if (in.public_key_hex.empty())
                {
                    reason = "public key does not match address";
                    return false;
                }
                const std::string presented = lower_hex(in.public_key_hex);
                if (have_local && presented != bound)
                {
                    reason = "public key does not match address";
                    return false;
                }
                std::vector<uint8_t> pubkey;
                std::vector<uint8_t> sig;
                if (!decode_hex(presented, pubkey) || pubkey.size() != 32)
                {
                    reason = "public key does not match address";
                    return false;
                }
                if (ps1_owner && long_address(pubkey) != owner)
                {
                    reason = "public key does not match address";
                    return false;
                }
                if (!decode_hex(in.signature_hex, sig) || !ed25519_verify(pubkey, sig, message))
                {
                    reason = "signature invalid";
                    return false;
                }
            }
            return true;
        }

        // Accepted spends live in memory. A restart used to drop them, so the
        // next block was mined with an empty tx list and the payment never
        // became a UTXO. The file is replayed after the chain UTXO set exists.
        void save_mempool(Storage &storage)
        {
            json arr = json::array();
            for (const auto &stored : storage.get_mempool_transactions(1000))
            {
                try
                {
                    arr.push_back(json::parse(stored.data.begin(), stored.data.end()));
                }
                catch (const std::exception &)
                {
                }
            }
            const auto path = storage.datadir() / "mempool.json";
            const auto tmp = storage.datadir() / "mempool.json.tmp";
            {
                std::ofstream out(tmp, std::ios::trunc);
                if (!out)
                {
                    std::cerr << "mempool save failed\n";
                    return;
                }
                out << arr.dump();
            }
            std::error_code ec;
            std::filesystem::rename(tmp, path, ec);
            if (ec)
            {
                std::cerr << "mempool save failed\n";
            }
        }

        void load_mempool(Storage &storage)
        {
            const auto path = storage.datadir() / "mempool.json";
            std::ifstream in(path);
            if (!in)
            {
                return;
            }
            json arr;
            try
            {
                in >> arr;
            }
            catch (const std::exception &)
            {
                return;
            }
            if (!arr.is_array())
            {
                return;
            }
            uint32_t kept = 0;
            for (const auto &obj : arr)
            {
                Tx tx;
                std::string reason;
                if (!parse_user_tx(obj, tx, reason))
                {
                    continue;
                }
                resolve_output_names(tx);
                if (storage.has_transaction(tx.txid))
                {
                    continue;
                }
                if (tx.inputs.empty() || !check_spendable(storage, tx, reason, nullptr) || !verify_input_signatures(storage, tx, reason, true, nullptr))
                {
                    continue;
                }
                const json stored_tx = tx_to_json(tx);
                const auto dumped = stored_tx.dump();
                Transaction stored;
                stored.hash = tx.txid;
                stored.data.assign(dumped.begin(), dumped.end());
                stored.timestamp = now_seconds();
                stored.fee = tx.fee;
                if (storage.add_transaction(stored))
                {
                    ++kept;
                }
            }
            if (kept != arr.size())
            {
                save_mempool(storage);
            }
            if (kept > 0)
            {
                std::cout << "mempool restored " << kept << "\n";
            }
        }
    }

    bool restore_chain(Storage &storage)
    {
        load_names_file(storage.datadir());
        const uint64_t count = storage.next_index();
        struct Found
        {
            uint64_t index = 0;
            uint32_t height = 0;
            json obj;
        };
        std::vector<Found> found;
        for (uint64_t i = 0; i < count; ++i)
        {
            auto raw = storage.read_block(i);
            if (!raw)
            {
                continue;
            }
            try
            {
                const std::string text(raw->begin(), raw->end());
                json obj = json::parse(text);
                if (!obj.is_object() || !obj.contains("height") || !obj.contains("hash") || !obj.contains("prev_block_hash"))
                {
                    continue;
                }
                found.push_back(Found{i, obj["height"].get<uint32_t>(), obj});
            }
            catch (const std::exception &)
            {
            }
        }
        std::sort(found.begin(), found.end(), [](const Found &a, const Found &b)
                  { return a.height < b.height; });

        std::array<uint8_t, 32> expected_prev{};
        uint32_t expected_height = 1;
        uint32_t restored = 0;
        for (const auto &item : found)
        {
            std::array<uint8_t, 32> prev{};
            std::array<uint8_t, 32> hash{};
            if (!from_hex(item.obj.value("prev_block_hash", ""), prev) || !from_hex(item.obj.value("hash", ""), hash))
            {
                continue;
            }
            if (item.height != expected_height || prev != expected_prev)
            {
                continue;
            }

            BlockHeader header{};
            header.version = item.obj.value("version", 1u);
            header.prevBlockHash = prev;
            from_hex(item.obj.value("merkle_root", std::string(64, '0')), header.merkleRoot);
            header.timestamp = item.obj.value("timestamp", 0ull);
            header.difficulty = item.obj.value("difficulty", 0u);
            header.nonce = item.obj.value("nonce", 0ull);
            header.hash = hash;
            header.height = item.height;
            if (!storage.index_existing_block(item.index, header))
            {
                std::cerr << "Failed to index block at height " << item.height << "\n";
                return false;
            }

            std::vector<Storage::UtxoCredit> coinbase_credits;
            if (item.obj.contains("coinbase") && item.obj["coinbase"].is_object())
            {
                const auto &cb = item.obj["coinbase"];
                std::array<uint8_t, 32> txid{};
                if (cb.contains("txid") && cb["txid"].is_string() && from_hex(cb["txid"].get<std::string>(), txid))
                {
                    if (cb.contains("outputs") && cb["outputs"].is_array())
                    {
                        uint32_t vout = 0;
                        for (const auto &o : cb["outputs"])
                        {
                            uint64_t units = 0;
                            if (o.is_object() && units_of(o, units) && units > 0)
                            {
                                coinbase_credits.push_back(Storage::UtxoCredit{txid, vout, units, o.value("address", std::string())});
                            }
                            ++vout;
                        }
                    }
                    else
                    {
                        coinbase_credits.push_back(Storage::UtxoCredit{txid, 0, cb.value("value", 0ull), cb.value("wallet", std::string())});
                    }
                }
            }
            if (!coinbase_credits.empty() && !storage.apply_utxos({}, coinbase_credits))
            {
                std::cerr << "UTXO replay failed at height " << item.height << "\n";
                return false;
            }
            if (item.obj.contains("txs") && item.obj["txs"].is_array())
            {
                for (const auto &txj : item.obj["txs"])
                {
                    Tx tx;
                    std::string reason;
                    if (!parse_user_tx(txj, tx, reason))
                    {
                        continue;
                    }
                    std::vector<Storage::UtxoSpend> spends;
                    std::vector<Storage::UtxoCredit> credits;
                    for (const auto &in : tx.inputs)
                    {
                        spends.push_back(Storage::UtxoSpend{in.prev, in.vout});
                    }
                    uint32_t vout = 0;
                    for (const auto &o : tx.outputs)
                    {
                        credits.push_back(Storage::UtxoCredit{tx.txid, vout, o.value, o.address});
                        ++vout;
                    }
                    if (!storage.apply_utxos(spends, credits))
                    {
                        std::cerr << "UTXO replay failed at height " << item.height << "\n";
                        return false;
                    }
                }
            }
            absorb_block_names(item.obj);
            expected_prev = hash;
            expected_height = item.height + 1;
            ++restored;
        }
        if (restored == 0)
        {
            std::cout << "Chain restore: no linked blocks on disk\n";
        }
        else
        {
            std::cout << "Chain restore: tip height " << storage.get_best_height() << "\n";
        }
        load_mempool(storage);
        return true;
    }

    json rpc_getblocktemplate(Storage &storage, const json &params)
    {
        const std::string wallet = wallet_from_params(params);
        std::string shown;
        std::string payout;
        std::string why;
        if (!resolve_miner(wallet, shown, payout, why))
        {
            throw std::runtime_error(why);
        }

        const bool tipped = storage.has_tip();
        // Empty chain reports height 0, so the next block is height 1.
        const uint32_t next_height = storage.get_best_height() + 1;
        std::array<uint8_t, 32> prev{};
        if (tipped)
        {
            prev = storage.get_best_block_hash();
        }
        const uint32_t difficulty = next_difficulty(storage);
        uint64_t fee_units = 0;
        json txs = json::array();
        std::vector<std::array<uint8_t, 32>> txids;
        for (const auto &tx : mempool_txs(storage))
        {
            txs.push_back(tx_to_json(tx));
            // Placeholders have no inputs and cannot be mined. Their fee is not emitted.
            if (!tx.inputs.empty())
            {
                fee_units += tx.fee;
                txids.push_back(tx.txid);
            }
        }
        const Emission emit = emission_for(next_height, fee_units);
        const std::vector<CbOut> cb_outs = template_coinbase(payout, emit);
        Tx cb = coinbase_from(next_height, cb_outs);
        std::vector<std::array<uint8_t, 32>> ids{cb.txid};
        ids.insert(ids.end(), txids.begin(), txids.end());
        const auto root = merkle_root(ids);
        json coinbase = coinbase_body(shown, next_height, emit, cb, cb_outs);

        return json{
            {"version", 1},
            {"height", next_height},
            {"prev_block_hash", to_hex(prev)},
            {"timestamp", now_seconds()},
            {"difficulty", difficulty},
            {"subsidy_units", emit.subsidy},
            {"coinbase", coinbase},
            {"coinbase_txid", to_hex(cb.txid)},
            {"merkle_root", to_hex(root)},
            {"txs", txs},
            {"hw_proof", next_height >= 4
                             ? json{{"model", ""},
                                   {"serial_commitment", ""},
                                   {"challenge", issue_challenge()},
                                   {"serial_rule", "sha256(serial_utf8 || challenge_bytes)"}}
                             : json{{"model", ""}, {"serial_commitment", ""}}},
            {"pihash", next_height >= 5
                           ? json{{"algorithm", "pihash2"},
                                 {"domain", "PiHash2"},
                                 {"rounds", 1},
                                 {"memory_mb", 32},
                                 {"difficulty_means", "leading zero bits"}}
                           : json{{"algorithm", "sha256-pihash1"},
                                 {"domain", "PiHash1"},
                                 {"difficulty_means", "leading zero bits"}}},
        };
    }

    json rpc_sendtransaction(Storage &storage, const json &params)
    {
        json obj = as_object_param(params);
        if (obj.is_null() || !obj.is_object())
        {
            return rejected("malformed transaction");
        }
        Tx tx;
        std::string reason;
        if (!parse_user_tx(obj, tx, reason))
        {
            return rejected(reason);
        }
        resolve_output_names(tx);
        if (storage.has_transaction(tx.txid))
        {
            return rejected("duplicate transaction");
        }
        const std::vector<Tx> prior = mempool_txs(storage);
        if (!tx.inputs.empty())
        {
            if (!check_spendable(storage, tx, reason, &prior))
            {
                return rejected(reason);
            }
            if (!verify_input_signatures(storage, tx, reason, true, &prior))
            {
                return rejected(reason);
            }
            if (!admit_register(storage, tx, reason, true, &prior))
            {
                return rejected(reason);
            }
            for (const auto &existing : prior)
            {
                for (const auto &in : existing.inputs)
                {
                    for (const auto &mine : tx.inputs)
                    {
                        if (in.vout == mine.vout && in.prev == mine.prev)
                        {
                            return rejected("duplicate transaction");
                        }
                    }
                }
            }
        }

        const json stored_tx = tx_to_json(tx);
        auto dumped = stored_tx.dump();
        Transaction stored;
        stored.hash = tx.txid;
        stored.data.assign(dumped.begin(), dumped.end());
        stored.timestamp = now_seconds();
        stored.fee = tx.fee;
        if (!storage.add_transaction(stored))
        {
            return rejected("malformed transaction");
        }
        save_mempool(storage);
        std::cout << "accepted tx " << to_hex(tx.txid) << "\n";
        if (tx.reg)
        {
            const std::string kind = is_reserved_name(tx.name) ? "reserved_bind" : "register";
            if (!remember_name(tx.name, tx.reg_address, kind, to_hex(tx.txid), false, reason))
            {
                storage.remove_transaction(tx.txid);
                return rejected(reason.empty() ? "name is taken" : reason);
            }
            save_names(storage.datadir());
        }
        return json{{"status", "accepted"}, {"txid", to_hex(tx.txid)}};
    }

    json rpc_getmempool(Storage &storage)
    {
        json txs = json::array();
        uint64_t bytes = 0;
        for (const auto &tx : mempool_txs(storage))
        {
            json item = tx_to_json(tx);
            bytes += item.value("size", 0ull);
            txs.push_back(item);
        }
        return json{{"count", txs.size()}, {"bytes", bytes}, {"transactions", txs}};
    }

    json rpc_submitblock(Storage &storage, P2PServer *p2p, const json &params, bool require_local_policy)
    {
        json block = as_object_param(params);
        if (!block.is_object() || block.empty())
        {
            return rejected("missing block");
        }
        if (!block.contains("hw_proof") || !block["hw_proof"].is_object())
        {
            return rejected("missing hw_proof");
        }
        const json proof = block["hw_proof"];
        if (!proof.contains("model") || !proof["model"].is_string() || !official_pi_model(proof["model"].get<std::string>()))
        {
            return rejected("hw_proof model is not an official Raspberry Pi 2/3/4/5");
        }
        const std::string model = proof["model"].get<std::string>();
        std::array<uint8_t, 32> serial{};
        if (!proof.contains("serial_commitment") || !proof["serial_commitment"].is_string() || !from_hex(proof["serial_commitment"].get<std::string>(), serial) || is_zero(serial))
        {
            return rejected("hw_proof serial_commitment missing or malformed");
        }

        if (!block.contains("version") || !block["version"].is_number_unsigned() || block["version"].get<uint32_t>() != 1)
        {
            return rejected("version invalid");
        }
        if (!block.contains("height") || !block["height"].is_number_unsigned())
        {
            return rejected("height does not extend tip");
        }
        if (!block.contains("nonce") || !block["nonce"].is_number_unsigned())
        {
            return rejected("nonce invalid");
        }
        if (!block.contains("timestamp") || !block["timestamp"].is_number_unsigned())
        {
            return rejected("timestamp invalid");
        }
        if (!block.contains("difficulty") || !block["difficulty"].is_number_unsigned())
        {
            return rejected("difficulty mismatch");
        }
        if (!block.contains("prev_block_hash") || !block["prev_block_hash"].is_string())
        {
            return rejected("prev hash does not link tip");
        }
        if (!block.contains("merkle_root") || !block["merkle_root"].is_string())
        {
            return rejected("merkle root mismatch");
        }
        if (!block.contains("hash") || !block["hash"].is_string())
        {
            return rejected("pihash missing");
        }
        if (!block.contains("coinbase") || !block["coinbase"].is_object())
        {
            return rejected("coinbase missing");
        }
        const json coinbase = block["coinbase"];
        if (!coinbase.contains("wallet") || !coinbase["wallet"].is_string() || coinbase["wallet"].get<std::string>().empty())
        {
            return rejected("coinbase wallet missing");
        }
        const std::string wallet_field = coinbase["wallet"].get<std::string>();
        if (wallet_field.size() > 256)
        {
            return rejected("coinbase wallet missing");
        }
        std::string shown;
        std::string payout;
        std::string why;
        if (!resolve_miner(wallet_field, shown, payout, why))
        {
            // Blocks already on the chain used the literal wallet string
            // ("operator") before shortnames existed. Sync checks the amounts.
            // A newly mined block still has to name a ps1 or a registered shortname.
            if (!require_local_policy)
            {
                shown = wallet_field;
                payout = wallet_field;
            }
            else
            {
                return rejected(why == "wallet or miner address required" ? std::string("coinbase wallet missing") : why);
            }
        }
        const std::string wallet = shown;

        const bool tipped = storage.has_tip();
        const uint32_t expect_height = tipped ? storage.get_best_height() + 1 : 1;
        std::array<uint8_t, 32> expect_prev{};
        if (tipped)
        {
            expect_prev = storage.get_best_block_hash();
        }
        const uint32_t expect_diff = next_difficulty(storage);

        std::array<uint8_t, 32> prev{};
        if (!from_hex(block["prev_block_hash"].get<std::string>(), prev) || prev != expect_prev)
        {
            return rejected("prev hash does not link tip");
        }
        const uint32_t height = block["height"].get<uint32_t>();
        if (height != expect_height)
        {
            return rejected("height does not extend tip");
        }
        std::string serial_text;
        std::string challenge_hex;
        if (height >= 4)
        {
            if (!proof.contains("challenge") || !proof["challenge"].is_string() || proof["challenge"].get<std::string>().empty())
            {
                return rejected("hw_proof challenge missing");
            }
            challenge_hex = lower_hex(proof["challenge"].get<std::string>());
            std::array<uint8_t, 32> challenge_raw{};
            if (!from_hex(challenge_hex, challenge_raw) || (require_local_policy && !challenge_was_issued(challenge_hex)))
            {
                return rejected("hw_proof challenge mismatch");
            }
            if (!proof.contains("serial") || !proof["serial"].is_string() || !pi_serial_text(proof["serial"].get<std::string>()))
            {
                return rejected("hw_proof serial missing or malformed");
            }
            serial_text = proof["serial"].get<std::string>();
            std::vector<uint8_t> bind;
            bind.insert(bind.end(), serial_text.begin(), serial_text.end());
            bind.insert(bind.end(), challenge_raw.begin(), challenge_raw.end());
            if (sha256(bind) != serial)
            {
                return rejected("hw_proof serial_commitment does not bind serial and challenge");
            }
        }
        const uint32_t difficulty = block["difficulty"].get<uint32_t>();
        if (difficulty != expect_diff)
        {
            return rejected("difficulty mismatch");
        }
        const uint64_t timestamp = block["timestamp"].get<uint64_t>();
        const uint64_t now = now_seconds();
        if (timestamp == 0 || timestamp > now + 120)
        {
            return rejected("timestamp invalid");
        }
        if (tipped)
        {
            auto prev_header = storage.get_header_by_hash(expect_prev);
            if (prev_header && timestamp <= prev_header->timestamp)
            {
                return rejected("timestamp invalid");
            }
        }
        const uint64_t nonce = block["nonce"].get<uint64_t>();
        if (coinbase.value("height", 0u) != height)
        {
            return rejected("coinbase missing");
        }

        std::vector<Tx> txs;
        if (block.contains("txs") && !block["txs"].is_null())
        {
            if (!block["txs"].is_array())
            {
                return rejected("malformed transaction");
            }
            std::vector<Tx> prior;
            for (const auto &txj : block["txs"])
            {
                Tx tx;
                std::string reason;
                if (!parse_user_tx(txj, tx, reason))
                {
                    return rejected(reason);
                }
                resolve_output_names(tx);
                if (!check_spendable(storage, tx, reason, &prior))
                {
                    return rejected(reason);
                }
                if (!verify_input_signatures(storage, tx, reason, require_local_policy, &prior))
                {
                    return rejected(reason);
                }
                if (!admit_register(storage, tx, reason, require_local_policy, &prior))
                {
                    return rejected(reason);
                }
                prior.push_back(tx);
                txs.push_back(tx);
            }
        }

        uint64_t fee_units = 0;
        for (const auto &tx : txs)
        {
            fee_units += tx.fee;
        }
        const Emission emit = emission_for(height, fee_units);
        std::vector<CbOut> cb_outs;
        if (coinbase.contains("outputs") && coinbase["outputs"].is_array())
        {
            for (const auto &item : coinbase["outputs"])
            {
                if (!item.is_object() || !item.contains("role") || !item["role"].is_string() || !item.contains("address") || !item["address"].is_string())
                {
                    return rejected("coinbase missing");
                }
                CbOut out;
                out.role = item["role"].get<std::string>();
                out.address = item["address"].get<std::string>();
                if (!units_of(item, out.units) || out.address.empty())
                {
                    return rejected("coinbase missing");
                }
                if (out.role == "miner" && out.address != payout)
                {
                    return rejected("coinbase wallet missing");
                }
                cb_outs.push_back(out);
            }
        }
        else if (coinbase.contains("value") && coinbase["value"].is_number_unsigned())
        {
            cb_outs.push_back(CbOut{"miner", payout, coinbase["value"].get<uint64_t>()});
        }
        else
        {
            return rejected("coinbase missing");
        }

        uint64_t paid_miner = 0, paid_validator = 0, paid_stakers = 0, paid_loans = 0, paid_foundation = 0;
        for (const auto &o : cb_outs)
        {
            if (o.role == "burn")
            {
                return rejected("coinbase exceeds emission rules");
            }
            if (o.role == "miner")
                paid_miner += o.units;
            else if (o.role == "validator")
                paid_validator += o.units;
            else if (o.role == "stakers")
                paid_stakers += o.units;
            else if (o.role == "loans")
                paid_loans += o.units;
            else if (o.role == "foundation")
            {
                if (o.address != kFoundationPayout)
                {
                    return rejected("coinbase foundation address");
                }
                paid_foundation += o.units;
            }
            else
            {
                return rejected("coinbase exceeds emission rules");
            }
        }
        const uint64_t minted = paid_miner + paid_validator + paid_stakers + paid_loans + paid_foundation;
        const uint64_t mint_cap = emit.subsidy + emit.miner_fee + emit.stakers + emit.loans + emit.foundation;
        if (paid_miner > emit.miner_cap() || paid_validator > kValidatorUnits || paid_stakers > emit.stakers || paid_loans > emit.loans || paid_foundation != emit.foundation || minted > mint_cap)
        {
            return rejected("coinbase exceeds emission rules");
        }

        Tx cb = coinbase_from(height, cb_outs);
        if (cb.outputs.empty())
        {
            return rejected("coinbase missing");
        }
        if (coinbase.contains("txid") && coinbase["txid"].is_string() && coinbase["txid"].get<std::string>() != to_hex(cb.txid))
        {
            return rejected("coinbase missing");
        }

        std::vector<std::array<uint8_t, 32>> ids{cb.txid};
        for (const auto &tx : txs)
        {
            ids.push_back(tx.txid);
        }
        const auto root = merkle_root(ids);
        std::array<uint8_t, 32> claimed_root{};
        if (!from_hex(block["merkle_root"].get<std::string>(), claimed_root) || claimed_root != root)
        {
            return rejected("merkle root mismatch");
        }

        if (height >= 5)
        {
            std::string algo;
            if (block.contains("pihash") && block["pihash"].is_object() && block["pihash"].contains("algorithm") && block["pihash"]["algorithm"].is_string())
            {
                algo = block["pihash"]["algorithm"].get<std::string>();
            }
            if (algo != "pihash2")
            {
                return rejected("pihash algorithm not pihash2");
            }
        }
        const auto digest = height >= 5
                                ? pihash_v2(1, prev, root, timestamp, difficulty, nonce, model, serial)
                                : pihash_v1(1, prev, root, timestamp, difficulty, nonce, model, serial);
        std::array<uint8_t, 32> claimed{};
        if (!from_hex(block["hash"].get<std::string>(), claimed))
        {
            return rejected("pihash missing");
        }
        if (claimed != digest)
        {
            return rejected("pihash mismatch");
        }
        if (!storage.validate_block_pow(digest, difficulty))
        {
            return rejected("pihash does not meet difficulty");
        }

        json stored = block;
        stored["version"] = 1;
        stored["height"] = height;
        stored["prev_block_hash"] = to_hex(prev);
        stored["merkle_root"] = to_hex(root);
        stored["timestamp"] = timestamp;
        stored["difficulty"] = difficulty;
        stored["nonce"] = nonce;
        stored["hash"] = to_hex(digest);
        stored["coinbase"] = coinbase_body(wallet, height, emit, cb, cb_outs);
        json stored_txs = json::array();
        for (const auto &tx : txs)
        {
            stored_txs.push_back(tx_to_json(tx));
        }
        stored["txs"] = stored_txs;
        stored["names"] = snapshot_including(txs);
        json stored_proof = {{"model", model}, {"serial_commitment", to_hex(serial)}};
        if (height >= 4)
        {
            stored_proof["challenge"] = challenge_hex;
            stored_proof["serial"] = serial_text;
        }
        stored["hw_proof"] = stored_proof;

        const std::string dumped = stored.dump();
        if (dumped.size() > kMaxBlockBytes)
        {
            return rejected("block too large");
        }

        BlockHeader header{};
        header.version = 1;
        header.prevBlockHash = prev;
        header.merkleRoot = root;
        header.timestamp = timestamp;
        header.difficulty = difficulty;
        header.nonce = nonce;
        header.hash = digest;
        header.height = height;

        std::vector<uint8_t> raw(dumped.begin(), dumped.end());
        if (!storage.store_block_with_header(digest, header, raw))
        {
            return rejected("block too large");
        }
        if (height >= 4 && require_local_policy)
        {
            retire_challenge(challenge_hex);
        }

        std::vector<Storage::UtxoCredit> coinbase_credits;
        uint32_t cb_vout = 0;
        for (const auto &o : cb.outputs)
        {
            coinbase_credits.push_back(Storage::UtxoCredit{cb.txid, cb_vout, o.value, o.address});
            ++cb_vout;
        }
        if (!coinbase_credits.empty() && !storage.apply_utxos({}, coinbase_credits))
        {
            std::cerr << "Block stored but UTXO update failed at height " << height << "\n";
        }
        for (const auto &tx : txs)
        {
            std::vector<Storage::UtxoSpend> spends;
            std::vector<Storage::UtxoCredit> credits;
            for (const auto &in : tx.inputs)
            {
                spends.push_back(Storage::UtxoSpend{in.prev, in.vout});
            }
            uint32_t vout = 0;
            for (const auto &o : tx.outputs)
            {
                credits.push_back(Storage::UtxoCredit{tx.txid, vout, o.value, o.address});
                ++vout;
            }
            if (!storage.apply_utxos(spends, credits))
            {
                std::cerr << "Block stored but UTXO update failed at height " << height << "\n";
            }
            storage.remove_transaction(tx.txid);
            if (tx.reg)
            {
                std::string ignored;
                const std::string kind = is_reserved_name(tx.name) ? "reserved_bind" : "register";
                remember_name(tx.name, tx.reg_address, kind, to_hex(tx.txid), !require_local_policy, ignored);
            }
        }
        if (!txs.empty())
        {
            save_names(storage.datadir());
            save_mempool(storage);
        }

        if (p2p != nullptr && p2p->getPeerCount() > 0)
        {
            InvVect inv;
            inv.type = static_cast<uint32_t>(InvType::BLOCK);
            inv.hash = digest;
            p2p->broadcastInv(inv);
        }

        std::cout << "Accepted block height " << height << " hash " << to_hex(digest) << "\n";
        return json{{"status", "accepted"}, {"hash", to_hex(digest)}, {"height", height}};
    }

    namespace
    {
        bool find_header(Storage &storage, const json &params, BlockHeader &header)
        {
            json key = params;
            if (params.is_array())
            {
                if (params.empty())
                {
                    return false;
                }
                key = params[0];
            }
            if (key.is_object())
            {
                if (key.contains("height"))
                {
                    key = key["height"];
                }
                else if (key.contains("hash"))
                {
                    key = key["hash"];
                }
            }
            if (key.is_number_unsigned())
            {
                auto found = storage.get_header_by_height(key.get<uint32_t>());
                if (!found)
                {
                    return false;
                }
                header = *found;
                return true;
            }
            if (!key.is_string())
            {
                return false;
            }
            const std::string text = key.get<std::string>();
            if (text.size() == 64)
            {
                std::array<uint8_t, 32> hash{};
                if (!from_hex(text, hash))
                {
                    return false;
                }
                auto found = storage.get_header_by_hash(hash);
                if (!found)
                {
                    return false;
                }
                header = *found;
                return true;
            }
            try
            {
                auto found = storage.get_header_by_height(static_cast<uint32_t>(std::stoul(text)));
                if (!found)
                {
                    return false;
                }
                header = *found;
                return true;
            }
            catch (const std::exception &)
            {
                return false;
            }
        }

        json header_json(const BlockHeader &header)
        {
            return json{
                {"hash", to_hex(header.hash)},
                {"height", header.height},
                {"version", header.version},
                {"prev_block_hash", to_hex(header.prevBlockHash)},
                {"merkle_root", to_hex(header.merkleRoot)},
                {"timestamp", header.timestamp},
                {"difficulty", header.difficulty},
                {"nonce", header.nonce},
            };
        }
    }

    json rpc_getblock(Storage &storage, const json &params)
    {
        BlockHeader header{};
        if (!find_header(storage, params, header))
        {
            throw std::runtime_error("Block not found");
        }
        auto index = storage.block_index(header.hash);
        if (index)
        {
            auto raw = storage.read_block(*index);
            if (raw)
            {
                try
                {
                    const std::string text(raw->begin(), raw->end());
                    json obj = json::parse(text);
                    obj["hash"] = to_hex(header.hash);
                    obj["height"] = header.height;
                    return obj;
                }
                catch (const std::exception &)
                {
                }
            }
        }
        return header_json(header);
    }

    json rpc_getheader(Storage &storage, const json &params)
    {
        BlockHeader header{};
        if (!find_header(storage, params, header))
        {
            throw std::runtime_error("Header not found");
        }
        return header_json(header);
    }

    json rpc_listunspent(Storage &storage, const json &params)
    {
        std::string address;
        if (params.is_array() && !params.empty() && params[0].is_string())
        {
            address = params[0].get<std::string>();
        }
        else if (params.is_string())
        {
            address = params.get<std::string>();
        }
        else
        {
            json obj = as_object_param(params);
            if (obj.is_object() && obj.contains("address") && obj["address"].is_string())
            {
                address = obj["address"].get<std::string>();
            }
            else if (obj.is_object() && obj.contains("name") && obj["name"].is_string())
            {
                address = obj["name"].get<std::string>();
            }
        }
        load_names_file(storage.datadir());
        std::string shown;
        std::string kind;
        std::string resolved;
        const std::string query = address;
        if (lookup_name(query, resolved, shown, kind))
        {
            address = resolved;
        }
        else if (query.size() == 67)
        {
            std::string prefix = query.substr(0, 3);
            for (char &c : prefix)
            {
                if (c >= 'A' && c <= 'Z')
                {
                    c = static_cast<char>(c - 'A' + 'a');
                }
            }
            std::string hex = query.substr(3);
            for (char &c : hex)
            {
                if (c >= 'A' && c <= 'F')
                {
                    c = static_cast<char>(c - 'A' + 'a');
                }
            }
            if (prefix == "ps1" && is_long_address(prefix + hex))
            {
                address = prefix + hex;
                lookup_ps1(address, shown, kind);
            }
        }
        json rows = json::array();
        uint64_t total = 0;
        for (const auto &row : storage.list_utxos(address))
        {
            total += row.units;
            rows.push_back({{"txid", row.txid_hex},
                            {"vout", row.vout},
                            {"units", row.units},
                            {"address", row.address},
                            {"amount", units_314st(row.units)}});
        }
        json result = {{"address", address}, {"units", total}, {"amount", units_314st(total)}, {"utxos", rows}};
        if (!shown.empty())
        {
            result["name"] = shown;
        }
        if (!query.empty() && query != address)
        {
            result["query"] = query;
        }
        return result;
    }

    json rpc_namelookup(Storage &storage, const json &params)
    {
        load_names_file(storage.datadir());
        json obj = as_object_param(params);
        std::string by_name;
        std::string by_address;
        if (obj.is_object())
        {
            if (obj.contains("name") && obj["name"].is_string())
            {
                by_name = obj["name"].get<std::string>();
            }
            else if (obj.contains("address") && obj["address"].is_string())
            {
                by_address = obj["address"].get<std::string>();
            }
        }
        else if (params.is_string())
        {
            by_name = params.get<std::string>();
        }
        auto normalize_ps1 = [](std::string text) -> std::string
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
            if (text.compare(0, 3, "ps1") != 0 || !is_long_address(text))
            {
                return {};
            }
            return text;
        };
        auto wallet_file = [&](const std::string &name) -> bool
        {
            if (!address_filename(name))
            {
                return false;
            }
            std::error_code ec;
            return std::filesystem::exists(storage.datadir() / "wallets" / (name + ".json"), ec);
        };
        auto names_for = [&](const std::string &ps1) -> json
        {
            json names = json::array();
            std::lock_guard<std::mutex> lock(g_name_mu);
            for (const auto &rec : g_names)
            {
                if (rec.address == ps1)
                {
                    names.push_back(rec.name);
                }
            }
            return names;
        };
        auto ps1_hit = [&](const std::string &ps1) -> json
        {
            if (ps1.empty())
            {
                return json{{"found", false}};
            }
            const json names = names_for(ps1);
            if (!wallet_file(ps1) && names.empty())
            {
                return json{{"found", false}};
            }
            return json{{"found", true}, {"address", ps1}, {"names", names}};
        };
        if (!by_address.empty())
        {
            return ps1_hit(normalize_ps1(by_address));
        }
        if (by_name.empty())
        {
            return json{{"found", false}};
        }
        const std::string as_ps1 = normalize_ps1(by_name);
        if (!as_ps1.empty())
        {
            return ps1_hit(as_ps1);
        }
        std::string address;
        std::string shown;
        std::string kind;
        if (lookup_name(by_name, address, shown, kind))
        {
            return json{{"found", true}, {"name", shown}, {"address", address}, {"reserved", is_reserved_name(shown)}};
        }
        std::string file_name = by_name;
        if (!wallet_file(file_name))
        {
            const std::string folded = fold_name(by_name);
            if (folded != by_name && wallet_file(folded))
            {
                file_name = folded;
            }
            else
            {
                return json{{"found", false}};
            }
        }
        return json{{"found", true}, {"name", file_name}, {"address", file_name}, {"reserved", is_reserved_name(file_name)}};
    }

    json rpc_name_snapshot(Storage &storage)
    {
        load_names_file(storage.datadir());
        std::lock_guard<std::mutex> lock(g_name_mu);
        return name_snapshot_unlocked();
    }
}
