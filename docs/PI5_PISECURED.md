# pisecured on this Raspberry Pi 5

Native C++ daemon, Debian packages and systemd only. No Docker.

Recorded 2026-09-22 on host `pisecure.local` from branch `revive/pisecured-pi5`.

## Machine

Device tree (`tr -d '\0' < /proc/device-tree/model`):

```
Raspberry Pi 5 Model B Rev 1.1
```

`/etc/os-release`:

```
PRETTY_NAME="Debian GNU/Linux 13 (trixie)"
NAME="Debian GNU/Linux"
VERSION_ID="13"
VERSION="13 (trixie)"
VERSION_CODENAME=trixie
DEBIAN_VERSION_FULL=13.3
ID=debian
```

Kernel: `6.12.47+rpt-rpi-2712` aarch64.

## Daemon

| Item | Value |
| --- | --- |
| Binary | `/opt/pisecure/pisecured` |
| Unit | `pisecured.service` (`enabled`, `active`) |
| ExecStart | `/opt/pisecure/pisecured --host 0.0.0.0 --port 3144 --apply-update` |
| Listen | `0.0.0.0:3144` (WebSocket JSON-RPC) |
| P2P | `0.0.0.0:3141` |
| Data | `/var/lib/pisecure` |
| Env | `/etc/pisecure/pisecure.env` (not committed) |
| User | `pisecure` (already on this Pi; uid 999, shell `/bin/false`) |

`/etc/pisecure/pisecure.env` sets `PISECURE_DATA_DIR=/var/lib/pisecure`, `PISECURED_HOST=0.0.0.0`, `PISECURED_PORT=3144`, `PISECURE_VALIDATE_ONLY=0`, and `PISECURE_MOCK_HARDWARE=0`. The daemon reads the data dir and the host/port. It has no mock-hardware path.

`--host` and `--port` are aliases for the WebSocket bind and port. The unit binds `0.0.0.0:3144` and passes `--apply-update`.

## Packages

Installed or upgraded with apt for this build:

- `build-essential` 12.12
- `cmake` 3.31.6-2
- `pkg-config` 1.8.1-4
- `git` 1:2.47.3-0+deb13u1
- `libssl-dev` / `libssl3t64` 3.5.7-1~deb13u2+rpt1
- `libwebsockets-dev` / `libwebsockets19t64` 4.3.5-1+deb13u2
- `libsqlite3-dev` 3.46.1-7+deb13u2
- `python3-venv` / `python3-dev` 3.13.5-1

Already present and required to compile (`#include <nlohmann/json.hpp>`):

- `nlohmann-json3-dev` 3.11.3-2.1

Configure line:

```
cmake -S cpp/pisecured -B cpp/pisecured/build -DCMAKE_BUILD_TYPE=Release
```

libwebsockets was found via pkg-config.

## Journal

`journalctl -u pisecured` after the final restart (pid 6929):

```
Sep 22 16:45:04 pisecure systemd[1]: Started pisecured.service - PiSecure Blockchain Daemon.
Sep 22 16:45:04 pisecure pisecured[6929]: Validator bucket initialized at "/var/lib/pisecure/validator_bucket.json"
Sep 22 16:45:05 pisecure pisecured[6929]: P2P server started on port 3141
Sep 22 16:45:05 pisecure pisecured[6929]: [vh|1|default|0.0.0.0|0.0.0.0|3144]: lws_socket_bind: source ads 0.0.0.0
Sep 22 16:45:05 pisecure pisecured[6929]: [WS] WebSocket server listening on ws://0.0.0.0:3144 (libwebsockets)
```

`ss` shows `0.0.0.0:3144` owned by that pid. `python3 ws-client.py --url ws://127.0.0.1:3144` got `{"status":"pong"}` and a bucket subscription.

`curl -fsS https://bootstrap.pisecure.org/health` returned `"status":"healthy"`. Directory register, status, and chain report are described under Peers. The log line `Connected (HTTP fallback mode)` is the unused WebSocket placeholder and does not carry blocks.

`systemctl restart pisecured` completed with `Deactivated successfully` (no SIGKILL). An earlier build slept inside the 120s ping loop and systemd hit `TimeoutStopSec`.

systemd runs `/opt/pisecure/pisecured`. Wallets use `/opt/pisecure/pswallet` against `ws://127.0.0.1:3144`. There is no mock-hardware mode.

## Block template and validation

`getblocktemplate`, `submitblock`, and `sendtransaction` are the same methods on WebSocket `ws://0.0.0.0:3144` and on optional loopback HTTP (`--http-rpc`). The daemon does not mine. `--validate-only` does not skip these checks.

`getblockcount` result `count` is the tip height. It is `0` when no block has been accepted. The first block is height `1`. Its `prev_block_hash` is 64 zero hex digits (the genesis anchor, not a stored block). Later blocks must link the stored tip.

Difficulty is leading zero bits in **2–24**. Block 1 starts at **4** bits. After 10 stored blocks, each new block retargets from the last 10 timestamps: `elapsed = time[tip] - time[tip-9]` (9 gaps). Fewer than 10 blocks keeps the previous bits. A non-positive elapsed is ignored. `elapsed` is clamped to `[540/4, 540*4]` and work `2^bits` is then multiplied by `540 / elapsed`, and that product is clamped to `[work/4, work*4]`. `next_bits` is `round(log2(next_work))` clamped to 2–24. Fast spans raise bits. Slow spans lower them. `submitblock` must use that exact value. 146 is not accepted. A block timestamp more than **120 seconds** ahead of this node's clock is rejected.

### Activation height 1

`kDifficultyActivationHeight` is **1**. v0.2.8 applies the 218-unit subsidy and the 2–24 bit retarget from block 1. There is no block below height 1.

The subsidy is **218 units** (0.218 314ST): miner **216**, validator **2**. With `fee_units` 0 there are no other coinbase outputs. Transaction fees split 60% miner, 20% stakers, 8% loans, 7% foundation, and the remainder (at least 5%) is burn and is not an output. Integer division is `fee * percent / 100` for the four paid shares. There is no foundation output when fees are zero. When the 7% is at least 1 unit, that output is paid to the Foundation wallet `ps1a404246a1e6154e96bd02728fe1a988ae2abe6c6609426e2da7b71ab3dccb4f7` and the amount must match. Any other foundation address is rejected with `coinbase foundation address`. Stakers stay the address `stakers`, loans stay `loans`, and burn stays out of the coinbase. A coinbase that pays the miner more than 216 plus the miner's fee share, or the validator more than 2, is rejected with `coinbase exceeds emission rules`.

The blocks already stored on this Pi were mined before this schedule. Reloading them does not rewrite `blk*.dat`. A new chain starts at height 1 with these rules.

`getblocktemplate` returns the `difficulty` and `subsidy_units` (200 or 218) that `submitblock` will enforce for the height it is building. A miner-supplied difficulty that disagrees is `difficulty mismatch`.

### getblocktemplate

Request params: `{"miner":"<address>"}` or `{"wallet":"<address>"}`.

```json
{
  "version": 1,
  "height": 1,
  "prev_block_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp": 1790112500,
  "difficulty": 4,
  "coinbase": {
    "wallet": "pisecure-session3",
    "height": 1,
    "txid": "58b0d9b0695867fe068bf854987d7ddf77cbe3f5af17e7ae3c453c42b86bbc11",
    "unit": "0.001 314ST",
    "subsidy": "0.200",
    "subsidy_units": 200,
    "outputs": [
      {"role": "miner", "address": "pisecure-session3", "units": 198, "amount": "0.198"},
      {"role": "validator", "address": "validator", "units": 2, "amount": "0.002"}
    ],
    "fee_units": 0,
    "shares_units": {"miner": 0, "stakers": 0, "loans": 0, "foundation": 0, "burn": 0}
  },
  "coinbase_txid": "58b0d9b0695867fe068bf854987d7ddf77cbe3f5af17e7ae3c453c42b86bbc11",
  "merkle_root": "58b0d9b0695867fe068bf854987d7ddf77cbe3f5af17e7ae3c453c42b86bbc11",
  "txs": [],
  "hw_proof": {"model": "", "serial_commitment": ""},
  "pihash": {
    "algorithm": "sha256-pihash1",
    "domain": "PiHash1",
    "difficulty_means": "leading zero bits"
  }
}
```

`txs` lists mempool transactions in admission order. `spendable: false` means the tx has no inputs (a placeholder). It is listed, it is not included in `merkle_root` or `fee_units`, and a block that includes it is rejected. `merkle_root` commits the coinbase txid and then each spendable txid. A coinbase-only block sets `txs` to `[]` and sets `merkle_root` to `coinbase_txid`. If a spendable tx is dropped, recompute the fee shares and the merkle root. Fee shares in the template assume every spendable tx is included.

Empty mempool, wallet `pisecure-session3`, height 1: `coinbase_txid` is `58b0d9b0695867fe068bf854987d7ddf77cbe3f5af17e7ae3c453c42b86bbc11`.

### Canonical transaction (`TX1`)

Little-endian integers. `txid = SHA256(bytes)`.

```
"TX1"
u32 version          (1)
u8  type             (1 coinbase, 0 otherwise)
u32 input_count
  repeated: 32-byte prev_txid || u32 vout
u32 output_count
  repeated: u64 value || u16 address_len || address utf-8
u64 fee              (0 for coinbase, >= 1 otherwise)
u32 height           (coinbase height, else 0)
```

Coinbase has no inputs. Its outputs are the non-zero emission outputs, in role order `miner`, `validator`, `stakers`, `loans`, `foundation`. Burn is not an output. With no fees the outputs are miner 216 units and validator 2 units.

Merkle root: start with `coinbase_txid`, then each included `txid`. While more than one id remains, if the count is odd duplicate the last id, then replace the list with `SHA256(left || right)` for each pair. One id is itself the root.

### PiHash the validator recomputes

This is not the VideoCore-gated hasher in `cpp/hw`. Any machine can recompute it. The daemon does not read this host's serial to accept a block.

```
"PiHash1"
u32 version
32-byte prev_block_hash
32-byte merkle_root
u64 timestamp
u32 difficulty
u64 nonce
u16 model_len || model utf-8
32-byte serial_commitment
```

`hash = hex(SHA256(those bytes))`, lowercase. Leading zero **bits** of the raw digest must be at least `difficulty`. `serial_commitment` is 32 non-zero bytes (hex). The miner chooses it; this daemon does not invent serials. `model` must start with `Raspberry Pi 2`, `Raspberry Pi 3`, `Raspberry Pi 4`, or `Raspberry Pi 5`, and must not contain `Zero`.

### submitblock

Params are one object (or a one-element array containing that object) with `version`, `height`, `prev_block_hash`, `merkle_root`, `timestamp`, `difficulty`, `nonce`, `hash`, `coinbase`, `txs`, and `hw_proof`. Result is `{"status":"accepted","hash","height"}` or `{"status":"rejected","reason"}`. An empty or TODO body is never accepted. Accepted blocks are appended to `blocks/blk*.dat`, the tip moves, coinbase and spendable txs update the UTXO set, and an `inv` is sent if a handshake-complete peer exists.

Reject reasons:

- `missing block`
- `missing hw_proof`
- `hw_proof model is not an official Raspberry Pi 2/3/4/5`
- `hw_proof serial_commitment missing or malformed`
- `hw_proof challenge missing` (height 4 and later)
- `hw_proof challenge mismatch` (height 4 and later)
- `hw_proof serial missing or malformed` (height 4 and later)
- `hw_proof serial_commitment does not bind serial and challenge` (height 4 and later)
- `version invalid`
- `height does not extend tip`
- `nonce invalid`
- `timestamp invalid`
- `difficulty mismatch`
- `prev hash does not link tip`
- `merkle root mismatch`
- `pihash missing`
- `pihash mismatch`
- `pihash does not meet difficulty`
- `coinbase missing`
- `coinbase wallet missing`
- `coinbase exceeds emission rules`
- `malformed transaction`
- `transaction output invalid`
- `transaction inputs missing`
- `tx too large`
- `fee too low`
- `unknown input`
- `insufficient funds`
- `duplicate transaction`
- `block too large`

Smoke on this Pi: miner output of 200 units (the whole 0.200 subsidy) → `coinbase exceeds emission rules`. A foundation output with zero fees → the same reason. `qemu-x86` proof → `hw_proof model is not an official Raspberry Pi 2/3/4/5`. Difficulty 146 → `difficulty mismatch`. A Pi 5 model string whose hash was not the recomputed PiHash → `pihash mismatch`. `getblockcount` stayed `0`.

### sendtransaction

A JSON object, or one JSON string. Garbage (`"not-a-transaction"`) → `{"status":"rejected","reason":"malformed transaction"}`.

A placeholder that is stored and returned by `getmempool` and the next template:

```json
{"version": 1, "inputs": [], "outputs": [{"address": "placeholder", "value": 1}], "fee": 1}
```

Inputs, when present, must name UTXOs created by an earlier accepted block (coinbase vout 0, or a prior output) and the outputs plus `fee` must fit the input value. There is no second ledger and no signature check yet. The in-memory mempool is dropped on restart; accepted blocks are reloaded from `blk*.dat`.

### Peers

Block download is P2P on port 3141. It does not go through bootstrap. `getpeers` on this Pi reports `192.168.68.77:3141` (`pisecure.local`). `0.0.0.0` is only the listen bind.

A second validator syncs with the existing framing: `VERSION`, `VERACK`, `GETHEADERS`, `HEADERS`, `GETDATA`, `BLOCK`. Headers start at height 1. The block payload is the stored JSON. The receiver runs the same PiHash and `hw_proof` checks as `submitblock`. A challenge does not have to be in the receiver's template cache, because the binding is in the block. A `qemu-x86` model is still rejected.

```bash
/opt/pisecure/pisecured \
  --datadir /tmp/pisecure-sync \
  --host 127.0.0.1 --port 13144 \
  --p2p-bind 127.0.0.1 --p2p-port 31411 \
  --validate-only \
  --peer 127.0.0.1:3141
```

That process reached height 5, tip `0a560a2a038e03da504e50a865d565b01c1e1c33b08ab0fc26f826c9ed98ed28`.

Register is a helper. On startup this miner POSTs `https://bootstrap.pisecure.org/api/v1/nodes/register` once. `node_id` comes from `PISECURE_NODE_ID` or from `node_id` in the data directory, created once per install. `node_type` is `miner`, or `validator` when `--validate-only` is set. The body always includes `p2p_host` (first non-loopback IPv4), `p2p_port` 3141, and `rpc_port` 3144, plus the stored height and tip. HTTP 409 `NODE_ALREADY_REGISTERED` posts that same id to `/api/v1/nodes/status` and does not create another id. Status repeats every 300s with `status` `active`, `mining_active` false, and `peers_connected`. `/api/v1/chain/report` repeats every 30s with up to 120 newest blocks. HTTP 403 registers once more and the loop continues. A failed HTTPS call is logged and does not stop P2P or RPC. A process started with `--peer` does not publish, so a second validator leaves this host's directory record alone. `GET /api/v1/bootstrap/peers` and `GET /api/v1/nodes/list` supply `p2p_host:p2p_port` as hints (`hint: true` on `getpeers`). This process still handshakes and checks PiHash2 and `hw_proof`. Ignore advertised genesis `2742129a`. Height 1 hash is `0fbe305838fbb59e4ec010d7319a3461a2513663f3643959da3d39c23265fecf` and its `prev_block_hash` is 32 zero bytes. The in-process bootstrap WebSocket that logs `Connected (HTTP fallback mode)` is still a stub and is not used to fetch blocks.

## Height 1 spend

Block `0fbe305838fbb59e4ec010d7319a3461a2513663f3643959da3d39c23265fecf` is height 1. Its coinbase txid is `f67580eb5438505cdd19d0cbff2f4370d888be8acfed91d8b212af189db4b9d7`. Miner output vout **0** pays 198 units to `operator`. Validator output vout 1 pays 2 units to `validator`.

`pisecure wallet utxos` and `pisecure wallet send` talk to `ws://127.0.0.1:3144` and use this UTXO map. CLI amounts are **314ST**. `0.050` is 50 units, because 1 unit is 0.001 314ST. The default fee `0.001` is 1 unit.

Spend accepted into the mempool, not yet in a block:

- txid `8c2962a752385f08e2a9b4c74437e10d999931273f6b42de7d89b5dfee2a7345`
- input `f67580eb…b9d7` vout 0
- outputs: `student` 50 units, `operator` 147 units change
- fee 1 unit
- next template for miner `operator` includes it (`spendable: true`, `fee_units` 1)
- merkle root `fa64931b1c8f761f8b70081e33383aae30f65d86614466fd4e42d8c44c783eb0`

A 1-unit fee floors the 60/20/8/7 shares to 0. The 1 unit is the burn remainder, not an output. The old placeholder tx is not in this mempool. Block 2 is not mined from this session.

## PiHash2 from height 5

Heights 1–4 stay PiHash1: one SHA-256 of the header preimage whose 7-byte domain is `PiHash1`. From height 5 the template field `pihash` is:

```json
{"algorithm": "pihash2", "domain": "PiHash2", "rounds": 1, "memory_mb": 32}
```

The preimage is the same layout with domain `PiHash2`. `submitblock` rejects a height-5 header whose `pihash.algorithm` is not `pihash2` (`pihash algorithm not pihash2`), and a PiHash2 header whose digest does not match (`pihash mismatch`) or does not meet the 2–4 leading-zero band (`pihash does not meet difficulty`).

## Height 4 serial binding

Blocks 1–3 stay valid with the old rule: `serial_commitment` is any 32 non-zero bytes. From height 4, `getblocktemplate` adds a fresh challenge and does not fill the serial:

```json
"hw_proof": {
  "model": "",
  "serial_commitment": "",
  "challenge": "<64 hex, 32 random bytes>",
  "serial_rule": "sha256(serial_utf8 || challenge_bytes)"
}
```

`submitblock` must send `model`, that same `challenge`, the device-tree serial (hex, 1–64 chars, no NULs), and

`serial_commitment = hex(SHA256(utf8(serial) || raw 32-byte challenge))`.

The challenge has to be one this process issued. PiHash1 is unchanged: its preimage still ends with the model and the 32-byte commitment, not the serial plaintext. The accepted block JSON stores `challenge`, `serial`, and `serial_commitment` so a later check does not need the template cache.

## Spending keys

A spend is accepted only when each input is signed by the Ed25519 key bound to that input's address. Address strings stay UTF-8 names (`operator`, `student`). They are not pubkey hashes.

Key file, owner `pisecure`, mode `0600`:

`/var/lib/pisecure/wallets/<address>.json`

```json
{"address": "operator", "scheme": "ed25519", "public_key": "<64 hex>", "secret_key": "<64 hex>"}
```

`pisecure wallet bind operator` creates the file if it is missing and prints only the public key. `wallet send` loads the source key, signs, and does not print the secret.

The signed bytes are UTF-8 JSON of the tx with signature fields removed and object keys sorted: `version`, `inputs` (`prev_txid`, `vout` only), `outputs` (`address`, `value`), `fee`. Example shape:

```json
{"fee":1,"inputs":[{"prev_txid":"<64 hex>","vout":0}],"outputs":[{"address":"student","value":10},{"address":"operator","value":187}],"version":1}
```

Reject strings:

- `address has no spending key` — no key file for the UTXO address
- `signature missing` — a key is bound and the input has no signature
- `public key does not match address` — the signature was made by a different bound key
- `signature invalid` — the public key matches but the Ed25519 signature does not

On this Pi, an unsigned spend of `operator` returned `signature missing`. A spend of `operator` signed by `student` returned `public key does not match address`. The signed send `operator` → `student` of 0.010 314ST (10 units, fee 1, change 187) is mempool tx `9af4d1fea3000bf379db9b3f7eea4595b30f51200d7fb97d09d398eb3ca4d242`. Height is still 2. Block 3 was not mined.

## Blockers for later sessions

Wallet:

- No wallet create or send UI in this session. `sendtransaction` accepts a structural tx and, once a block exists, a spend of a real UTXO. Signatures are not checked.
- `cpp/pswallet` builds `/opt/pisecure/pswallet` and talks to `ws://127.0.0.1:3144`.
- `/var/lib/pisecure/wallets/` and `index.db` are older Python data. They were kept and chowned to `pisecure:pisecure`. `pisecured` does not read them. It stores blocks as `blocks/blkNNNNN.dat`.
- HTTP JSON-RPC is off unless `--http-rpc` is passed. Clients should use the WebSocket on port 3144.

Miner:

- `psminer` is not in this tree. Download the release binary for Raspberry Pi 2–5. `pisecured` does not produce blocks.
- The daemon does not mine. Mining is the separate `psminer` release binary.
- With no `--peer`, DNS still resolves `bootstrap.pisecure.org` onto P2P port 3141. Directory `p2p_host:p2p_port` values are hints. Blocks are not downloaded over HTTPS.

Left untouched on purpose: PiHash2, hw_proof, Ed25519 spend checks, namelookup, and the `blk*.dat` layout. v0.2.9 keeps activation height 1 and pays the Foundation fee share to `ps1a404246a1e6154e96bd02728fe1a988ae2abe6c6609426e2da7b71ab3dccb4f7`.

## Name backup

A long address is `ps1` plus hex(SHA256(ed25519 public key)). Key files are mode 0600 in `/var/lib/pisecure/wallets/`. `pswallet encrypt` stores the seed as scrypt and ChaCha20-Poly1305 in `secret_key_enc`. `public_key` stays plaintext. The passphrase is not written in the file. Back up the file and remember the passphrase, or the coins are unspendable.

On this Pi:

- `Foundation` → `ps1a404246a1e6154e96bd02728fe1a988ae2abe6c6609426e2da7b71ab3dccb4f7` at `/var/lib/pisecure/wallets/ps1a404246a1e6154e96bd02728fe1a988ae2abe6c6609426e2da7b71ab3dccb4f7.json`
- `OperatorX` → `ps1ff97b6682d9748878990a6f2b1dbac3554c38a3e64ffc18bf77159fbb80e86cb` at `/var/lib/pisecure/wallets/ps1ff97b6682d9748878990a6f2b1dbac3554c38a3e64ffc18bf77159fbb80e86cb.json`

`/var/lib/pisecure/names.json` stores the reserved bind. A fresh node learns names by replaying `type: register` transactions during blk restore, from the `names` snapshot written on blocks accepted after this, and from the `names` array on the bootstrap chain report. Heights 1–9 were not rewritten. The register transactions stay in the mempool until a miner includes them.
