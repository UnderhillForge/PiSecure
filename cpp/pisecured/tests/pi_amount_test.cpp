#include "amount.hpp"
#include "pisecured/chain_rpc.hpp"

#include <iostream>
#include <string>

namespace
{
    int fail(const std::string &message)
    {
        std::cerr << message << "\n";
        return 1;
    }
}

int main()
{
    using pisecured::kPiActivationHeight;
    const uint32_t H = kPiActivationHeight;
    std::string reason;

    if (pisecured::coinbase_subsidy_ok(H - 1, 0, 216, 2, reason))
    {
        reason.clear();
    }
    else
    {
        return fail("pre-H 216/2 should be accepted: " + reason);
    }
    if (pisecured::coinbase_subsidy_ok(H, 0, 216, 2, reason) || reason != "coinbase subsidy mismatch")
    {
        return fail("post-H 216 old units should be rejected");
    }
    reason.clear();
    if (pisecured::coinbase_subsidy_ok(H, 0, 218, 2, reason) || reason != "coinbase subsidy mismatch")
    {
        return fail("post-H 218 old units should be rejected");
    }
    reason.clear();
    if (pisecured::coinbase_subsidy_ok(H, 0, 216, 2000, reason) || reason != "coinbase subsidy mismatch")
    {
        return fail("post-H miner 216 should be rejected");
    }
    reason.clear();
    if (pisecured::coinbase_subsidy_ok(H, 0, 218, 2000, reason) || reason != "coinbase subsidy mismatch")
    {
        return fail("post-H miner 218 should be rejected");
    }
    reason.clear();
    if (!pisecured::coinbase_subsidy_ok(H, 0, 216000, 2000, reason))
    {
        return fail("post-H 216000/2000 should be accepted: " + reason);
    }
    if (pisecured::subsidy_for_height(H) != 218000 || pisecured::miner_subsidy_for_height(H) != 216000 || pisecured::validator_for_height(H) != 2000)
    {
        return fail("post-H subsidy is 218000 pi");
    }
    if (pisecured::subsidy_for_height(H - 1) != 218 || pisecured::miner_subsidy_for_height(H - 1) != 216 || pisecured::validator_for_height(H - 1) != 2)
    {
        return fail("pre-H subsidy stays 218 units");
    }

    uint64_t pi = 0;
    if (!pisecure::parse_314st_pi("0.000314", pi, reason) || pi != 314)
    {
        return fail("0.000314 should be 314 pi");
    }
    if (!pisecure::parse_314st_pi("0.216000", pi, reason) || pi != 216000)
    {
        return fail("0.216000 should be 216000 pi");
    }
    if (!pisecure::parse_314st_pi("0.216", pi, reason) || pi != 216000)
    {
        return fail("0.216 should be 216000 pi");
    }
    if (pisecure::parse_314st_pi("0.0003141", pi, reason) || reason != "amount has more than six decimal places")
    {
        return fail("seven decimal places should be rejected");
    }
    if (pisecure::format_314st_pi(216000) != "0.216000" || pisecure::format_314st_pi(314) != "0.000314" || pisecure::format_314st_pi(2000) != "0.002000")
    {
        return fail("display is six decimal places");
    }
    if (pisecured::min_fee_for_height(H) != 314 || pisecured::min_fee_for_height(H - 1) != 1)
    {
        return fail("minimum fee is 314 pi at H");
    }
    if (pisecured::amount_scale_for_next(H - 1) != 1 || pisecured::amount_scale_for_next(H) != 1000)
    {
        return fail("amount scale flips at H");
    }
    const pisecured::FeeShares shares = pisecured::fee_shares(314);
    if (shares.miner + shares.stakers + shares.loans + shares.foundation + shares.burn != 314 || shares.miner != 314 * 60 / 100)
    {
        return fail("fee split of 314 pi must sum to 314");
    }
    uint64_t scaled = 0;
    if (!pisecured::stored_to_pi(216, H - 1, scaled) || scaled != 216000)
    {
        return fail("a pre-H output of 216 spends as 216000 pi");
    }
    if (!pisecured::stored_to_pi(216000, H, scaled) || scaled != 216000)
    {
        return fail("a post-H output is already pi");
    }
    std::cout << "pi amount checks passed, H=" << H << "\n";
    return 0;
}
