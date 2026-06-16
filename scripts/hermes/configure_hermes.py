"""Configure Hermes on the VPS: Anthropic provider + Telegram gateway.

Step 1: append secrets to /root/.hermes/.env
Step 2: pin provider to direct Anthropic
Step 3: install + start the gateway systemd service

Secrets are passed via env vars so they never touch the repo on disk.
Telegram allowlist bootstrap (capturing user_id) is done in a separate step.
"""
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

ANTHROPIC_KEY = os.environ["HERMES_ANTHROPIC_KEY"]
TELEGRAM_TOKEN = os.environ["HERMES_TELEGRAM_TOKEN"]

# Lines to append. GATEWAY_ALLOW_ALL_USERS=true is TEMPORARY (bootstrap-only) —
# we'll lock down to TELEGRAM_ALLOWED_USERS once we capture Yoann's user_id.
ENV_APPEND = f"""
# === Added by configure_hermes.py ({time.strftime('%Y-%m-%d %H:%M')}) ===
ANTHROPIC_API_KEY={ANTHROPIC_KEY}
TELEGRAM_BOT_TOKEN={TELEGRAM_TOKEN}
TELEGRAM_ALLOWED_USERS=
GATEWAY_ALLOW_ALL_USERS=true
"""


def run(ssh, cmd, *, get_pty=False, label=None):
    if label:
        print(f"\n=== {label} ===")
    transport = ssh.get_transport()
    chan = transport.open_session()
    if get_pty:
        chan.get_pty()
    chan.exec_command(cmd)
    out = b""
    while True:
        if chan.recv_ready():
            data = chan.recv(4096)
            sys.stdout.write(data.decode(errors="replace"))
            sys.stdout.flush()
            out += data
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(4096)
            sys.stderr.write(data.decode(errors="replace"))
            out += data
        if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
            break
        time.sleep(0.05)
    rc = chan.recv_exit_status()
    print(f"\n[rc={rc}]")
    return rc, out.decode(errors="replace")


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

# --- Step 1: write secrets to /root/.hermes/.env via SFTP (avoids shell quoting)
print("[1/4] Appending secrets to /root/.hermes/.env via SFTP")
sftp = ssh.open_sftp()
with sftp.open("/root/.hermes/.env", "a") as f:
    f.write(ENV_APPEND)
sftp.chmod("/root/.hermes/.env", 0o600)
sftp.close()
print("  OK (chmod 600)")

# --- Step 2: pin provider to direct Anthropic in config.yaml
run(
    ssh,
    "hermes config set model.provider anthropic",
    get_pty=True,
    label="[2/4] hermes config set model.provider anthropic",
)

# --- Step 3: install gateway as systemd service
run(
    ssh,
    "hermes gateway install --accept-hooks 2>&1",
    get_pty=True,
    label="[3/4] hermes gateway install",
)

# --- Step 4: status check (auto-starts after install on systemd)
run(
    ssh,
    "sleep 3 && systemctl status 'hermes-gateway*' --no-pager 2>&1 | head -40 "
    "&& echo '---' && hermes gateway status 2>&1 | head -30",
    label="[4/4] gateway status",
)

ssh.close()
