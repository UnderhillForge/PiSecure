#include "pisecured/p2p.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace
{
    pisecured::BlockHeader sample(uint32_t n)
    {
        pisecured::BlockHeader header{};
        header.version = n;
        header.timestamp = 1700000000ull + n;
        header.difficulty = 2u + (n % 3u);
        header.nonce = 1000ull + n;
        header.height = 999;
        for (size_t i = 0; i < 32; ++i)
        {
            header.prevBlockHash[i] = static_cast<uint8_t>(n + i);
            header.merkleRoot[i] = static_cast<uint8_t>((3u * n) + i);
            header.hash[i] = static_cast<uint8_t>((7u * n) + i);
        }
        return header;
    }

    void expect(bool cond, const char *what)
    {
        if (!cond)
        {
            std::cerr << "header frame test failed: " << what << std::endl;
            std::exit(1);
        }
    }

    void round_trip(size_t count)
    {
        std::vector<pisecured::BlockHeader> input;
        input.reserve(count);
        for (size_t i = 0; i < count; ++i)
        {
            input.push_back(sample(static_cast<uint32_t>(i + 1)));
        }

        const auto bytes = pisecured::MessageSerializer::serializeHeaders(input);
        const size_t prefix = count < 0xFD ? 1u : 3u;
        expect(bytes.size() == prefix + count * pisecured::kCompactHeaderBytes, "written size");

        std::vector<pisecured::BlockHeader> output;
        size_t consumed = 0;
        expect(pisecured::MessageSerializer::deserializeHeaders(bytes, output, consumed), "decode");
        expect(consumed == bytes.size(), "bytes written == bytes consumed");
        expect(output.size() == count, "count");

        for (size_t i = 0; i < count; ++i)
        {
            expect(output[i].version == input[i].version, "version");
            expect(output[i].prevBlockHash == input[i].prevBlockHash, "prev");
            expect(output[i].merkleRoot == input[i].merkleRoot, "merkle");
            expect(output[i].timestamp == input[i].timestamp, "timestamp");
            expect(output[i].difficulty == input[i].difficulty, "difficulty");
            expect(output[i].nonce == input[i].nonce, "nonce");
            expect(output[i].hash == input[i].hash, "hash");
            expect(output[i].height == 0, "height is not on the wire");
        }

        const auto again = pisecured::MessageSerializer::serializeHeaders(output);
        expect(again == bytes, "re-encode");

        auto missing = bytes;
        missing.pop_back();
        size_t unused = 0;
        std::vector<pisecured::BlockHeader> junk;
        expect(!pisecured::MessageSerializer::deserializeHeaders(missing, junk, unused), "missing byte");

        auto extra = bytes;
        extra.push_back(0x51);
        expect(!pisecured::MessageSerializer::deserializeHeaders(extra, junk, unused), "extra byte");
    }
}

int main()
{
    static_assert(pisecured::kCompactHeaderBytes == 4u + 32u + 32u + 8u + 4u + 8u + 32u);
    round_trip(1);
    round_trip(2000);

    std::vector<pisecured::BlockHeader> one{sample(1)};
    const auto bytes = pisecured::MessageSerializer::serializeHeaders(one);
    expect(bytes.size() == 121, "one header is 1 + 120");
    expect(bytes[0] == 1, "count");
    expect(bytes[1] == 1 && bytes[2] == 0 && bytes[3] == 0 && bytes[4] == 0, "version at offset 1");
    expect(bytes[89] == one[0].hash[0], "hash starts at offset 89");

    std::cout << "header frame round-trip ok" << std::endl;
    return 0;
}
