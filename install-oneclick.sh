#!/bin/sh
# Download the latest PiSecure release for this machine and install the binaries.
# Installs the runtime libraries those binaries need. Does not copy a node id,
# env file, wallet, or blk*.dat, and does not enable or start pisecured.
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

# Bookworm publishes libssl3 and libcurl4. Trixie publishes libssl3t64 and
# libcurl4t64. Install the name this release has.
install_named() {
  pkg=$1
  fallback=$2
  if apt-cache show "$pkg" >/dev/null 2>&1; then
    apt-get install -y "$pkg"
    return
  fi
  if [ -n "$fallback" ] && apt-cache show "$fallback" >/dev/null 2>&1; then
    apt-get install -y "$fallback"
    return
  fi
  echo "package not found: $pkg" >&2
  exit 1
}

apt-get update
install_named ca-certificates ""
install_named curl ""
install_named python3 ""
install_named libssl3 libssl3t64
install_named libcurl4 libcurl4t64

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

# libwebsockets ships under a different package name on each Debian release.
# Install the runtime package that provides a soname ldd could not find.
# Do not install a compiler, cmake, or a -dev package.
missing=$tmpdir/missing-sonames
: >"$missing"
for bin in pisecured pswallet psminer; do
  path=/opt/pisecure/$bin
  if [ ! -f "$path" ]; then
    continue
  fi
  ldd "$path" >"$tmpdir/ldd-$bin.txt" 2>/dev/null || true
  while IFS= read -r line; do
    case "$line" in
      *"not found"*)
        printf '%s\n' "$line" | awk '{print $1}' >>"$missing"
        ;;
    esac
  done <"$tmpdir/ldd-$bin.txt"
done
if [ -s "$missing" ]; then
  sort -u "$missing" -o "$missing"
  if ! command -v apt-file >/dev/null 2>&1; then
    apt-get install -y apt-file
  fi
  apt-file update
  while IFS= read -r soname; do
    [ -n "$soname" ] || continue
    escaped=$(printf '%s\n' "$soname" | sed 's/\./\\./g')
    pkg=$(apt-file search -x "/${escaped}\$" | awk -F: '$1 !~ /-dev$/ && $1 !~ /-dbg$/ { print $1; exit }')
    if [ -z "$pkg" ]; then
      echo "no Debian package provides $soname" >&2
      exit 1
    fi
    apt-get install -y "$pkg"
  done <"$missing"
fi
for bin in pisecured pswallet psminer; do
  path=/opt/pisecure/$bin
  if [ ! -f "$path" ]; then
    continue
  fi
  if ldd "$path" 2>/dev/null | grep -q 'not found'; then
    echo "unresolved library in $path" >&2
    ldd "$path" >&2 || true
    exit 1
  fi
done

if ! getent group pisecure >/dev/null 2>&1; then
  groupadd --system pisecure
fi
if ! getent passwd pisecure >/dev/null 2>&1; then
  useradd --system --gid pisecure --no-create-home --home-dir /var/lib/pisecure --shell /usr/sbin/nologin pisecure
fi
# Create the data directories. Do not replace an existing env file, node id, or blocks.
install -d -o pisecure -g pisecure -m 0755 /var/lib/pisecure
install -d -o pisecure -g pisecure -m 0750 /var/lib/pisecure/wallets
install -d -m 0755 /etc/pisecure

if [ -f "$tmpdir/pisecured.service" ]; then
  install -m 0644 "$tmpdir/pisecured.service" /etc/systemd/system/pisecured.service
  systemctl daemon-reload
fi

echo "Installed into /opt/pisecure."
echo "Enable with: systemctl enable --now pisecured"
echo "An existing pisecure.env, node id, and blocks directory were left in place."
