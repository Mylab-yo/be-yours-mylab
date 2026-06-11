"""Install Hermes Agent on the VPS (root, non-interactive, no browser)."""
import os
import sys
import time
from pathlib import Path

import paramiko
from dotenv import load_dotenv

# Force UTF-8 stdout on Windows so the installer banner doesn't crash
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

INSTALL_CMD = (
    "set -e && "
    "export NON_INTERACTIVE=true && "
    "export DEBIAN_FRONTEND=noninteractive && "
    "curl -fsSL https://hermes-agent.nousresearch.com/install.sh "
    "| bash -s -- --skip-setup --non-interactive --skip-browser"
)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

print(f"[i] Streaming Hermes installer on {USER}@{HOST}...\n")

transport = ssh.get_transport()
chan = transport.open_session()
chan.get_pty()
chan.exec_command(INSTALL_CMD)

start = time.time()
buf = b""
while True:
    if chan.recv_ready():
        data = chan.recv(4096)
        sys.stdout.write(data.decode(errors="replace"))
        sys.stdout.flush()
        buf += data
    if chan.exit_status_ready() and not chan.recv_ready():
        break
    if time.time() - start > 1200:
        print("\n[!] Timeout 20 min", file=sys.stderr)
        break
    time.sleep(0.2)

rc = chan.recv_exit_status()
print(f"\n[i] Install exit code: {rc} (elapsed {int(time.time() - start)}s)")
ssh.close()
sys.exit(rc)
