#pragma once

#include "storage.hpp"
#include <nlohmann/json.hpp>
#include <string>

namespace pisecured
{
    class P2PServer;

    // Leading-zero bits for a 60 second target. Clamped to this band
    // for every block before kDifficultyActivationHeight.
    constexpr uint32_t kMinDifficultyBits = 2;
    constexpr uint32_t kMaxDifficultyBits = 4;
    constexpr uint32_t kInitialDifficultyBits = 4;
    constexpr uint32_t kTargetBlockSeconds = 60;

    // Tip height was 23363 when this constant was chosen. From block 23863
    // the subsidy is 218 units and difficulty is the 2–24 bit retarget.
    constexpr uint32_t kDifficultyActivationHeight = 23863;

    // 1 unit = 0.001 314ST. Base subsidy is 0.200 314ST per block until
    // activation, then 0.218. Miner receives subsidy minus the validator 2 units.
    constexpr uint64_t kSubsidyUnits = 200;
    constexpr uint64_t kSubsidyUnitsAfterActivation = 218;
    constexpr uint64_t kValidatorUnits = 2;

    // 7% of transaction fees. Stakers, loans, and burn are unchanged.
    inline constexpr char kFoundationPayout[] = "ps154bc21d4a37549c5a599a16b4822bf771ed29001095e241d05ef8ebf709854ee";

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
