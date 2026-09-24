# PiSecure

PiSecure is a low-power chain for Raspberry Pi. Each block pays **0.200 314ST**. Official Pi 2, 3, 4, and 5 can mine. Any CPU can validate.

## Install

Download the v0.2.1 aarch64 archive from this repo's GitHub Releases and check the sha256 printed on that release:

```bash
curl -fL -O https://github.com/UnderhillForge/PiSecure/releases/download/v0.2.1/pisecure-pi5-v0.2.1-aarch64.tar.gz
sha256sum pisecure-pi5-v0.2.1-aarch64.tar.gz
tar -xzf pisecure-pi5-v0.2.1-aarch64.tar.gz
sudo install -d /opt/pisecure
sudo install -m 0755 pisecured pswallet psminer /opt/pisecure/
sudo cp deploy/pisecured.service /etc/systemd/system/pisecured.service
sudo systemctl daemon-reload
```

There is no Docker install and no mock-hardware mode.

An x86_64 validator is `pisecure-v*-x86_64.tar.gz` on the same release. It is `pisecured` only. Run it with `--validate-only`. The first start writes a new node id in the data directory. Do not copy that file, `/etc/pisecure/pisecure.env`, or `blk*.dat` onto another machine.

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

`pisecured` and `pswallet` read the latest GitHub Release on this repository (`pisecure-pi5-v*-aarch64.tar.gz`). A newer tag is logged with its URL and sha256. Nothing is installed unless the daemon is started with `--apply-update`, or you run `pisecure update download`. `pswallet` asks before it downloads, and the default is no. `psminer` asks before it downloads an update.
