"""Wire the Airtable MCP (airtable-mcp-server, npx/stdio) into Hermes.

Idempotent. Steps:
  1. Read the Airtable PAT (bare `pat….secret` line under '# HERMES AGENT
     (AIRTABLE)' in the configurateur .env.local) — never printed.
  2. Push it as AIRTABLE_API_KEY into /root/.hermes/.env  (SFTP, chmod 600).
  3. Smoke-test `npx -y airtable-mcp-server` as the unprivileged `hermes` user
     (the uid the gateway spawns MCP children as) — proves the npm cache under
     HOME is writable and the server answers an MCP initialize.
  4. `hermes mcp add airtable --command npx --args -y airtable-mcp-server
        --env AIRTABLE_API_KEY=${AIRTABLE_API_KEY}`  (Y piped to the prompt).
  5. Make sure HOME/.npm is hermes-owned, restart gateway, verify.

Run: python scripts/hermes/add_airtable_mcp.py
"""
import base64
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
ENV_LOCAL = Path(r"D:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
HOST_ENV = "/root/.hermes/.env"


def read_pat() -> str:
    text = ENV_LOCAL.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = re.match(r"^(pat[A-Za-z0-9]{14}\.[A-Za-z0-9]{40,})\s*$", line.strip())
        if m:
            return m.group(1)
    sys.exit(f"No Airtable PAT (pat….secret) found in {ENV_LOCAL}")


def run(ssh, cmd, *, timeout=600, label=None):
    if label:
        print(f"\n=== {label} ===")
    _in, out, err = ssh.exec_command(cmd, timeout=timeout)
    o = out.read().decode(errors="replace").rstrip()
    e = err.read().decode(errors="replace").rstrip()
    rc = out.channel.recv_exit_status()
    if o:
        print(o)
    if e:
        print(e)
    print(f"[rc={rc}]")
    return rc, o, e


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


# MCP initialize handshake driver, run as `hermes` via npx.
SMOKE_PY = '''
import json, os, subprocess, time
p = subprocess.Popen(["npx","-y","airtable-mcp-server"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    env=dict(os.environ), bufsize=0)
p.stdin.write((json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}})+"\\n").encode()); p.stdin.flush()
t0=time.time()
line=p.stdout.readline()
print(f"[{time.time()-t0:.1f}s] init:", (line[:70] or b"<none>"))
p.stdin.write((json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"})+"\\n").encode())
p.stdin.write((json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})+"\\n").encode()); p.stdin.flush()
line=p.stdout.readline()
import re
n=len(re.findall(b'"name"', line))
print(f"[{time.time()-t0:.1f}s] tools/list approx tools:", n)
p.terminate()
'''


def main():
    pat = read_pat()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()

    # 1+2. push PAT to .env
    print("=== push AIRTABLE_API_KEY to .env ===")
    upsert_env(sftp, HOST_ENV, {"AIRTABLE_API_KEY": pat})

    # 3. smoke-test npx as hermes (HOME writable + server answers)
    smoke_b64 = base64.b64encode(SMOKE_PY.encode()).decode()
    run(ssh,
        "docker exec -u hermes hermes-gateway sh -c '"
        "set -a; . /opt/data/.env; set +a; export HOME=/opt/data; "
        f"echo {smoke_b64} | base64 -d | python3 -' 2>&1",
        label="npx smoke-test as hermes", timeout=180)

    # 4a. wrapper: `hermes mcp add --args` can't carry `-y`/`--`-prefixed values
    #     (argparse eats them). Bake the npx invocation + HOME + stderr redirect
    #     into a run.sh, same as the google connector.
    AIR_DIR = "/opt/data/mcp-servers/airtable"
    run_sh = (
        "#!/bin/sh\n"
        "export HOME=/opt/data\n"
        f"exec npx -y airtable-mcp-server 2>>{AIR_DIR}/server.log\n"
    )
    run(ssh, f"docker exec hermes-gateway mkdir -p {AIR_DIR}", label="mkdir airtable dir")
    with sftp.open(f"/root/.hermes/mcp-servers/airtable/run.sh", "w") as f:
        f.write(run_sh)
    sftp.chmod("/root/.hermes/mcp-servers/airtable/run.sh", 0o755)
    with sftp.open(f"/root/.hermes/mcp-servers/airtable/server.log", "a") as f:
        f.write("")
    print(f"  {AIR_DIR}/run.sh + server.log written")

    # 4b. register (skip if present)
    rc, listing, _ = run(ssh, "docker exec hermes-gateway hermes mcp list 2>&1",
                         label="current MCP servers")
    if re.search(r"(^|\s)airtable(\s|$)", listing or ""):
        print("\n=== mcp add airtable ===\n  already configured — skipping")
    else:
        run(ssh,
            "printf 'Y\\n' | docker exec -i hermes-gateway hermes mcp add airtable "
            f"--command {AIR_DIR}/run.sh "
            "--env 'AIRTABLE_API_KEY=${AIRTABLE_API_KEY}' 2>&1",
            label="mcp add airtable", timeout=180)

    # 4c. a failed connect during `add` (cold npx run as root) saves it disabled
    enable_py = (
        'import yaml; p="/opt/data/config.yaml"; c=yaml.safe_load(open(p)); '
        'c["mcp_servers"]["airtable"]["enabled"]=True; '
        'yaml.safe_dump(c, open(p,"w"), sort_keys=False); '
        'print("airtable.enabled =", c["mcp_servers"]["airtable"]["enabled"])'
    )
    enable_b64 = base64.b64encode(enable_py.encode()).decode()
    run(ssh, f"echo {enable_b64} | base64 -d | docker exec -i hermes-gateway python3 -",
        label="enable airtable in config")

    # 5. npm cache + airtable dir must be hermes-owned (gateway spawns as hermes)
    run(ssh,
        "docker exec hermes-gateway sh -c '"
        f"mkdir -p /opt/data/.npm; chown -R hermes:hermes /opt/data/.npm {AIR_DIR}' && echo ok",
        label="chown npm cache + airtable dir -> hermes")
    run(ssh, "cd /root/hermes && docker compose restart 2>&1", label="restart gateway", timeout=120)
    run(ssh,
        "sleep 9 && echo '--- mcp list ---' && docker exec hermes-gateway hermes mcp list 2>&1 && "
        f"echo '--- airtable server.log ---' && docker exec hermes-gateway tail -4 {AIR_DIR}/server.log 2>&1",
        label="verify airtable")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
