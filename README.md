# PiSecure

PiSecure is a low-power chain for Raspberry Pi. A new block pays **0.218 314ST** (miner 0.216, validator 0.002). At height 3000 the stored unit becomes pi, where 1 314ST is 1000000 pi, and the same coinbase is 0.218000 314ST. From block 32 the validator output is a ps1; if `getblocktemplate` omits `validator`, that address is Foundation. v0.2.18 keeps one hw_proof challenge for the same tip, merkle root, and miner until that block is accepted or the work changes. A template is stamped one second after the parent when the node clock is still in that same second. psminer keeps hashing the next nonce while that template stays the same, and it opens a new socket when the node connection drops. Difficulty starts at 4 bits and retargets in the band 2–24. Official Pi 2, 3, 4, and 5 can mine. Any CPU can validate.

## Install

Download the v0.2.18 archive from this repo's GitHub Releases and check the sha256 printed on that release:

```bash
curl -fL -O https://github.com/UnderhillForge/PiSecure/releases/download/v0.2.18/pisecure-pi5-v0.2.18-aarch64.tar.gz
sha256sum pisecure-pi5-v0.2.18-aarch64.tar.gz
tar -xzf pisecure-pi5-v0.2.18-aarch64.tar.gz
sudo ./update.sh
```

On a Pi, `update.sh` stops `pisecured`, installs `pisecured`, `pswallet`, and `psminer` into `/opt/pisecure`, writes `/etc/pisecure/pisecured.version`, enables the service at boot, and starts it. It does not replace a node id, `/etc/pisecure/pisecure.env`, a wallet, or `blk*.dat`.

`install-oneclick.sh` does the same download for the latest aarch64 or x86_64 release. It installs ca-certificates, curl, python3, the OpenSSL and curl runtime libraries, and any shared library `ldd` still reports missing. It creates the `pisecure` user and `/var/lib/pisecure`. It does not compile the tree, copy a data directory, or start the daemon.

There is no Docker install and no mock-hardware mode.

An x86_64 archive is [pisecure-v0.2.18-x86_64.tar.gz](https://github.com/UnderhillForge/PiSecure/releases/download/v0.2.18/pisecure-v0.2.18-x86_64.tar.gz). It contains `pisecured`, `pswallet`, and `update.sh`. `psminer` is in the Pi archive only. On x86_64, `update.sh` installs `pisecured` and `pswallet`, enables the service at boot, and starts it. Run the daemon with `--validate-only`. The first start writes a new node id in the data directory. Do not copy that file, `/etc/pisecure/pisecure.env`, or `blk*.dat` onto another machine.

An extra node that can accept inbound port 3141 is dialed by nodes that already have the chain. Bootstrap only introduces addresses. Blocks are not downloaded over HTTPS.

```bash
/opt/pisecure/pisecured --validate-only --host 0.0.0.0 --port 3144 --p2p-port 3141
```

## Run

```bash
systemctl enable --now pisecured
pswallet create
pswallet register AdaPi      # if namelookup live
/opt/pisecure/psminer --once # default wallet
/opt/pisecure/psminer -w AdaPi --once
```

## Wallets

A long address is `ps1` plus 64 hex characters, `hex(SHA256(ed25519 public key))`. Shortnames are unique. Reserved names: foundation, validator, stakers, loans, operator.

Keys live in `/var/lib/pisecure/wallets/*.json`. Back them up. A lost key cannot spend those coins.

Grandfather strings `operator` and `student` still spend when that key file exists.

## Ports

- WebSocket JSON-RPC: **3144**
- P2P: **3141**

`https://bootstrap.pisecure.org` is a helper directory. Sync does not need it.

## OTA

After listen, and again every 6 hours (`PISECURE_UPDATE_INTERVAL_SEC`), `pisecured` reads `https://api.github.com/repos/UnderhillForge/PiSecure/releases/latest`. It compares that tag with `/etc/pisecure/pisecured.version`, or with the compile-time tag when the file is empty. aarch64 downloads `pisecure-pi5-v*-aarch64.tar.gz`. x86_64 downloads `pisecure-v*-x86_64.tar.gz`. The sha256 must match `SHA256SUMS` inside the archive, or the hash in the release notes.

The systemd unit starts with `--apply-update`. A newer tag is extracted as `pisecured` only, written to `/opt/pisecure/pisecured.new`, renamed over `/opt/pisecure/pisecured`, recorded in the version file, and the service restarts. A failed HTTP check, a bad hash, or a tag that is not newer logs one line and keeps serving. `--apply-update=ask` only logs. `--no-update-check` and `PISECURE_NO_UPDATE=1` skip the check. The archive is not allowed to replace wallets, env, or `blk*.dat`.

`pswallet` asks on a tty before it downloads a newer release. A yes runs `update.sh`, which installs the binaries in that archive, restarts `pisecured`, and the wallet starts again as the new binary. On a Pi, `psminer` asks the same way, then starts the new miner after that install. `psminer` is shipped in the Pi archive and is not built from this repo.
