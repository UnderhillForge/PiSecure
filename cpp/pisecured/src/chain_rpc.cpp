#include "pisecured/chain_rpc.hpp"
#include "pisecured/p2p.hpp"

#include <openssl/sha.h>

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iostream>

namespace pisecured
{
    namespace
    {
        constexpr uint64_t kMaxTxBytes = 100000;
        constexpr uint64_t kMaxBlockBytes = 1000000;
        constexpr uint64_t kFutureSkewSeconds = 2 * 60 * 60;

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
            uint32_t height = 0;
            uint64_t fee = 0;
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

        // PiHash1 || header fields || model || serial commitment. SHA-256.
        // Any host can recompute this. It does not read local device-tree.
        std::array<uint8_t, 32> pihash_v1(uint32_t version,
                                           const std::array<uint8_t, 32> &prev,
                                           const std::array<uint8_t, 32> &merkle,
                                           uint64_t timestamp,
                                           uint32_t difficulty,
                                           uint64_t nonce,
                                           const std::string &model,
                                           const std::array<uint8_t, 32> &serial_commitment)
        {
            std::vector<uint8_t> pre;
            append_str(pre, "PiHash1");
            append_u32(pre, version);
            append_bytes(pre, prev.data(), 32);
            append_bytes(pre, merkle.data(), 32);
            append_u64(pre, timestamp);
            append_u32(pre, difficulty);
            append_u64(pre, nonce);
            append_u16(pre, static_cast<uint16_t>(model.size()));
            pre.insert(pre.end(), model.begin(), model.end());
            append_bytes(pre, serial_commitment.data(), 32);
            return sha256(pre);
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
                inputs.push_back(in);
            }
            return true;
        }

        json tx_to_json(const Tx &tx)
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
            return json{
                {"txid", to_hex(tx.txid)},
                {"version", tx.version},
                {"inputs", inputs},
                {"outputs", outputs},
                {"fee", tx.fee},
                {"spendable", !tx.inputs.empty()},
                {"size", canonical_tx(tx).size()},
            };
        }

        bool parse_user_tx(const json &obj, Tx &tx, std::string &reason)
        {
            if (!obj.is_object())
            {
                reason = "malformed transaction";
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
            tx.fee = obj["fee"].get<uint64_t>();
            if (tx.fee < 1)
            {
                reason = "fee too low";
                return false;
            }
            if (!obj.contains("inputs") || !obj.contains("outputs"))
            {
                reason = "malformed transaction";
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
                reason = "transaction too large";
                return false;
            }
            tx.txid = sha256(raw);
            return true;
        }

        struct Emission
        {
            uint64_t fee = 0;
            uint64_t miner_fee = 0;
            uint64_t stakers = 0;
            uint64_t loans = 0;
            uint64_t foundation = 0;
            uint64_t burn = 0;

            uint64_t miner_cap() const { return (kSubsidyUnits - kValidatorUnits) + miner_fee; }
        };

        Emission emission_for(uint64_t fee)
        {
            Emission e;
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
                outs.push_back(CbOut{"foundation", "foundation", e.foundation});
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
                {"subsidy", units_314st(kSubsidyUnits)},
                {"subsidy_units", kSubsidyUnits},
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
        uint32_t next_difficulty(Storage &storage)
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
                    txs.push_back(tx);
                }
                catch (const std::exception &)
                {
                }
            }
            return txs;
        }

        bool check_spendable(Storage &storage, const Tx &tx, std::string &reason)
        {
            if (tx.inputs.empty())
            {
                reason = "transaction inputs missing";
                return false;
            }
            uint64_t input_value = 0;
            for (const auto &in : tx.inputs)
            {
                uint64_t value = 0;
                if (!storage.utxo_available(in.prev, in.vout, value))
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
    }

    bool restore_chain(Storage &storage)
    {
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

            std::vector<Storage::UtxoSpend> spends;
            std::vector<Storage::UtxoCredit> credits;
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
                                credits.push_back(Storage::UtxoCredit{txid, vout, units, o.value("address", std::string())});
                            }
                            ++vout;
                        }
                    }
                    else
                    {
                        credits.push_back(Storage::UtxoCredit{txid, 0, cb.value("value", 0ull), cb.value("wallet", std::string())});
                    }
                }
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
                }
            }
            if (!storage.apply_utxos(spends, credits))
            {
                std::cerr << "UTXO replay failed at height " << item.height << "\n";
                return false;
            }
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
        return true;
    }

    json rpc_getblocktemplate(Storage &storage, const json &params)
    {
        const std::string wallet = wallet_from_params(params);
        if (wallet.empty() || wallet.size() > 256)
        {
            throw std::runtime_error("wallet or miner address required");
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
        const Emission emit = emission_for(fee_units);
        const std::vector<CbOut> cb_outs = template_coinbase(wallet, emit);
        Tx cb = coinbase_from(next_height, cb_outs);
        std::vector<std::array<uint8_t, 32>> ids{cb.txid};
        ids.insert(ids.end(), txids.begin(), txids.end());
        const auto root = merkle_root(ids);
        json coinbase = coinbase_body(wallet, next_height, emit, cb, cb_outs);

        return json{
            {"version", 1},
            {"height", next_height},
            {"prev_block_hash", to_hex(prev)},
            {"timestamp", now_seconds()},
            {"difficulty", difficulty},
            {"coinbase", coinbase},
            {"coinbase_txid", to_hex(cb.txid)},
            {"merkle_root", to_hex(root)},
            {"txs", txs},
            {"hw_proof", {{"model", ""}, {"serial_commitment", ""}}},
            {"pihash", {{"algorithm", "sha256-pihash1"}, {"domain", "PiHash1"}, {"difficulty_means", "leading zero bits"}}},
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
        if (storage.has_transaction(tx.txid))
        {
            return rejected("duplicate transaction");
        }
        if (!tx.inputs.empty())
        {
            if (!check_spendable(storage, tx, reason))
            {
                return rejected(reason);
            }
            for (const auto &existing : mempool_txs(storage))
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

        obj["txid"] = to_hex(tx.txid);
        auto dumped = obj.dump();
        Transaction stored;
        stored.hash = tx.txid;
        stored.data.assign(dumped.begin(), dumped.end());
        stored.timestamp = now_seconds();
        stored.fee = tx.fee;
        if (!storage.add_transaction(stored))
        {
            return rejected("malformed transaction");
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

    json rpc_submitblock(Storage &storage, P2PServer *p2p, const json &params)
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
        const std::string wallet = coinbase["wallet"].get<std::string>();
        if (wallet.size() > 256)
        {
            return rejected("coinbase wallet missing");
        }

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
        const uint32_t difficulty = block["difficulty"].get<uint32_t>();
        if (difficulty != expect_diff)
        {
            return rejected("difficulty mismatch");
        }
        const uint64_t timestamp = block["timestamp"].get<uint64_t>();
        const uint64_t now = now_seconds();
        if (timestamp == 0 || timestamp > now + kFutureSkewSeconds)
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
            for (const auto &txj : block["txs"])
            {
                Tx tx;
                std::string reason;
                if (!parse_user_tx(txj, tx, reason))
                {
                    return rejected(reason);
                }
                if (!check_spendable(storage, tx, reason))
                {
                    return rejected(reason);
                }
                txs.push_back(tx);
            }
        }

        uint64_t fee_units = 0;
        for (const auto &tx : txs)
        {
            fee_units += tx.fee;
        }
        const Emission emit = emission_for(fee_units);
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
                if (out.role == "miner" && out.address != wallet)
                {
                    return rejected("coinbase wallet missing");
                }
                cb_outs.push_back(out);
            }
        }
        else if (coinbase.contains("value") && coinbase["value"].is_number_unsigned())
        {
            cb_outs.push_back(CbOut{"miner", wallet, coinbase["value"].get<uint64_t>()});
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
                paid_foundation += o.units;
            else
            {
                return rejected("coinbase exceeds emission rules");
            }
        }
        const uint64_t minted = paid_miner + paid_validator + paid_stakers + paid_loans + paid_foundation;
        const uint64_t mint_cap = kSubsidyUnits + emit.miner_fee + emit.stakers + emit.loans + emit.foundation;
        if (paid_miner > emit.miner_cap() || paid_validator > kValidatorUnits || paid_stakers > emit.stakers || paid_loans > emit.loans || paid_foundation > emit.foundation || minted > mint_cap)
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

        const auto digest = pihash_v1(1, prev, root, timestamp, difficulty, nonce, model, serial);
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
        stored["hw_proof"] = json{{"model", model}, {"serial_commitment", to_hex(serial)}};

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

        std::vector<Storage::UtxoSpend> spends;
        std::vector<Storage::UtxoCredit> credits;
        uint32_t cb_vout = 0;
        for (const auto &o : cb.outputs)
        {
            credits.push_back(Storage::UtxoCredit{cb.txid, cb_vout, o.value, o.address});
            ++cb_vout;
        }
        for (const auto &tx : txs)
        {
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
            storage.remove_transaction(tx.txid);
        }
        if (!storage.apply_utxos(spends, credits))
        {
            std::cerr << "Block stored but UTXO update failed at height " << height << "\n";
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
        return json{{"address", address}, {"units", total}, {"amount", units_314st(total)}, {"utxos", rows}};
    }
}
