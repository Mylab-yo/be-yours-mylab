"""Run a single command on the VPS, stream all output to stdout.

Usage: python ssh_run.py "<command>"
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

if len(sys.argv) < 2:
    print("Usage: ssh_run.py '<command>'", file=sys.stderr)
    sys.exit(2)
CMD = sys.argv[1]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)

chan = ssh.get_transport().open_session()
chan.get_pty()
chan.set_combine_stderr(True)
chan.exec_command(CMD)
while True:
    if chan.recv_ready():
        sys.stdout.write(chan.recv(4096).decode(errors="replace"))
        sys.stdout.flush()
    if chan.exit_status_ready() and not chan.recv_ready():
        break
    time.sleep(0.05)
rc = chan.recv_exit_status()
sys.stdout.write(f"\n[rc={rc}]\n")
ssh.close()
sys.exit(rc)
