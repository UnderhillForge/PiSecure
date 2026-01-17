# PiSecure Architecture Diagrams

## Layer Stack Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 7: Security & Monitoring                │
│  OWASP • DDoS Protection • Audit Logging • Health Monitoring     │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 6: Network & P2P                        │
│  Bootstrap Servers • Peer Discovery • NAT Traversal • Sync       │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 5: IoT Integration                      │
│  Device Oracles • Trust Scores • Sensor Data • Edge Computing    │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 4: Application Services                   │
│  REST API • WebSocket • Client SDKs • Developer Tools            │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                Layer 3: Smart Contract Primitives                │
│  Oracles • Custody • Compliance • Events • State Management      │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 2: Token Economy & DeFi                   │
│  314ST Token • DEX • AMM • Liquidity Pools • Cross-Chain         │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                Layer 1: Consensus & Blockchain Core              │
│  PiHash PoW • Blocks • Transactions • Difficulty • Syndicates    │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 0: Hardware Foundation                    │
│  Raspberry Pi • PiHash • CPU Serial • VideoCore • TrustZone      │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
┌─────────────┐
│   Miner     │ ──┐
│  (Pi Zero)  │   │
└─────────────┘   │
                  │
┌─────────────┐   │     ┌──────────────────┐
│   Miner     │ ──┼────→│  Mining Syndicate│
│   (Pi 4)    │   │     │   Coordinator    │
└─────────────┘   │     └──────────────────┘
                  │              │
┌─────────────┐   │              ↓
│   Miner     │ ──┘     ┌──────────────────┐
│   (Pi 5)    │         │   Blockchain     │←──┐
└─────────────┘         │   Core (Layer 1) │   │
                        └──────────────────┘   │
                                 │              │
                                 ↓              │
                        ┌──────────────────┐   │
                        │   Hybrid Storage │   │
                        │ ┌──────────────┐ │   │
                        │ │ Block Files  │ │   │
                        │ │ (blk*.dat)   │ │   │
                        │ └──────────────┘ │   │
                        │ ┌──────────────┐ │   │
                        │ │   SQLite     │ │   │
                        │ │  (pisecure.db)  │ │   │
                        │ └──────────────┘ │   │
                        │ ┌──────────────┐ │   │
                        │ │Memory Cache  │ │   │
                        │ └──────────────┘ │   │
                        └──────────────────┘   │
                                 │              │
                ┌────────────────┼──────────────┤
                ↓                ↓              ↓
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │   DEX/AMM    │ │   Oracles    │ │  IoT Devices │
        │  (Layer 2)   │ │  (Layer 3)   │ │  (Layer 5)   │
        └──────────────┘ └──────────────┘ └──────────────┘
                │                │                │
                └────────────────┼────────────────┘
                                 ↓
                        ┌──────────────────┐
                        │    REST API      │
                        │  (Layer 4)       │
                        └──────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ↓                ↓                ↓
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  Web Apps    │ │  Mobile Apps │ │  IoT Apps    │
        │  (JS/TS)     │ │  (Android)   │ │  (C/Rust)    │
        └──────────────┘ └──────────────┘ └──────────────┘
```

## Transaction Flow

```
1. Transaction Created
   ┌──────────────────┐
   │   User Wallet    │
   │   (Layer 4)      │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │   Sign & Submit  │
   │  (Private Key)   │
   └────────┬─────────┘
            │
            ↓
2. Validation
   ┌──────────────────┐
   │   API Server     │
   │  Input Checking  │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │   IoT Enhanced   │
   │  Security Check  │
   │  (Layer 5)       │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │  Risk Analysis   │
   │  Fee Adjustment  │
   └────────┬─────────┘
            │
            ↓
3. Mempool
   ┌──────────────────┐
   │   Pending TX     │
   │   Queue          │
   └────────┬─────────┘
            │
            ↓
4. Mining
   ┌──────────────────┐
   │   Miner selects  │
   │   transactions   │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │   PiHash Mining  │
   │  (Pi Hardware)   │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │   Block Found    │
   │   (Nonce Valid)  │
   └────────┬─────────┘
            │
            ↓
5. Propagation
   ┌──────────────────┐
   │   Broadcast to   │
   │   P2P Network    │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │  Peer Validation │
   │  (Universal)     │
   └────────┬─────────┘
            │
            ↓
6. Confirmation
   ┌──────────────────┐
   │   Block Added    │
   │   to Chain       │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────┐
   │  TX Confirmed    │
   │  (Irreversible)  │
   └──────────────────┘
```

## PiHash Mining Process

```
┌─────────────────────────────────────────────────────────────────┐
│                     Raspberry Pi Miner                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Hardware Fingerprinting                                │  │
│  │     • CPU Serial Number                                    │  │
│  │     • VideoCore GPU Patterns                               │  │
│  │     • ARM TrustZone RNG                                    │  │
│  │     • Temperature Baseline                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  2. PiHash Algorithm                                       │  │
│  │     • Blake2b base hash                                    │  │
│  │     • Memory-hard mixing (16K blocks = 1MB)                │  │
│  │     • ARM NEON optimization patterns                       │  │
│  │     • Hardware entropy mixing                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  3. Nonce Search                                           │  │
│  │     • Target: "0000..." (difficulty-based)                 │  │
│  │     • Performance: 0.05-2.0 H/s                            │  │
│  │     • Adjusted difficulty per Pi model                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  4. Block Creation                                         │  │
│  │     • Valid nonce found                                    │  │
│  │     • Block assembled                                      │  │
│  │     • Hardware signature attached                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Network Validation                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  5. Fast Validation (Any Hardware)                         │  │
│  │     • Synthetic hardware fingerprint                       │  │
│  │     • PiHash verification (32MB, 1 round)                  │  │
│  │     • Hash matches target                                  │  │
│  │     • Time: <1 second                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  6. Block Accepted                                         │  │
│  │     • Added to blockchain                                  │  │
│  │     • Reward distributed (50 314ST)                        │  │
│  │     • Propagated to peers                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## DEX Architecture

```
                    ┌──────────────────────┐
                    │   Trading Interface  │
                    │    (Web/Mobile)      │
                    └──────────┬───────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │   DEX API            │
                    │   (Layer 4)          │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ↓                ↓                ↓
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Order Book     │ │  AMM Pools  │ │  Bridges    │
    │  • Limit orders │ │  • 314ST/X  │ │  • Ethereum │
    │  • Market orders│ │  • Liquidity│ │  • Bitcoin  │
    │  • Stop-loss    │ │  • 0.3% fee │ │  • Solana   │
    └────────┬────────┘ └──────┬──────┘ └──────┬──────┘
             │                 │                │
             └─────────────────┼────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │   Blockchain Core    │
                    │   • Transactions     │
                    │   • Token Transfers  │
                    │   • Smart Contracts  │
                    └──────────────────────┘
```

## IoT Oracle System

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ IoT Sensor  │  │ IoT Sensor  │  │ IoT Sensor  │  │ IoT Sensor  │
│   Device 1  │  │   Device 2  │  │   Device 3  │  │   Device 4  │
│  (Pi Zero)  │  │   (Pi 4)    │  │   (Pi 4)    │  │   (Pi 5)    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┼────────────────┼────────────────┘
                        ↓
              ┌──────────────────────┐
              │   Device Network     │
              │   • Trust Scores     │
              │   • Reputation       │
              │   • Health Checks    │
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │   Consensus Engine   │
              │   • Byzantine Fault  │
              │   • 2/3 Majority     │
              │   • Outlier Filter   │
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │   Oracle Contract    │
              │   • Verified Data    │
              │   • Timestamped      │
              │   • Blockchain-Stored│
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │   Smart Contracts    │
              │   • Price Feeds      │
              │   • Triggers         │
              │   • Automation       │
              └──────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 7: Application Security (OWASP, DDoS, Rate Limiting)  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: Network Security (SSL/TLS, P2P Encryption)         │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: API Security (Authentication, Authorization)        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Smart Contract Security (Input Validation)         │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Consensus Security (Block Validation)              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Cryptographic Security (Signatures, Hashes)        │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Hardware Security (PiHash, CPU Serial, TrustZone)  │
└─────────────────────────────────────────────────────────────┘
```

## Comparison: Blockchain Generations

```
┌─────────────────────────────────────────────────────────────┐
│                    Blockchain 1.0 (Bitcoin)                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • Cryptocurrency                                    │    │
│  │  • Proof-of-Work                                     │    │
│  │  • Peer-to-Peer                                      │    │
│  │  • Immutable Ledger                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Blockchain 2.0 (Ethereum)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Everything from 1.0 PLUS:                           │    │
│  │  • Smart Contracts                                   │    │
│  │  • DApps                                             │    │
│  │  • Token Standards (ERC-20, ERC-721)                 │    │
│  │  • DeFi Protocols                                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Blockchain 3.0 (Solana, Cardano)            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Everything from 2.0 PLUS:                           │    │
│  │  • High Scalability (50K+ TPS)                       │    │
│  │  • Cross-Chain Bridges                               │    │
│  │  • Sharding                                          │    │
│  │  • Proof-of-Stake                                    │    │
│  │  • Lower Fees                                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               PiSecure 2.5 (Hybrid + Innovation)             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  2.0 Features + 3.0 Features PLUS:                   │    │
│  │  • Hardware-Verified Consensus                       │    │
│  │  • IoT Native Integration                            │    │
│  │  • Device Oracles                                    │    │
│  │  • Edge Computing Optimized                          │    │
│  │  • ASIC-Resistant (Memory-Hard)                      │    │
│  │  • Pi-Exclusive Mining                               │    │
│  │  • Universal Validation                              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```
