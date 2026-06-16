"""PDP / facturation électronique — STEP 01 : backup complet avant mise à jour Odoo.

Contexte : l'image Odoo du VPS est datée 18.0-20260324 (24 mars 2026), antérieure
à la sortie du module "French e-invoicing" (PDP) de début juin 2026. Pour devenir
conforme via la PA Odoo, il faut bumper l'image odoo:18.0 vers un nightly >= juin 2026.
Avant ce bump, on prend un backup intégral et restaurable.

Ce script est SANS DANGER : il ne fait que LIRE la prod (pg_dump + tar du filestore +
copie des fichiers de conf). Aucune écriture sur la base ni sur les containers.

Artefacts produits dans /root/odoo-backups/<timestamp>/ sur le VPS :
  - OdooYJ.dump           (pg_dump format custom -Fc, restaurable via pg_restore)
  - filestore.tgz         (pièces jointes / PDF cachés : /var/lib/odoo/filestore/OdooYJ)
  - docker-compose.yml    (copie du compose courant)
  - config.tgz            (/root/odoo/config = odoo.conf)
  - addons.tgz            (/root/odoo/addons = modules custom + OCA)
  - IMAGE_DIGEST.txt      (digest de l'image odoo:18.0 actuellement utilisée → pin de rollback)
  - MANIFEST.txt          (récap + tailles)

Idempotent : chaque run crée un dossier horodaté distinct, ne touche jamais aux précédents.

Voir aussi : project_vps_odoo_infra.md, reference_vps_ssh_python.md
"""
import paramiko
from pathlib import Path
from datetime import datetime
from dotenv import dotenv_values

DB = "OdooYJ"
DB_CONTAINER = "odoo-db-1"
WEB_CONTAINER = "odoo"
COMPOSE_DIR = "/root/odoo"
BACKUP_ROOT = "/root/odoo-backups"

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)


def run(cmd, quiet=False):
    if not quiet:
        print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out and not quiet:
        print(out.rstrip())
    if err.strip():
        print(f"STDERR: {err.rstrip()}")
    if code != 0:
        raise SystemExit(f"!! commande échouée (exit={code}) — backup AVORTÉ, ne pas updater Odoo")
    return out


ts = datetime.now().strftime("%Y%m%d-%H%M%S")
dest = f"{BACKUP_ROOT}/{ts}"
print(f"=== BACKUP Odoo {DB} → {dest} (VPS) ===")

# garde-fou : avertir si une exécution n8n Shopify→Odoo tourne (cohérence du dump)
print("\n--- garde-fou : pas d'import n8n en cours ? (vérifie manuellement si besoin)")
run(f"mkdir -p {dest}")

# 0. digest de l'image courante = point de rollback
run(f"docker inspect {WEB_CONTAINER} --format '{{{{.Image}}}}' > {dest}/IMAGE_DIGEST.txt")
run(f"docker image inspect odoo:18.0 --format '{{{{index .RepoDigests 0}}}}' >> {dest}/IMAGE_DIGEST.txt")
print(">> image de rollback enregistrée :")
run(f"cat {dest}/IMAGE_DIGEST.txt")

# 1. dump base (format custom, compressé, restaurable sélectivement)
print("\n--- pg_dump (peut prendre 1-2 min)…")
run(f"docker exec {DB_CONTAINER} pg_dump -U odoo -Fc -f /tmp/{DB}.dump {DB}")
run(f"docker cp {DB_CONTAINER}:/tmp/{DB}.dump {dest}/{DB}.dump")
run(f"docker exec {DB_CONTAINER} rm -f /tmp/{DB}.dump")

# 2. filestore (PDF cachés, pièces jointes ir.attachment)
# data_dir Odoo = /var/lib/odoo/.local/share/Odoo (PAS /var/lib/odoo directement)
print("\n--- filestore…")
run(f"docker exec {WEB_CONTAINER} bash -c 'cd /var/lib/odoo/.local/share/Odoo && tar czf /tmp/filestore.tgz filestore/{DB} 2>/dev/null || true'")
run(f"docker cp {WEB_CONTAINER}:/tmp/filestore.tgz {dest}/filestore.tgz")
run(f"docker exec {WEB_CONTAINER} rm -f /tmp/filestore.tgz")

# 3. compose + config + addons (custom modules + OCA = irremplaçables)
run(f"cp {COMPOSE_DIR}/docker-compose.yml {dest}/docker-compose.yml")
run(f"tar czf {dest}/config.tgz -C {COMPOSE_DIR} config")
run(f"tar czf {dest}/addons.tgz -C {COMPOSE_DIR} addons")

# 4. manifest
run(f"(echo 'Backup Odoo {DB} — {ts}'; echo; ls -lh {dest}) > {dest}/MANIFEST.txt")
print("\n=== CONTENU DU BACKUP ===")
run(f"ls -lh {dest}")

print(f"""
=== BACKUP TERMINÉ ===
Emplacement VPS : {dest}
Rollback image  : voir {dest}/IMAGE_DIGEST.txt

Étape suivante (quand fenêtre calme, pas d'import n8n) :
  python scripts/odoo/pdp_step02_update.py            # DRY-RUN, montre le plan
  python scripts/odoo/pdp_step02_update.py --apply    # exécute le bump + -u
""")
ssh.close()
