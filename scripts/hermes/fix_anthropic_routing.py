"""Fix Hermes config so all requests go to native Anthropic.

Problem: config.yaml had `model.base_url: https://openrouter.ai/api/v1` left
over from the template. With `provider: anthropic` BUT base_url still set,
Hermes still POSTs to OpenRouter (with a None bearer because we never set
OPENROUTER_API_KEY).

Fix:
  1. Remove the `base_url` line from the `model:` section.
  2. Pin model to canonical Anthropic name (no `anthropic/` prefix).
  3. Disable auxiliary OpenRouter/Nous fallbacks — pin auxiliaries to "main"
     so they reuse the Anthropic config instead of trying OpenRouter.

Then restart the systemd service and validate via `hermes config show`.
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

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.environ["VPS_HOST"],
    port=int(os.environ.get("VPS_PORT", "22")),
    username=os.environ["VPS_USER"],
    password=os.environ["VPS_PASS"],
    timeout=15,
)

# Pull current config.yaml via SFTP, edit in Python (safer than sed), push back
sftp = ssh.open_sftp()
with sftp.open("/root/.hermes/config.yaml", "r") as f:
    cfg = f.read().decode("utf-8")

# Backup first
with sftp.open("/root/.hermes/config.yaml.bak-pre-anthropic-fix", "w") as f:
    f.write(cfg)
print("[i] backup: /root/.hermes/config.yaml.bak-pre-anthropic-fix")

# 1) Remove `base_url: ...` line inside the `model:` block (the very next
# non-comment occurrence). Simplest: comment it out.
new_lines = []
in_model_block = False
for line in cfg.splitlines():
    stripped = line.strip()
    if stripped == "model:":
        in_model_block = True
        new_lines.append(line)
        continue
    # Detect end of model block: a new top-level key (no leading whitespace and ends with ':')
    if in_model_block and line and not line.startswith((" ", "\t", "#")) and line.endswith(":"):
        in_model_block = False
    # Inside model block: handle base_url and default
    if in_model_block:
        if stripped.startswith("base_url:"):
            new_lines.append("  # base_url: removed — provider=anthropic uses api.anthropic.com directly")
            continue
        if stripped.startswith("default:"):
            # Pin to canonical Anthropic name
            new_lines.append('  default: "claude-opus-4-5"')
            continue
    new_lines.append(line)
cfg2 = "\n".join(new_lines) + "\n"

# 2) Append an auxiliary section forcing "main" (= our Anthropic config) for
# vision/web_extract/session_search/compression so they never try OpenRouter.
if "\nauxiliary:" not in cfg2 and "\n# auxiliary:" not in cfg2.replace("# auxiliary:", "\n# auxiliary:"):
    # Most templates ship with a commented `# auxiliary:` block — append our
    # active one at the very end so it overrides defaults.
    cfg2 += """
# === Added by fix_anthropic_routing.py ===
auxiliary:
  vision:
    provider: "main"
  web_extract:
    provider: "main"
  session_search:
    provider: "main"
"""

with sftp.open("/root/.hermes/config.yaml", "w") as f:
    f.write(cfg2)
sftp.close()
print("[i] config.yaml patched")

# Print the resulting model + auxiliary sections for verification
for cmd, label in [
    ("sed -n '/^model:/,/^[a-z]/p' /root/.hermes/config.yaml | head -20", "PATCHED model: section"),
    ("grep -A 6 '^auxiliary:' /root/.hermes/config.yaml || echo 'no explicit auxiliary section'", "PATCHED auxiliary: section"),
    ("/usr/bin/systemctl enable hermes-gateway", "re-enable systemd unit"),
    ("/usr/bin/systemctl restart hermes-gateway && sleep 4 && /usr/bin/systemctl is-active hermes-gateway", "restart + status"),
    ("hermes config show 2>&1 | sed -n '/Model/,/Display/p'", "hermes config show (Model section)"),
    ("tail -20 /root/.hermes/logs/gateway.log", "fresh gateway log"),
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

ssh.close()
