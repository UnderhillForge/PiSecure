#pragma once

#include <cstdint>
#include <cstdio>
#include <string>

namespace pisecure
{
    // 1 314ST = 1000000 pi. 0.000314 314ST = 314 pi.
    constexpr uint64_t kPiPer314ST = 1000000;

    // Decimal 314ST text to pi. No floating point. More than six fractional
    // digits, a sign, an exponent, a comma, or a space is rejected. Zero is rejected.
    inline bool parse_314st_pi(const std::string &text, uint64_t &pi, std::string &reason)
    {
        if (text.empty())
        {
            reason = "amount must be 314ST, for example 0.216000";
            return false;
        }
        for (char c : text)
        {
            if (c != '.' && (c < '0' || c > '9'))
            {
                reason = "amount must be 314ST, for example 0.216000";
                return false;
            }
        }
        const auto dot = text.find('.');
        if (dot != std::string::npos && text.find('.', dot + 1) != std::string::npos)
        {
            reason = "amount must be 314ST, for example 0.216000";
            return false;
        }
        const std::string whole = dot == std::string::npos ? text : text.substr(0, dot);
        const std::string frac = dot == std::string::npos ? std::string() : text.substr(dot + 1);
        if (whole.empty() || (dot != std::string::npos && frac.empty()))
        {
            reason = "amount must be 314ST, for example 0.216000";
            return false;
        }
        if (frac.size() > 6)
        {
            reason = "amount has more than six decimal places";
            return false;
        }
        auto accumulate = [](const std::string &digits, uint64_t &out) -> bool
        {
            out = 0;
            for (char c : digits)
            {
                const uint64_t digit = static_cast<uint64_t>(c - '0');
                if (out > (UINT64_MAX - digit) / 10ull)
                {
                    return false;
                }
                out = out * 10ull + digit;
            }
            return true;
        };
        uint64_t whole_v = 0;
        uint64_t frac_v = 0;
        if (!accumulate(whole, whole_v))
        {
            reason = "amount overflow";
            return false;
        }
        if (!accumulate(frac, frac_v))
        {
            reason = "amount overflow";
            return false;
        }
        for (size_t i = frac.size(); i < 6; ++i)
        {
            if (frac_v > UINT64_MAX / 10ull)
            {
                reason = "amount overflow";
                return false;
            }
            frac_v *= 10ull;
        }
        if (whole_v > UINT64_MAX / kPiPer314ST)
        {
            reason = "amount overflow";
            return false;
        }
        const uint64_t scaled = whole_v * kPiPer314ST;
        if (scaled > UINT64_MAX - frac_v)
        {
            reason = "amount overflow";
            return false;
        }
        pi = scaled + frac_v;
        if (pi == 0)
        {
            reason = "amount must be greater than 0";
            return false;
        }
        return true;
    }

    inline std::string format_314st_pi(uint64_t pi)
    {
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%llu.%06llu",
                      static_cast<unsigned long long>(pi / kPiPer314ST),
                      static_cast<unsigned long long>(pi % kPiPer314ST));
        return buf;
    }
}
