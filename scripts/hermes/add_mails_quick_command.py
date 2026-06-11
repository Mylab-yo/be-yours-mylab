"""Ajoute la quick-command Telegram `/mails` au gateway Hermes.

`/mails` → exec `hermes cron run email-responder` (déclenche le job cron email-responder,
sans LLM, sans limite 30s ; le résumé arrive ensuite sur Telegram via la livraison cron).

Mécanisme : bloc `quick_commands` de /opt/data/config.yaml (= /root/.hermes/config.yaml),
type `exec` (cf. gateway/run.py : bypass agent loop, env sanitizé, sortie renvoyée au chat).

Idempotent : ré-exécutable. Backup du config.yaml avant modif. Restart du gateway pour
recharger la config.
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

REMOTE_CONFIG = "/root/.hermes/config.yaml"

QUICK_BLOCK = (
    "quick_commands:\n"
    "  mails:\n"
    "    type: exec\n"
    "    command: hermes cron run email-responder\n"
)


def run(ssh, cmd, label=None, timeout=120):
    if label:
        print(f"\n=== {label} ===")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        for l in err.splitlines():
            if l.strip():
                print(f"[stderr] {l}")
    print(f"[rc={rc}]")
    return out, rc


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()

    with sftp.open(REMOTE_CONFIG, "r") as f:
        cfg = f.read().decode("utf-8")

    if "command: hermes cron run email-responder" in cfg:
        print("Quick-command /mails déjà présente — rien à faire.")
        sftp.close()
        ssh.close()
        return

    if "quick_commands: {}" not in cfg:
        print("⚠️ Bloc 'quick_commands: {}' introuvable (peut-être déjà non vide).")
        print("   Édition manuelle requise — abandon pour ne pas casser le YAML.")
        sftp.close()
        ssh.close()
        sys.exit(1)

    print("[1/3] Backup + insertion de la quick-command /mails")
    with sftp.open(REMOTE_CONFIG + ".bak-mails", "w") as f:
        f.write(cfg)
    new_cfg = cfg.replace("quick_commands: {}\n", QUICK_BLOCK)
    with sftp.open(REMOTE_CONFIG, "w") as f:
        f.write(new_cfg)
    print("  done (backup: config.yaml.bak-mails)")
    sftp.close()

    print("\n[2/3] Restart du gateway pour recharger la config")
    run(ssh, "cd /root/hermes && docker compose restart 2>&1 | tail -5", label="compose restart", timeout=120)
    run(ssh, "sleep 6 && docker ps --filter name=hermes-gateway --format '{{.Status}}'", label="status")

    print("\n[3/3] Vérif : bloc quick_commands dans la config")
    run(ssh, "grep -A3 'quick_commands:' /root/.hermes/config.yaml", label="config quick_commands")

    ssh.close()
    print("\n✅ /mails ajoutée. Teste depuis le bot Telegram : envoie  /mails")


if __name__ == "__main__":
    main()
