#!/bin/sh
# Install the binaries next to this script and start pisecured.
# aarch64 installs pisecured, psminer, and pswallet.
# x86_64 installs psminer and pswallet only. The x86 pisecured binary stays
# in the archive for the daemon's own update check.
# Does not copy or replace a node id, env file, wallet, or blk*.dat.
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi

here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

case "$(uname -m)" in
  aarch64|arm64)
    replace_daemon=1
    set -- pisecured pswallet psminer
    ;;
  x86_64|amd64)
    replace_daemon=0
    set -- pswallet psminer
    ;;
  *)
    echo "unsupported architecture $(uname -m)" >&2
    exit 1
    ;;
esac

binary_matches_machine() {
  desc=$(file -b "$1")
  case "$(uname -m)" in
    aarch64|arm64)
      case "$desc" in
        *aarch64*) return 0 ;;
      esac
      ;;
    x86_64|amd64)
      case "$desc" in
        *x86-64*|*x86_64*) return 0 ;;
      esac
      ;;
  esac
  echo "binary does not match $(uname -m): $1" >&2
  return 1
}

for bin in "$@"; do
  if [ ! -f "$here/$bin" ]; then
    echo "missing $bin next to update.sh" >&2
    exit 1
  fi
  binary_matches_machine "$here/$bin"
done

if ! getent group pisecure >/dev/null 2>&1; then
  groupadd --system pisecure
fi
if ! getent passwd pisecure >/dev/null 2>&1; then
  useradd --system --gid pisecure --no-create-home --home-dir /var/lib/pisecure --shell /usr/sbin/nologin pisecure
fi

if [ ! -d /var/lib/pisecure ]; then
  install -d -o pisecure -g pisecure -m 0755 /var/lib/pisecure
fi
if [ ! -d /var/lib/pisecure/wallets ]; then
  install -d -o pisecure -g pisecure -m 0750 /var/lib/pisecure/wallets
fi
if [ ! -d /etc/pisecure ]; then
  install -d -m 0755 /etc/pisecure
fi

unit_installed=0
if [ -f /etc/systemd/system/pisecured.service ] || systemctl cat pisecured.service >/dev/null 2>&1; then
  unit_installed=1
  systemctl stop pisecured
fi

install -d -o pisecure -g pisecure -m 0755 /opt/pisecure
for bin in "$@"; do
  install -m 0755 -o pisecure -g pisecure "$here/$bin" "/opt/pisecure/$bin"
done

if [ "$replace_daemon" -eq 1 ]; then
  if [ ! -f "$here/VERSION" ]; then
    echo "missing VERSION next to update.sh" >&2
    exit 1
  fi
  ver=$(tr -d ' \t\r\n' <"$here/VERSION")
  case "$ver" in
    ""|*[!0-9.]*)
      echo "VERSION is not a release number" >&2
      exit 1
      ;;
  esac
  printf '%s\n' "$ver" >/etc/pisecure/pisecured.version
  chmod 0644 /etc/pisecure/pisecured.version
fi

if [ "$unit_installed" -eq 0 ]; then
  service=$here/deploy/pisecured.service
  if [ ! -f "$service" ]; then
    service=$here/pisecured.service
  fi
  if [ ! -f "$service" ]; then
    echo "Installed binaries into /opt/pisecure." >&2
    echo "pisecured.service is not on this machine, so it was not enabled." >&2
    exit 1
  fi
  install -m 0644 "$service" /etc/systemd/system/pisecured.service
fi

systemctl daemon-reload
systemctl enable pisecured
enabled=$(systemctl is-enabled pisecured)
if [ "$enabled" != "enabled" ]; then
  echo "pisecured is not enabled at boot ($enabled)" >&2
  exit 1
fi

systemctl start pisecured
if ! systemctl is-active --quiet pisecured; then
  echo "pisecured did not start" >&2
  exit 1
fi

echo "Installed into /opt/pisecure."
echo "pisecured is enabled at boot and the service is active."
if [ "$replace_daemon" -eq 0 ]; then
  echo "The x86_64 pisecured binary was left in place."
fi
