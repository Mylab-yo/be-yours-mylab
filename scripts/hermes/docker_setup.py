"""Deploy Hermes Agent via Docker on the VPS.

Approach:
1. Ensure /root/.hermes exists fresh
2. Write .env with ANTHROPIC + OPENAI workaround + TELEGRAM creds
3. Write docker-compose.yml at /root/hermes/
4. Bring up container, tail logs
5. Bootstrap Telegram allowlist (separate step after first message)

Required env vars:
  HERMES_ANTHROPIC_KEY     -- sk-ant-api03-...
  HERMES_TELEGRAM_TOKEN    -- 1234:ABC...
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

ANTHROPIC = os.environ["HERMES_ANTHROPIC_KEY"]
TG_TOKEN = os.environ["HERMES_TELEGRAM_TOKEN"]

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

# --- 1. fresh /root/.hermes directory
print("[1/4] Reset /root/.hermes")
ssh.exec_command("rm -rf /root/.hermes && mkdir -p /root/.hermes && mkdir -p /root/hermes")[1].read()

# --- 2. Write .env (workaround: OPENAI_API_KEY = ANTHROPIC key)
env_content = f"""# Hermes Agent .env — managed by docker_setup.py
# LLM provider — Anthropic direct
ANTHROPIC_API_KEY={ANTHROPIC}

# WORKAROUND for Hermes 0.16.0 routing bug:
# Hermes uses OpenAI SDK to hit Anthropic's OpenAI-compat endpoint.
# OpenAI SDK reads OPENAI_API_KEY by default. Anthropic accepts the same
# key value as Bearer auth on its /v1/chat/completions endpoint, so we
# set OPENAI_API_KEY to the same Anthropic key.
OPENAI_API_KEY={ANTHROPIC}

# Telegram messaging gateway
TELEGRAM_BOT_TOKEN={TG_TOKEN}
# TELEGRAM_ALLOWED_USERS will be populated by bootstrap_allowlist.py after first message
TELEGRAM_ALLOWED_USERS=
# Temporary bootstrap — locked down to allowlist after capturing user_id
GATEWAY_ALLOW_ALL_USERS=true
"""
with sftp.open("/root/.hermes/.env", "w") as f:
    f.write(env_content)
sftp.chmod("/root/.hermes/.env", 0o600)
print("  .env written (chmod 600)")

# --- 3. Write config.yaml with proper Anthropic provider config
config_content = """# Hermes Agent config — managed by docker_setup.py

model:
  default: "claude-opus-4-6"
  provider: anthropic
  # base_url intentionally omitted: provider=anthropic defaults to https://api.anthropic.com

# Pin auxiliary tasks to "main" so they don't try OpenRouter/Nous Portal
auxiliary:
  vision:
    provider: "main"
  web_extract:
    provider: "main"
  session_search:
    provider: "main"

agent:
  max_turns: 60

# Reasonable session reset (gateway-specific)
session_reset:
  mode: both
  idle_minutes: 1440
  at_hour: 4
"""
with sftp.open("/root/.hermes/config.yaml", "w") as f:
    f.write(config_content)
print("  config.yaml written")

# --- 4. Write docker-compose.yml
compose = """services:
  hermes:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-gateway
    restart: unless-stopped
    command: gateway run
    volumes:
      - /root/.hermes:/opt/data
    deploy:
      resources:
        limits:
          memory: 2G
"""
with sftp.open("/root/hermes/docker-compose.yml", "w") as f:
    f.write(compose)
print("  /root/hermes/docker-compose.yml written")

sftp.close()

# --- 5. Bring container up + show logs
for cmd, label in [
    ("cd /root/hermes && docker compose up -d 2>&1", "compose up"),
    ("sleep 5 && docker ps --filter name=hermes-gateway --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", "container status"),
    ("docker logs hermes-gateway 2>&1 | tail -30", "container startup logs"),
]:
    print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        for line in err.splitlines():
            if line.strip() and "Pulling" not in line and "Pulled" not in line:
                print(f"[stderr] {line}")
    print(f"[rc={rc}]")

ssh.close()
