#pragma once

#include "storage.hpp"
#include <nlohmann/json.hpp>
#include <string>

namespace pisecured
{
    class P2PServer;

    // Leading-zero bits for a 60 second target. Clamped to this band.
    constexpr uint32_t kMinDifficultyBits = 2;
    constexpr uint32_t kMaxDifficultyBits = 4;
    constexpr uint32_t kInitialDifficultyBits = 4;
    constexpr uint32_t kTargetBlockSeconds = 60;

    // 1 unit = 0.001 314ST. Base subsidy is 0.200 314ST per block.
    // Miner receives subsidy minus the validator 1% (198 units).
    constexpr uint64_t kSubsidyUnits = 200;
    constexpr uint64_t kValidatorUnits = 2;

    using json = nlohmann::json;

    // Reload headers and the UTXO set from blk*.dat. Safe on an empty chain.
    bool restore_chain(Storage &storage);

    json rpc_getblocktemplate(Storage &storage, const json &params);
    json rpc_submitblock(Storage &storage, P2PServer *p2p, const json &params);
    json rpc_sendtransaction(Storage &storage, const json &params);
    json rpc_getmempool(Storage &storage);
}
