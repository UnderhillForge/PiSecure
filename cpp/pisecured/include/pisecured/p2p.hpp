#pragma once

#include "config.hpp"
#include "storage.hpp"
#include <thread>
#include <atomic>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <array>
#include <cstdint>
#include <memory>
#include <mutex>
#include <chrono>
#include <netinet/in.h>
#include <functional>

namespace pisecured
{
    // Forward declarations
    class Storage;

    // --- P2P Protocol Constants ---
    constexpr uint32_t PROTOCOL_VERSION = 31400;
    constexpr uint32_t SERVICES_NODE = 1;
    constexpr int MAX_PEERS = 125;
    constexpr int MAX_OUTBOUND_CONNECTIONS = 8;
    constexpr int BAN_SCORE_THRESHOLD = 100;
    constexpr int PING_INTERVAL_SECONDS = 120;
    constexpr int MAX_INV_SIZE = 50000;

    // --- P2P Message Types ---
    enum class P2PMsgType : uint8_t
    {
        VERSION = 0,
        VERACK = 1,
        ADDR = 2,
        INV = 3,
        GETDATA = 4,
        HEADERS = 5,
        GETHEADERS = 6,
        BLOCK = 7,
        TX = 8,
        PING = 9,
        PONG = 10,
        REJECT = 11,
        GETBLOCKS = 12,
        THREAT_ALERT = 13 // Distributed threat coordination
    };

    // --- Inventory Types ---
    enum class InvType : uint32_t
    {
        ERROR = 0,
        TX = 1,
        BLOCK = 2
    };

    // --- Inventory Vector ---
    struct InvVect
    {
        uint32_t type;
        std::array<uint8_t, 32> hash;
        bool operator<(const InvVect &o) const { return std::tie(type, hash) < std::tie(o.type, o.hash); }
        bool operator==(const InvVect &o) const { return type == o.type && hash == o.hash; }
    };

    // --- Peer Address ---
    struct PeerAddr
    {
        sockaddr_in addr;
        uint64_t lastSeen;
        uint32_t services;
        int failures;
        bool operator==(const PeerAddr &o) const { return addr.sin_addr.s_addr == o.addr.sin_addr.s_addr && addr.sin_port == o.addr.sin_port; }
    };

    // BlockHeader is defined in storage.hpp

    // --- Threat Alert ---
    struct ThreatAlert
    {
        std::string threatType; // "ddos_attack", "suspicious_behavior", "network_anomaly"
        std::string severity;   // "low", "medium", "high", "critical"
        uint32_t sourceIP;      // IP address of threat source
        uint64_t timestamp;
        std::string details;
        std::string reportingNodeId;
        double confidenceScore; // ML confidence: 0.0-1.0
    };

    // Forward declarations
    class Peer;
    class AddrMan;

    // --- Local Threat Detector (ML-based) ---
    class ThreatDetector
    {
    public:
        ThreatDetector();

        // Real-time threat analysis
        bool analyzeMessagePattern(const Peer &peer, P2PMsgType msgType, size_t payloadSize);
        bool analyzeConnectionPattern(const PeerAddr &addr);
        double calculateThreatScore(const Peer &peer);

        // ML-based detection
        bool detectDDoSPattern(const std::vector<std::shared_ptr<Peer>> &peers);
        bool detectSybilAttack(const std::vector<std::shared_ptr<Peer>> &peers);
        bool detectEclipseAttack(const AddrMan &addrman);

        // Threat history
        void recordThreat(const ThreatAlert &alert);
        std::vector<ThreatAlert> getRecentThreats(uint64_t timeWindow) const;
        bool isKnownThreat(uint32_t ip) const;

    private:
        std::map<uint32_t, std::vector<uint64_t>> connectionAttempts_; // IP -> timestamps
        std::map<uint32_t, uint32_t> messageCounts_;                   // IP -> message count
        std::vector<ThreatAlert> threatHistory_;
        std::set<uint32_t> knownThreats_;
        mutable std::mutex mutex_;

        // ML feature extraction
        double extractConnectionFrequency(uint32_t ip) const;
        double extractMessageRateAnomaly(const Peer &peer) const;
        double extractBehaviorScore(const Peer &peer) const;
    };

    // --- Message Serialization ---
    class MessageSerializer
    {
    public:
        static std::vector<uint8_t> serializeVersion(uint32_t version, uint32_t services, uint64_t timestamp, const PeerAddr &addrRecv, const PeerAddr &addrFrom, uint64_t nonce, const std::string &userAgent, uint32_t startHeight);
        static std::vector<uint8_t> serializeVerack();
        static std::vector<uint8_t> serializeAddr(const std::vector<PeerAddr> &addrs);
        static std::vector<uint8_t> serializeInv(const std::vector<InvVect> &invs);
        static std::vector<uint8_t> serializeGetData(const std::vector<InvVect> &invs);
        static std::vector<uint8_t> serializeGetHeaders(const std::vector<std::array<uint8_t, 32>> &locatorHashes, const std::array<uint8_t, 32> &hashStop);
        static std::vector<uint8_t> serializeHeaders(const std::vector<BlockHeader> &headers);
        static std::vector<uint8_t> serializeBlock(const std::vector<uint8_t> &blockData);
        static std::vector<uint8_t> serializeTx(const std::vector<uint8_t> &txData);
        static std::vector<uint8_t> serializePing(uint64_t nonce);
        static std::vector<uint8_t> serializePong(uint64_t nonce);
        static std::vector<uint8_t> serializeReject(const std::string &message, uint8_t code, const std::string &reason);
        static std::vector<uint8_t> serializeThreatAlert(const ThreatAlert &alert);

        static bool deserializeVersion(const std::vector<uint8_t> &data, uint32_t &version, uint32_t &services, uint64_t &timestamp, std::string &userAgent, uint32_t &startHeight);
        static bool deserializeAddr(const std::vector<uint8_t> &data, std::vector<PeerAddr> &addrs);
        static bool deserializeInv(const std::vector<uint8_t> &data, std::vector<InvVect> &invs);
        static bool deserializeGetHeaders(const std::vector<uint8_t> &data, std::vector<std::array<uint8_t, 32>> &locatorHashes, std::array<uint8_t, 32> &hashStop);
        static bool deserializeHeaders(const std::vector<uint8_t> &data, std::vector<BlockHeader> &headers);
        static bool deserializePing(const std::vector<uint8_t> &data, uint64_t &nonce);
        static bool deserializePong(const std::vector<uint8_t> &data, uint64_t &nonce);
        static bool deserializeThreatAlert(const std::vector<uint8_t> &data, ThreatAlert &alert);

        // Public helper methods for block parsing
        static uint32_t readUint32(const uint8_t *data, size_t &offset);
        static uint64_t readUint64(const uint8_t *data, size_t &offset);

    private:
        static void writeUint32(std::vector<uint8_t> &buf, uint32_t val);
        static void writeUint64(std::vector<uint8_t> &buf, uint64_t val);
        static void writeString(std::vector<uint8_t> &buf, const std::string &str);
        static void writeVarInt(std::vector<uint8_t> &buf, uint64_t val);
        static std::string readString(const uint8_t *data, size_t &offset, size_t maxLen);
        static uint64_t readVarInt(const uint8_t *data, size_t &offset, size_t maxSize);
    };

    // --- Peer Connection State ---
    class Peer
    {
    public:
        int fd;
        PeerAddr address;
        bool inbound;
        bool handshakeComplete;
        int64_t lastPingTime;
        int64_t lastPongTime;
        int64_t lastRecvTime;
        int64_t lastSendTime;
        int banScore;
        uint32_t version;
        uint32_t services;
        uint32_t startHeight;
        std::string userAgent;
        uint64_t pingNonce;
        std::set<InvVect> knownInv;
        std::vector<uint8_t> recvBuffer;

        Peer(int fd, const PeerAddr &addr, bool inbound);
        bool sendMessage(P2PMsgType type, const std::vector<uint8_t> &payload);
        bool sendRawData(const std::vector<uint8_t> &data);
        void increaseBanScore(int amount);
        bool shouldBan() const { return banScore >= BAN_SCORE_THRESHOLD; }
        int64_t getIdleTime() const;
    };

    // --- WebSocket Bootstrap Client ---
    class BootstrapWebSocketClient
    {
    public:
        BootstrapWebSocketClient(const std::string &nodeId, const std::string &bootstrapUrl);
        ~BootstrapWebSocketClient();

        bool connect();
        void disconnect();
        bool isConnected() const { return connected_; }

        // Send messages to bootstrap
        void sendHeartbeat(const std::map<std::string, double> &metrics);
        void reportThreat(const std::string &threatType, const std::string &severity, const std::string &details);
        void reportNodeStatus(int peerCount, double uptime);

        // Callbacks for received events
        void setThreatCallback(std::function<void(const std::string &, const std::string &, const std::string &)> cb) { threatCallback_ = cb; }
        void setPeerDiscoveryCallback(std::function<void(const std::vector<PeerAddr> &)> cb) { peerDiscoveryCallback_ = cb; }
        void setDefenseCallback(std::function<void(const std::string &, const std::string &)> cb) { defenseCallback_ = cb; }

    private:
        std::string nodeId_;
        std::string bootstrapUrl_;
        int sockFd_;
        std::atomic<bool> connected_;
        std::atomic<bool> running_;
        std::thread recvThread_;
        std::mutex sendMutex_;
        uint64_t lastHeartbeat_;

        // Callbacks
        std::function<void(const std::string &, const std::string &, const std::string &)> threatCallback_;
        std::function<void(const std::vector<PeerAddr> &)> peerDiscoveryCallback_;
        std::function<void(const std::string &, const std::string &)> defenseCallback_;

        // Internal methods
        void recvLoop();
        bool sendWebSocketMessage(const std::string &message);
        bool performWebSocketHandshake();
        void handleMessage(const std::string &message);
    };

    // --- AddrMan (Peer Address Manager with Bootstrap) ---
    class AddrMan
    {
    public:
        AddrMan();
        void add(const PeerAddr &addr);
        PeerAddr select();
        std::vector<PeerAddr> getMany(size_t n);
        void markGood(const PeerAddr &addr);
        void markAttempt(const PeerAddr &addr);
        void markFailure(const PeerAddr &addr);
        void ban(const PeerAddr &addr);
        bool isBanned(const PeerAddr &addr) const;
        void addBootstrapPeers(const std::vector<std::string> &bootstrapHosts, uint16_t port);
        void queryBootstrapServer(const std::string &bootstrapUrl);
        void reportToBootstrap(const std::string &bootstrapUrl, const std::string &nodeId, const PeerAddr &myAddr);
        size_t size() const { return addrList.size(); }

    private:
        std::vector<PeerAddr> addrList;
        std::map<uint32_t, uint64_t> bannedIPs; // IP -> unban timestamp
        std::mutex mutex_;
        void cleanupBans();
    };

    // --- P2P Server ---
    class P2PServer
    {
    public:
        P2PServer();
        ~P2PServer();

        bool start(const Config &cfg, Storage *storage);
        void stop();
        void connectToPeers();
        void sendToAll(P2PMsgType type, const std::vector<uint8_t> &payload);
        void broadcastInv(const InvVect &inv);
        void requestBlock(const std::array<uint8_t, 32> &blockHash);
        void requestHeaders(uint32_t startHeight);
        size_t getPeerCount() const;
        // Non-loopback IPv4 and the listen port, for getpeers. Not 0.0.0.0.
        std::string reachableHost() const;
        int listenPort() const { return config_.p2p_port; }
        // Bootstrap list addresses. Hints only; blocks are still verified.
        std::vector<std::pair<std::string, int>> bootstrapHints() const;

        // Distributed threat detection and coordination
        void broadcastThreatAlert(const ThreatAlert &alert);
        void activateCoordinatedDefense(const ThreatAlert &alert);
        std::vector<ThreatAlert> getNetworkThreats() const;
        ThreatDetector *getThreatDetector() { return &threatDetector_; }

    private:
        Config config_;
        Storage *storage_;
        std::atomic<bool> running_;
        int listenFd_;
        std::vector<std::shared_ptr<Peer>> peers_;
        AddrMan addrman_;
        ThreatDetector threatDetector_;
        std::unique_ptr<BootstrapWebSocketClient> bootstrapWs_;
        std::thread acceptThread_;
        std::thread messageThread_;
        std::thread connectThread_;
        std::thread pingThread_;
        std::thread bootstrapHeartbeatThread_;
        std::thread threatDetectionThread_;
        mutable std::mutex peersMutex_;
        uint32_t bestHeight_;
        std::string nodeId_;
        mutable std::mutex hintMutex_;
        std::vector<std::pair<std::string, int>> bootstrapHints_;
        std::string bootstrapNodeId_;
        void registerBootstrapNode();
        void postBootstrapStatus();
        void reportBootstrapChain();
        void refreshBootstrapHints();

        // Thread functions
        void acceptLoop();
        void messageLoop();
        void connectLoop();
        void pingLoop();
        void bootstrapHeartbeatLoop();
        void threatDetectionLoop();
        // Wake within ~200ms of stop() so systemd does not hit TimeoutStopSec.
        void sleepWhileRunning(std::chrono::milliseconds total);

        // Bootstrap callbacks
        void onBootstrapThreatDetected(const std::string &threatType, const std::string &severity, const std::string &details);
        void onBootstrapPeerDiscovery(const std::vector<PeerAddr> &peers);
        void onBootstrapDefenseActivated(const std::string &defenseType, const std::string &details);

        // Connection management
        bool startListening(uint16_t port);
        void acceptConnection();
        void connectToPeer(const PeerAddr &addr);
        void disconnectPeer(std::shared_ptr<Peer> peer, const std::string &reason);
        void processMessages(std::shared_ptr<Peer> peer);

        // Message handlers
        void handleVersion(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleVerack(std::shared_ptr<Peer> peer);
        void handleAddr(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleInv(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleGetData(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleGetHeaders(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleHeaders(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleBlock(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleTx(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handlePing(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handlePong(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);
        void handleThreatAlert(std::shared_ptr<Peer> peer, const std::vector<uint8_t> &payload);

        // Protocol helpers
        void sendVersion(std::shared_ptr<Peer> peer);
        void sendVerack(std::shared_ptr<Peer> peer);
        void sendAddr(std::shared_ptr<Peer> peer);
        void sendPing(std::shared_ptr<Peer> peer);
        void relayTransaction(const std::vector<uint8_t> &txData);
        void relayBlock(const std::array<uint8_t, 32> &blockHash);

        // Utilities
        int getOutboundCount() const;
        bool shouldAcceptConnection() const;
        std::array<uint8_t, 32> computeHash(const std::vector<uint8_t> &data);
    };

} // namespace pisecured
