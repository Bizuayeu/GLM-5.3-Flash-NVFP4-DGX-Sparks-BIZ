#!/bin/sh
# One-time install on each host: the GPU clock cap and the telemetry logger.
#   sudo sh install.sh [USER]
# USER runs the logger and owns /var/log/gb10-telemetry; it defaults to the user who ran sudo.
# Files come from the directory of this script.
set -eu
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
user=${1:-${SUDO_USER:-}}
[ -n "$user" ] || { echo "usage: sudo sh install.sh USER (no SUDO_USER to default to)" >&2; exit 1; }
case $user in
  *[!A-Za-z0-9._-]*) echo "not a user name: $user" >&2; exit 1 ;;
esac
id -u "$user" >/dev/null || { echo "no such user: $user" >&2; exit 1; }
group=$(id -gn "$user")
here=$(cd "$(dirname "$0")" && pwd)
install -o root -g root -m 0755 "$here/gb10-telemetry" /usr/local/sbin/gb10-telemetry
sed "s/@SERVICE_USER@/$user/" "$here/gb10-telemetry.service" >/etc/systemd/system/gb10-telemetry.service
chown root:root /etc/systemd/system/gb10-telemetry.service
chmod 0644 /etc/systemd/system/gb10-telemetry.service
install -o root -g root -m 0644 "$here/gb10-clock-cap.service" /etc/systemd/system/gb10-clock-cap.service
install -d -o "$user" -g "$group" -m 0755 /var/log/gb10-telemetry
systemctl daemon-reload
systemctl enable --now gb10-clock-cap.service gb10-telemetry.service
sleep 5
systemctl is-active gb10-clock-cap.service gb10-telemetry.service
nvidia-smi -q -d CLOCK | sed -n '/Locked/,+3p;/Max Clocks/,+2p' | head -8
tail -1 /var/log/gb10-telemetry/*.jsonl
echo "$(hostname): installed for $user"
