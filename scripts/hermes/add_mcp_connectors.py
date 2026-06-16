"""Wire MCP connectors into the Hermes Agent container on the VPS.

Idempotent. Currently wires:
  - n8n  (always — Nous catalog bridge, creds read locally, never printed)

Scaffolded (activate by passing creds via env when running this script):
  - airtable        -> set AIRTABLE_API_KEY
  - google workspace-> handled by a separate OAuth-consent step (see report)

The n8n catalog installer is interactive (input() prompts), which paramiko's
non-TTY exec can't drive. So we replicate it deterministically:
  1. git clone the bridge + build a venv  (idempotent: skipped if .venv exists)
  2. write N8N_BASE_URL + N8N_API_KEY into /root/.hermes/.env via SFTP
     (host path of the container's /opt/data/.env bind mount)
  3. `hermes mcp add n8n --command <venv python> --args <server.py>
       --env N8N_BASE_URL=... N8N_API_KEY=${N8N_API_KEY}`
     The ${N8N_API_KEY} literal is interpolated from .env at load time, so the
     secret lives only in .env (chmod 600), not in config.yaml.
  4. `hermes mcp test n8n` then restart the gateway to load the tools.

Run: python scripts/hermes/add_mcp_connectors.py
"""
import io
import os
import re
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

# --- n8n connection details
N8N_BASE_URL = "https://n8n.startec-paris.com"
ENV_LOCAL = Path(r"D:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
INSTALL_DIR = "/opt/data/mcp-servers/n8n"          # inside container
HOST_ENV = "/root/.hermes/.env"                    # host path of /opt/data/.env
BRIDGE_REPO = "https://github.com/CyberSamuraiX/hermes-n8n-mcp.git"


def read_n8n_api_key() -> str:
    """The n8n JWT lives on its own line under '# Clé API N8N' in .env.local."""
    text = ENV_LOCAL.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^(eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)\s*$",
                  text, re.MULTILINE)
    if not m:
        sys.exit(f"Could not find n8n JWT (eyJ...) in {ENV_LOCAL}")
    return m.group(1)


def run(ssh, cmd, *, timeout=600, label=None, quiet=False):
    if label:
        print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if not quiet:
        if out:
            print(out)
        if err:
            print(err)
        print(f"[rc={rc}]")
    return rc, out, err


def upsert_env(sftp, path, updates: dict):
    """Read host .env, replace/append the given keys, write back (chmod 600)."""
    try:
        with sftp.open(path, "r") as f:
            content = f.read().decode("utf-8", errors="replace")
    except IOError:
        content = ""
    lines = content.splitlines()
    seen = set()
    for i, line in enumerate(lines):
        for k, v in updates.items():
            if re.match(rf"^{re.escape(k)}=", line):
                lines[i] = f"{k}={v}"
                seen.add(k)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    body = "\n".join(lines).rstrip() + "\n"
    with sftp.open(path, "w") as f:
        f.write(body)
    sftp.chmod(path, 0o600)
    print(f"  {path}: set {', '.join(updates)} (chmod 600)")


def main():
    api_key = read_n8n_api_key()

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

    # --- already configured?
    rc, listing, _ = run(ssh, "docker exec hermes-gateway hermes mcp list 2>&1",
                          label="current MCP servers")
    n8n_present = re.search(r"(^|\s)n8n(\s|$)", listing or "") is not None

    # --- 1. clone + venv (idempotent)
    run(
        ssh,
        "docker exec hermes-gateway sh -c '"
        f"test -x {INSTALL_DIR}/.venv/bin/python && echo VENV_OK || ("
        f"mkdir -p /opt/data/mcp-servers && "
        f"git clone --depth 1 {BRIDGE_REPO} {INSTALL_DIR} && "
        f"cd {INSTALL_DIR} && python3 -m venv .venv && "
        f".venv/bin/pip install -q -r requirements.txt && echo VENV_BUILT)'",
        label="n8n bridge clone + venv",
    )

    # --- 2. write creds into host .env (container sees /opt/data/.env)
    print("\n=== write n8n creds to .env ===")
    upsert_env(sftp, HOST_ENV, {
        "N8N_BASE_URL": N8N_BASE_URL,
        "N8N_API_KEY": api_key,
    })

    # --- 3. register the server (literal ${N8N_API_KEY} -> interpolated from .env)
    if n8n_present:
        print("\n=== mcp add n8n === \n  already in config — skipping add")
    else:
        # `mcp add` ends with an interactive "Enable all N tools?" prompt;
        # feed it 'Y' over `docker exec -i` (non-TTY exec can't answer otherwise).
        run(
            ssh,
            "printf 'Y\\n' | docker exec -i hermes-gateway hermes mcp add n8n "
            f"--command {INSTALL_DIR}/.venv/bin/python "
            f"--args {INSTALL_DIR}/server.py "
            "--env 'N8N_BASE_URL=${N8N_BASE_URL}' 'N8N_API_KEY=${N8N_API_KEY}' 2>&1",
            label="mcp add n8n",
        )

    # --- 4. test + restart gateway to load tools
    run(ssh, "docker exec hermes-gateway hermes mcp test n8n 2>&1",
        label="mcp test n8n", timeout=120)
    run(ssh, "cd /root/hermes && docker compose restart 2>&1",
        label="restart gateway", timeout=120)
    run(ssh, "sleep 6 && docker exec hermes-gateway hermes mcp list 2>&1",
        label="final MCP list")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
