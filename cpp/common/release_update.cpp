#include "release_update.hpp"

#include <openssl/sha.h>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <unistd.h>
#include <vector>

namespace pisecure_update
{
    namespace
    {
        using json = nlohmann::json;

        std::string trim(std::string text)
        {
            while (!text.empty() && std::isspace(static_cast<unsigned char>(text.front())))
            {
                text.erase(text.begin());
            }
            while (!text.empty() && std::isspace(static_cast<unsigned char>(text.back())))
            {
                text.pop_back();
            }
            return text;
        }

        std::string shell_single(const std::string &text)
        {
            std::string out = "'";
            for (char c : text)
            {
                if (c == '\'')
                {
                    out += "'\\''";
                }
                else
                {
                    out.push_back(c);
                }
            }
            out.push_back('\'');
            return out;
        }

        bool https_url(const std::string &url)
        {
            return url.compare(0, 8, "https://") == 0 && url.find('\'') == std::string::npos && url.find(' ') == std::string::npos;
        }

        int curl_status(const std::string &url, const std::string &out_path, std::string &body_or_err)
        {
            if (!https_url(url))
            {
                body_or_err = "update check skipped";
                return 0;
            }
            const std::string cmd = "curl -sS -m 20 -A pisecure -L -w '\\nHTTPSTATUS:%{http_code}' -o " + shell_single(out_path) + " " + shell_single(url);
            FILE *pipe = popen(cmd.c_str(), "r");
            if (pipe == nullptr)
            {
                body_or_err = "update check skipped";
                return 0;
            }
            std::string meta;
            char buf[256];
            while (fgets(buf, sizeof(buf), pipe) != nullptr)
            {
                meta += buf;
            }
            pclose(pipe);
            const auto mark = meta.rfind("HTTPSTATUS:");
            if (mark == std::string::npos)
            {
                body_or_err = "update check skipped";
                return 0;
            }
            return std::atoi(meta.c_str() + mark + 11);
        }

        std::string file_sha256(const std::string &path)
        {
            std::ifstream in(path, std::ios::binary);
            if (!in)
            {
                return {};
            }
            SHA256_CTX ctx;
            SHA256_Init(&ctx);
            char buf[8192];
            while (in)
            {
                in.read(buf, sizeof(buf));
                if (in.gcount() > 0)
                {
                    SHA256_Update(&ctx, buf, static_cast<size_t>(in.gcount()));
                }
            }
            unsigned char dig[SHA256_DIGEST_LENGTH];
            SHA256_Final(dig, &ctx);
            static const char *hexd = "0123456789abcdef";
            std::string out(64, '0');
            for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i)
            {
                out[static_cast<size_t>(i) * 2] = hexd[dig[i] >> 4];
                out[static_cast<size_t>(i) * 2 + 1] = hexd[dig[i] & 0x0f];
            }
            return out;
        }

        std::vector<int> version_parts(std::string text)
        {
            text = trim(text);
            if (!text.empty() && (text[0] == 'v' || text[0] == 'V'))
            {
                text.erase(text.begin());
            }
            std::vector<int> parts;
            std::string cur;
            for (char c : text)
            {
                if (c >= '0' && c <= '9')
                {
                    cur.push_back(c);
                }
                else if (!cur.empty())
                {
                    parts.push_back(std::atoi(cur.c_str()));
                    cur.clear();
                }
            }
            if (!cur.empty())
            {
                parts.push_back(std::atoi(cur.c_str()));
            }
            return parts;
        }

        int compare_versions(const std::string &left, const std::string &right)
        {
            const auto a = version_parts(left);
            const auto b = version_parts(right);
            const size_t n = std::max(a.size(), b.size());
            for (size_t i = 0; i < n; ++i)
            {
                const int av = i < a.size() ? a[i] : 0;
                const int bv = i < b.size() ? b[i] : 0;
                if (av < bv)
                {
                    return -1;
                }
                if (av > bv)
                {
                    return 1;
                }
            }
            return 0;
        }

        bool asset_name_ok(const std::string &name)
        {
            const std::string prefix = "pisecure-pi5-v";
            const std::string suffix = "-aarch64.tar.gz";
            return name.size() > prefix.size() + suffix.size() && name.compare(0, prefix.size(), prefix) == 0 && name.compare(name.size() - suffix.size(), suffix.size(), suffix) == 0;
        }

        std::string body_sha256(const std::string &body)
        {
            const auto pos = body.find("sha256:");
            if (pos == std::string::npos)
            {
                return {};
            }
            std::string hex;
            for (size_t i = pos + 7; i < body.size(); ++i)
            {
                const char c = body[i];
                if (std::isxdigit(static_cast<unsigned char>(c)))
                {
                    hex.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
                }
                else if (!hex.empty())
                {
                    break;
                }
            }
            return hex.size() == 64 ? hex : std::string();
        }

        std::string sums_hash_for(const std::string &sums, const std::string &member)
        {
            const std::string base = member.substr(member.find_last_of('/') == std::string::npos ? 0 : member.find_last_of('/') + 1);
            std::istringstream in(sums);
            std::string line;
            while (std::getline(in, line))
            {
                if (!line.empty() && line.back() == '\r')
                {
                    line.pop_back();
                }
                std::string hex;
                size_t i = 0;
                while (i < line.size() && std::isxdigit(static_cast<unsigned char>(line[i])))
                {
                    hex.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(line[i]))));
                    ++i;
                }
                if (hex.size() != 64)
                {
                    continue;
                }
                while (i < line.size() && std::isspace(static_cast<unsigned char>(line[i])))
                {
                    ++i;
                }
                if (i < line.size() && (line[i] == '*' || line[i] == ' '))
                {
                    ++i;
                }
                const std::string name = line.substr(i);
                const auto slash = name.find_last_of('/');
                const std::string tail = slash == std::string::npos ? name : name.substr(slash + 1);
                if (tail == base || name == member)
                {
                    return hex;
                }
            }
            return {};
        }

        std::string tar_member(const std::string &tar, const std::string &suffix)
        {
            const std::string cmd = "tar -tzf " + shell_single(tar) + " 2>/dev/null";
            FILE *pipe = popen(cmd.c_str(), "r");
            if (pipe == nullptr)
            {
                return {};
            }
            std::string found;
            char buf[512];
            while (fgets(buf, sizeof(buf), pipe) != nullptr)
            {
                std::string line = trim(buf);
                if (line == suffix || (line.size() > suffix.size() && line.compare(line.size() - suffix.size(), suffix.size(), suffix) == 0 && line[line.size() - suffix.size() - 1] == '/'))
                {
                    found = line;
                    break;
                }
            }
            pclose(pipe);
            return found;
        }

        std::string tar_text(const std::string &tar, const std::string &member)
        {
            const std::string cmd = "tar -xOf " + shell_single(tar) + " " + shell_single(member) + " 2>/dev/null";
            FILE *pipe = popen(cmd.c_str(), "r");
            if (pipe == nullptr)
            {
                return {};
            }
            std::string out;
            char buf[1024];
            while (true)
            {
                const size_t n = fread(buf, 1, sizeof(buf), pipe);
                if (n == 0)
                {
                    break;
                }
                out.append(buf, n);
            }
            pclose(pipe);
            return out;
        }

        bool tar_extract_file(const std::string &tar, const std::string &member, const std::string &dest)
        {
            const std::string cmd = "tar -xOf " + shell_single(tar) + " " + shell_single(member) + " > " + shell_single(dest) + " 2>/dev/null";
            return std::system(cmd.c_str()) == 0;
        }
    }

    std::string local_version(const std::string &compile_time)
    {
        std::ifstream in("/etc/pisecure/pisecured.version");
        if (in)
        {
            std::stringstream buf;
            buf << in.rdbuf();
            const std::string text = trim(buf.str());
            if (!text.empty())
            {
                return text;
            }
        }
        return compile_time;
    }

    Report check_release(const std::string &compile_time)
    {
        Report report;
        report.local = local_version(compile_time);
        char path[] = "/tmp/pisecure-release-XXXXXX";
        const int fd = mkstemp(path);
        if (fd < 0)
        {
            report.line = "update check skipped";
            return report;
        }
        close(fd);
        std::string ignored;
        const int http = curl_status("https://api.github.com/repos/UnderhillForge/PiSecure/releases/latest", path, ignored);
        if (http == 401 || http == 404 || http == 0)
        {
            std::remove(path);
            report.line = "update check skipped";
            return report;
        }
        if (http != 200)
        {
            std::remove(path);
            report.line = "update check skipped";
            return report;
        }
        json doc;
        try
        {
            std::ifstream in(path);
            doc = json::parse(in);
        }
        catch (const std::exception &)
        {
            std::remove(path);
            report.line = "update check skipped";
            return report;
        }
        std::remove(path);
        report.tag = doc.value("tag_name", "");
        report.sha256 = body_sha256(doc.value("body", ""));
        if (doc.contains("assets") && doc["assets"].is_array())
        {
            for (const auto &asset : doc["assets"])
            {
                const std::string name = asset.value("name", "");
                if (asset_name_ok(name))
                {
                    report.asset = name;
                    report.url = asset.value("browser_download_url", "");
                }
                if (name == "SHA256SUMS")
                {
                    const std::string sums_url = asset.value("browser_download_url", "");
                    char sums_path[] = "/tmp/pisecure-sums-XXXXXX";
                    const int sfd = mkstemp(sums_path);
                    if (sfd >= 0)
                    {
                        close(sfd);
                        std::string sums_err;
                        if (curl_status(sums_url, sums_path, sums_err) == 200)
                        {
                            std::ifstream sin(sums_path);
                            std::stringstream sbuf;
                            sbuf << sin.rdbuf();
                            const std::string hashed = sums_hash_for(sbuf.str(), report.asset);
                            if (!hashed.empty())
                            {
                                report.sha256 = hashed;
                            }
                        }
                        std::remove(sums_path);
                    }
                }
            }
        }
        if (report.tag.empty() || report.url.empty())
        {
            report.line = "update check skipped";
            return report;
        }
        if (compare_versions(report.tag, report.local) <= 0)
        {
            report.kind = Report::Kind::Current;
            report.line = "update check: " + report.tag + " is current";
            return report;
        }
        report.kind = Report::Kind::Newer;
        report.line = "update available: " + report.tag + " " + report.url;
        if (!report.sha256.empty())
        {
            report.line += " sha256 " + report.sha256;
        }
        return report;
    }

    bool write_available(const std::string &path, const Report &report)
    {
        json doc = {{"current", report.local}, {"tag", report.tag}, {"url", report.url}, {"sha256", report.sha256}, {"asset", report.asset}};
        const std::string tmp = path + ".tmp";
        {
            std::ofstream out(tmp, std::ios::trunc);
            if (!out)
            {
                return false;
            }
            out << doc.dump(2) << "\n";
        }
        return std::rename(tmp.c_str(), path.c_str()) == 0;
    }

    bool download_member(const Report &report, const std::string &member, const std::string &dest, std::string &err)
    {
        if (report.url.empty() || !https_url(report.url))
        {
            err = "update check skipped";
            return false;
        }
        if (dest.compare(0, 16, "/opt/pisecure/") == 0)
        {
            err = "refusing to replace a running install path";
            return false;
        }
        char tar_path[] = "/tmp/pisecure-ota-XXXXXX";
        const int fd = mkstemp(tar_path);
        if (fd < 0)
        {
            err = "could not store the release download";
            return false;
        }
        close(fd);
        std::string curl_err;
        const int http = curl_status(report.url, tar_path, curl_err);
        if (http != 200)
        {
            std::remove(tar_path);
            err = "update check skipped";
            return false;
        }
        const std::string got = file_sha256(tar_path);
        if (!report.sha256.empty() && got != report.sha256)
        {
            std::remove(tar_path);
            err = "release sha256 does not match";
            return false;
        }
        const std::string sums_member = tar_member(tar_path, "SHA256SUMS");
        const std::string bin_member = tar_member(tar_path, member);
        if (sums_member.empty() || bin_member.empty())
        {
            std::remove(tar_path);
            err = "release archive has no " + member;
            return false;
        }
        const std::string sums = tar_text(tar_path, sums_member);
        const std::string expect = sums_hash_for(sums, bin_member);
        if (expect.empty() || !tar_extract_file(tar_path, bin_member, dest))
        {
            std::remove(tar_path);
            err = "could not verify " + member;
            return false;
        }
        std::remove(tar_path);
        if (file_sha256(dest) != expect)
        {
            std::remove(dest.c_str());
            err = member + " sha256 does not match SHA256SUMS";
            return false;
        }
        return true;
    }

    void print_daemon_install(const std::string &tag)
    {
        std::cout << "sudo systemctl stop pisecured\n"
                  << "sudo install -m 755 /tmp/pisecured /opt/pisecure/pisecured\n"
                  << "echo " << tag << " | sudo tee /etc/pisecure/pisecured.version\n"
                  << "sudo systemctl start pisecured\n";
    }

    void print_wallet_install()
    {
        std::cout << "sudo install -m 755 /tmp/pswallet /opt/pisecure/pswallet\n";
    }
}
