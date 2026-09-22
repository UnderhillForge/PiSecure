# PiSecure

Validator and peer-to-peer node for a Raspberry Pi chain. The daemon is `pisecured`. Mining is a separate release binary, not this source tree.

## Run a validator

Debian aarch64 or Raspberry Pi OS. Any CPU can validate. It does not need to be a Pi.

```bash
pisecured --validate-only --host 0.0.0.0 --port 3144 --p2p-port 3141
```

WebSocket JSON-RPC is port **3144**. P2P is port **3141**.

Sync from a peer:

```bash
pisecured --validate-only --datadir /var/lib/pisecure-sync \
  --host 127.0.0.1 --port 13144 \
  --p2p-bind 127.0.0.1 --p2p-port 31411 \
  --peer 192.168.68.77:3141
```

## Mine

Download `psminer` from [GitHub Releases](https://github.com/UnderhillForge/PiSecure/releases). Binary only. Official Raspberry Pi 2, 3, 4, or 5.

## Updates

OTA packages are GitHub Releases on this repository. No token is required once the repository is public.

Native packages and systemd are the install path. See `docs/PI5_PISECURED.md`.
