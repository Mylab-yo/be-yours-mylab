"""Stop and disable Hermes gateway service (keeps install in place)."""
import os
import sys
import time
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

# Each as separate exec so paramiko sends them clean
for cmd in [
    "/usr/bin/systemctl stop hermes-gateway",
    "/usr/bin/systemctl disable hermes-gateway",
    "/usr/bin/systemctl is-active hermes-gateway",
    "/usr/bin/systemctl is-enabled hermes-gateway",
    "ps -ef | grep -E 'hermes_cli.main gateway' | grep -v grep | head -3",
]:
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}")
    print(f"[rc={rc}]")

ssh.close()
