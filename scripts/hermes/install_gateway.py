"""Install + start Hermes gateway as a systemd system service."""
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

HOST = os.environ["VPS_HOST"]
USER = os.environ["VPS_USER"]
PASS = os.environ["VPS_PASS"]
PORT = int(os.environ.get("VPS_PORT", "22"))


def run(ssh, cmd, *, get_pty=True, label=None):
    if label:
        print(f"\n=== {label} ===")
    chan = ssh.get_transport().open_session()
    if get_pty:
        chan.get_pty()
    chan.exec_command(cmd)
    while True:
        if chan.recv_ready():
            sys.stdout.write(chan.recv(4096).decode(errors="replace"))
            sys.stdout.flush()
        if chan.recv_stderr_ready():
            sys.stderr.write(chan.recv_stderr(4096).decode(errors="replace"))
        if (
            chan.exit_status_ready()
            and not chan.recv_ready()
            and not chan.recv_stderr_ready()
        ):
            break
        time.sleep(0.05)
    print(f"\n[rc={chan.recv_exit_status()}]")


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# --accept-hooks goes BEFORE the subcommand
run(
    ssh,
    "hermes --accept-hooks gateway install --system 2>&1",
    label="hermes --accept-hooks gateway install --system",
)

# After install --system, start the service
run(
    ssh,
    "sleep 2 && systemctl list-units --all 'hermes*' --no-pager 2>&1 | head -20 "
    "&& echo '---' && systemctl status hermes-gateway --no-pager 2>&1 | head -30 "
    "|| systemctl status hermes --no-pager 2>&1 | head -30",
    label="systemd unit status",
)

ssh.close()
