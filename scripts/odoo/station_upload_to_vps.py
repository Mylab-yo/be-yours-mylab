"""PC -> VPS : uploade le(s) dernier(s) export(s) Station vers le VPS puis declenche
l'envoi des mails de tracking (vps_notify_tracking.py --send, idempotent).

Concu pour tourner en tache planifiee Windows pendant la journee. Grace au dedup
niveau colis cote VPS, l'executer plusieurs fois par jour est sans danger.

Usage :
  python -m scripts.odoo.station_upload_to_vps            # upload + ENVOI
  python -m scripts.odoo.station_upload_to_vps --dry-run  # upload + dry-run (aucun mail)
  python -m scripts.odoo.station_upload_to_vps --last 3   # uploade les 3 derniers fichiers
"""
import sys, io, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from datetime import datetime
import paramiko
from dotenv import dotenv_values

REPO = Path(r"d:\be-yours-mylab")
ENV_VPS = dotenv_values(REPO / ".env.vps")
STATION_LOCAL = Path(r"C:\ProgramData\Station.NET")
REMOTE_DIR = "/root/mylab-tracking"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="VPS en dry-run (aucun mail)")
    ap.add_argument("--last", type=int, default=1, help="nb de fichiers recents a uploader")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    files = sorted(STATION_LOCAL.glob("*_Expeditions.txt"))
    if not files:
        print(f"[{stamp}] Aucun export local — rien a faire.")
        return
    to_send = files[-args.last:]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ENV_VPS["VPS_HOST"], port=int(ENV_VPS.get("VPS_PORT", 22)),
                username=ENV_VPS["VPS_USER"], password=ENV_VPS["VPS_PASS"], timeout=20)

    sftp = ssh.open_sftp()
    for f in to_send:
        sftp.put(str(f), f"{REMOTE_DIR}/station/{f.name}")
    sftp.close()
    print(f"[{stamp}] Uploade : {', '.join(f.name for f in to_send)}")

    flag = "" if args.dry_run else "--send"
    cmd = f"cd {REMOTE_DIR} && /usr/bin/python3 vps_notify_tracking.py {flag} 2>&1"
    _, out, err = ssh.exec_command(cmd)
    print(out.read().decode("utf-8", "replace").strip())
    e = err.read().decode("utf-8", "replace").strip()
    if e:
        print("STDERR:", e)
    ssh.close()


if __name__ == "__main__":
    main()
