"""Hardcode ANTHROPIC_API_KEY into config.yaml (model.api_key) so Hermes'
runtime_provider doesn't depend on .env being loaded before init.

Also writes ANTHROPIC_API_KEY into the systemd unit via override.conf so the
process environment has it from the start (belt-and-suspenders).
"""
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

ANTHROPIC_KEY = os.environ["HERMES_ANTHROPIC_KEY"]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.environ["VPS_HOST"],
    port=int(os.environ.get("VPS_PORT", "22")),
    username=os.environ["VPS_USER"],
    password=os.environ["VPS_PASS"],
    timeout=15,
)

sftp = ssh.open_sftp()

# --- Pull config.yaml, inject api_key under model: section
with sftp.open("/root/.hermes/config.yaml", "r") as f:
    cfg = f.read().decode("utf-8")

# Remove any existing api_key line first (idempotent)
new_lines = []
in_model_block = False
for line in cfg.splitlines():
    stripped = line.strip()
    if stripped == "model:":
        in_model_block = True
        new_lines.append(line)
        continue
    if in_model_block and line and not line.startswith((" ", "\t", "#")) and line.endswith(":"):
        in_model_block = False
    if in_model_block and stripped.startswith("api_key:"):
        continue  # drop old
    new_lines.append(line)
cfg2 = "\n".join(new_lines)

# Insert api_key right after provider: anthropic
cfg2 = cfg2.replace(
    "  provider: anthropic\n",
    f'  provider: anthropic\n  api_key: "{ANTHROPIC_KEY}"\n',
    1,
)

with sftp.open("/root/.hermes/config.yaml", "w") as f:
    f.write(cfg2 + ("\n" if not cfg2.endswith("\n") else ""))
print("[i] config.yaml updated with model.api_key")

# --- Write systemd drop-in override so the env var is also in process env
override_dir = "/etc/systemd/system/hermes-gateway.service.d"
ssh.exec_command(f"mkdir -p {override_dir}")[1].read()
override_content = f"""[Service]
Environment="ANTHROPIC_API_KEY={ANTHROPIC_KEY}"
"""
with sftp.open(f"{override_dir}/anthropic-env.conf", "w") as f:
    f.write(override_content)
sftp.chmod(f"{override_dir}/anthropic-env.conf", 0o600)
print(f"[i] systemd override written: {override_dir}/anthropic-env.conf")

sftp.close()

# --- Reload systemd and restart
for cmd, label in [
    ("/usr/bin/systemctl daemon-reload", "daemon-reload"),
    ("/usr/bin/systemctl restart hermes-gateway", "restart"),
    ("sleep 4 && /usr/bin/systemctl is-active hermes-gateway", "is-active"),
    ("sed -n '/^model:/,/^[a-z]/p' /root/.hermes/config.yaml | head -8 | sed 's|api_key: \"sk-ant-api03-.\\{10\\}.*|api_key: \"sk-ant-api03-...REDACTED\"|'", "PATCHED model: section"),
]:
    print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}")
    print(f"[rc={rc}]")

# Run a one-shot CLI test
print("\n=== one-shot test: hermes -z 'Bonjour, qui es-tu ?' ===")
chan = ssh.get_transport().open_session()
chan.get_pty()
chan.set_combine_stderr(True)
chan.exec_command("hermes -z 'Bonjour, qui es-tu en une phrase ?' 2>&1")
import time
deadline = time.time() + 45
buf = b""
while time.time() < deadline:
    if chan.recv_ready():
        d = chan.recv(4096)
        sys.stdout.write(d.decode(errors="replace"))
        sys.stdout.flush()
        buf += d
    if chan.exit_status_ready() and not chan.recv_ready():
        break
    time.sleep(0.1)
print(f"\n[rc={chan.recv_exit_status()}]")

ssh.close()
