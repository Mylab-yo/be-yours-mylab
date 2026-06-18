"""ETAPE 2 : re-uploade le script VPS corrige + installe le cron de securite.
Cron quotidien 17:00 UTC (= 19:00 Paris CEST) lun-sam, idempotent (dedup colis).
N'ecrase PAS les crons existants. Affiche la crontab finale."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import paramiko
from dotenv import dotenv_values

REPO = Path(r"d:\be-yours-mylab")
ENV_VPS = dotenv_values(REPO / ".env.vps")
REMOTE_DIR = "/root/mylab-tracking"
CRON_LINE = (f"0 17 * * 1-6 cd {REMOTE_DIR} && /usr/bin/python3 vps_notify_tracking.py "
             f"--send >> /var/log/mylab-tracking.log 2>&1")
CRON_TAG = "vps_notify_tracking.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ENV_VPS["VPS_HOST"], port=int(ENV_VPS.get("VPS_PORT", 22)),
            username=ENV_VPS["VPS_USER"], password=ENV_VPS["VPS_PASS"], timeout=20)


def run(cmd):
    _, out, err = ssh.exec_command(cmd)
    return out.read().decode("utf-8", "replace").strip(), err.read().decode("utf-8", "replace").strip()


# re-upload script corrige
sftp = ssh.open_sftp()
sftp.put(str(REPO / "scripts/odoo/vps_notify_tracking.py"), f"{REMOTE_DIR}/vps_notify_tracking.py")
sftp.close()
print("Script re-uploade.")

# install cron idempotent
cur, _ = run("crontab -l 2>/dev/null")
if CRON_TAG in cur:
    print("Cron deja present -> no-op.")
else:
    new = (cur + "\n" if cur else "") + "# MY.LAB - Notif tracking DPD quotidienne\n" + CRON_LINE + "\n"
    # ecrit via fichier temp pour eviter les soucis de quoting
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/mylab_cron.txt", "w") as fh:
        fh.write(new)
    sftp.close()
    out, err = run("crontab /tmp/mylab_cron.txt && rm -f /tmp/mylab_cron.txt")
    print("Cron installe." if not err else f"ERREUR cron: {err}")

print("\n=== crontab finale ===")
out, _ = run("crontab -l")
print(out)

# cree le fichier log s'il n'existe pas
run("touch /var/log/mylab-tracking.log")
ssh.close()
