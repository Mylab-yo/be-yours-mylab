"""Find why Hermes is referencing OpenRouter despite Anthropic provider config."""
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

CMDS = [
    # What does current config look like?
    ("config show MODEL section", "hermes config show 2>&1 | sed -n '/Model/,/Display/p'"),
    # config.yaml — is base_url still pointing to OpenRouter?
    ("config.yaml model section", "sed -n '/^model:/,/^[a-z]/p' /root/.hermes/config.yaml | head -30"),
    # .env — are there any OpenRouter keys leaked?
    ("env OPENROUTER refs", "grep -i openrouter /root/.hermes/.env || echo 'no openrouter refs in .env'"),
    # In the last gateway log: which provider was actually called?
    ("last 50 gateway log lines", "tail -50 /root/.hermes/logs/gateway.log"),
    # What did Hermes ACTUALLY send to Anthropic? Look at sessions
    ("latest session file", "ls -t /root/.hermes/sessions/ 2>/dev/null | head -3"),
    # Is there a system prompt referencing openrouter?
    ("system prompt mention OpenRouter?", "grep -ri openrouter /usr/local/lib/hermes-agent/hermes_cli/ 2>/dev/null | grep -i 'system_prompt\\|description\\|prompt' | head -10"),
]

for label, cmd in CMDS:
    print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out[:3000])
        if len(out) > 3000:
            print(f"... (truncated, {len(out)} total chars)")
    if err and "tar:" not in err:
        print(f"[stderr] {err[:500]}")
    print(f"[rc={rc}]")

ssh.close()
