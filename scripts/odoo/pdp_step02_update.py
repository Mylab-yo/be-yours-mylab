"""PDP / facturation électronique — STEP 02 : bump de l'image Odoo 18 + mise à jour modules.

PRÉREQUIS : pdp_step01_backup.py a tourné et tu as un dossier dans /root/odoo-backups/.

Ce que fait --apply :
  1. docker pull odoo:18.0            (récupère le nightly courant >= juin 2026)
  2. docker compose up -d web         (recrée le container web avec la nouvelle image)
  3. -u all sur OdooYJ --stop-after-init  (met à jour le SCHÉMA des modules installés)
  4. redémarre web normalement
  5. vérifie que le module PDP "French e-invoicing" est désormais DISPONIBLE

Sans --apply : DRY-RUN. N'écrit rien, montre juste le plan + l'état courant.

⚠️ Pourquoi -u all : un saut de nightly peut changer le schéma de modules déjà installés.
   Sans -u, Odoo démarre mais peut planter sur des vues/champs désynchronisés. -u all
   resynchronise tout. C'est l'étape qui touche les MODULES CUSTOM (x_carton_capacity,
   rapports QWeb BL/colisage, vues héritées CH) → d'où l'obligation du backup step01.

⚠️ À LANCER sur une fenêtre calme : aucun import n8n Shopify→Odoo en cours
   (workflow Xj8T5a7aO8drZk5v). Downtime ~2-5 min pendant le -u all.

ROLLBACK si ça casse : voir le runbook dans README.md section "PDP / Odoo update rollback",
ou en express :
  - re-pin l'image au digest de IMAGE_DIGEST.txt dans docker-compose.yml
  - docker compose up -d web
  - si la DB a été migrée : pg_restore depuis OdooYJ.dump dans une base neuve

Voir aussi : pdp_step01_backup.py, project_vps_odoo_infra.md
"""
import sys
import paramiko
from pathlib import Path
from dotenv import dotenv_values

APPLY = "--apply" in sys.argv
DB = "OdooYJ"
COMPOSE_DIR = "/root/odoo"

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)


def run(cmd, check=True):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.rstrip())
    if err.strip():
        print(f"STDERR: {err.rstrip()}")
    if check and code != 0:
        raise SystemExit(f"!! exit={code} — STOP. Vérifie l'état, rollback si besoin.")
    return out


print(f"=== PDP STEP 02 — {'APPLY' if APPLY else 'DRY-RUN'} ===")

# état courant
print("\n--- image Odoo actuelle :")
run("docker inspect odoo --format '{{.Image}}'  ; docker exec odoo odoo --version")
print("\n--- backups disponibles :")
run("ls -1 /root/odoo-backups/ 2>/dev/null | tail -5", check=False)
print("\n--- module PDP actuellement présent ? (attendu: vide AVANT update)")
run("docker exec odoo-db-1 psql -U odoo -d %s -t -c "
    "\"SELECT name,state FROM ir_module_module WHERE name LIKE '%%pdp%%' OR name LIKE '%%einvoic%%' "
    "OR name LIKE 'l10n_fr%%edi%%' ORDER BY name\"" % DB, check=False)

if not APPLY:
    print("""
=== DRY-RUN — rien n'a été modifié ===
Plan d'exécution avec --apply :
  1. docker pull odoo:18.0
  2. cd /root/odoo && docker compose up -d web        (recreate, nouvelle image)
  3. docker compose run --rm -u 0 web odoo -u all -d OdooYJ --stop-after-init   (~2-5 min)
  4. docker compose up -d web                          (redémarrage normal)
  5. re-check disponibilité du module PDP

⚠️ Avant --apply : confirme qu'AUCUN import n8n Shopify→Odoo ne tourne.
""")
    ssh.close()
    raise SystemExit(0)

# ---- APPLY ----
print("\n############ APPLY — bump image + update ############")

# 1. pull nouvelle image
run("docker pull odoo:18.0")

# 2. ARRÊTER web pendant la migration (sinon le code neuf sert contre l'ancien schéma)
run(f"cd {COMPOSE_DIR} && docker compose stop web")

# 3. update schéma de tous les modules (resync custom + base) avec la NOUVELLE image
print("\n--- -u all (downtime, ~2-5 min)…")
run(f"cd {COMPOSE_DIR} && docker compose run --rm web odoo -u all -d {DB} --stop-after-init 2>&1 | tail -50")

# 4. redémarrage normal (image neuve, schéma migré)
run(f"cd {COMPOSE_DIR} && docker compose up -d web")
run("sleep 8 && docker exec odoo odoo --version")
run("sleep 8 && docker ps --filter name=odoo --format '{{.Names}} {{.Status}}'")

# 5. module PDP désormais disponible ?
print("\n--- module PDP / French e-invoicing désormais présent ?")
run("docker exec odoo-db-1 psql -U odoo -d %s -t -c "
    "\"SELECT name,state FROM ir_module_module WHERE name LIKE '%%pdp%%' OR name LIKE '%%einvoic%%' "
    "OR name LIKE 'l10n_fr%%' ORDER BY name\"" % DB, check=False)

print("""
=== UPDATE TERMINÉ ===
Vérifs manuelles à faire MAINTENANT :
  1. Ouvrir Odoo → imprimer un BL custom + une facture (rapports QWeb custom OK ?)
  2. Apps → Update Apps List → chercher "PDP" / "French e-invoicing" → installer
  3. Comptabilité → Config → Paramètres → Facturation électronique française → KYC/KYB
Si un rapport custom est cassé → voir runbook rollback dans README.md.
""")
ssh.close()
