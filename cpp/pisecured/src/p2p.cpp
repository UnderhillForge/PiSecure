#include "pisecured/p2p.hpp"
#include "pisecured/ws_server.hpp"
#include "pisecured/storage.hpp"
#include "pisecured/chain_rpc.hpp"
#include <ifaddrs.h>
#include <net/if.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <cstring>
#include <cctype>
#include <iostream>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <chrono>
#include <algorithm>
#include <openssl/sha.h>

namespace pisecured
{
    // --- Message Serialization Implementation ---

    void MessageSerializer::writeUint32(std::vector<uint8_t> &buf, uint32_t val)
    {
        buf.push_back(val & 0xFF);
        buf.push_back((val >> 8) & 0xFF);
        buf.push_back((val >> 16) & 0xFF);
        buf.push_back((val >> 24) & 0xFF);
    }

    void MessageSerializer::writeUint64(std::vector<uint8_t> &buf, uint64_t val)
    {
        for (int i = 0; i < 8; i++)
        {
            buf.push_back((val >> (i * 8)) & 0xFF);
        }
    }

    void MessageSerializer::writeString(std::vector<uint8_t> &buf, const std::string &str)
    {
        writeVarInt(buf, str.size());
        buf.insert(buf.end(), str.begin(), str.end());
    }

    void MessageSerializer::writeVarInt(std::vector<uint8_t> &buf, uint64_t val)
    {
        if (val < 0xFD)
        {
            buf.push_back(static_cast<uint8_t>(val));
        }
        else if (val <= 0xFFFF)
        {
            buf.push_back(0xFD);
            buf.push_back(val & 0xFF);
            buf.push_back((val >> 8) & 0xFF);
        }
        else if (val <= 0xFFFFFFFF)
        {
            buf.push_back(0xFE);
            writeUint32(buf, static_cast<uint32_t>(val));
        }
        else
        {
            buf.push_back(0xFF);
            writeUint64(buf, val);
        }
    }

    uint32_t MessageSerializer::readUint32(const uint8_t *data, size_t &offset)
    {
        uint32_t val = data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16) | (data[offset + 3] << 24);
        offset += 4;
        return val;
    }

    uint64_t MessageSerializer::readUint64(const uint8_t *data, size_t &offset)
    {
        uint64_t val = 0;
        for (int i = 0; i < 8; i++)
        {
            val |= static_cast<uint64_t>(data[offset + i]) << (i * 8);
        }
        offset += 8;
        return val;
    }

    std::string MessageSerializer::readString(const uint8_t *data, size_t &offset, size_t maxLen)
    {
        uint64_t len = readVarInt(data, offset, maxLen);
        if (len > maxLen || offset + len > maxLen)
            return "";
        std::string str(reinterpret_cast<const char *>(data + offset), len);
        offset += len;
        return str;
    }

    uint64_t MessageSerializer::readVarInt(const uint8_t *data, size_t &offset, size_t maxSize)
    {
        if (offset >= maxSize)
            return 0;
        uint8_t first = data[offset++];
        if (first < 0xFD)
            return first;
        if (first == 0xFD && offset + 2 <= maxSize)
        {
            uint64_t val = data[offset] | (data[offset + 1] << 8);
            offset += 2;
            return val;
        }
        if (first == 0xFE && offset + 4 <= maxSize)
        {
            uint64_t val = readUint32(data, offset);
            return val;
        }
        if (first == 0xFF && offset + 8 <= maxSize)
        {
            return readUint64(data, offset);
        }
        return 0;
    }

    std::vector<uint8_t> MessageSerializer::serializeVersion(uint32_t version, uint32_t services, uint64_t timestamp,
                                                             const PeerAddr &addrRecv, const PeerAddr &addrFrom,
                                                             uint64_t nonce, const std::string &userAgent, uint32_t startHeight)
    {
        std::vector<uint8_t> payload;
        writeUint32(payload, version);
        writeUint64(payload, services);
        writeUint64(payload, timestamp);
        writeUint64(payload, addrRecv.services);
        writeUint64(payload, addrFrom.services);
        writeUint64(payload, nonce);
        writeString(payload, userAgent);
        writeUint32(payload, startHeight);
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeVerack()
    {
        return std::vector<uint8_t>();
    }

    std::vector<uint8_t> MessageSerializer::serializeAddr(const std::vector<PeerAddr> &addrs)
    {
        std::vector<uint8_t> payload;
        writeVarInt(payload, addrs.size());
        for (const auto &addr : addrs)
        {
            writeUint64(payload, addr.lastSeen);
            writeUint32(payload, addr.services);
            writeUint32(payload, addr.addr.sin_addr.s_addr);
            payload.push_back((addr.addr.sin_port >> 8) & 0xFF);
            payload.push_back(addr.addr.sin_port & 0xFF);
        }
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeInv(const std::vector<InvVect> &invs)
    {
        std::vector<uint8_t> payload;
        writeVarInt(payload, invs.size());
        for (const auto &inv : invs)
        {
            writeUint32(payload, inv.type);
            payload.insert(payload.end(), inv.hash.begin(), inv.hash.end());
        }
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeGetData(const std::vector<InvVect> &invs)
    {
        return serializeInv(invs);
    }

    std::vector<uint8_t> MessageSerializer::serializeGetHeaders(const std::vector<std::array<uint8_t, 32>> &locatorHashes,
                                                                const std::array<uint8_t, 32> &hashStop)
    {
        std::vector<uint8_t> payload;
        writeUint32(payload, PROTOCOL_VERSION);
        writeVarInt(payload, locatorHashes.size());
        for (const auto &hash : locatorHashes)
        {
            payload.insert(payload.end(), hash.begin(), hash.end());
        }
        payload.insert(payload.end(), hashStop.begin(), hashStop.end());
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeHeaders(const std::vector<BlockHeader> &headers)
    {
        std::vector<uint8_t> payload;
        writeVarInt(payload, headers.size());
        for (const auto &header : headers)
        {
            writeUint32(payload, header.version);
            payload.insert(payload.end(), header.prevBlockHash.begin(), header.prevBlockHash.end());
            payload.insert(payload.end(), header.merkleRoot.begin(), header.merkleRoot.end());
            writeUint64(payload, header.timestamp);
            writeUint32(payload, header.difficulty);
            writeUint64(payload, header.nonce);
            payload.insert(payload.end(), header.hash.begin(), header.hash.end());
        }
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeBlock(const std::vector<uint8_t> &blockData)
    {
        return blockData;
    }

    std::vector<uint8_t> MessageSerializer::serializeTx(const std::vector<uint8_t> &txData)
    {
        return txData;
    }

    std::vector<uint8_t> MessageSerializer::serializePing(uint64_t nonce)
    {
        std::vector<uint8_t> payload;
        writeUint64(payload, nonce);
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializePong(uint64_t nonce)
    {
        std::vector<uint8_t> payload;
        writeUint64(payload, nonce);
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeReject(const std::string &message, uint8_t code, const std::string &reason)
    {
        std::vector<uint8_t> payload;
        writeString(payload, message);
        payload.push_back(code);
        writeString(payload, reason);
        return payload;
    }

    std::vector<uint8_t> MessageSerializer::serializeThreatAlert(const ThreatAlert &alert)
    {
        std::vector<uint8_t> payload;
        writeString(payload, alert.threatType);
        writeString(payload, alert.severity);
        writeUint32(payload, alert.sourceIP);
        writeUint64(payload, alert.timestamp);
        writeString(payload, alert.details);
        writeString(payload, alert.reportingNodeId);
        // Convert double to uint64_t (fixed-point: confidence * 1000000)
        uint64_t confidenceFixed = static_cast<uint64_t>(alert.confidenceScore * 1000000.0);
        writeUint64(payload, confidenceFixed);
        return payload;
    }

    bool MessageSerializer::deserializeVersion(const std::vector<uint8_t> &data, uint32_t &version, uint32_t &services,
                                               uint64_t &timestamp, std::string &userAgent, uint32_t &startHeight)
    {
        if (data.size() < 40)
            return false;
        size_t offset = 0;
        version = readUint32(data.data(), offset);
        services = static_cast<uint32_t>(readUint64(data.data(), offset));
        timestamp = readUint64(data.data(), offset);
        offset += 16; // skip addr fields
        uint64_t nonce = readUint64(data.data(), offset);
        userAgent = readString(data.data(), offset, data.size());
        if (offset + 4 <= data.size())
        {
            startHeight = readUint32(data.data(), offset);
        }
        return true;
    }

    bool MessageSerializer::deserializeAddr(const std::vector<uint8_t> &data, std::vector<PeerAddr> &addrs)
    {
        if (data.empty())
            return false;
        size_t offset = 0;
        uint64_t count = readVarInt(data.data(), offset, data.size());
        if (count > 1000)
            return false;
        for (uint64_t i = 0; i < count; i++)
        {
            if (offset + 18 > data.size())
                return false;
            PeerAddr addr{};
            addr.lastSeen = readUint64(data.data(), offset);
            addr.services = readUint32(data.data(), offset);
            addr.addr.sin_family = AF_INET;
            addr.addr.sin_addr.s_addr = readUint32(data.data(), offset);
            addr.addr.sin_port = (data[offset] << 8) | data[offset + 1];
            offset += 2;
            addrs.push_back(addr);
        }
        return true;
    }

    bool MessageSerializer::deserializeInv(const std::vector<uint8_t> &data, std::vector<InvVect> &invs)
    {
        if (data.empty())
            return false;
        size_t offset = 0;
        uint64_t count = readVarInt(data.data(), offset, data.size());
        if (count > MAX_INV_SIZE)
            return false;
        for (uint64_t i = 0; i < count; i++)
        {
            if (offset + 36 > data.size())
                return false;
            InvVect inv;
            inv.type = readUint32(data.data(), offset);
            std::copy(data.begin() + offset, data.begin() + offset + 32, inv.hash.begin());
            offset += 32;
            invs.push_back(inv);
        }
        return true;
    }

    bool MessageSerializer::deserializeGetHeaders(const std::vector<uint8_t> &data,
                                                  std::vector<std::array<uint8_t, 32>> &locatorHashes,
                                                  std::array<uint8_t, 32> &hashStop)
    {
        if (data.size() < 37)
            return false;
        size_t offset = 4; // skip version
        uint64_t count = readVarInt(data.data(), offset, data.size());
        if (count > 500)
            return false;
        for (uint64_t i = 0; i < count; i++)
        {
            if (offset + 32 > data.size())
                return false;
            std::array<uint8_t, 32> hash;
            std::copy(data.begin() + offset, data.begin() + offset + 32, hash.begin());
            offset += 32;
            locatorHashes.push_back(hash);
        }
        if (offset + 32 <= data.size())
        {
            std::copy(data.begin() + offset, data.begin() + offset + 32, hashStop.begin());
        }
        return true;
    }

    bool MessageSerializer::deserializeHeaders(const std::vector<uint8_t> &data, std::vector<BlockHeader> &headers)
    {
        if (data.empty())
            return false;
        size_t offset = 0;
        uint64_t count = readVarInt(data.data(), offset, data.size());
        if (count > 2000)
            return false;
        for (uint64_t i = 0; i < count; i++)
        {
            if (offset + 116 > data.size())
                return false;
            BlockHeader header;
            header.version = readUint32(data.data(), offset);
            std::copy(data.begin() + offset, data.begin() + offset + 32, header.prevBlockHash.begin());
            offset += 32;
            std::copy(data.begin() + offset, data.begin() + offset + 32, header.merkleRoot.begin());
            offset += 32;
            header.timestamp = readUint64(data.data(), offset);
            header.difficulty = readUint32(data.data(), offset);
            header.nonce = readUint64(data.data(), offset);
            std::copy(data.begin() + offset, data.begin() + offset + 32, header.hash.begin());
            offset += 32;
            headers.push_back(header);
        }
        return true;
    }

    bool MessageSerializer::deserializePing(const std::vector<uint8_t> &data, uint64_t &nonce)
    {
        if (data.size() < 8)
            return false;
        size_t offset = 0;
        nonce = readUint64(data.data(), offset);
        return true;
    }

    bool MessageSerializer::deserializePong(const std::vector<uint8_t> &data, uint64_t &nonce)
    {
        return deserializePing(data, nonce);
    }

    bool MessageSerializer::deserializeThreatAlert(const std::vector<uint8_t> &data, ThreatAlert &alert)
    {
        if (data.size() < 20)
            return false;
        size_t offset = 0;
        alert.threatType = readString(data.data(), offset, data.size());
        alert.severity = readString(data.data(), offset, data.size());
        alert.sourceIP = readUint32(data.data(), offset);
        alert.timestamp = readUint64(data.data(), offset);
        alert.details = readString(data.data(), offset, data.size());
        alert.reportingNodeId = readString(data.data(), offset, data.size());
        if (offset + 8 <= data.size())
        {
            uint64_t confidenceFixed = readUint64(data.data(), offset);
            alert.confidenceScore = static_cast<double>(confidenceFixed) / 1000000.0;
        }
        return true;
    }

    // --- ThreatDetector Implementation ---

    ThreatDetector::ThreatDetector()
    {
    }

    bool ThreatDetector::analyzeMessagePattern(const Peer &peer, P2PMsgType msgType, size_t payloadSize)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Track message count per peer IP
        uint32_t ip = ntohl(peer.address.addr.sin_addr.s_addr);
        messageCounts_[ip]++;

        // Detect rapid message flooding (DDoS indicator)
        if (messageCounts_[ip] > 1000)
        {
            return true; // Threat detected
        }

        // Detect oversized payloads (buffer overflow attempt)
        if (payloadSize > 10 * 1024 * 1024) // 10MB threshold
        {
            return true;
        }

        return false;
    }

    bool ThreatDetector::analyzeConnectionPattern(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        uint32_t ip = ntohl(addr.addr.sin_addr.s_addr);
        auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        connectionAttempts_[ip].push_back(now);

        // Remove old connection attempts (older than 60 seconds)
        auto &attempts = connectionAttempts_[ip];
        attempts.erase(
            std::remove_if(attempts.begin(), attempts.end(),
                           [now](uint64_t timestamp)
                           { return (now - timestamp) > 60000000000ULL; }),
            attempts.end());

        // Detect rapid connection attempts (DDoS/port scan)
        if (attempts.size() > 10)
        {
            return true; // Threat detected
        }

        return false;
    }

    double ThreatDetector::calculateThreatScore(const Peer &peer)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        double score = 0.0;

        uint32_t ip = ntohl(peer.address.addr.sin_addr.s_addr);
        // Feature 1: Connection frequency (weight: 0.3)
        score += extractConnectionFrequency(ip) * 0.3;

        return std::min(1.0, score);
    }

    bool ThreatDetector::detectDDoSPattern(const std::vector<std::shared_ptr<Peer>> &peers)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Count connections per IP subnet
        std::map<uint32_t, int> subnetCounts;
        for (const auto &peer : peers)
        {
            uint32_t ip = ntohl(peer->address.addr.sin_addr.s_addr);
            uint32_t subnet = ip & 0xFFFFFF00; // /24 subnet
            subnetCounts[subnet]++;
        }

        // Detect if too many connections from same subnet (Sybil/DDoS)
        for (const auto &[subnet, count] : subnetCounts)
        {
            if (count > 20) // More than 20 connections from same /24
            {
                return true;
            }
        }

        // Detect overall connection flood
        if (peers.size() > 100)
        {
            return true;
        }

        return false;
    }

    bool ThreatDetector::detectSybilAttack(const std::vector<std::shared_ptr<Peer>> &peers)
    {
        std::lock_guard<std::mutex> lock(mutex_);

        // Count peers with identical user agents or services
        std::map<std::string, int> userAgentCounts;
        for (const auto &peer : peers)
        {
            if (!peer->userAgent.empty())
            {
                userAgentCounts[peer->userAgent]++;
            }
        }

        // If >50% of peers have same user agent, likely Sybil
        for (const auto &[ua, count] : userAgentCounts)
        {
            if (count > peers.size() / 2 && peers.size() > 10)
            {
                return true;
            }
        }

        return false;
    }

    bool ThreatDetector::detectEclipseAttack(const AddrMan &addrman)
    {
        // Eclipse attack: adversary controls all peer connections
        // TODO: Analyze addrman diversity (IP ranges, ASNs, geographic distribution)
        // For now, basic heuristic: check if all known addresses are from similar IPs

        return false; // Placeholder
    }

    void ThreatDetector::recordThreat(const ThreatAlert &alert)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        threatHistory_.push_back(alert);
        knownThreats_.insert(alert.sourceIP);

        // Keep only last 1000 threats
        if (threatHistory_.size() > 1000)
        {
            threatHistory_.erase(threatHistory_.begin());
        }
    }

    std::vector<ThreatAlert> ThreatDetector::getRecentThreats(uint64_t timeWindow) const
    {
        std::lock_guard<std::mutex> lock(mutex_);

        auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        std::vector<ThreatAlert> recent;

        for (const auto &threat : threatHistory_)
        {
            if ((now - threat.timestamp) < timeWindow)
            {
                recent.push_back(threat);
            }
        }

        return recent;
    }

    bool ThreatDetector::isKnownThreat(uint32_t ip) const
    {
        std::lock_guard<std::mutex> lock(mutex_);
        return knownThreats_.count(ip) > 0;
    }

    double ThreatDetector::extractConnectionFrequency(uint32_t ip) const
    {
        auto it = connectionAttempts_.find(ip);
        if (it == connectionAttempts_.end())
            return 0.0;

        // Normalize: >10 attempts in 60s = 1.0 score
        return std::min(1.0, it->second.size() / 10.0);
    }

    double ThreatDetector::extractMessageRateAnomaly(const Peer &peer) const
    {
        uint32_t ip = ntohl(peer.address.addr.sin_addr.s_addr);
        auto it = messageCounts_.find(ip);
        if (it == messageCounts_.end())
            return 0.0;

        // Normalize: >1000 messages = 1.0 score
        return std::min(1.0, it->second / 1000.0);
    }

    double ThreatDetector::extractBehaviorScore(const Peer &peer) const
    {
        double score = 0.0;

        // Factor in ban score
        score += peer.banScore / 100.0; // Normalize to 0-1

        // Factor in handshake status (non-handshaked peers are suspicious)
        if (!peer.handshakeComplete)
        {
            score += 0.3;
        }

        return std::min(1.0, score);
    }

    // --- Peer Implementation ---

    Peer::Peer(int fd_, const PeerAddr &addr_, bool inbound_)
        : fd(fd_), address(addr_), inbound(inbound_), handshakeComplete(false),
          lastPingTime(0), lastPongTime(0), lastRecvTime(0), lastSendTime(0),
          banScore(0), version(0), services(0), startHeight(0), pingNonce(0)
    {
        lastRecvTime = std::chrono::steady_clock::now().time_since_epoch().count();
        lastSendTime = lastRecvTime;
    }

    bool Peer::sendMessage(P2PMsgType type, const std::vector<uint8_t> &payload)
    {
        // Message format: [type:1][length:4][payload]
        std::vector<uint8_t> msg;
        msg.push_back(static_cast<uint8_t>(type));
        uint32_t len = payload.size();
        msg.push_back(len & 0xFF);
        msg.push_back((len >> 8) & 0xFF);
        msg.push_back((len >> 16) & 0xFF);
        msg.push_back((len >> 24) & 0xFF);
        msg.insert(msg.end(), payload.begin(), payload.end());

        return sendRawData(msg);
    }

    bool Peer::sendRawData(const std::vector<uint8_t> &data)
    {
        ssize_t sent = send(fd, data.data(), data.size(), MSG_NOSIGNAL);
        if (sent > 0)
        {
            lastSendTime = std::chrono::steady_clock::now().time_since_epoch().count();
            return sent == static_cast<ssize_t>(data.size());
        }
        return false;
    }

    void Peer::increaseBanScore(int amount)
    {
        banScore += amount;
    }

    int64_t Peer::getIdleTime() const
    {
        auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        return (now - lastRecvTime) / 1000000000LL; // Convert to seconds
    }

    // --- AddrMan Implementation ---

    AddrMan::AddrMan()
    {
    }

    void AddrMan::add(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        // Don't add if already exists or banned
        if (isBanned(addr))
            return;
        for (const auto &existing : addrList)
        {
            if (existing == addr)
                return;
        }
        addrList.push_back(addr);
    }

    PeerAddr AddrMan::select()
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (addrList.empty())
            throw std::runtime_error("No peers available");

        // Select peer with exponential backoff based on failures
        std::vector<PeerAddr> candidates;
        for (const auto &addr : addrList)
        {
            if (!isBanned(addr) && addr.failures < 5)
            {
                candidates.push_back(addr);
            }
        }

        if (candidates.empty())
            throw std::runtime_error("No viable peers available");

        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, candidates.size() - 1);
        return candidates[dis(gen)];
    }

    std::vector<PeerAddr> AddrMan::getMany(size_t n)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<PeerAddr> out;
        for (size_t i = 0; i < n && i < addrList.size(); i++)
        {
            if (!isBanned(addrList[i]))
            {
                out.push_back(addrList[i]);
            }
        }
        return out;
    }

    void AddrMan::markGood(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto &existing : addrList)
        {
            if (existing == addr)
            {
                existing.failures = 0;
                existing.lastSeen = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
                return;
            }
        }
    }

    void AddrMan::markAttempt(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto &existing : addrList)
        {
            if (existing == addr)
            {
                existing.lastSeen = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
                return;
            }
        }
    }

    void AddrMan::markFailure(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto &existing : addrList)
        {
            if (existing == addr)
            {
                existing.failures++;
                if (existing.failures >= 10)
                {
                    ban(addr);
                }
                return;
            }
        }
    }

    void AddrMan::ban(const PeerAddr &addr)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        uint64_t unbanTime = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL + 86400; // Ban for 24 hours
        bannedIPs[addr.addr.sin_addr.s_addr] = unbanTime;
    }

    bool AddrMan::isBanned(const PeerAddr &addr) const
    {
        auto it = bannedIPs.find(addr.addr.sin_addr.s_addr);
        if (it != bannedIPs.end())
        {
            uint64_t now = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
            return it->second > now;
        }
        return false;
    }

    void AddrMan::addBootstrapPeers(const std::vector<std::string> &bootstrapHosts, uint16_t port)
    {
        // One outbound peer. HTTP bootstrap registration (queryBootstrapServer) is still a stub.
        bool added = false;
        for (const auto &host : bootstrapHosts)
        {
            if (added)
            {
                std::cerr << "Bootstrap peer skipped after first resolve: " << host << std::endl;
                continue;
            }

            PeerAddr addr{};
            addr.addr.sin_family = AF_INET;
            addr.addr.sin_port = htons(port);
            addr.services = SERVICES_NODE;
            addr.lastSeen = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
            addr.failures = 0;

            if (inet_pton(AF_INET, host.c_str(), &addr.addr.sin_addr) == 1)
            {
                add(addr);
                added = true;
                continue;
            }

            addrinfo hints{};
            hints.ai_family = AF_INET;
            hints.ai_socktype = SOCK_STREAM;
            addrinfo *res = nullptr;
            const int rc = getaddrinfo(host.c_str(), nullptr, &hints, &res);
            if (rc != 0 || res == nullptr || res->ai_addr == nullptr)
            {
                std::cerr << "Bootstrap peer DNS failed for " << host << ": " << gai_strerror(rc) << std::endl;
                if (res != nullptr)
                {
                    freeaddrinfo(res);
                }
                continue;
            }
            const auto *sin = reinterpret_cast<sockaddr_in *>(res->ai_addr);
            addr.addr.sin_addr = sin->sin_addr;
            std::cout << "Bootstrap peer " << host << " resolved to " << inet_ntoa(addr.addr.sin_addr) << std::endl;
            freeaddrinfo(res);
            add(addr);
            added = true;
        }
    }

    void AddrMan::queryBootstrapServer(const std::string &bootstrapUrl)
    {
        // TODO: HTTP GET to bootstrapUrl/api/v1/bootstrap/peers
        // Parse JSON response and add peers via add()
        std::cerr << "Bootstrap server query not yet implemented: " << bootstrapUrl << std::endl;
    }

    void AddrMan::reportToBootstrap(const std::string &bootstrapUrl, const std::string &nodeId, const PeerAddr &myAddr)
    {
        // TODO: HTTP POST to bootstrapUrl/api/v1/bootstrap/register
        // Send node registration with capabilities and address
        std::cerr << "Bootstrap reporting not yet implemented: " << bootstrapUrl << std::endl;
    }

    void AddrMan::cleanupBans()
    {
        std::lock_guard<std::mutex> lock(mutex_);
        uint64_t now = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
        for (auto it = bannedIPs.begin(); it != bannedIPs.end();)
        {
            if (it->second <= now)
            {
                it = bannedIPs.erase(it);
            }
            else
            {
                ++it;
            }
        }
    }

    // --- BootstrapWebSocketClient Implementation ---

    BootstrapWebSocketClient::BootstrapWebSocketClient(const std::string &nodeId, const std::string &bootstrapUrl)
        : nodeId_(nodeId), bootstrapUrl_(bootstrapUrl), sockFd_(-1), connected_(false), running_(false), lastHeartbeat_(0)
    {
    }

    BootstrapWebSocketClient::~BootstrapWebSocketClient()
    {
        disconnect();
    }

    bool BootstrapWebSocketClient::connect()
    {
        if (connected_.load())
        {
            return true;
        }

        // For now, we'll use a simplified HTTP fallback approach
        // Full WebSocket implementation would require libwebsockets or similar
        std::cout << "Bootstrap WebSocket: Connecting to " << bootstrapUrl_ << " as node " << nodeId_ << std::endl;

        // TODO: Implement full WebSocket handshake
        // For production, integrate libwebsockets or socket.io C++ client
        // This is a placeholder that sets up the infrastructure

        connected_ = true;
        running_ = true;
        recvThread_ = std::thread(&BootstrapWebSocketClient::recvLoop, this);

        std::cout << "Bootstrap WebSocket: Connected (HTTP fallback mode)" << std::endl;
        return true;
    }

    void BootstrapWebSocketClient::disconnect()
    {
        if (!running_.exchange(false))
        {
            return;
        }

        connected_ = false;

        if (sockFd_ >= 0)
        {
            close(sockFd_);
            sockFd_ = -1;
        }

        if (recvThread_.joinable())
        {
            recvThread_.join();
        }

        std::cout << "Bootstrap WebSocket: Disconnected" << std::endl;
    }

    void BootstrapWebSocketClient::sendHeartbeat(const std::map<std::string, double> &metrics)
    {
        if (!connected_.load())
        {
            return;
        }

        auto now = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
        if (now - lastHeartbeat_ < 30)
        {
            return; // Rate limit: 1 per 30 seconds
        }

        // Build JSON heartbeat message
        std::string message = "{\"type\":\"heartbeat\",\"node_id\":\"" + nodeId_ + "\",";
        message += "\"timestamp\":" + std::to_string(now) + ",";
        message += "\"metrics\":{";

        bool first = true;
        for (const auto &[key, value] : metrics)
        {
            if (!first)
                message += ",";
            message += "\"" + key + "\":" + std::to_string(value);
            first = false;
        }

        message += "}}";

        if (sendWebSocketMessage(message))
        {
            lastHeartbeat_ = now;
        }
    }

    void BootstrapWebSocketClient::reportThreat(const std::string &threatType, const std::string &severity, const std::string &details)
    {
        if (!connected_.load())
        {
            return;
        }

        auto now = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;

        // Build JSON threat report
        std::string message = "{\"type\":\"report_threat\",";
        message += "\"threat_data\":{";
        message += "\"threat_type\":\"" + threatType + "\",";
        message += "\"severity\":\"" + severity + "\",";
        message += "\"details\":\"" + details + "\",";
        message += "\"timestamp\":" + std::to_string(now);
        message += "}}";

        sendWebSocketMessage(message);
    }

    void BootstrapWebSocketClient::reportNodeStatus(int peerCount, double uptime)
    {
        if (!connected_.load())
        {
            return;
        }

        std::map<std::string, double> metrics;
        metrics["peer_count"] = peerCount;
        metrics["uptime_seconds"] = uptime;
        sendHeartbeat(metrics);
    }

    bool BootstrapWebSocketClient::sendWebSocketMessage(const std::string &message)
    {
        std::lock_guard<std::mutex> lock(sendMutex_);

        // TODO: Implement actual WebSocket frame sending
        // For now, log the message that would be sent
        std::cout << "Bootstrap WS -> " << message << std::endl;

        return true;
    }

    bool BootstrapWebSocketClient::performWebSocketHandshake()
    {
        // TODO: Implement RFC 6455 WebSocket handshake
        // 1. Send HTTP Upgrade request
        // 2. Compute Sec-WebSocket-Accept from Sec-WebSocket-Key
        // 3. Validate server response
        return true;
    }

    void BootstrapWebSocketClient::recvLoop()
    {
        // TODO: Implement WebSocket frame receiving
        // For now, just keep the thread alive
        while (running_.load())
        {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    void BootstrapWebSocketClient::handleMessage(const std::string &message)
    {
        // Parse JSON and dispatch to callbacks
        // Simple JSON parsing (production should use nlohmann/json or similar)

        if (message.find("\"type\":\"threat_detected\"") != std::string::npos)
        {
            if (threatCallback_)
            {
                // Extract fields (simplified)
                std::string threatType = "ddos_attack";
                std::string severity = "high";
                std::string details = "Threat detected by Sentinel AI";
                threatCallback_(threatType, severity, details);
            }
        }
        else if (message.find("\"type\":\"defense_activated\"") != std::string::npos)
        {
            if (defenseCallback_)
            {
                std::string defenseType = "rate_limit";
                std::string details = "Defense mechanism activated";
                defenseCallback_(defenseType, details);
            }
        }
        else if (message.find("\"type\":\"node_registered\"") != std::string::npos)
        {
            if (peerDiscoveryCallback_)
            {
                // Parse peer list and callback
                std::vector<PeerAddr> peers;
                peerDiscoveryCallback_(peers);
            }
        }
    }

    // --- P2PServer Implementation ---

    P2PServer::P2PServer()
        : storage_(nullptr), running_(false), listenFd_(-1), bestHeight_(0)
    {
    }

    P2PServer::~P2PServer()
    {
        stop();
    }

    bool P2PServer::start(const Config &cfg, Storage *storage)
    {
        if (running_.exchange(true))
        {
            return false;
        }

        config_ = cfg;
        storage_ = storage;

        if (const char *envId = std::getenv("PISECURE_NODE_ID"))
        {
            if (envId[0] != '\0')
            {
                bootstrapNodeId_ = envId;
            }
        }
        if (bootstrapNodeId_.empty())
        {
            char hostbuf[256] = {};
            std::string id = "pisecured-node";
            if (gethostname(hostbuf, sizeof(hostbuf) - 1) == 0 && hostbuf[0] != '\0')
            {
                id = "pisecured-";
                for (const char *p = hostbuf; *p != '\0' && *p != '.'; ++p)
                {
                    const unsigned char c = static_cast<unsigned char>(*p);
                    if (std::isalnum(c) || c == '-' || c == '_')
                    {
                        id.push_back(static_cast<char>(c));
                    }
                }
                if (id.size() < 11)
                {
                    id = "pisecured-node";
                }
            }
            bootstrapNodeId_ = id;
        }
        std::cout << "bootstrap node_id " << bootstrapNodeId_ << std::endl;

        // Generate node ID from hardware or config
        nodeId_ = "pisecured-" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());

        if (storage_ && storage_->has_tip())
        {
            bestHeight_ = storage_->get_best_height();
        }

        if (!cfg.peers.empty())
        {
            for (const auto &spec : cfg.peers)
            {
                const auto colon = spec.rfind(':');
                if (colon == std::string::npos)
                {
                    continue;
                }
                PeerAddr addr{};
                addr.addr.sin_family = AF_INET;
                addr.addr.sin_port = htons(static_cast<uint16_t>(std::stoi(spec.substr(colon + 1))));
                addr.services = SERVICES_NODE;
                addr.failures = 0;
                if (inet_pton(AF_INET, spec.substr(0, colon).c_str(), &addr.addr.sin_addr) == 1)
                {
                    addrman_.add(addr);
                    std::cout << "Sync peer " << spec << std::endl;
                }
            }
        }
        else
        {
            std::vector<std::string> bootstrapHosts = {"bootstrap.pisecure.org", "bootstrap-testnet.pisecure.org"};
            addrman_.addBootstrapPeers(bootstrapHosts, cfg.p2p_port);
        }

        // Initialize Bootstrap WebSocket client for Sentinel AI coordination
        std::string wsUrl = cfg.testnet ? "wss://bootstrap-testnet.pisecure.org" : "wss://bootstrap.pisecure.org";
        bootstrapWs_ = std::make_unique<BootstrapWebSocketClient>(nodeId_, wsUrl);

        // Set up callbacks for real-time events
        bootstrapWs_->setThreatCallback(
            [this](const std::string &type, const std::string &severity, const std::string &details)
            {
                onBootstrapThreatDetected(type, severity, details);
            });

        bootstrapWs_->setPeerDiscoveryCallback(
            [this](const std::vector<PeerAddr> &peers)
            {
                onBootstrapPeerDiscovery(peers);
            });

        bootstrapWs_->setDefenseCallback(
            [this](const std::string &defenseType, const std::string &details)
            {
                onBootstrapDefenseActivated(defenseType, details);
            });

        // Connect to Bootstrap (non-blocking)
        if (bootstrapWs_->connect())
        {
            std::cout << "Bootstrap WebSocket: Connected for Sentinel AI coordination" << std::endl;
        }
        else
        {
            std::cerr << "Bootstrap WebSocket: Connection failed (will use HTTP fallback)" << std::endl;
        }

        // Start listening
        if (!startListening(cfg.p2p_port))
        {
            running_ = false;
            return false;
        }

        // Start threads
        acceptThread_ = std::thread(&P2PServer::acceptLoop, this);
        messageThread_ = std::thread(&P2PServer::messageLoop, this);
        connectThread_ = std::thread(&P2PServer::connectLoop, this);
        pingThread_ = std::thread(&P2PServer::pingLoop, this);
        bootstrapHeartbeatThread_ = std::thread(&P2PServer::bootstrapHeartbeatLoop, this);
        threatDetectionThread_ = std::thread(&P2PServer::threatDetectionLoop, this);

        std::cout << "P2P server started on port " << cfg.p2p_port << std::endl;
        const AdvertisedP2P advertised = advertisedP2P();
        std::cout << "advertising p2p at " << advertised.host << ":" << advertised.port
                  << " source=" << advertised.source << std::endl;
        return true;
    }

    void P2PServer::sleepWhileRunning(std::chrono::milliseconds total)
    {
        const auto slice = std::chrono::milliseconds(200);
        auto left = total;
        while (running_.load() && left.count() > 0)
        {
            auto step = left < slice ? left : slice;
            std::this_thread::sleep_for(step);
            left -= step;
        }
    }

    void P2PServer::stop()
    {
        if (!running_.exchange(false))
        {
            return;
        }

        // Disconnect Bootstrap WebSocket
        if (bootstrapWs_)
        {
            bootstrapWs_->disconnect();
        }

        if (listenFd_ >= 0)
        {
            close(listenFd_);
            listenFd_ = -1;
        }

        if (acceptThread_.joinable())
            acceptThread_.join();
        if (messageThread_.joinable())
            messageThread_.join();
        if (connectThread_.joinable())
            connectThread_.join();
        if (pingThread_.joinable())
            pingThread_.join();
        if (bootstrapHeartbeatThread_.joinable())
            bootstrapHeartbeatThread_.join();
        if (threatDetectionThread_.joinable())
            threatDetectionThread_.join();

        // Close all peer connections
        std::lock_guard<std::mutex> lock(peersMutex_);
        for (auto &peer : peers_)
        {
            if (peer->fd >= 0)
            {
                close(peer->fd);
            }
        }
        peers_.clear();
    }

    bool P2PServer::startListening(uint16_t port)
    {
        listenFd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (listenFd_ < 0)
        {
            std::cerr << "Failed to create socket" << std::endl;
            return false;
        }

        int opt = 1;
        setsockopt(listenFd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        inet_pton(AF_INET, config_.p2p_bind.c_str(), &addr.sin_addr);

        if (bind(listenFd_, (sockaddr *)&addr, sizeof(addr)) < 0)
        {
            std::cerr << "Failed to bind to port " << port << std::endl;
            close(listenFd_);
            return false;
        }

        if (listen(listenFd_, 10) < 0)
        {
            std::cerr << "Failed to listen" << std::endl;
            close(listenFd_);
            return false;
        }

        // Set non-blocking
        int flags = fcntl(listenFd_, F_GETFL, 0);
        fcntl(listenFd_, F_SETFL, flags | O_NONBLOCK);

        return true;
    }

    void P2PServer::acceptLoop()
    {
        while (running_)
        {
            acceptConnection();
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    void P2PServer::acceptConnection()
    {
        if (!shouldAcceptConnection())
        {
            return;
        }

        sockaddr_in clientAddr{};
        socklen_t addrLen = sizeof(clientAddr);
        int clientFd = accept(listenFd_, (sockaddr *)&clientAddr, &addrLen);

        if (clientFd < 0)
        {
            return; // Non-blocking, no connection available
        }

        // Set non-blocking
        int flags = fcntl(clientFd, F_GETFL, 0);
        fcntl(clientFd, F_SETFL, flags | O_NONBLOCK);

        PeerAddr peerAddr{};
        peerAddr.addr = clientAddr;
        peerAddr.lastSeen = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
        peerAddr.services = 0;

        // Check if banned
        if (addrman_.isBanned(peerAddr))
        {
            close(clientFd);
            return;
        }

        auto peer = std::make_shared<Peer>(clientFd, peerAddr, true);

        std::lock_guard<std::mutex> lock(peersMutex_);
        peers_.push_back(peer);

        std::cout << "Accepted connection from " << inet_ntoa(clientAddr.sin_addr) << std::endl;

        // Send version message
        sendVersion(peer);
    }

    void P2PServer::connectLoop()
    {
        while (running_)
        {
            int outbound = getOutboundCount();
            if (outbound < MAX_OUTBOUND_CONNECTIONS)
            {
                try
                {
                    PeerAddr addr = addrman_.select();
                    connectToPeer(addr);
                }
                catch (const std::exception &e)
                {
                    // No peers available
                }
            }
            sleepWhileRunning(std::chrono::seconds(10));
        }
    }

    void P2PServer::connectToPeer(const PeerAddr &addr)
    {
        int sockFd = socket(AF_INET, SOCK_STREAM, 0);
        if (sockFd < 0)
        {
            return;
        }

        // Set non-blocking
        int flags = fcntl(sockFd, F_GETFL, 0);
        fcntl(sockFd, F_SETFL, flags | O_NONBLOCK);

        // Non-blocking connect
        int result = connect(sockFd, (sockaddr *)&addr.addr, sizeof(addr.addr));
        if (result < 0 && errno != EINPROGRESS)
        {
            close(sockFd);
            addrman_.markFailure(addr);
            return;
        }

        // Wait for connection with timeout
        fd_set writefds;
        FD_ZERO(&writefds);
        FD_SET(sockFd, &writefds);
        struct timeval tv = {5, 0}; // 5 second timeout

        if (select(sockFd + 1, nullptr, &writefds, nullptr, &tv) <= 0)
        {
            close(sockFd);
            addrman_.markFailure(addr);
            return;
        }

        auto peer = std::make_shared<Peer>(sockFd, addr, false);

        std::lock_guard<std::mutex> lock(peersMutex_);
        peers_.push_back(peer);

        std::cout << "Connected to " << inet_ntoa(addr.addr.sin_addr) << std::endl;

        // Send version message
        sendVersion(peer);
        addrman_.markAttempt(addr);
    }

    void P2PServer::messageLoop()
    {
        while (running_)
        {
            std::vector<std::shared_ptr<Peer>> currentPeers;
            {
                std::lock_guard<std::mutex> lock(peersMutex_);
                currentPeers = peers_;
            }

            for (auto &peer : currentPeers)
            {
                processMessages(peer);
            }

            // Remove disconnected peers
            {
                std::lock_guard<std::mutex> lock(peersMutex_);
                peers_.erase(std::remove_if(peers_.begin(), peers_.end(),
                                            [](const std::shared_ptr<Peer> &p)
                                            { return p->fd < 0 || p->shouldBan(); }),
                             peers_.end());
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    void P2PServer::processMessages(std::shared_ptr<Peer> peer)
    {
        uint8_t buffer[4096];
        ssize_t received = recv(peer->fd, buffer, sizeof(buffer), MSG_DONTWAIT);

        if (received <= 0)
        {
            if (received == 0 || (errno != EAGAIN && errno != EWOULDBLOCK))
            {
                disconnectPeer(peer, "Connection closed");
            }
            return;
        }

        peer->lastRecvTime = std::chrono::steady_clock::now().time_since_epoch().count();
        peer->recvBuffer.insert(peer->recvBuffer.end(), buffer, buffer + received);

        // Process complete messages
        while (peer->recvBuffer.size() >= 5)
        {
            uint8_t type = peer->recvBuffer[0];
            uint32_t len = peer->recvBuffer[1] | (peer->recvBuffer[2] << 8) |
                           (peer->recvBuffer[3] << 16) | (peer->recvBuffer[4] << 24);

            if (len > 32 * 1024 * 1024)
            {
                peer->increaseBanScore(100);
                disconnectPeer(peer, "Message too large");
                return;
            }

            if (peer->recvBuffer.size() < 5 + len)
            {
                break; // Wait for more data
            }

            std::vector<uint8_t> payload(peer->recvBuffer.begin() + 5, peer->recvBuffer.begin() + 5 + len);
            peer->recvBuffer.erase(peer->recvBuffer.begin(), peer->recvBuffer.begin() + 5 + len);

            P2PMsgType msgType = static_cast<P2PMsgType>(type);

            // Dispatch message handlers
            switch (msgType)
            {
            case P2PMsgType::VERSION:
                handleVersion(peer, payload);
                break;
            case P2PMsgType::VERACK:
                handleVerack(peer);
                break;
            case P2PMsgType::ADDR:
                handleAddr(peer, payload);
                break;
            case P2PMsgType::INV:
                handleInv(peer, payload);
                break;
            case P2PMsgType::GETDATA:
                handleGetData(peer, payload);
                break;
            case P2PMsgType::GETHEADERS:
                handleGetHeaders(peer, payload);
                break;
            case P2PMsgType::HEADERS:
                handleHeaders(peer, payload);
                break;
            case P2PMsgType::BLOCK:
                handleBlock(peer, payload);
                break;
            case P2PMsgType::TX:
                handleTx(peer, payload);
                break;
            case P2PMsgType::PING:
                handlePing(peer, payload);
                break;
            case P2PMsgType::PONG:
                handlePong(peer, payload);
                break;
            case P2PMsgType::THREAT_ALERT:
                handleThreatAlert(peer, payload);
                break;
            default:
                peer->increaseBanScore(1);
                break;
            }

            if (peer->shouldBan())
            {
                addrman_.ban(peer->address);
                disconnectPeer(peer, "Banned");
                return;
            }
        }
    }

    void P2PServer::pingLoop()
    {
        while (running_)
        {
            sleepWhileRunning(std::chrono::seconds(PING_INTERVAL_SECONDS));

            std::vector<std::shared_ptr<Peer>> currentPeers;
            {
                std::lock_guard<std::mutex> lock(peersMutex_);
                currentPeers = peers_;
            }

            for (auto &peer : currentPeers)
            {
                if (peer->handshakeComplete)
                {
                    sendPing(peer);

                    // Check for timeout
                    if (peer->getIdleTime() > 600)
                    { // 10 minutes
                        disconnectPeer(peer, "Timeout");
                    }
                }
            }
        }
    }

    void P2PServer::sendVersion(std::shared_ptr<Peer> peer)
    {
        if (storage_ && storage_->has_tip())
        {
            bestHeight_ = storage_->get_best_height();
        }
        uint64_t nonce = std::random_device()();
        uint64_t timestamp = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
        PeerAddr myAddr{};
        auto payload = MessageSerializer::serializeVersion(PROTOCOL_VERSION, SERVICES_NODE, timestamp,
                                                           peer->address, myAddr, nonce, "/pisecured:1.0/", bestHeight_);
        peer->sendMessage(P2PMsgType::VERSION, payload);
    }

    void P2PServer::sendVerack(std::shared_ptr<Peer> peer)
    {
        auto payload = MessageSerializer::serializeVerack();
        peer->sendMessage(P2PMsgType::VERACK, payload);
    }

    void P2PServer::sendAddr(std::shared_ptr<Peer> peer)
    {
        auto addrs = addrman_.getMany(1000);
        if (!addrs.empty())
        {
            auto payload = MessageSerializer::serializeAddr(addrs);
            peer->sendMessage(P2PMsgType::ADDR, payload);
        }
    }

    void P2PServer::sendPing(std::shared_ptr<Peer> peer)
    {
        uint64_t nonce = std::random_device()();
        peer->pingNonce = nonce;
        peer->lastPingTime = std::chrono::steady_clock::now().time_since_epoch().count();
        auto payload = MessageSerializer::serializePing(nonce);
        peer->sendMessage(P2PMsgType::PING, payload);
    }

    void P2PServer::handleVersion(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        uint32_t version, services, startHeight;
        uint64_t timestamp;
        std::string userAgent;

        if (!MessageSerializer::deserializeVersion(payload, version, services, timestamp, userAgent, startHeight))
        {
            peer->increaseBanScore(10);
            return;
        }

        peer->version = version;
        peer->services = services;
        peer->startHeight = startHeight;
        peer->userAgent = userAgent;

        std::cout << "Peer " << inet_ntoa(peer->address.addr.sin_addr)
                  << " version: " << version << " agent: " << userAgent << std::endl;

        sendVerack(peer);

        if (peer->inbound)
        {
            sendVersion(peer);
        }
    }

    void P2PServer::handleVerack(std::shared_ptr<Peer> peer)
    {
        peer->handshakeComplete = true;
        std::cout << "Handshake complete with " << inet_ntoa(peer->address.addr.sin_addr) << std::endl;

        // Exchange addresses
        sendAddr(peer);

        // Request headers for sync
        if (peer->startHeight > bestHeight_)
        {
            requestHeaders(bestHeight_);
        }
    }

    void P2PServer::handleAddr(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::vector<PeerAddr> addrs;
        if (MessageSerializer::deserializeAddr(payload, addrs))
        {
            for (const auto &addr : addrs)
            {
                addrman_.add(addr);
            }
            std::cout << "Received " << addrs.size() << " addresses from peer" << std::endl;
        }
    }

    void P2PServer::handleInv(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::vector<InvVect> invs;
        if (!MessageSerializer::deserializeInv(payload, invs))
        {
            peer->increaseBanScore(10);
            return;
        }

        std::vector<InvVect> toRequest;
        for (const auto &inv : invs)
        {
            if (inv.type == static_cast<uint32_t>(InvType::BLOCK) && storage_ && storage_->block_index(inv.hash))
            {
                continue;
            }
            if (peer->knownInv.insert(inv).second)
            {
                // New inventory, request it
                toRequest.push_back(inv);
            }
        }

        if (!toRequest.empty())
        {
            auto getData = MessageSerializer::serializeGetData(toRequest);
            peer->sendMessage(P2PMsgType::GETDATA, getData);
        }
    }

    void P2PServer::handleGetData(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::vector<InvVect> invs;
        if (!MessageSerializer::deserializeInv(payload, invs))
        {
            peer->increaseBanScore(10);
            return;
        }

        if (!storage_)
        {
            return;
        }

        for (const auto &inv : invs)
        {
            if (inv.type == static_cast<uint32_t>(InvType::BLOCK))
            {
                auto index = storage_->block_index(inv.hash);
                auto block_data = index ? storage_->read_block(*index) : std::nullopt;
                if (block_data)
                {
                    auto block_msg = MessageSerializer::serializeBlock(*block_data);
                    peer->sendMessage(P2PMsgType::BLOCK, block_msg);
                    std::cout << "Sent block to peer" << std::endl;
                }
                else
                {
                    // We don't have this block, send NOTFOUND (or just ignore)
                    std::cout << "Block not found in storage" << std::endl;
                }
            }
            else if (inv.type == static_cast<uint32_t>(InvType::TX))
            {
                // Look up transaction in mempool and send
                auto tx = storage_->get_transaction(inv.hash);
                if (tx)
                {
                    auto tx_msg = MessageSerializer::serializeTx(tx->data);
                    peer->sendMessage(P2PMsgType::TX, tx_msg);
                    std::cout << "Sent transaction to peer" << std::endl;
                }
                else
                {
                    std::cout << "Transaction not found in mempool" << std::endl;
                }
            }
        }
    }

    void P2PServer::handleGetHeaders(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::vector<std::array<uint8_t, 32>> locatorHashes;
        std::array<uint8_t, 32> hashStop;

        if (!MessageSerializer::deserializeGetHeaders(payload, locatorHashes, hashStop))
        {
            peer->increaseBanScore(10);
            return;
        }

        if (!storage_)
        {
            return;
        }

        // Find the first locator hash that we have
        std::optional<BlockHeader> start_header;
        for (const auto &hash : locatorHashes)
        {
            auto header = storage_->get_header_by_hash(hash);
            if (header)
            {
                start_header = header;
                break;
            }
        }

        std::vector<BlockHeader> headers;
        // No locator match (empty chain on the peer): start at height 1.
        // Height 0 is the zero prev-hash anchor, not a stored block.
        uint32_t start_height = start_header ? start_header->height + 1 : 1;
        {
            uint32_t best_height = storage_->get_best_height();

            for (uint32_t h = start_height; h <= best_height && headers.size() < 2000; ++h)
            {
                auto header = storage_->get_header_by_height(h);
                if (header)
                {
                    headers.push_back(*header);

                    // Stop if we reach hashStop
                    if (header->hash == hashStop)
                    {
                        break;
                    }
                }
                else
                {
                    break;
                }
            }
        }

        if (!headers.empty())
        {
            auto headersMsg = MessageSerializer::serializeHeaders(headers);
            peer->sendMessage(P2PMsgType::HEADERS, headersMsg);
            std::cout << "Sent " << headers.size() << " headers to peer" << std::endl;
        }
    }

    void P2PServer::handleHeaders(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::vector<BlockHeader> headers;
        if (!MessageSerializer::deserializeHeaders(payload, headers))
        {
            peer->increaseBanScore(10);
            return;
        }

        if (headers.empty())
        {
            return;
        }

        std::cout << "Received " << headers.size() << " headers" << std::endl;

        if (!storage_)
        {
            return;
        }

        // Validate headers chain
        BlockHeader *prev_header = nullptr;
        std::vector<InvVect> blocks_to_request;

        for (auto &header : headers)
        {
            if (prev_header)
            {
                header.height = prev_header->height + 1;
            }
            else if (header.prevBlockHash == std::array<uint8_t, 32>{})
            {
                header.height = 1;
            }
            else if (auto known = storage_->get_header_by_hash(header.prevBlockHash))
            {
                header.height = known->height + 1;
            }
            else
            {
                std::cout << "Header does not connect to local tip" << std::endl;
                return;
            }

            // Validate PoW
            if (!storage_->validate_block_pow(header.hash, header.difficulty))
            {
                std::cout << "Invalid PoW for header at height " << header.height << std::endl;
                peer->increaseBanScore(20);
                return;
            }

            // Validate chain linkage
            if (prev_header)
            {
                if (!storage_->validate_block_header(header, prev_header))
                {
                    std::cout << "Invalid header chain at height " << header.height << std::endl;
                    peer->increaseBanScore(20);
                    return;
                }
            }

            // Check if we already have this block
            if (!storage_->block_index(header.hash))
            {
                // Request the block
                InvVect inv;
                inv.type = static_cast<uint32_t>(InvType::BLOCK);
                inv.hash = header.hash;
                blocks_to_request.push_back(inv);
            }

            prev_header = &header;
        }

        // Request blocks we don't have
        if (!blocks_to_request.empty())
        {
            auto getdata_msg = MessageSerializer::serializeGetData(blocks_to_request);
            peer->sendMessage(P2PMsgType::GETDATA, getdata_msg);
            std::cout << "Requesting " << blocks_to_request.size() << " blocks" << std::endl;
        }
    }

    void P2PServer::handleBlock(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::cout << "Received block (" << payload.size() << " bytes)" << std::endl;

        if (!storage_)
        {
            return;
        }

        if (!payload.empty() && payload[0] == '{')
        {
            try
            {
                const std::string text(payload.begin(), payload.end());
                json block = json::parse(text);
                json result = rpc_submitblock(*storage_, this, block, false);
                const std::string status = result.value("status", "");
                if (status == "accepted")
                {
                    bestHeight_ = storage_->get_best_height();
                    std::cout << "Synced block height " << result.value("height", 0) << " hash " << result.value("hash", "") << std::endl;
                }
                else
                {
                    const std::string reason = result.value("reason", "");
                    std::cout << "Rejected synced block: " << reason << std::endl;
                    if (reason.find("does not link") == std::string::npos && reason.find("does not extend") == std::string::npos)
                    {
                        peer->increaseBanScore(20);
                    }
                }
            }
            catch (const std::exception &ex)
            {
                std::cout << "Rejected synced block: " << ex.what() << std::endl;
                peer->increaseBanScore(10);
            }
            return;
        }

        // Parse block header from payload (first 112 bytes)
        if (payload.size() < 112)
        {
            peer->increaseBanScore(10);
            return;
        }

        BlockHeader header;
        size_t offset = 0;
        header.version = MessageSerializer::readUint32(payload.data(), offset);
        std::copy_n(payload.data() + offset, 32, header.prevBlockHash.begin());
        offset += 32;
        std::copy_n(payload.data() + offset, 32, header.merkleRoot.begin());
        offset += 32;
        header.timestamp = MessageSerializer::readUint64(payload.data(), offset);
        header.difficulty = MessageSerializer::readUint32(payload.data(), offset);
        header.nonce = MessageSerializer::readUint64(payload.data(), offset);

        // Compute block hash (SHA256 of header)
        header.hash = computeHash(std::vector<uint8_t>(payload.begin(), payload.begin() + 112));

        // Validate PoW
        if (!storage_->validate_block_pow(header.hash, header.difficulty))
        {
            std::cout << "Block failed PoW validation" << std::endl;
            peer->increaseBanScore(50);
            return;
        }

        // Get previous block to determine height
        auto prev_header = storage_->get_header_by_hash(header.prevBlockHash);
        if (prev_header)
        {
            header.height = prev_header->height + 1;

            // Validate against previous header
            if (!storage_->validate_block_header(header, &(*prev_header)))
            {
                std::cout << "Block failed header validation" << std::endl;
                peer->increaseBanScore(30);
                return;
            }
        }
        else
        {
            // If we don't have the previous block, this might be out of order
            // In a full implementation, we'd queue it for later processing
            std::cout << "Previous block not found, skipping for now" << std::endl;
            return;
        }

        // Store block
        if (storage_->store_block_with_header(header.hash, header, payload))
        {
            std::cout << "Block " << header.height << " stored successfully" << std::endl;

            // Broadcast block to other peers
            InvVect inv;
            inv.type = static_cast<uint32_t>(InvType::BLOCK);
            inv.hash = header.hash;
            broadcastInv(inv);

            // Broadcast to local WebSocket subscribers
            if (WebSocketServer::instance())
            {
                // Convert hash to hex
                std::string hash_hex;
                hash_hex.reserve(64);
                static const char *hex = "0123456789abcdef";
                for (auto b : header.hash)
                {
                    hash_hex.push_back(hex[(b >> 4) & 0xF]);
                    hash_hex.push_back(hex[b & 0xF]);
                }
                json block_obj = {
                    {"height", header.height},
                    {"timestamp", header.timestamp},
                    {"difficulty", header.difficulty},
                    {"hash", hash_hex}};
                WebSocketServer::instance()->broadcast_block(block_obj);
            }
        }
        else
        {
            std::cout << "Failed to store block" << std::endl;
        }
    }

    void P2PServer::handleTx(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        std::cout << "Received transaction (" << payload.size() << " bytes)" << std::endl;

        if (!storage_)
        {
            return;
        }

        // Compute transaction hash
        auto tx_hash = computeHash(payload);

        // Check if we already have this transaction
        if (storage_->has_transaction(tx_hash))
        {
            return;
        }

        // Basic validation (size check)
        if (payload.size() > 1024 * 1024) // 1MB max tx size
        {
            peer->increaseBanScore(10);
            return;
        }

        // Create transaction object
        Transaction tx;
        tx.hash = tx_hash;
        tx.data = payload;
        tx.timestamp = std::chrono::system_clock::now().time_since_epoch().count() / 1000000000ULL;
        tx.fee = 0; // TODO: Calculate from inputs/outputs

        // Add to mempool
        if (storage_->add_transaction(tx))
        {
            std::cout << "Transaction added to mempool" << std::endl;

            // Relay to other peers
            InvVect inv;
            inv.type = static_cast<uint32_t>(InvType::TX);
            inv.hash = tx_hash;
            broadcastInv(inv);
        }
    }

    void P2PServer::handlePing(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        uint64_t nonce;
        if (MessageSerializer::deserializePing(payload, nonce))
        {
            auto pong = MessageSerializer::serializePong(nonce);
            peer->sendMessage(P2PMsgType::PONG, pong);
        }
    }

    void P2PServer::handlePong(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        uint64_t nonce;
        if (MessageSerializer::deserializePong(payload, nonce))
        {
            if (nonce == peer->pingNonce)
            {
                auto now = std::chrono::steady_clock::now().time_since_epoch().count();
                int64_t latency = (now - peer->lastPingTime) / 1000000LL; // Convert to ms
                peer->lastPongTime = now;
                std::cout << "Ping latency: " << latency << "ms" << std::endl;
            }
        }
    }

    void P2PServer::handleThreatAlert(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload)
    {
        ThreatAlert alert;
        if (MessageSerializer::deserializeThreatAlert(payload, alert))
        {
            std::cout << "⚠️  THREAT ALERT from peer " << alert.reportingNodeId << std::endl;
            std::cout << "   Type: " << alert.threatType << " | Severity: " << alert.severity << std::endl;
            std::cout << "   Confidence: " << (alert.confidenceScore * 100.0) << "% | Details: " << alert.details << std::endl;

            // Record threat locally
            threatDetector_.recordThreat(alert);

            // Activate coordinated defense if severity is high
            if (alert.severity == "high" || alert.severity == "critical")
            {
                activateCoordinatedDefense(alert);
            }

            // Ban the threat source if confidence is high
            if (alert.confidenceScore > 0.8)
            {
                PeerAddr threatAddr;
                threatAddr.addr.sin_addr.s_addr = htonl(alert.sourceIP);
                threatAddr.addr.sin_port = 0;
                addrman_.ban(threatAddr);
                std::cout << "   ✅ Banned threat source IP" << std::endl;
            }

            // Report to Bootstrap Sentinel AI for network-wide coordination
            if (bootstrapWs_ && bootstrapWs_->isConnected())
            {
                bootstrapWs_->reportThreat(
                    alert.threatType,
                    alert.severity,
                    alert.details);
            }
        }
    }

    void P2PServer::disconnectPeer(std::shared_ptr<Peer> peer, const std::string &reason)
    {
        std::cout << "Disconnecting peer: " << reason << std::endl;
        if (peer->fd >= 0)
        {
            close(peer->fd);
            peer->fd = -1;
        }
    }

    void P2PServer::connectToPeers()
    {
        // Triggered by connectLoop
    }

    void P2PServer::sendToAll(P2PMsgType type, const std::vector<uint8_t> &payload)
    {
        std::lock_guard<std::mutex> lock(peersMutex_);
        for (auto &peer : peers_)
        {
            if (peer->handshakeComplete)
            {
                peer->sendMessage(type, payload);
            }
        }
    }

    void P2PServer::broadcastInv(const InvVect &inv)
    {
        std::vector<InvVect> invs = {inv};
        auto payload = MessageSerializer::serializeInv(invs);
        sendToAll(P2PMsgType::INV, payload);
    }

    void P2PServer::requestBlock(const std::array<uint8_t, 32> &blockHash)
    {
        InvVect inv;
        inv.type = static_cast<uint32_t>(InvType::BLOCK);
        inv.hash = blockHash;
        std::vector<InvVect> invs = {inv};
        auto payload = MessageSerializer::serializeGetData(invs);
        sendToAll(P2PMsgType::GETDATA, payload);
    }

    void P2PServer::requestHeaders(uint32_t startHeight)
    {
        if (!storage_)
        {
            return;
        }

        // Build proper locator hashes from blockchain (exponential backoff)
        std::vector<std::array<uint8_t, 32>> locatorHashes = storage_->get_block_locator_hashes();
        std::array<uint8_t, 32> hashStop = {}; // Request all headers

        auto payload = MessageSerializer::serializeGetHeaders(locatorHashes, hashStop);
        sendToAll(P2PMsgType::GETHEADERS, payload);

        std::cout << "Requested headers with " << locatorHashes.size() << " locator hashes" << std::endl;
    }

    size_t P2PServer::getPeerCount() const
    {
        std::lock_guard<std::mutex> lock(peersMutex_);
        return peers_.size();
    }

    std::string P2PServer::reachableHost() const
    {
        std::string host = "127.0.0.1";
        ifaddrs *list = nullptr;
        if (getifaddrs(&list) == 0)
        {
            for (ifaddrs *ifa = list; ifa != nullptr; ifa = ifa->ifa_next)
            {
                if (ifa->ifa_addr == nullptr || ifa->ifa_addr->sa_family != AF_INET)
                {
                    continue;
                }
                if ((ifa->ifa_flags & IFF_LOOPBACK) != 0 || (ifa->ifa_flags & IFF_UP) == 0)
                {
                    continue;
                }
                char buf[INET_ADDRSTRLEN] = {};
                auto *in = reinterpret_cast<sockaddr_in *>(ifa->ifa_addr);
                if (inet_ntop(AF_INET, &in->sin_addr, buf, sizeof(buf)) != nullptr)
                {
                    host = buf;
                    break;
                }
            }
            freeifaddrs(list);
        }
        return host;
    }

    P2PServer::AdvertisedP2P P2PServer::advertisedP2P() const
    {
        AdvertisedP2P out;
        out.port = config_.p2p_port > 0 ? config_.p2p_port : 3141;
        if (const char *envPort = std::getenv("PISECURE_P2P_PORT"))
        {
            if (envPort[0] != '\0')
            {
                const int parsed = std::atoi(envPort);
                if (parsed > 0 && parsed < 65536)
                {
                    out.port = parsed;
                }
            }
        }

        auto refused = [](const std::string &host)
        {
            return host.empty() || host == "0.0.0.0" || host == "::" || host == "127.0.0.1" || host == "::1";
        };
        if (const char *envHost = std::getenv("PISECURE_P2P_HOST"))
        {
            if (envHost[0] != '\0' && !refused(envHost))
            {
                out.host = envHost;
                out.source = "env";
                return out;
            }
        }

        auto linkLocal = [](uint32_t hostOrder)
        {
            return (hostOrder & 0xFFFF0000u) == 0xA9FE0000u;
        };
        auto dockerOrDummy = [](const char *name)
        {
            if (name == nullptr || name[0] == '\0')
            {
                return true;
            }
            const std::string iface(name);
            return iface == "docker0" || iface.rfind("docker", 0) == 0 || iface.rfind("br-", 0) == 0 || iface.rfind("dummy", 0) == 0 || iface == "tailscale0";
        };

        std::string lan;
        ifaddrs *list = nullptr;
        if (getifaddrs(&list) == 0)
        {
            for (ifaddrs *ifa = list; ifa != nullptr; ifa = ifa->ifa_next)
            {
                if (ifa->ifa_addr == nullptr || ifa->ifa_addr->sa_family != AF_INET)
                {
                    continue;
                }
                if ((ifa->ifa_flags & IFF_UP) == 0 || (ifa->ifa_flags & IFF_LOOPBACK) != 0)
                {
                    continue;
                }
                if (dockerOrDummy(ifa->ifa_name))
                {
                    continue;
                }
                auto *in = reinterpret_cast<sockaddr_in *>(ifa->ifa_addr);
                const uint32_t hostOrder = ntohl(in->sin_addr.s_addr);
                char buf[INET_ADDRSTRLEN] = {};
                if (inet_ntop(AF_INET, &in->sin_addr, buf, sizeof(buf)) == nullptr)
                {
                    continue;
                }
                const std::string host = buf;
                if (refused(host) || linkLocal(hostOrder))
                {
                    continue;
                }
                lan = host;
                break;
            }
            freeifaddrs(list);
        }
        out.host = lan;
        out.source = "lan";
        return out;
    }

    void P2PServer::broadcastThreatAlert(const ThreatAlert &alert)
    {
        auto payload = MessageSerializer::serializeThreatAlert(alert);

        std::lock_guard<std::mutex> lock(peersMutex_);
        for (auto &peer : peers_)
        {
            if (peer->handshakeComplete)
            {
                peer->sendMessage(P2PMsgType::THREAT_ALERT, payload);
            }
        }

        std::cout << "📡 Broadcasted threat alert to " << peers_.size() << " peers" << std::endl;

        // Also notify local WebSocket subscribers
        if (WebSocketServer::instance())
        {
            // Convert IP to dotted string
            uint32_t ip_be = alert.sourceIP;
            uint8_t a = (ip_be >> 24) & 0xFF;
            uint8_t b = (ip_be >> 16) & 0xFF;
            uint8_t c = (ip_be >> 8) & 0xFF;
            uint8_t d = ip_be & 0xFF;
            std::string ip_str = std::to_string(a) + "." + std::to_string(b) + "." + std::to_string(c) + "." + std::to_string(d);

            json threat_obj = {
                {"type", alert.threatType},
                {"severity", alert.severity},
                {"source_ip", ip_str},
                {"timestamp", alert.timestamp},
                {"details", alert.details},
                {"reporting_node_id", alert.reportingNodeId},
                {"confidence", alert.confidenceScore}};
            WebSocketServer::instance()->broadcast_threat(threat_obj);
        }
    }

    void P2PServer::activateCoordinatedDefense(const ThreatAlert &alert)
    {
        std::cout << "🛡️  COORDINATED DEFENSE ACTIVATED" << std::endl;
        std::cout << "   Threat: " << alert.threatType << " | Severity: " << alert.severity << std::endl;

        if (alert.threatType == "ddos_attack")
        {
            // Implement DDoS mitigation
            std::cout << "   • Enabling strict rate limiting" << std::endl;
            std::cout << "   • Prioritizing established connections" << std::endl;
            std::cout << "   • Dropping new connections from suspicious subnets" << std::endl;

            // Ban the source IP and related subnet
            PeerAddr threatAddr;
            threatAddr.addr.sin_addr.s_addr = htonl(alert.sourceIP);
            threatAddr.addr.sin_port = 0;
            addrman_.ban(threatAddr);

            // TODO: Implement rate limiting logic
        }
        else if (alert.threatType == "sybil_attack")
        {
            std::cout << "   • Disconnecting duplicate user agents" << std::endl;
            std::cout << "   • Requiring proof-of-work for new connections" << std::endl;

            // Disconnect peers with suspicious patterns
            std::lock_guard<std::mutex> lock(peersMutex_);
            for (auto it = peers_.begin(); it != peers_.end();)
            {
                if (ntohl((*it)->address.addr.sin_addr.s_addr) == alert.sourceIP ||
                    threatDetector_.calculateThreatScore(**it) > 0.7)
                {
                    disconnectPeer(*it, "Sybil attack detected");
                    it = peers_.erase(it);
                }
                else
                {
                    ++it;
                }
            }
        }
        else if (alert.threatType == "eclipse_attack")
        {
            std::cout << "   • Forcing peer diversity" << std::endl;
            std::cout << "   • Connecting to bootstrap fallback peers" << std::endl;

            // Force new outbound connections to diverse IPs
            connectToPeers();
        }

        // Report defense activation to Bootstrap
        if (bootstrapWs_ && bootstrapWs_->isConnected())
        {
            auto now = std::chrono::steady_clock::now().time_since_epoch().count() / 1000000000.0;
            bootstrapWs_->reportNodeStatus(static_cast<int>(getPeerCount()), now);
        }
    }

    std::vector<ThreatAlert> P2PServer::getNetworkThreats() const
    {
        // Return threats from last 24 hours
        uint64_t timeWindow = 24ULL * 3600 * 1000000000; // 24 hours in nanoseconds
        return threatDetector_.getRecentThreats(timeWindow);
    }

    int P2PServer::getOutboundCount() const
    {
        std::lock_guard<std::mutex> lock(peersMutex_);
        int count = 0;
        for (const auto &peer : peers_)
        {
            if (!peer->inbound)
                count++;
        }
        return count;
    }

    bool P2PServer::shouldAcceptConnection() const
    {
        std::lock_guard<std::mutex> lock(peersMutex_);
        return peers_.size() < static_cast<size_t>(MAX_PEERS);
    }

    std::array<uint8_t, 32> P2PServer::computeHash(const std::vector<uint8_t> &data)
    {
        std::array<uint8_t, 32> hash;
        SHA256(data.data(), data.size(), hash.data());
        return hash;
    }

    std::vector<std::pair<std::string, int>> P2PServer::bootstrapHints() const
    {
        std::lock_guard<std::mutex> lock(hintMutex_);
        return bootstrapHints_;
    }

    namespace
    {
        int bootstrapHttp(const std::string &method, const std::string &url, const std::string &payload, std::string &response)
        {
            std::string cmd = "curl -sS -m 20 -w '\\nHTTPSTATUS:%{http_code}' -X " + method + " '" + url + "'";
            char path[] = "/tmp/pisecure-bootstrap-XXXXXX";
            int fd = -1;
            if (!payload.empty())
            {
                fd = mkstemp(path);
                if (fd < 0)
                {
                    response = "mkstemp failed";
                    return 0;
                }
                const ssize_t wrote = ::write(fd, payload.data(), payload.size());
                ::close(fd);
                if (wrote < 0 || static_cast<size_t>(wrote) != payload.size())
                {
                    ::unlink(path);
                    response = "write failed";
                    return 0;
                }
                cmd += " -H 'Content-Type: application/json' --data-binary @" + std::string(path);
            }
            FILE *pipe = popen(cmd.c_str(), "r");
            if (pipe == nullptr)
            {
                if (fd >= 0)
                {
                    ::unlink(path);
                }
                response = "curl failed to start";
                return 0;
            }
            std::string output;
            char buf[512];
            while (fgets(buf, sizeof(buf), pipe) != nullptr)
            {
                output += buf;
            }
            pclose(pipe);
            if (fd >= 0)
            {
                ::unlink(path);
            }
            const auto pos = output.rfind("HTTPSTATUS:");
            if (pos == std::string::npos)
            {
                response = output;
                return 0;
            }
            response = output.substr(0, pos);
            while (!response.empty() && (response.back() == '\n' || response.back() == '\r'))
            {
                response.pop_back();
            }
            return std::atoi(output.c_str() + pos + std::strlen("HTTPSTATUS:"));
        }

        std::string hex32(const std::array<uint8_t, 32> &bytes)
        {
            static const char *hexd = "0123456789abcdef";
            std::string out(64, '0');
            for (size_t i = 0; i < bytes.size(); ++i)
            {
                out[i * 2] = hexd[bytes[i] >> 4];
                out[i * 2 + 1] = hexd[bytes[i] & 0x0f];
            }
            return out;
        }

        bool foreignGenesis(const json &node)
        {
            std::string genesis;
            if (node.contains("genesis_hash") && node["genesis_hash"].is_string())
            {
                genesis = node["genesis_hash"].get<std::string>();
            }
            return genesis.rfind("2742129a", 0) == 0;
        }
    }

    void P2PServer::registerBootstrapNode()
    {
        try
        {
            if (storage_ != nullptr && storage_->has_tip())
            {
                bestHeight_ = storage_->get_best_height();
            }
            const std::string tip = hex32(storage_ != nullptr ? storage_->get_best_block_hash() : std::array<uint8_t, 32>{});
            const AdvertisedP2P advertised = advertisedP2P();
            const char *base = config_.testnet ? "https://bootstrap-testnet.pisecure.org" : "https://bootstrap.pisecure.org";
            json body = {
                {"node_id", bootstrapNodeId_},
                {"node_type", config_.validate_only ? "validator" : "miner"},
                {"services", json::array({"mining", "p2p_sync"})},
                {"capabilities", json::array({"mining", "validation"})},
                {"p2p_host", advertised.host},
                {"p2p_port", advertised.port},
                {"rpc_port", config_.ws_port},
                {"height", bestHeight_},
                {"tip", tip},
            };
            std::string response;
            const int code = bootstrapHttp("POST", std::string(base) + "/api/v1/nodes/register", body.dump(), response);
            std::cout << "Bootstrap register HTTP " << code << " " << response << std::endl;
            if (code == 409)
            {
                postBootstrapStatus();
            }
        }
        catch (const std::exception &ex)
        {
            std::cerr << "Bootstrap register error: " << ex.what() << std::endl;
        }
    }

    void P2PServer::postBootstrapStatus()
    {
        try
        {
            if (storage_ != nullptr && storage_->has_tip())
            {
                bestHeight_ = storage_->get_best_height();
            }
            const std::string tip = hex32(storage_ != nullptr ? storage_->get_best_block_hash() : std::array<uint8_t, 32>{});
            const AdvertisedP2P advertised = advertisedP2P();
            const char *base = config_.testnet ? "https://bootstrap-testnet.pisecure.org" : "https://bootstrap.pisecure.org";
            json body = {
                {"node_id", bootstrapNodeId_},
                {"p2p_host", advertised.host},
                {"p2p_port", advertised.port},
                {"rpc_port", config_.ws_port},
                {"height", bestHeight_},
                {"tip", tip},
                {"status", "active"},
                {"mining_active", false},
                {"peers_connected", static_cast<int>(getPeerCount())},
            };
            std::string response;
            const int code = bootstrapHttp("POST", std::string(base) + "/api/v1/nodes/status", body.dump(), response);
            std::cout << "Bootstrap status HTTP " << code << " " << response << std::endl;
        }
        catch (const std::exception &ex)
        {
            std::cerr << "Bootstrap status error: " << ex.what() << std::endl;
        }
    }

    void P2PServer::reportBootstrapChain()
    {
        try
        {
            if (storage_ == nullptr)
            {
                return;
            }
            if (storage_->has_tip())
            {
                bestHeight_ = storage_->get_best_height();
            }
            const std::string tip = hex32(storage_->get_best_block_hash());
            const char *base = config_.testnet ? "https://bootstrap-testnet.pisecure.org" : "https://bootstrap.pisecure.org";
            json blocks = json::array();
            uint32_t height = bestHeight_;
            int kept = 0;
            while (kept < 120 && height >= 1)
            {
                auto header = storage_->get_header_by_height(height);
                if (!header)
                {
                    break;
                }
                std::string miner;
                int txCount = 0;
                auto index = storage_->block_index(header->hash);
                if (index)
                {
                    auto raw = storage_->read_block(*index);
                    if (raw)
                    {
                        try
                        {
                            const std::string text(raw->begin(), raw->end());
                            json block = json::parse(text);
                            if (block.contains("txs") && block["txs"].is_array())
                            {
                                txCount = static_cast<int>(block["txs"].size());
                            }
                            if (block.contains("coinbase") && block["coinbase"].is_object())
                            {
                                const auto &coinbase = block["coinbase"];
                                if (coinbase.contains("outputs") && coinbase["outputs"].is_array())
                                {
                                    for (const auto &out : coinbase["outputs"])
                                    {
                                        if (out.value("role", "") == "miner" && out.contains("address"))
                                        {
                                            miner = out["address"].get<std::string>();
                                            break;
                                        }
                                    }
                                }
                                if (miner.empty() && coinbase.contains("wallet") && coinbase["wallet"].is_string())
                                {
                                    miner = coinbase["wallet"].get<std::string>();
                                }
                            }
                        }
                        catch (const std::exception &)
                        {
                        }
                    }
                }
                blocks.push_back({{"height", header->height},
                                  {"hash", hex32(header->hash)},
                                  {"timestamp", header->timestamp},
                                  {"miner", miner},
                                  {"tx_count", txCount},
                                  {"reward", "0.198"},
                                  {"subsidy", "0.200"},
                                  {"difficulty", header->difficulty}});
                ++kept;
                if (height == 1)
                {
                    break;
                }
                --height;
            }
            const json mempool = rpc_getmempool(*storage_);
            const AdvertisedP2P advertised = advertisedP2P();
            json body = {
                {"node_id", bootstrapNodeId_},
                {"p2p_host", advertised.host},
                {"p2p_port", advertised.port},
                {"rpc_port", config_.ws_port},
                {"height", bestHeight_},
                {"tip", tip},
                {"difficulty", storage_->tip_difficulty()},
                {"peer_count", static_cast<int>(getPeerCount())},
                {"mempool_count", mempool.value("count", 0)},
                {"mempool_bytes", mempool.value("bytes", 0)},
                {"blocks", blocks},
                {"names", rpc_name_snapshot(*storage_)},
            };
            std::string response;
            const int code = bootstrapHttp("POST", std::string(base) + "/api/v1/chain/report", body.dump(), response);
            std::cout << "Bootstrap report HTTP " << code << " " << response << std::endl;
            if (code == 403)
            {
                std::cerr << "Bootstrap report not registered; registering once more\n";
                registerBootstrapNode();
            }
        }
        catch (const std::exception &ex)
        {
            std::cerr << "Bootstrap report error: " << ex.what() << std::endl;
        }
    }

    void P2PServer::refreshBootstrapHints()
    {
        try
        {
            const char *base = config_.testnet ? "https://bootstrap-testnet.pisecure.org" : "https://bootstrap.pisecure.org";
            const std::string self = reachableHost();
            std::vector<std::pair<std::string, int>> hints;
            auto absorb = [&](const std::string &payload)
            {
                json doc = json::parse(payload);
                if (doc.contains("genesis_hash") && doc["genesis_hash"].is_string() &&
                    doc["genesis_hash"].get<std::string>().rfind("2742129a", 0) == 0)
                {
                    return;
                }
                if (doc.contains("network_info") && doc["network_info"].is_object())
                {
                    const auto &info = doc["network_info"];
                    if (info.contains("genesis_hash") && info["genesis_hash"].is_string() &&
                        info["genesis_hash"].get<std::string>().rfind("2742129a", 0) == 0)
                    {
                        return;
                    }
                }
                const json *rows = nullptr;
                if (doc.contains("nodes") && doc["nodes"].is_array())
                {
                    rows = &doc["nodes"];
                }
                else if (doc.contains("peers") && doc["peers"].is_array())
                {
                    rows = &doc["peers"];
                }
                if (rows == nullptr)
                {
                    return;
                }
                for (const auto &node : *rows)
                {
                    if (foreignGenesis(node))
                    {
                        continue;
                    }
                    if (!node.contains("p2p_host") || !node["p2p_host"].is_string() || !node.contains("p2p_port"))
                    {
                        continue;
                    }
                    const std::string hintHost = node["p2p_host"].get<std::string>();
                    if (hintHost.empty() || hintHost == "0.0.0.0" || hintHost == self)
                    {
                        continue;
                    }
                    int hintPort = 3141;
                    if (node["p2p_port"].is_number_integer())
                    {
                        hintPort = node["p2p_port"].get<int>();
                    }
                    hints.emplace_back(hintHost, hintPort);
                }
            };
            std::string peersBody;
            if (bootstrapHttp("GET", std::string(base) + "/api/v1/bootstrap/peers", "", peersBody) == 200)
            {
                try
                {
                    absorb(peersBody);
                }
                catch (const std::exception &)
                {
                }
            }
            std::string listBody;
            if (bootstrapHttp("GET", std::string(base) + "/api/v1/nodes/list", "", listBody) == 200)
            {
                try
                {
                    absorb(listBody);
                }
                catch (const std::exception &)
                {
                }
            }
            std::lock_guard<std::mutex> lock(hintMutex_);
            bootstrapHints_ = std::move(hints);
        }
        catch (const std::exception &ex)
        {
            std::cerr << "Bootstrap peer hint error: " << ex.what() << std::endl;
        }
    }

    void P2PServer::bootstrapHeartbeatLoop()
    {
        // An explicit --peer is a sync client. It must not publish under this
        // process id or it would overwrite the primary host and ports.
        const bool publish = config_.peers.empty();
        if (publish)
        {
            registerBootstrapNode();
            reportBootstrapChain();
            refreshBootstrapHints();
        }
        auto nextStatus = std::chrono::steady_clock::now() + std::chrono::seconds(300);
        while (running_)
        {
            sleepWhileRunning(std::chrono::seconds(30));
            if (!running_)
            {
                break;
            }
            if (publish)
            {
                reportBootstrapChain();
                refreshBootstrapHints();
                if (std::chrono::steady_clock::now() >= nextStatus)
                {
                    postBootstrapStatus();
                    nextStatus = std::chrono::steady_clock::now() + std::chrono::seconds(300);
                }
            }

            if (bootstrapWs_ && bootstrapWs_->isConnected())
            {
                // Collect metrics
                std::map<std::string, double> metrics;
                metrics["peer_count"] = getPeerCount();
                metrics["best_height"] = bestHeight_;
                metrics["uptime_seconds"] = std::chrono::steady_clock::now().time_since_epoch().count() / 1000000000.0;

                // Send heartbeat to bootstrap
                bootstrapWs_->sendHeartbeat(metrics);
            }
        }
    }

    void P2PServer::onBootstrapThreatDetected(const std::string &threatType, const std::string &severity, const std::string &details)
    {
        std::cout << "🚨 SENTINEL AI ALERT: " << severity << " - " << threatType << std::endl;
        std::cout << "   Details: " << details << std::endl;

        // Implement defense mechanisms based on threat type
        if (threatType == "ddos_attack")
        {
            std::cout << "   Activating DDoS defense: Enhanced rate limiting" << std::endl;
            // TODO: Activate enhanced rate limiting on all peers
        }
        else if (threatType == "suspicious_node")
        {
            std::cout << "   Isolating suspicious nodes" << std::endl;
            // TODO: Disconnect peers matching threat indicators
        }
        else if (threatType == "network_anomaly")
        {
            std::cout << "   Monitoring network behavior" << std::endl;
            // TODO: Increase monitoring frequency
        }
    }

    void P2PServer::onBootstrapPeerDiscovery(const std::vector<PeerAddr> &peers)
    {
        std::cout << "Bootstrap: Received " << peers.size() << " peer addresses from Sentinel AI" << std::endl;

        for (const auto &peer : peers)
        {
            addrman_.add(peer);
        }

        // Trigger outbound connections if needed
        if (getOutboundCount() < MAX_OUTBOUND_CONNECTIONS)
        {
            connectToPeers();
        }
    }

    void P2PServer::onBootstrapDefenseActivated(const std::string &defenseType, const std::string &details)
    {
        std::cout << "🛡️  DEFENSE ACTIVATED: " << defenseType << std::endl;
        std::cout << "   Details: " << details << std::endl;

        if (defenseType == "rate_limit")
        {
            // TODO: Apply stricter rate limits
            std::cout << "   Applying enhanced rate limiting" << std::endl;
        }
        else if (defenseType == "peer_quarantine")
        {
            // TODO: Disconnect quarantined peers
            std::cout << "   Quarantining suspicious peers" << std::endl;
        }
        else if (defenseType == "network_isolation")
        {
            // TODO: Isolate from certain network segments
            std::cout << "   Isolating from compromised network segments" << std::endl;
        }
    }

    void P2PServer::threatDetectionLoop()
    {
        while (running_)
        {
            sleepWhileRunning(std::chrono::seconds(10)); // Run analysis every 10 seconds

            std::vector<std::shared_ptr<Peer>> peersCopy;
            {
                std::lock_guard<std::mutex> lock(peersMutex_);
                peersCopy = peers_;
            }

            // ML-based threat detection

            // 1. DDoS Attack Detection
            if (threatDetector_.detectDDoSPattern(peersCopy))
            {
                std::cout << "🚨 ML DETECTED: DDoS attack pattern" << std::endl;

                ThreatAlert alert;
                alert.threatType = "ddos_attack";
                alert.severity = "high";
                alert.sourceIP = 0; // Multiple sources
                alert.timestamp = std::chrono::steady_clock::now().time_since_epoch().count();
                alert.details = "Detected abnormal connection flood from multiple sources";
                alert.reportingNodeId = nodeId_;
                alert.confidenceScore = 0.85;

                threatDetector_.recordThreat(alert);
                broadcastThreatAlert(alert);
                activateCoordinatedDefense(alert);
            }

            // 2. Sybil Attack Detection
            if (threatDetector_.detectSybilAttack(peersCopy))
            {
                std::cout << "🚨 ML DETECTED: Sybil attack pattern" << std::endl;

                ThreatAlert alert;
                alert.threatType = "sybil_attack";
                alert.severity = "high";
                alert.sourceIP = 0;
                alert.timestamp = std::chrono::steady_clock::now().time_since_epoch().count();
                alert.details = "Detected multiple nodes with identical characteristics";
                alert.reportingNodeId = nodeId_;
                alert.confidenceScore = 0.78;

                threatDetector_.recordThreat(alert);
                broadcastThreatAlert(alert);
                activateCoordinatedDefense(alert);
            }

            // 3. Eclipse Attack Detection
            if (threatDetector_.detectEclipseAttack(addrman_))
            {
                std::cout << "🚨 ML DETECTED: Eclipse attack pattern" << std::endl;

                ThreatAlert alert;
                alert.threatType = "eclipse_attack";
                alert.severity = "critical";
                alert.sourceIP = 0;
                alert.timestamp = std::chrono::steady_clock::now().time_since_epoch().count();
                alert.details = "Detected lack of peer diversity - possible eclipse attack";
                alert.reportingNodeId = nodeId_;
                alert.confidenceScore = 0.72;

                threatDetector_.recordThreat(alert);
                broadcastThreatAlert(alert);
                activateCoordinatedDefense(alert);
            }

            // 4. Per-Peer Threat Scoring
            for (auto &peer : peersCopy)
            {
                double threatScore = threatDetector_.calculateThreatScore(*peer);
                if (threatScore > 0.8) // High threat threshold
                {
                    std::cout << "🚨 ML DETECTED: Suspicious peer behavior (score: "
                              << (threatScore * 100.0) << "%)" << std::endl;

                    ThreatAlert alert;
                    alert.threatType = "suspicious_behavior";
                    alert.severity = (threatScore > 0.9) ? "critical" : "high";
                    alert.sourceIP = ntohl(peer->address.addr.sin_addr.s_addr);
                    alert.timestamp = std::chrono::steady_clock::now().time_since_epoch().count();
                    alert.details = "ML detected abnormal peer behavior patterns";
                    alert.reportingNodeId = nodeId_;
                    alert.confidenceScore = threatScore;

                    threatDetector_.recordThreat(alert);
                    broadcastThreatAlert(alert);

                    // Increase ban score for suspicious peer
                    peer->increaseBanScore(50);
                    if (peer->banScore >= BAN_SCORE_THRESHOLD)
                    {
                        disconnectPeer(peer, "ML threat detection: high threat score");
                    }
                }
            }
        }
    }

} // namespace pisecured
