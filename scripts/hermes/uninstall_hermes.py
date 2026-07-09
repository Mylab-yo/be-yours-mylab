"""Fully uninstall Hermes Agent from the VPS — service, code, config, data."""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.environ["VPS_HOST"],
    port=int(os.environ.get("VPS_PORT", "22")),
    username=os.environ["VPS_USER"],
    password=os.environ["VPS_PASS"],
    timeout=15,
)

STEPS = [
    ("disk usage BEFORE", "df -h / | tail -1 && du -sh /usr/local/lib/hermes-agent /root/.hermes 2>/dev/null"),
    ("stop + disable systemd", "/usr/bin/systemctl stop hermes-gateway 2>&1; /usr/bin/systemctl disable hermes-gateway 2>&1"),
    ("remove systemd unit + override", "rm -f /etc/systemd/system/hermes-gateway.service && rm -rf /etc/systemd/system/hermes-gateway.service.d"),
    ("daemon-reload", "/usr/bin/systemctl daemon-reload && /usr/bin/systemctl reset-failed 2>&1 | head -5"),
    ("remove install dir", "rm -rf /usr/local/lib/hermes-agent"),
    ("remove hermes launcher", "rm -f /usr/local/bin/hermes /usr/bin/hermes ~/.local/bin/hermes 2>&1 | head -3"),
    ("remove user data ~/.hermes", "rm -rf /root/.hermes"),
    ("kill leftover processes", "pkill -f 'hermes_cli' 2>&1; pkill -f 'hermes-agent' 2>&1; sleep 1; ps -ef | grep -E 'hermes' | grep -v grep || echo 'no leftover hermes process'"),
    ("disk usage AFTER", "df -h / | tail -1"),
    ("verify hermes command gone", "which hermes 2>&1 || echo 'hermes binary removed OK'"),
    ("verify /root cleanup", "ls -la /root/ | grep -i hermes || echo 'no hermes traces in /root'"),
    ("verify systemd cleanup", "/usr/bin/systemctl list-unit-files | grep -i hermes || echo 'no hermes systemd units left'"),
]

for label, cmd in STEPS:
    print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err and "tar:" not in err and "Removed" not in err:
        # Show stderr only if it's not the normal "Removed symlink" messages
        for line in err.splitlines():
            if "Removed" not in line and "Failed to" not in line and line.strip():
                print(f"[stderr] {line}")
            elif "Removed" in line:
                print(line)
    print(f"[rc={rc}]")

ssh.close()
print("\n✓ Uninstall complete. Remaining manual cleanup:")
print("  - Anthropic key: revoke 'hermes-vps' at https://console.anthropic.com/settings/keys")
print("  - Telegram bot: delete @mylab_hermes_bot via @BotFather → /mybots → MyLab Hermes → Delete Bot")
