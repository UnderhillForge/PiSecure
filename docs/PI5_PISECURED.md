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
| ExecStart | `/opt/pisecure/pisecured --host 0.0.0.0 --port 3144` |
| Listen | `0.0.0.0:3144` (WebSocket JSON-RPC) |
| P2P | `0.0.0.0:3141` |
| Data | `/var/lib/pisecure` |
| Env | `/etc/pisecure/pisecure.env` (not committed) |
| User | `pisecure` (already on this Pi; uid 999, shell `/bin/false`) |

`/etc/pisecure/pisecure.env` sets `PISECURE_DATA_DIR=/var/lib/pisecure`, `PISECURED_HOST=0.0.0.0`, `PISECURED_PORT=3144`, `PISECURE_VALIDATE_ONLY=0`, and `PISECURE_MOCK_HARDWARE=0`. The daemon reads the data dir and the host/port. It has no mock-hardware path.

`--host` and `--port` are aliases for the WebSocket bind and port. Without them the unit's `ExecStart` would have been ignored and the process would have stayed on `127.0.0.1:3142`.

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

`curl -fsS https://bootstrap.pisecure.org/health` returned `"status":"healthy"`. The in-process bootstrap client is still a stub: the journal says `Bootstrap peer DNS resolution not yet implemented` and `Connected (HTTP fallback mode)` without opening a socket.

`systemctl restart pisecured` completed with `Deactivated successfully` (no SIGKILL). An earlier build slept inside the 120s ping loop and systemd hit `TimeoutStopSec`.

The previous unit on this Pi ran `/usr/local/bin/pisecured` as user `pi` on port 3142. systemd now runs `/opt/pisecure/pisecured` only. The old binary is still on disk and is not referenced by the unit.

Python CLI (optional, daemon already healthy): `python3 -m venv $HOME/PiSecure/.venv`, then `pip install -r requirements.txt` and `pip install -e .`. `pisecure version` prints `PiSecure 0.1.1`. `status` is registered once, from `pisecure/cli/commands/monitoring.py`.

## Block template and validation

`getblocktemplate`, `submitblock`, and `sendtransaction` are the same methods on WebSocket `ws://0.0.0.0:3144` and on optional loopback HTTP (`--http-rpc`). The daemon does not mine. `--validate-only` does not skip these checks.

`getblockcount` result `count` is the tip height. It is `0` when no block has been accepted. The first block is height `1`. Its `prev_block_hash` is 64 zero hex digits (the genesis anchor, not a stored block). Later blocks must link the stored tip.

Difficulty is leading zero bits in the band **2–4**, aimed at a **60 second** block. The first template uses 4. After two stored blocks, the next template steps by one: faster than 60s raises difficulty (cap 4), slower lowers it (floor 2). `submitblock` must use that exact value. 146 is not accepted.

Base subsidy is **0.200 314ST** per block (`subsidy_units` 200, where 1 unit = 0.001 314ST). About 288 blocks/day at the 60s target. The miner output is the subsidy minus the validator 1% (198 units, 0.198 314ST). The validator output is 2 units (0.002 314ST). Transaction fees, in the same units, split 60% miner, 20% stakers, 8% loans, 7% foundation, and the remainder (at least 5%) is burn and is not an output. Integer division is `fee * percent / 100` for the four paid shares; burn is whatever is left, so a block cannot mint more than the subsidy plus the paid fee shares. There is no foundation output when fees are zero. A coinbase over any of those caps is rejected with `coinbase exceeds emission rules`.

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

Coinbase has no inputs. Its outputs are the non-zero emission outputs, in role order `miner`, `validator`, `stakers`, `loans`, `foundation`. Burn is not an output. With no fees the outputs are miner 198 units and validator 2 units.

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
- `transaction too large`
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

`bootstrap.pisecure.org` is resolved with `getaddrinfo` and one IPv4 address is dialed on the P2P port. The HTTP bootstrap register/query calls, and the in-process "WebSocket" client that logs `Connected (HTTP fallback mode)`, are still stubs.

## Blockers for later sessions

Wallet:

- No wallet create or send UI in this session. `sendtransaction` accepts a structural tx and, once a block exists, a spend of a real UTXO. Signatures are not checked.
- `pswallet` is not in the git tree (removed in `caaf39f`). It has to be built from `cpp/pswallet` later.
- `/var/lib/pisecure/wallets/` and `index.db` are older Python data. They were kept and chowned to `pisecure:pisecure`. `pisecured` does not read them. It stores blocks as `blocks/blkNNNNN.dat`.
- HTTP JSON-RPC is off unless `--http-rpc` is passed. Clients should use the WebSocket on port 3144.

Miner:

- `psminer` and the private PiSecure-Miner repo were not built or run. `pisecured` does not produce blocks. Session 3 should call `getblocktemplate`, compute `sha256-pihash1` on an official Pi 2/3/4/5, and `submitblock`. A block that skips PiHash or `hw_proof` is rejected, so height stays 0 until that miner exists.
- `--mock-hardware` and `PISECURE_MOCK_HARDWARE` are hard errors. `pisecure mine` does not mine.
- DNS now resolves one bootstrap address onto P2P port 3141. The HTTP bootstrap client is still a stub, so a live peer is not guaranteed.

Left untouched on purpose: Docker/compose files from `bda1027` / `5cbaab1`, OTA apply, DEX, tokenomics, and the genesis hash.
