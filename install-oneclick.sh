#!/bin/sh
# Download the latest PiSecure release for this machine and install the binaries.
# Does not copy a node id, env file, wallet, or blk*.dat.
set -eu

api="https://api.github.com/repos/UnderhillForge/PiSecure/releases/latest"
case "$(uname -m)" in
  aarch64|arm64)
    prefix="pisecure-pi5-v"
    suffix="-aarch64.tar.gz"
    ;;
  x86_64|amd64)
    prefix="pisecure-v"
    suffix="-x86_64.tar.gz"
    ;;
  *)
    echo "unsupported architecture $(uname -m)" >&2
    exit 1
    ;;
esac

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
curl -fsSL -A pisecure -o "$tmpdir/release.json" "$api"

python3 - "$tmpdir" "$prefix" "$suffix" <<'PY'
import hashlib, json, os, sys, tarfile, urllib.request

tmpdir, prefix, suffix = sys.argv[1:]
doc = json.load(open(os.path.join(tmpdir, "release.json"), encoding="utf-8"))
asset = None
sums = None
for item in doc.get("assets", []):
    name = item.get("name", "")
    if name.startswith(prefix) and name.endswith(suffix):
        asset = item
    if name == "SHA256SUMS":
        sums = item
if asset is None:
    sys.exit("no release archive for this architecture")

def fetch(url, dest):
    urllib.request.urlretrieve(url, dest)

archive = os.path.join(tmpdir, asset["name"])
fetch(asset["browser_download_url"], archive)
digest = hashlib.sha256(open(archive, "rb").read()).hexdigest()
if sums is not None:
    sums_path = os.path.join(tmpdir, "SHA256SUMS")
    fetch(sums["browser_download_url"], sums_path)
    matched = False
    for line in open(sums_path, encoding="utf-8"):
        parts = line.split()
        if len(parts) >= 2 and parts[-1].endswith(asset["name"]) and parts[0].lower() == digest:
            matched = True
    if not matched:
        sys.exit("release sha256 does not match")

with tarfile.open(archive, "r:gz") as tar:
    for member in tar.getmembers():
        base = os.path.basename(member.name)
        if base not in {"pisecured", "pswallet", "psminer", "pisecured.service"}:
            continue
        if not member.isfile():
            continue
        dest = os.path.join(tmpdir, base)
        src = tar.extractfile(member)
        if src is None:
            continue
        with open(dest, "wb") as out:
            out.write(src.read())
        print(dest)
PY

install -d /opt/pisecure
if [ -f "$tmpdir/pisecured" ]; then
  install -m 0755 "$tmpdir/pisecured" /opt/pisecure/pisecured
fi
if [ -f "$tmpdir/pswallet" ]; then
  install -m 0755 "$tmpdir/pswallet" /opt/pisecure/pswallet
fi
if [ -f "$tmpdir/psminer" ]; then
  install -m 0755 "$tmpdir/psminer" /opt/pisecure/psminer
fi
if [ -f "$tmpdir/pisecured.service" ]; then
  install -m 0644 "$tmpdir/pisecured.service" /etc/systemd/system/pisecured.service
  systemctl daemon-reload
fi

echo "Installed into /opt/pisecure."
echo "Enable with: systemctl enable --now pisecured"
echo "The archive did not change /var/lib/pisecure or /etc/pisecure/pisecure.env."
