#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace pisecured
{
    struct Flag
    {
        std::string id;
        std::string commitment;
        std::string awards_pubkey;
        uint32_t max_claims = 0;
        uint32_t expires_height = 0;
        uint64_t bounty_units = 0;
        std::string note;
        uint64_t escrow = 0;
        std::string txid;
        std::vector<std::string> claimants;
        std::vector<std::string> claim_txids;
    };

    struct FlagClaim
    {
        std::string ps1;
        std::string txid;
    };

    inline bool escrow_lock(uint32_t max_claims, uint64_t bounty_units, uint64_t &lock, std::string &reason);

    // Pure flag rules. The answer itself is never stored.
    class FlagBook
    {
    public:
        const Flag *find(const std::string &id) const
        {
            for (const auto &flag : flags_)
            {
                if (flag.id == id)
                {
                    return &flag;
                }
            }
            return nullptr;
        }

        const std::vector<Flag> &all() const { return flags_; }

        bool create(const Flag &incoming, std::string &reason)
        {
            if (const Flag *existing = find(incoming.id))
            {
                if (!incoming.txid.empty() && existing->txid == incoming.txid)
                {
                    return true;
                }
                reason = "duplicate flag";
                return false;
            }
            uint64_t lock = 0;
            if (!escrow_lock(incoming.max_claims, incoming.bounty_units, lock, reason))
            {
                return false;
            }
            Flag stored = incoming;
            stored.escrow = lock;
            flags_.push_back(stored);
            return true;
        }

        bool claim(const std::string &flag_id, const std::string &recipient, const std::string &awards_pubkey,
                   uint32_t height, const std::string &txid, std::string &reason)
        {
            Flag *flag = nullptr;
            for (auto &item : flags_)
            {
                if (item.id == flag_id)
                {
                    flag = &item;
                    break;
                }
            }
            if (flag == nullptr)
            {
                reason = "unknown flag";
                return false;
            }
            for (size_t i = 0; i < flag->claimants.size(); ++i)
            {
                if (flag->claimants[i] == recipient)
                {
                    if (!txid.empty() && i < flag->claim_txids.size() && flag->claim_txids[i] == txid)
                    {
                        return true;
                    }
                    reason = "already claimed";
                    return false;
                }
            }
            if (awards_pubkey != flag->awards_pubkey)
            {
                reason = "awards signature required";
                return false;
            }
            if (flag->expires_height != 0 && height > flag->expires_height)
            {
                reason = "flag expired";
                return false;
            }
            if (flag->max_claims != 0 && flag->claimants.size() >= flag->max_claims)
            {
                reason = "flag exhausted";
                return false;
            }
            if (flag->bounty_units > flag->escrow)
            {
                reason = "flag exhausted";
                return false;
            }
            flag->escrow -= flag->bounty_units;
            flag->claimants.push_back(recipient);
            flag->claim_txids.push_back(txid);
            return true;
        }

        std::vector<std::string> claimed_by(const std::string &ps1) const
        {
            std::vector<std::string> ids;
            for (const auto &flag : flags_)
            {
                for (const auto &who : flag.claimants)
                {
                    if (who == ps1)
                    {
                        ids.push_back(flag.id);
                        break;
                    }
                }
            }
            return ids;
        }

    private:
        std::vector<Flag> flags_;
    };

    inline bool flag_id_ok(const std::string &id)
    {
        if (id.empty() || id.size() > 32)
        {
            return false;
        }
        for (unsigned char c : id)
        {
            const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
            if (!ok)
            {
                return false;
            }
        }
        return true;
    }

    inline bool hex64(const std::string &text)
    {
        if (text.size() != 64)
        {
            return false;
        }
        for (unsigned char c : text)
        {
            const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
            if (!hex)
            {
                return false;
            }
        }
        return true;
    }

    inline bool escrow_lock(uint32_t max_claims, uint64_t bounty_units, uint64_t &lock, std::string &reason)
    {
        if (max_claims == 0)
        {
            if (bounty_units != 0)
            {
                reason = "unlimited flag cannot pay";
                return false;
            }
            lock = 0;
            return true;
        }
        if (bounty_units != 0 && bounty_units > UINT64_MAX / max_claims)
        {
            reason = "malformed transaction";
            return false;
        }
        lock = bounty_units * static_cast<uint64_t>(max_claims);
        return true;
    }

    // Escrow is bookkeeping, not a coin. listunspent only returns spendable outputs.
    inline bool escrow_is_spendable_output()
    {
        return false;
    }
}
