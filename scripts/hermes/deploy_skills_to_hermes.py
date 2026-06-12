"""Deploy MyLab business skills into the Hermes agent (VPS container).

Hermes user skills live in /opt/data/skills/<name>/SKILL.md (persisted volume).
This pushes the adapted SKILL.md files from scripts/hermes/skills/<name>/ — they
read Shopify/Odoo creds from os.environ (already in /opt/data/.env), not from a
local Windows path. Idempotent (overwrites). Run: python scripts/hermes/deploy_skills_to_hermes.py
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
LOCAL_SKILLS = Path(__file__).resolve().parent / "skills"
REMOTE_BASE = "/opt/data/skills"

SKILLS = ["check-order", "check-customer", "relance-impayes", "faire-of", "gerer-bl"]


def run(ssh, cmd, *, label=None, timeout=120):
    if label:
        print(f"\n=== {label} ===")
    _i, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode(errors="replace").rstrip()
    err = e.read().decode(errors="replace").rstrip()
    rc = o.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(err)
    print(f"[rc={rc}]")
    return rc, out, err


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()

    for name in SKILLS:
        local = LOCAL_SKILLS / name / "SKILL.md"
        if not local.exists():
            print(f"  SKIP {name}: {local} not found")
            continue
        # host path of the container's /opt/data volume = /root/.hermes
        host_dir = f"/root/.hermes/skills/{name}"
        ssh.exec_command(f"mkdir -p {host_dir}")[1].read()
        with sftp.open(f"{host_dir}/SKILL.md", "w") as f:
            f.write(local.read_text(encoding="utf-8"))
        print(f"  pushed {name} -> {REMOTE_BASE}/{name}/SKILL.md")

    # gateway spawns/reads as hermes (uid 10000)
    run(ssh, f"docker exec hermes-gateway chown -R hermes:hermes {REMOTE_BASE} && echo ok",
        label="chown skills -> hermes")
    run(ssh, "cd /root/hermes && docker compose restart 2>&1", label="restart gateway")
    run(ssh, "sleep 7 && docker exec hermes-gateway hermes skills list 2>&1 | grep -iE 'check-order|check-customer|relance-impayes|faire-of|gerer-bl|installed|name' | head",
        label="verify skills")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
