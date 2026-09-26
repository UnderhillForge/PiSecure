#pragma once

#include "storage.hpp"
#include <nlohmann/json.hpp>
#include <string>

namespace pisecured
{
    class P2PServer;

    // Old one-step band. Unused once activation is height 1.
    constexpr uint32_t kMinDifficultyBits = 2;
    constexpr uint32_t kMaxDifficultyBits = 4;
    constexpr uint32_t kInitialDifficultyBits = 4;
    constexpr uint32_t kTargetBlockSeconds = 60;

    // Block 1 is the first block. It starts at 4 bits. Later blocks retarget
    // in the 2–24 band. The subsidy is 218 units from block 1.
    constexpr uint32_t kDifficultyActivationHeight = 1;

    // 1 unit = 0.001 314ST. Subsidy is 0.218 314ST from block 1.
    // Miner receives subsidy minus the validator 2 units (216).
    constexpr uint64_t kSubsidyUnits = 200;
    constexpr uint64_t kSubsidyUnitsAfterActivation = 218;
    constexpr uint64_t kValidatorUnits = 2;

    // 7% of transaction fees. Stakers, loans, and burn are unchanged.
    inline constexpr char kFoundationPayout[] = "ps1a404246a1e6154e96bd02728fe1a988ae2abe6c6609426e2da7b71ab3dccb4f7";

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
    // require_local_policy: miner RPC. Synced blocks still check PiHash, model,
    // and the serial commitment equation, but not this process's challenge cache.
    json rpc_submitblock(Storage &storage, P2PServer *p2p, const json &params, bool require_local_policy = true);
    json rpc_sendtransaction(Storage &storage, const json &params);
    json rpc_getmempool(Storage &storage);
    json rpc_getblock(Storage &storage, const json &params);
    json rpc_getheader(Storage &storage, const json &params);
    json rpc_listunspent(Storage &storage, const json &params);
    json rpc_namelookup(Storage &storage, const json &params);
    // Name map for chain report and for the names snapshot stored on new blocks.
    json rpc_name_snapshot(Storage &storage);
}
