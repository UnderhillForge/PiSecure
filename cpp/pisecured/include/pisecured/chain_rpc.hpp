#pragma once

#include "storage.hpp"
#include "amount.hpp"
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

    // 1 unit = 0.001 314ST = 1000 pi. From block 32 the subsidy is 0.218 314ST.
    // Miner receives subsidy minus the validator 2 units (216).
    constexpr uint64_t kSubsidyUnits = 200;
    constexpr uint64_t kSubsidyUnitsAfterActivation = 218;
    constexpr uint64_t kValidatorUnits = 2;

    // Tip 674 on 2026-10-01. The next multiple of 1000 that is at least 2000
    // blocks above that tip is 3000. Below this height a stored amount is the
    // old unit. At and after it, a new block stores pi. 1 314ST = 1000000 pi.
    // The 218-unit subsidy is 218000 pi: miner 216000, validator 2000.
    constexpr uint32_t kPiActivationHeight = 3000;
    constexpr uint64_t kPiPerOldUnit = 1000;
    constexpr uint64_t kSubsidyPi = 218000;
    constexpr uint64_t kValidatorPi = 2000;
    constexpr uint64_t kMinFeePi = 314;

    inline uint64_t subsidy_for_height(uint32_t height)
    {
        if (height >= kPiActivationHeight)
        {
            return kSubsidyPi;
        }
        if (height >= kMiner216ActivationHeight)
        {
            return kSubsidyUnitsAfterActivation;
        }
        return kSubsidyUnits;
    }

    inline uint64_t validator_for_height(uint32_t height)
    {
        return height >= kPiActivationHeight ? kValidatorPi : kValidatorUnits;
    }

    inline uint64_t miner_subsidy_for_height(uint32_t height)
    {
        return subsidy_for_height(height) - validator_for_height(height);
    }

    inline uint64_t min_fee_for_height(uint32_t height)
    {
        return height >= kPiActivationHeight ? kMinFeePi : 1;
    }

    // Scale of the next block. 1 while that block is below H, 1000 at and after H.
    inline uint32_t amount_scale_for_next(uint32_t next_height)
    {
        return next_height >= kPiActivationHeight ? static_cast<uint32_t>(kPiPerOldUnit) : 1u;
    }

    // A pre-H output spends as stored * 1000 pi. A post-H output is already pi.
    inline bool stored_to_pi(uint64_t stored, uint32_t created_height, uint64_t &pi)
    {
        if (created_height >= kPiActivationHeight)
        {
            pi = stored;
            return true;
        }
        if (stored > UINT64_MAX / kPiPerOldUnit)
        {
            return false;
        }
        pi = stored * kPiPerOldUnit;
        return true;
    }

    struct FeeShares
    {
        uint64_t miner = 0;
        uint64_t stakers = 0;
        uint64_t loans = 0;
        uint64_t foundation = 0;
        uint64_t burn = 0;
    };

    inline FeeShares fee_shares(uint64_t fee)
    {
        FeeShares shares;
        shares.miner = fee * 60 / 100;
        shares.stakers = fee * 20 / 100;
        shares.loans = fee * 8 / 100;
        shares.foundation = fee * 7 / 100;
        shares.burn = fee - (shares.miner + shares.stakers + shares.loans + shares.foundation);
        return shares;
    }

    // Post-H miner outputs of 216, 218, or 198 are the old unit and are rejected.
    inline bool coinbase_subsidy_ok(uint32_t height, uint64_t fee, uint64_t paid_miner, uint64_t paid_validator, std::string &reason)
    {
        if (height >= kPiActivationHeight && (paid_miner == 216 || paid_miner == 218 || paid_miner == kLegacyMinerSubsidy))
        {
            reason = "coinbase subsidy mismatch";
            return false;
        }
        if (paid_validator != validator_for_height(height))
        {
            reason = "coinbase validator amount";
            return false;
        }
        const FeeShares shares = fee_shares(fee);
        const uint64_t miner_due = miner_subsidy_for_height(height) + shares.miner;
        if (height >= kMiner216ActivationHeight)
        {
            if (paid_miner != miner_due)
            {
                reason = "coinbase subsidy mismatch";
                return false;
            }
            return true;
        }
        const uint64_t miner_legacy = kLegacyMinerSubsidy + shares.miner;
        const uint64_t miner_full = (kSubsidyUnitsAfterActivation - kValidatorUnits) + shares.miner;
        if (paid_miner != miner_legacy && paid_miner != miner_full)
        {
            reason = "coinbase subsidy mismatch";
            return false;
        }
        return true;
    }

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

    json rpc_getblockchaininfo(Storage &storage);
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
