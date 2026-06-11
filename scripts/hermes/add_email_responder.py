"""Déploie le cron email-responder sur le VPS Hermes.

1. Build le system prompt depuis SKILL.md (build_email_prompt.extract_kb_prompt)
2. Lit la signature depuis docs/signature-email.html
3. Upsert GMAIL_* dans /root/.hermes/.env
4. SFTP upload : email_responder.py, email_responder_prompt.md, email_responder_signature.html
5. Crée/maj le cron (idempotent : remove puis create)
6. Test dry-run dans le container

Idempotent : ré-exécutable à volonté (ex : après édition de SKILL.md).
"""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_email_prompt import extract_kb_prompt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

SKILL_MD = ROOT / "skills" / "mylab-email-responder" / "SKILL.md"
SIGNATURE_HTML = ROOT / "docs" / "signature-email.html"
WORKER_PY = Path(__file__).resolve().parent / "email_responder.py"

REMOTE_DIR = "/root/.hermes/scripts"
REMOTE_ENV = "/root/.hermes/.env"
CRON_NAME = "email-responder"
CRON_SCHEDULE = "0 9,13,17 * * 1-5"

GMAIL_KEYS = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]


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


def upsert_env(sftp, remote_path, pairs):
    """Met à jour/ajoute des clés dans un fichier .env distant, sans toucher au reste."""
    try:
        with sftp.open(remote_path, "r") as f:
            lines = f.read().decode("utf-8").splitlines()
    except IOError:
        lines = []
    keys = set(pairs)
    kept = [l for l in lines if l.split("=", 1)[0].strip() not in keys]
    kept += [f"{k}={v}" for k, v in pairs.items()]
    with sftp.open(remote_path, "w") as f:
        f.write("\n".join(kept) + "\n")


def main():
    # 1. Build prompt
    prompt = extract_kb_prompt(SKILL_MD.read_text(encoding="utf-8"))
    signature = SIGNATURE_HTML.read_text(encoding="utf-8").strip()
    worker_src = WORKER_PY.read_text(encoding="utf-8")
    gmail_pairs = {k: os.environ[k] for k in GMAIL_KEYS}  # KeyError clair si manquant

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()

    print("[1/5] Upsert GMAIL_* dans /root/.hermes/.env")
    upsert_env(sftp, REMOTE_ENV, gmail_pairs)
    print("  done (3 clés Gmail)")

    print("\n[2/5] Upload worker + prompt + signature")
    with sftp.open(f"{REMOTE_DIR}/email_responder.py", "w") as f:
        f.write(worker_src)
    sftp.chmod(f"{REMOTE_DIR}/email_responder.py", 0o755)
    with sftp.open(f"{REMOTE_DIR}/email_responder_prompt.md", "w") as f:
        f.write(prompt)
    with sftp.open(f"{REMOTE_DIR}/email_responder_signature.html", "w") as f:
        f.write(signature)
    print(f"  done (prompt {len(prompt)} chars, signature {len(signature)} chars)")
    sftp.close()

    print("\n[3/5] Test dry-run dans le container (pas d'écriture Gmail, appelle Claude)")
    run(ssh, "docker exec -e EMAIL_RESPONDER_DRY_RUN=1 hermes-gateway "
             "python /opt/data/scripts/email_responder.py", label="dry-run", timeout=180)

    print("\n[4/5] (Re)création du cron (idempotent)")
    run(ssh, f"docker exec hermes-gateway hermes cron remove {CRON_NAME} 2>/dev/null; true",
        label="remove ancien cron si présent")
    run(ssh, f'docker exec hermes-gateway hermes cron create '
             f'"Auto-draft emails pro MY.LAB" --no-agent '
             f'--script email_responder.py --deliver telegram '
             f'--name {CRON_NAME} --schedule "{CRON_SCHEDULE}"',
        label="cron create")

    print("\n[5/5] Vérif cron")
    run(ssh, "docker exec hermes-gateway hermes cron list", label="cron list")

    ssh.close()


if __name__ == "__main__":
    main()
