"""Check VPS environment before Hermes install."""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

HOST = os.environ["VPS_HOST"]
USER = os.environ["VPS_USER"]
PASS = os.environ["VPS_PASS"]
PORT = int(os.environ.get("VPS_PORT", "22"))

CMDS = [
    ("OS", "cat /etc/os-release | grep -E '^(NAME|VERSION)='"),
    ("Kernel", "uname -r"),
    ("RAM", "free -h | head -2"),
    ("Disk root", "df -h / | tail -1"),
    ("Python", "which python3 && python3 --version"),
    ("Node", "which node && node --version 2>/dev/null || echo 'node not found'"),
    ("ripgrep", "which rg && rg --version | head -1 || echo 'rg not found'"),
    ("ffmpeg", "which ffmpeg && ffmpeg -version | head -1 || echo 'ffmpeg not found'"),
    ("uv", "which uv && uv --version || echo 'uv not found'"),
    ("hermes existant", "ls -la ~/.hermes 2>/dev/null || echo 'no ~/.hermes'"),
    ("Docker running", "docker ps --format 'table {{.Names}}\\t{{.Status}}' | head -20"),
    ("Listening ports", "ss -tlnp | grep -E ':(22|80|443|3000|5432|8069|8070|8080|8443) ' | head -20"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
print(f"Connected to {USER}@{HOST}\n")
for label, cmd in CMDS:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    print(f"=== {label} ===")
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}", file=sys.stderr)
    print()
ssh.close()
