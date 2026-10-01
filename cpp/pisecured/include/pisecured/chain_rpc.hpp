#pragma once

#include "storage.hpp"
#include <nlohmann/json.hpp>
#include <array>
#include <string>
#include <vector>

namespace pisecured
{
    class P2PServer;

    // Old one-step band. Unused once activation is height 1.
    constexpr uint32_t kMinDifficultyBits = 2;
    constexpr uint32_t kMaxDifficultyBits = 4;
    constexpr uint32_t kInitialDifficultyBits = 4;
    constexpr uint32_t kTargetBlockSeconds = 60;

    // Block 1 is the first block. It starts at 4 bits. Later blocks retarget
    // in the 2–24 band.
    constexpr uint32_t kDifficultyActivationHeight = 1;

    // Tip 31 on 2026-09-27. Heights before 32 still accept a miner subsidy of
    // 198 or 216 plus the miner fee share, including the stored validator
    // address. From height 32 the miner output is exactly 216 plus the miner
    // fee share, and the validator output is exactly 2 units to a ps1.
    constexpr uint32_t kMiner216ActivationHeight = 32;
    constexpr uint64_t kLegacyMinerSubsidy = 198;

    // 1 unit = 0.001 314ST. From block 32 the subsidy is 0.218 314ST.
    // Miner receives subsidy minus the validator 2 units (216).
    constexpr uint64_t kSubsidyUnits = 200;
    constexpr uint64_t kSubsidyUnitsAfterActivation = 218;
    constexpr uint64_t kValidatorUnits = 2;

    // 7% of transaction fees. Stakers, loans, and burn are unchanged.
    inline constexpr char kFoundationPayout[] = "ps1522db177e6452cbb6e48f296b19e6f2bdeb5b5e7a41a9552eb60a01464c3a5ba";

    // One transaction as JSON, including the public key and signature on
    // every input. At most 200 inputs. Anything larger is rejected whole,
    // before the signature check and the balance check.
    constexpr uint64_t kMaxTxJsonBytes = 64ull * 1024ull;
    constexpr size_t kMaxTxInputs = 200;
    // Stored block JSON. A larger body is not parsed and is not written.
    constexpr uint64_t kMaxBlockBytes = 256ull * 1024ull;

    using json = nlohmann::json;

    // Reload headers and the UTXO set from blk*.dat. Safe on an empty chain.
    bool restore_chain(Storage &storage);

    json rpc_getblocktemplate(Storage &storage, const json &params);
    // require_local_policy: miner RPC. A coinbase-only block that pays a ps1 or a
    // registered name is valid here and on a peer. No wallet key is required.
    // Synced blocks still check PiHash, model, and the serial commitment, but not
    // this process's challenge cache.
    json rpc_submitblock(Storage &storage, P2PServer *p2p, const json &params, bool require_local_policy = true);
    // True for 10 minutes after getblocktemplate is called.
    void rpc_note_template_request();
    bool rpc_mining_active();
    // Rebuild the in-memory tip from the on-disk chain that ends at tip_hash.
    bool rpc_replay_chain(Storage &storage, const std::array<uint8_t, 32> &tip_hash);
    // Switch to blocks when their tip is taller than the local one. On failure
    // the previous tip is restored from disk.
    bool rpc_adopt_peer_chain(Storage &storage, P2PServer *p2p, const std::array<uint8_t, 32> &ancestor, const std::vector<json> &blocks);
    json rpc_sendtransaction(Storage &storage, const json &params);
    json rpc_getmempool(Storage &storage);
    json rpc_getblock(Storage &storage, const json &params);
    json rpc_getheader(Storage &storage, const json &params);
    json rpc_listunspent(Storage &storage, const json &params);
    json rpc_namelookup(Storage &storage, const json &params);
    json rpc_createflag(Storage &storage, const json &params);
    json rpc_claimflag(Storage &storage, const json &params);
    json rpc_listflags(Storage &storage, const json &params);
    // Name map for chain report and for the names snapshot stored on new blocks.
    json rpc_name_snapshot(Storage &storage);
}
