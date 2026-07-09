"""Deploie le pipeline notif-tracking sur le VPS (ETAPE 1, sans envoi) :
 1. cree /root/mylab-tracking/ + station/
 2. uploade vps_notify_tracking.py
 3. ecrit /root/mylab-tracking/.env (creds Odoo, chmod 600) — JAMAIS imprime
 4. uploade le dernier export Station local pour pouvoir tester
 5. lance un DRY-RUN sur le VPS (ne touche a rien)

Idempotent. Aucun mail envoye a cette etape."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import paramiko
from dotenv import dotenv_values

REPO = Path(r"d:\be-yours-mylab")
ENV_VPS = dotenv_values(REPO / ".env.vps")
ENV_ODOO = dotenv_values(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))
STATION_LOCAL = Path(r"C:\ProgramData\Station.NET")
REMOTE_DIR = "/root/mylab-tracking"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ENV_VPS["VPS_HOST"], port=int(ENV_VPS.get("VPS_PORT", 22)),
            username=ENV_VPS["VPS_USER"], password=ENV_VPS["VPS_PASS"], timeout=20)


def run(cmd):
    _, out, err = ssh.exec_command(cmd)
    return out.read().decode("utf-8", "replace").strip(), err.read().decode("utf-8", "replace").strip()


# 1. dirs
run(f"mkdir -p {REMOTE_DIR}/station && chmod 700 {REMOTE_DIR}")
print("1. dirs OK")

sftp = ssh.open_sftp()

# 2. script
sftp.put(str(REPO / "scripts/odoo/vps_notify_tracking.py"), f"{REMOTE_DIR}/vps_notify_tracking.py")
print("2. script uploade")

# 3. .env (creds odoo) — contenu jamais imprime
env_lines = []
for k in ("ODOO_URL", "ODOO_DB", "ODOO_LOGIN", "ODOO_USER", "ODOO_API_KEY"):
    if ENV_ODOO.get(k):
        env_lines.append(f"{k}={ENV_ODOO[k]}")
with sftp.file(f"{REMOTE_DIR}/.env", "w") as fh:
    fh.write("\n".join(env_lines) + "\n")
run(f"chmod 600 {REMOTE_DIR}/.env")
print(f"3. .env ecrit ({len(env_lines)} cles, chmod 600) — contenu non imprime")

# 4. dernier export local -> VPS
files = sorted(STATION_LOCAL.glob("*_Expeditions.txt"))
if files:
    latest = files[-1]
    sftp.put(str(latest), f"{REMOTE_DIR}/station/{latest.name}")
    print(f"4. export uploade : {latest.name}")
else:
    print("4. AUCUN export local a uploader")
sftp.close()

# 5. DRY-RUN sur le VPS
print("\n5. DRY-RUN sur le VPS :")
out, err = run(f"cd {REMOTE_DIR} && /usr/bin/python3 vps_notify_tracking.py 2>&1")
print(out or "(vide)")
if err:
    print("STDERR:", err)

ssh.close()
