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

## Blockers for later sessions

Wallet:

- No wallet create, send, or UTXO work in this session.
- `pswallet` is not in the git tree (removed in `caaf39f`). It has to be built from `cpp/pswallet` later.
- `/var/lib/pisecure/wallets/` and `index.db` are older Python data. They were kept and chowned to `pisecure:pisecure`. `pisecured` does not read them. It stores blocks as `blocks/blkNNNNN.dat` and writes `validator_bucket.json`.
- HTTP JSON-RPC is off unless `--http-rpc` is passed. `rpc-client.py` talks HTTP, and that socket still binds loopback only. Clients should use the WebSocket on port 3144.

Miner:

- `psminer`, PiHash, and the private PiSecure-Miner repo were not built or run. This daemon does not produce blocks.
- `pisecured` does not read the Pi serial or device tree, and it does not contain a mock-hardware switch. A miner session has to bind to this board for real. Do not add `PISECURE_MOCK_HARDWARE`, `--mock-hardware`, fake serials, Docker mining, x86 mining, or a verifier fallback.
- Outbound peer DNS for `bootstrap.pisecure.org` is not implemented, so the node will not find peers until that lands.
- The Python CLI still has `--mock-hardware`, `mine`, and `verify-hardware` from `origin/main`. This session did not use them. Do not pass `--mock-hardware`.

Left untouched on purpose: Docker/compose files from `bda1027` / `5cbaab1`, OTA apply, DEX, tokenomics, and the genesis hash.
