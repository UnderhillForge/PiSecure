# PiSecure

`pisecured` is the validator and peer-to-peer node. It runs on Debian aarch64 and Raspberry Pi OS under systemd.

## Validate

Any CPU can validate. A Pi is not required.

```bash
pisecured --validate-only --host 0.0.0.0 --port 3144 --p2p-port 3141
```

- WebSocket JSON-RPC: **3144**
- P2P: **3141**

There is no Docker install and no mock-hardware mode.

Sync from a peer:

```bash
pisecured --validate-only --datadir /var/lib/pisecure-sync \
  --host 127.0.0.1 --port 13144 \
  --p2p-bind 127.0.0.1 --p2p-port 31411 \
  --peer 192.168.68.77:3141
```

The unit file is `deploy/pisecured.service`. Bring-up notes are in `docs/PI5_PISECURED.md`.

## Mine

Download the `psminer` binary from [GitHub Releases](https://github.com/UnderhillForge/PiSecure/releases). Raspberry Pi 2, 3, 4, or 5 only. The miner source is not in this repository.

## Updates

OTA packages are GitHub Releases on this repository. No token is required once the repository is public.
