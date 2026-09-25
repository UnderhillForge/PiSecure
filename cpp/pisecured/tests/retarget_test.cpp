#include "pisecured/retarget.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>

namespace
{
    void expect(bool cond, const char *what)
    {
        if (!cond)
        {
            std::cerr << "retarget test failed: " << what << std::endl;
            std::exit(1);
        }
    }
}

int main()
{
    using pisecured::retarget_difficulty_bits;
    const uint32_t fast = retarget_difficulty_bits(4, 9 * 4);
    expect(fast > 4, "4-second gaps raise bits");
    expect(fast <= 6, "one 4x step from 2^4 stays at or below 6");

    const uint32_t slow = retarget_difficulty_bits(8, 9 * 240);
    expect(slow < 8, "240-second gaps lower bits");

    expect(retarget_difficulty_bits(2, 9 * 100000) == 2, "floor is 2");
    expect(retarget_difficulty_bits(24, 9 * 1) == 24, "ceiling is 24");
    expect(retarget_difficulty_bits(8, 0) == 8, "non-positive elapsed keeps bits");
    expect(retarget_difficulty_bits(8, -40) == 8, "negative elapsed keeps bits");

    for (uint32_t bits = 2; bits <= 24; ++bits)
    {
        for (int64_t gap : {1, 4, 60, 240, 100000})
        {
            const uint32_t next = retarget_difficulty_bits(bits, 9 * gap);
            expect(next >= 2 && next <= 24, "bits stay inside 2-24");
        }
    }

    std::cout << "retarget ok fast=" << fast << " slow=" << slow << std::endl;
    return 0;
}
