"""Wire the Google Workspace MCP (Gmail + Calendar + Drive) into Hermes, headless.

workspace-mcp normally bootstraps via a browser OAuth flow whose callback lands
on the *server's* localhost — unreachable from Yoann's browser when the server
runs in a remote container. So instead we pre-seed the credential the server
expects, using a refresh token already minted locally (with gmail.modify +
calendar + drive scopes) by google_workspace_oauth_setup.py.

Steps (idempotent):
  1. Push GOOGLE_WS_* + workspace-mcp env into /root/.hermes/.env  (SFTP, no leak)
  2. Ensure venv + `workspace-mcp` installed under /opt/data/mcp-servers/workspace-mcp
  3. Seed the credential for USER via the package's own credential_store API
     (so the on-disk JSON format is exactly what the server reads back)
  4. `hermes mcp add google --command <venv>/bin/workspace-mcp
        --args --single-user --transport stdio --tools gmail calendar drive
               --tool-tier extended
        --env USER_GOOGLE_EMAIL=... GOOGLE_OAUTH_CLIENT_ID=${...} ...`
  5. test + restart gateway

Prereq: .env.vps must contain GOOGLE_WS_CLIENT_ID/SECRET/REFRESH_TOKEN
(produced by google_workspace_oauth_setup.py). Run: python scripts/hermes/add_google_workspace_mcp.py
"""
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

USER_EMAIL = "yoann@mylab-shop.com"
INSTALL_DIR = "/opt/data/mcp-servers/workspace-mcp"
CREDS_DIR = f"{INSTALL_DIR}/credentials"
HOST_ENV = "/root/.hermes/.env"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]

CID = os.environ.get("GOOGLE_WS_CLIENT_ID")
CSECRET = os.environ.get("GOOGLE_WS_CLIENT_SECRET")
RTOKEN = os.environ.get("GOOGLE_WS_REFRESH_TOKEN")
if not (CID and CSECRET and RTOKEN):
    sys.exit("Missing GOOGLE_WS_* in .env.vps — run google_workspace_oauth_setup.py first")


def run(ssh, cmd, *, timeout=600, label=None, get_pty=False):
    if label:
        print(f"\n=== {label} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=get_pty)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err and not get_pty:
        print(err)
    print(f"[rc={rc}]")
    return rc, out, err


def upsert_env(sftp, path, updates: dict):
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
    with sftp.open(path, "w") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    sftp.chmod(path, 0o600)
    print(f"  {path}: set {', '.join(updates)} (chmod 600)")


# Seed script runs INSIDE the container; reads secrets from the sourced .env
# (never on argv). Uses workspace-mcp's own store so the format is correct.
SEED_PY = f'''
import os
from google.oauth2.credentials import Credentials
os.environ["WORKSPACE_MCP_CREDENTIALS_DIR"] = "{CREDS_DIR}"
creds = Credentials(
    token=None,
    refresh_token=os.environ["GOOGLE_WS_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["GOOGLE_WS_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_WS_CLIENT_SECRET"],
    scopes={SCOPES!r},
)
# prove the refresh token + enabled APIs work before we commit
from google.auth.transport.requests import Request
creds.refresh(Request())
print("refresh OK, access token len:", len(creds.token or ""))
from auth.credential_store import get_credential_store
store = get_credential_store()
store.store_credential("{USER_EMAIL}", creds)
back = store.get_credential("{USER_EMAIL}")
print("stored + readback OK:", bool(back and back.refresh_token))
'''


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
        username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15,
    )
    sftp = ssh.open_sftp()

    # 1. creds + server env into .env
    print("=== push GOOGLE_WS_* + workspace-mcp env to .env ===")
    upsert_env(sftp, HOST_ENV, {
        "GOOGLE_WS_CLIENT_ID": CID,
        "GOOGLE_WS_CLIENT_SECRET": CSECRET,
        "GOOGLE_WS_REFRESH_TOKEN": RTOKEN,
        "USER_GOOGLE_EMAIL": USER_EMAIL,
        "WORKSPACE_MCP_CREDENTIALS_DIR": CREDS_DIR,
    })

    # 2. venv + install (idempotent)
    run(ssh,
        "docker exec hermes-gateway sh -c '"
        f"test -x {INSTALL_DIR}/.venv/bin/workspace-mcp && echo INSTALL_OK || ("
        f"mkdir -p {INSTALL_DIR} && python3 -m venv {INSTALL_DIR}/.venv && "
        f"{INSTALL_DIR}/.venv/bin/pip install -q workspace-mcp && echo INSTALLED)'",
        label="install workspace-mcp")

    # 3. seed credential (secrets sourced from .env, not argv)
    seed_b64 = __import__("base64").b64encode(SEED_PY.encode()).decode()
    run(ssh,
        "docker exec hermes-gateway sh -c '"
        f"mkdir -p {CREDS_DIR}; set -a; . /opt/data/.env; set +a; "
        f"echo {seed_b64} | base64 -d | {INSTALL_DIR}/.venv/bin/python -' 2>&1",
        label="seed Google credential", timeout=120)

    # 4a. wrapper script with the server flags baked in — `hermes mcp add --args`
    #     can't carry `--`-prefixed values (argparse eats them as hermes options).
    #     stderr -> logfile: workspace-mcp's verbose banner would otherwise fill
    #     the MCP client's stderr pipe and deadlock the handshake ("Connection
    #     closed" ~15s). Protocol travels on stdout only, so this is safe.
    run_sh = (
        "#!/bin/sh\n"
        f"exec {INSTALL_DIR}/.venv/bin/workspace-mcp "
        "--single-user --transport stdio "
        "--tools gmail calendar drive --tool-tier extended "
        f"2>>{INSTALL_DIR}/server.log\n"
    )
    with sftp.open(f"/root/.hermes/mcp-servers/workspace-mcp/run.sh", "w") as f:
        f.write(run_sh)
    sftp.chmod("/root/.hermes/mcp-servers/workspace-mcp/run.sh", 0o755)
    print(f"\n=== wrapper ===\n  {INSTALL_DIR}/run.sh written (chmod 755)")

    # 4b. register in hermes (feed Y to the 'enable all tools?' prompt)
    rc, listing, _ = run(ssh, "docker exec hermes-gateway hermes mcp list 2>&1",
                         label="current MCP servers")
    if re.search(r"(^|\s)google(\s|$)", listing or ""):
        print("\n=== mcp add google ===\n  already configured — skipping")
    else:
        run(ssh,
            "printf 'Y\\n' | docker exec -i hermes-gateway hermes mcp add google "
            f"--command {INSTALL_DIR}/run.sh "
            "--env "
            "'USER_GOOGLE_EMAIL=${USER_GOOGLE_EMAIL}' "
            "'GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_WS_CLIENT_ID}' "
            "'GOOGLE_OAUTH_CLIENT_SECRET=${GOOGLE_WS_CLIENT_SECRET}' "
            "'WORKSPACE_MCP_CREDENTIALS_DIR=${WORKSPACE_MCP_CREDENTIALS_DIR}' 2>&1",
            label="mcp add google", timeout=180)

    # 4c. ensure enabled (a failed connect during `add` saves it disabled)
    enable_py = (
        'import yaml; p="/opt/data/config.yaml"; c=yaml.safe_load(open(p)); '
        'c["mcp_servers"]["google"]["enabled"]=True; '
        'yaml.safe_dump(c, open(p,"w"), sort_keys=False, default_flow_style=False); '
        'print("google.enabled =", c["mcp_servers"]["google"]["enabled"])'
    )
    enable_b64 = __import__("base64").b64encode(enable_py.encode()).decode()
    run(ssh,
        f"echo {enable_b64} | base64 -d | docker exec -i hermes-gateway python3 -",
        label="enable google in config")

    # 4d. CRITICAL: all docker-exec writes above run as root, but the gateway
    #     runs MCP children as the unprivileged `hermes` user (uid 10000).
    #     workspace-mcp must WRITE (credential refresh + server.log) — root-owned
    #     files cause "Permission denied" and a failed handshake. Hand the whole
    #     tree (and a pre-created log) to hermes. (n8n works root-owned because
    #     its bridge is read-only.)
    run(ssh,
        "docker exec hermes-gateway sh -c '"
        f":> {INSTALL_DIR}/server.log; "
        f"chown -R hermes:hermes {INSTALL_DIR}' && echo chowned",
        label="chown workspace-mcp -> hermes")

    # 5. restart, then verify from the GATEWAY's side (hermes user). NB: `hermes
    #    mcp test` runs as root and spawns a *second* instance that collides on
    #    the OAuth callback port range 8000-8004 — a false negative — so we read
    #    the server's own log instead.
    run(ssh, "cd /root/hermes && docker compose restart 2>&1", label="restart gateway", timeout=120)
    run(ssh,
        "sleep 8 && echo '--- mcp list ---' && docker exec hermes-gateway hermes mcp list 2>&1 && "
        "echo '--- google server.log (last lines) ---' && "
        f"docker exec hermes-gateway tail -6 {INSTALL_DIR}/server.log 2>&1",
        label="verify google via gateway")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
