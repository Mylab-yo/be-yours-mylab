"""Inspect Hermes config templates to know what to set."""
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

HOST = os.environ["VPS_HOST"]
USER = os.environ["VPS_USER"]
PASS = os.environ["VPS_PASS"]
PORT = int(os.environ.get("VPS_PORT", "22"))

CMDS = [
    ("hermes version", "hermes --version 2>&1 | head -5"),
    ("hermes config show", "hermes config show 2>&1 | head -50"),
    (".env content", "cat /root/.hermes/.env"),
    ("config.yaml content", "cat /root/.hermes/config.yaml"),
    ("hermes config set --help", "hermes config set --help 2>&1 | head -40"),
    ("hermes model --help", "hermes model --help 2>&1 | head -40"),
    ("hermes gateway --help", "hermes gateway --help 2>&1 | head -40"),
    ("hermes doctor", "hermes doctor 2>&1 | tail -40"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
for label, cmd in CMDS:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    print(f"\n=== {label} ===")
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}", file=sys.stderr)
ssh.close()
