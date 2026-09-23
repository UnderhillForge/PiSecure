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

An extra node syncs from this Pi over P2P. Bootstrap is not required:

```bash
/opt/pisecure/pisecured --validate-only --peer 192.168.68.77:3141
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

`psminer` checks GitHub Releases on this repository. It asks before it downloads an update.
