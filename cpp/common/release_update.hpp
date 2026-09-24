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
    // Refuses a destination under /opt/pisecure. Does not copy datadir, wallets, or env.
    bool download_member(const Report &report, const std::string &member, const std::string &dest, std::string &err);

    // Remember argv so a non-systemd apply can exec the installed binary.
    void set_restart_args(int argc, char **argv);

    // Verify member, write final_path.new, then rename it over final_path.
    bool install_member(const Report &report, const std::string &member, const std::string &final_path, std::string &err);

    // Install pisecured and write /etc/pisecure/pisecured.version. Does not restart.
    // On a failed version write, the previous executable image is restored.
    bool apply_daemon(const Report &report, std::string &err);

    // systemd: schedule systemctl restart. Otherwise exec /opt/pisecure/pisecured.
    bool restart_after_apply(std::string &err);

    void print_daemon_install(const std::string &tag);
    void print_wallet_install();
}
