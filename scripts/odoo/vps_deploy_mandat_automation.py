"""Deploie l'envoi automatique des mandats sur le VPS (cron 24/7).

Cree /root/mandat-automation/ : scripts + venv + secret Google + .env + run.sh + cron flock.
Idempotent : ne duplique pas le cron, re-uploade les scripts a chaque run.
Ne PRINT jamais les secrets (token Telegram lu cote VPS, creds Odoo/Google ecrits sans echo).

Run : python -m scripts.odoo.vps_deploy_mandat_automation
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
import paramiko
from dotenv import dotenv_values

REPO = Path(r"d:\be-yours-mylab")
ENV_VPS = dotenv_values(REPO / ".env.vps")
ENV_LOCAL = dotenv_values(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

REMOTE = "/root/mandat-automation"
HERMES_ENV = "/root/.hermes/.env"
TELEGRAM_CHAT_ID = "7760145552"   # user_id Yoann (= chat_id prive), depuis /root/.hermes/.env
MANDAT_AUTO_SINCE = "2026-06-29"
LOCAL_SA = Path(ENV_LOCAL["GOOGLE_SA_JSON"])  # d:\...\secrets\google-sa-mandat.json

CRON_TAG = "mandat-automation/run.sh"
CRON_LINE = (f"*/15 * * * * /usr/bin/flock -n {REMOTE}/.lock {REMOTE}/run.sh "
             f">> {REMOTE}/logs/mandat.log 2>&1")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ENV_VPS["VPS_HOST"], port=int(ENV_VPS.get("VPS_PORT", 22)),
            username=ENV_VPS["VPS_USER"], password=ENV_VPS["VPS_PASS"], timeout=30)


def run(cmd, label=None):
    _, out, err = ssh.exec_command(cmd, timeout=600)
    o = out.read().decode("utf-8", "replace").strip()
    e = err.read().decode("utf-8", "replace").strip()
    if label:
        print(f"### {label}\n{o or '(ok)'}{(' | ERR: ' + e) if e else ''}\n")
    return o, e


# 1) Arborescence
run(f"mkdir -p {REMOTE}/scripts/odoo {REMOTE}/secrets {REMOTE}/logs && touch {REMOTE}/logs/mandat.log",
    "1. Arborescence")

# 2) Upload scripts
sftp = ssh.open_sftp()
run(f": > {REMOTE}/scripts/__init__.py")  # package marker (cree vide cote serveur)
for fname in ["__init__.py", "_client.py", "send_mandat_representation.py", "auto_send_mandats.py"]:
    sftp.put(str(REPO / "scripts/odoo" / fname), f"{REMOTE}/scripts/odoo/{fname}")
print("2. Scripts uploades (4 fichiers + __init__ package)\n")

# 3) Secret Google (jamais loggue)
sftp.put(str(LOCAL_SA), f"{REMOTE}/secrets/google-sa-mandat.json")
run(f"chmod 600 {REMOTE}/secrets/google-sa-mandat.json")
print("3. Secret Google uploade (chmod 600)\n")

# 4) Token Telegram : lu cote VPS depuis le .env Hermes (reste sur le serveur)
tok_line, _ = run(f"grep -E '^TELEGRAM_BOT_TOKEN=' {HERMES_ENV} | head -1")
tg_token = tok_line.split("=", 1)[1].strip() if "=" in tok_line else ""
print(f"4. Token Telegram recupere depuis Hermes : {'OK (present)' if tg_token else 'ABSENT !'}\n")

# 5) .env distant (ecrit sans echo des valeurs)
env_lines = [
    "# Genere par vps_deploy_mandat_automation.py -- NE PAS COMMITER",
    f"ODOO_ENV_FILE={REMOTE}/.env",
    f"ODOO_URL={ENV_LOCAL['ODOO_URL']}",
    f"ODOO_DB={ENV_LOCAL['ODOO_DB']}",
    f"ODOO_LOGIN={ENV_LOCAL['ODOO_LOGIN']}",
    f"ODOO_API_KEY={ENV_LOCAL['ODOO_API_KEY']}",
    f"GOOGLE_SA_JSON={REMOTE}/secrets/google-sa-mandat.json",
    f"MANDAT_TEMPLATE_DOC_ID={ENV_LOCAL['MANDAT_TEMPLATE_DOC_ID']}",
    f"MANDAT_SENT_FOLDER_ID={ENV_LOCAL['MANDAT_SENT_FOLDER_ID']}",
    f"MANDAT_AUTO_SINCE={MANDAT_AUTO_SINCE}",
    f"TELEGRAM_BOT_TOKEN={tg_token}",
    f"TELEGRAM_CHAT_ID={TELEGRAM_CHAT_ID}",
    "",
]
with sftp.file(f"{REMOTE}/.env", "w") as fh:
    fh.write("\n".join(env_lines))
run(f"chmod 600 {REMOTE}/.env")
print("5. .env distant ecrit (chmod 600) -- 12 cles, valeurs non affichees\n")

# 6) run.sh wrapper
run_sh = (
    "#!/bin/bash\n"
    f"cd {REMOTE} || exit 1\n"
    "set -a\n"
    f". {REMOTE}/.env\n"
    "set +a\n"
    f"exec {REMOTE}/venv/bin/python -m scripts.odoo.auto_send_mandats \"$@\"\n"
)
with sftp.file(f"{REMOTE}/run.sh", "w") as fh:
    fh.write(run_sh)
run(f"chmod +x {REMOTE}/run.sh")
sftp.close()
print("6. run.sh ecrit (+x)\n")

# 7) venv + deps
print("7. Creation venv + pip install (peut prendre 1-2 min)...")
out, err = run(
    f"test -d {REMOTE}/venv || python3 -m venv {REMOTE}/venv; "
    f"{REMOTE}/venv/bin/pip install --quiet --upgrade pip && "
    f"{REMOTE}/venv/bin/pip install --quiet google-api-python-client google-auth python-dotenv && "
    f"{REMOTE}/venv/bin/python -c 'import googleapiclient, google.oauth2, dotenv; print(\"deps OK\")'"
)
print(f"   {out or err}\n")

# 8) Cron idempotent (flock)
cur, _ = run("crontab -l 2>/dev/null")
if CRON_TAG in cur:
    print("8. Cron deja present -> no-op\n")
else:
    new = (cur + "\n" if cur else "") + "# MY.LAB - Envoi auto mandats (toutes les 15 min)\n" + CRON_LINE + "\n"
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/mandat_cron.txt", "w") as fh:
        fh.write(new)
    sftp.close()
    _, e = run("crontab /tmp/mandat_cron.txt && rm -f /tmp/mandat_cron.txt")
    print("8. Cron installe\n" if not e else f"8. ERREUR cron: {e}\n")

# 9) Dry-run de validation sur le VPS
print("9. Dry-run de validation sur le VPS (doit dire 'aucune facture eligible') :")
out, err = run(f"{REMOTE}/run.sh --dry-run")
print(out or err)
print()

# 10) Crontab finale
out, _ = run("crontab -l 2>/dev/null | grep -A1 -i mandat")
print("=== ligne(s) cron mandat ===")
print(out)

ssh.close()
print("\n=== DEPLOIEMENT TERMINE ===")
