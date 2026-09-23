#pragma once

#include <string>

namespace pisecure_update
{
    struct Report
    {
        enum class Kind
        {
            Current,
            Newer,
            Skipped
        } kind = Kind::Skipped;
        std::string line;
        std::string local;
        std::string tag;
        std::string url;
        std::string sha256;
        std::string asset;
    };

    // /etc/pisecure/pisecured.version when it is non-empty, otherwise compile_time.
    std::string local_version(const std::string &compile_time);

    // Network probe. 401 and 404 become Kind::Skipped. Never throws.
    Report check_release(const std::string &compile_time);

    bool write_available(const std::string &path, const Report &report);

    // Download the release tar, check SHA256SUMS, write one member to dest.
    // Does not replace /opt/pisecure and does not run anything from the archive.
    bool download_member(const Report &report, const std::string &member, const std::string &dest, std::string &err);

    void print_daemon_install(const std::string &tag);
    void print_wallet_install();
}
