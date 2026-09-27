#include "pisecured/flags.hpp"

#include <iostream>
#include <string>

namespace
{
    int fail(const std::string &message)
    {
        std::cerr << message << "\n";
        return 1;
    }

    pisecured::Flag sample(const std::string &id, uint32_t max_claims, uint64_t bounty)
    {
        pisecured::Flag flag;
        flag.id = id;
        flag.commitment = std::string(64, 'a');
        flag.awards_pubkey = std::string(64, 'b');
        flag.max_claims = max_claims;
        flag.expires_height = 0;
        flag.bounty_units = bounty;
        flag.note = "n";
        flag.txid = "create-" + id;
        return flag;
    }
}

int main()
{
    std::string reason;
    uint64_t lock = 0;
    if (pisecured::escrow_lock(0, 5, lock, reason) || reason != "unlimited flag cannot pay")
    {
        return fail("unlimited flag with a bounty was accepted");
    }
    if (!pisecured::escrow_lock(0, 0, lock, reason) || lock != 0)
    {
        return fail("unlimited flag without a bounty was rejected");
    }
    if (!pisecured::escrow_lock(2, 10, lock, reason) || lock != 20)
    {
        return fail("escrow lock was not bounty times max_claims");
    }
    if (pisecured::escrow_is_spendable_output())
    {
        return fail("escrow is visible to listunspent");
    }

    pisecured::FlagBook open;
    if (!open.create(sample("Train", 0, 0), reason))
    {
        return fail(reason);
    }
    const std::string awards = std::string(64, 'b');
    if (!open.claim("Train", "ps1aa", awards, 10, "c1", reason))
    {
        return fail(reason);
    }
    if (open.claim("Train", "ps1aa", awards, 10, "c2", reason) || reason != "already claimed")
    {
        return fail("repeat claim was accepted");
    }
    if (!open.claim("Train", "ps1bb", awards, 11, "c3", reason))
    {
        return fail(reason);
    }
    if (!open.claim("Train", "ps1cc", awards, 12, "c4", reason))
    {
        return fail("third distinct claim was rejected");
    }
    if (open.find("Train")->claimants.size() != 3)
    {
        return fail("unlimited flag did not keep three claimants");
    }

    pisecured::FlagBook finite;
    if (!finite.create(sample("Event", 2, 10), reason))
    {
        return fail(reason);
    }
    if (finite.find("Event")->escrow != 20)
    {
        return fail("escrow was not locked");
    }
    if (!finite.claim("Event", "ps1aa", awards, 3, "e1", reason) || !finite.claim("Event", "ps1bb", awards, 3, "e2", reason))
    {
        return fail(reason);
    }
    if (finite.claim("Event", "ps1cc", awards, 4, "e3", reason) || reason != "flag exhausted")
    {
        return fail("third claim on max_claims 2 was accepted");
    }
    if (finite.find("Event")->escrow != 0)
    {
        return fail("escrow was not paid out");
    }
    std::cout << "flag tests passed\n";
    return 0;
}
