"""Met à jour l'image Docker de Hermes Agent sur le VPS — en sécurité.

Idempotent. Par défaut : **check-only** (ne touche à rien).

    python scripts/hermes/update_hermes_image.py            # compare local vs registre + inspecte la nouvelle version
    python scripts/hermes/update_hermes_image.py --apply     # backup + bascule + vérif

Principe clé (c'est ce qui rend le check sans risque) :
la nouvelle image est pull **par digest**, ce qui NE déplace PAS le tag `:latest` utilisé par le
container qui tourne. On peut donc l'inspecter dans un container jetable avant de décider quoi que ce
soit. Le `:latest` n'est repointé qu'avec `--apply`.

Pièges couverts (cf. docs/superpowers/notes/2026-07-13-session-hermes-maj-v0.18.2.md) :
  - `hermes migrate` ne gère QUE les modèles xAI — ni crons ni config.
  - Le store des crons peut changer entre versions → vérifier `/opt/data/cron/` avant de crier à la
    régression (les jobs peuvent être simplement en pause).
  - Toute écriture SFTP dans /root/.hermes arrive root-owned → chown 10000:10000 obligatoire.
  - Ne jamais `cat` /opt/data/.env sans redaction stricte (secrets Gmail/n8n/Shopify/Odoo…).
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

import paramiko
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

IMAGE = "nousresearch/hermes-agent"
TAG = f"{IMAGE}:latest"
CONTAINER = "hermes-gateway"
COMPOSE_DIR = "/root/hermes"
DATA_DIR = "/root/.hermes"


def redact(s: str) -> str:
    s = re.sub(r"sk-[A-Za-z0-9_\-]{12,}", "sk-…REDACTED", s)
    s = re.sub(r"\b\d{6,}:[A-Za-z0-9_\-]{25,}\b", "…REDACTED", s)
    s = re.sub(r"(?im)^(.*(?:_SECRET|_TOKEN|_KEY|api_key|password)\s*[:=]).*$", r"\1 …REDACTED", s)
    return s


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ["VPS_HOST"],
        port=int(os.environ.get("VPS_PORT", "22")),
        username=os.environ["VPS_USER"],
        password=os.environ["VPS_PASS"],
        timeout=15,
    )
    return ssh


def sh(ssh, cmd, *, label=None, timeout=180, check=False, quiet=False):
    if label:
        print(f"\n=== {label} ===")
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    o = out.read().decode(errors="replace")
    e = err.read().decode(errors="replace")
    rc = out.channel.recv_exit_status()
    if not quiet:
        if o.strip():
            print(redact(o).rstrip())
        if e.strip():
            print("[stderr]", redact(e).rstrip()[:600])
        print(f"[rc={rc}]")
    if check and rc != 0:
        print(f"\n!!! ABORT — étape critique échouée : {label or cmd}")
        ssh.close()
        sys.exit(1)
    return rc, o


def main():
    ap = argparse.ArgumentParser(description="Update Hermes Agent Docker image (safe, idempotent)")
    ap.add_argument("--apply", action="store_true", help="Applique réellement la MAJ (sinon check-only)")
    args = ap.parse_args()

    ssh = connect()

    # --- État courant -------------------------------------------------------
    _, running = sh(ssh, f"docker inspect {CONTAINER} --format '{{{{.Image}}}}'", quiet=True)
    old_image_id = running.strip()
    _, local_dig_raw = sh(ssh, f"docker image inspect {TAG} --format '{{{{index .RepoDigests 0}}}}'", quiet=True)
    local_digest = local_dig_raw.strip().split("@")[-1]

    _, ver_now = sh(ssh, f"docker exec {CONTAINER} hermes --version 2>&1 | head -1", quiet=True)

    print("=== État actuel ===")
    print(f"  version   : {ver_now.strip()}")
    print(f"  image ID  : {old_image_id}")
    print(f"  digest    : {local_digest}")

    # --- Digest distant -----------------------------------------------------
    _, remote_raw = sh(ssh, f"docker buildx imagetools inspect {TAG} 2>&1 | head -5", quiet=True)
    m = re.search(r"^Digest:\s+(sha256:[0-9a-f]+)", remote_raw, re.M)
    if not m:
        print("\n[!] Impossible de lire le digest distant :\n" + remote_raw)
        ssh.close()
        sys.exit(1)
    remote_digest = m.group(1)
    print(f"\n=== Registre ===\n  digest distant : {remote_digest}")

    if remote_digest == local_digest:
        print("\n✅ Déjà à jour — rien à faire.")
        ssh.close()
        return

    print("\n🆕 Une nouvelle image est disponible.")

    # --- Pull PAR DIGEST : ne déplace pas :latest, container intact ---------
    new_ref = f"{IMAGE}@{remote_digest}"
    sh(ssh, f"docker pull {new_ref} 2>&1 | tail -3", label="Pull par digest (:latest NON déplacé)", timeout=600, check=True)
    sh(ssh, f"docker run --rm --entrypoint hermes {new_ref} --version 2>&1 | head -5", label="Version de la NOUVELLE image")
    sh(ssh, f"docker image inspect {TAG} --format 'SAFETY — :latest toujours = {{{{.Id}}}}'", label="Contrôle de sécurité")

    if not args.apply:
        print("\n────────────────────────────────────────────")
        print("Check-only : rien n'a été modifié. Le container tourne toujours sur l'ancienne image.")
        print("Pour appliquer :  python scripts/hermes/update_hermes_image.py --apply")
        ssh.close()
        return

    # --- Backups ------------------------------------------------------------
    suffix = ".bak-pre-update"
    sh(
        ssh,
        f"for f in {DATA_DIR}/config.yaml {DATA_DIR}/.env {DATA_DIR}/*.db {DATA_DIR}/*.sqlite3; do "
        f'[ -f "$f" ] && cp -a "$f" "$f{suffix}" && echo "backup: $f"; done; true',
        label="Backups (config, .env, DBs)",
        check=True,
    )

    # --- Bascule ------------------------------------------------------------
    sh(ssh, f"docker tag {new_ref} {TAG} && echo 'tag :latest -> nouvelle image'", label="Repointe :latest", check=True)
    sh(ssh, f"cd {COMPOSE_DIR} && docker compose up -d 2>&1", label="Recreate container", timeout=300, check=True)
    time.sleep(9)

    # --- Vérifs -------------------------------------------------------------
    sh(ssh, f"docker ps --filter name={CONTAINER} --format '{{{{.Names}}}} | {{{{.Status}}}}'", label="Status")
    sh(ssh, f"docker exec {CONTAINER} hermes --version 2>&1 | head -5", label="Nouvelle version active")
    sh(ssh, f"docker exec {CONTAINER} hermes config show 2>&1 | grep -iE 'Model|Anthropic|OpenAI'", label="Config (routage/modèle)")
    sh(ssh, f"docker exec {CONTAINER} timeout 40 hermes skills list 2>&1 | head -12", label="Skills")
    sh(ssh, f"docker exec {CONTAINER} timeout 40 hermes cron list 2>&1 | head -12", label="Crons (voir note: store peut changer)")
    sh(ssh, f"docker exec {CONTAINER} timeout 90 hermes -z 'Reponds uniquement: OK' 2>&1 | tail -4",
       label="Smoke test (appel LLM)", timeout=140)
    sh(ssh, f"docker logs {CONTAINER} --since 2m 2>&1 | tail -20", label="Logs récents")

    print("\n────────────────────────────────────────────")
    print("✅ MAJ appliquée.")
    print(f"ROLLBACK : docker tag {old_image_id} {TAG} && cd {COMPOSE_DIR} && docker compose up -d")
    print(f"           puis restaurer les fichiers {DATA_DIR}/*{suffix}")
    ssh.close()


if __name__ == "__main__":
    main()
