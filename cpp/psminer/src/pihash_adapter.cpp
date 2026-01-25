// Adapter to use pisecure::pihash::PiHash in psminer
// No namespace to avoid STL header pollution
#include "../../hw/pihash.h"
#include "pihash_adapter.hpp"

struct psminer::PiHashAdapter::Impl
{
    pisecure::pihash::PiHash pihash;
    pisecure::pihash::HardwareFingerprint fingerprint;

    Impl(uint32_t rounds, uint32_t memory_mb, bool npu_enabled)
        : pihash(rounds, memory_mb, npu_enabled)
    {
        fingerprint = pisecure::pihash::PiHash::GetHardwareFingerprint();
    }
};

psminer::PiHashAdapter::PiHashAdapter(uint32_t rounds, uint32_t memory_mb, bool npu_enabled)
    : impl_(new Impl(rounds, memory_mb, npu_enabled))
{
}

psminer::PiHashAdapter::~PiHashAdapter()
{
    delete impl_;
}

std::string psminer::PiHashAdapter::compute(
    const uint8_t *data,
    size_t data_len,
    uint32_t nonce,
    void *hardware_fingerprint)
{
    std::vector<uint8_t> data_vec(data, data + data_len);

    pisecure::pihash::HardwareFingerprint *fp = nullptr;
    if (hardware_fingerprint == nullptr)
    {
        fp = &impl_->fingerprint;
    }
    else
    {
        fp = static_cast<pisecure::pihash::HardwareFingerprint *>(hardware_fingerprint);
    }

    return impl_->pihash.Compute(data_vec, nonce, fp);
}

bool psminer::PiHashAdapter::find_nonce(
    const uint8_t *data,
    size_t data_len,
    uint32_t difficulty,
    uint32_t max_nonce,
    uint32_t &out_nonce,
    std::string &out_hash)
{
    std::vector<uint8_t> data_vec(data, data + data_len);

    try
    {
        auto result = impl_->pihash.FindNonce(
            data_vec,
            difficulty,
            &impl_->fingerprint,
            max_nonce);

        out_nonce = result.first;
        out_hash = result.second;
        return true;
    }
    catch (...)
    {
        return false;
    }
}
