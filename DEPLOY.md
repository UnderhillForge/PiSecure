# PiSecure deploy guide (2026-09-22 restart)

This repo is **private**. Public `curl | bash` from raw.githubusercontent.com will fail for anyone without a token. Clone with GitHub auth, then install from the working tree.

## What is actually deployable today

| Target | How | Notes |
|--------|-----|-------|
| Validator / API node | Docker Compose or Python venv | Works on Mac, Linux, Pi |
| `pisecured` RPC daemon | C++ build + systemd | Needs `libwebsockets-dev` + OpenSSL |
| `psminer` | Private `PiSecure-Miner` repo | Pi hardware only |
| Bootstrap | Separate public `PiSecure-Bootstrap` | Already on Railway at bootstrap.pisecure.org |

## 1. Docker validator (fastest)

```bash
git clone git@github.com:UnderhillForge/PiSecure.git
cd PiSecure
cp .env.example .env
docker compose up --build -d
docker compose logs -f
```

Healthcheck runs `pisecure status`. Data lives in named volumes.

## 2. Native Linux / Pi node

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential cmake \
  libssl-dev libffi-dev libsqlite3-dev libwebsockets-dev pkg-config git

python3 -m venv pisecure_env
source pisecure_env/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
pip install -e .

mkdir -p cpp/pisecured/build && cd cpp/pisecured/build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j"$(nproc)"
cd ../../..

sudo mkdir -p /opt/pisecure /var/lib/pisecure /etc/pisecure
sudo cp cpp/pisecured/build/pisecured /opt/pisecure/
sudo cp deploy/pisecured.service /etc/systemd/system/
sudo cp .env.example /etc/pisecure/pisecure.env
# create system user pisecure and chown data dirs before enable
sudo systemctl daemon-reload
sudo systemctl enable --now pisecured
```

Do **not** use `ProtectHome=read-only` while binaries live under `$HOME`. The unit in `deploy/` assumes `/opt/pisecure`.

## 3. Known issues fixed in this restart

- `pisecured` main was missing `#include <chrono>` and would not compile.
- CLI entry imported a legacy path that does not exist; it now uses `cli_refactored`.
- `bool(os.getenv(...))` treated any set string (including `"0"`) as true.
- Dockerfile had no C++ / libwebsockets packages and a healthcheck command that did not exist.
- Installer advertised a public raw GitHub URL for a private repo.
- systemd snippet wrote `ProtectHome=read-only` against a home-directory install path.

## 4. Still not production-grade (do next)

- `pisecure/core/blockchain.py` is ~150k lines of mixed concerns; needs a real consensus review before mainnet claims.
- Hardware binding / PiHash lives partly here and partly in private miner — do not treat this tree as a complete miner.
- No wallet key encryption audit in this pass.
- Bootstrap integration should be smoke-tested against `https://bootstrap.pisecure.org/health`.
- Add a dedicated `validate --continuous` loop; status is one-shot.

## 5. Smoke checks after deploy

```bash
pisecure --validate-only --mock-hardware version
pisecure --validate-only --mock-hardware status
curl -fsS https://bootstrap.pisecure.org/health
```
