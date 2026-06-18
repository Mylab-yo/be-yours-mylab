"""PDP / facturation electronique — STEP 03 : probe READ-ONLY de l'etat de config.

Le module l10n_fr_pdp est deja 'installed' et l'image est bumpee (18.0-20260609).
Ce script ne fait que LIRE pour comprendre ce qu'il reste a faire :
  - etats des modules pdp / edi / l10n_fr
  - champs de config e-invoicing sur res.company (SIRET, registration, mode PDP)
  - presence d'erreurs recentes dans les logs Odoo liees a pdp/einvoice
  - parametres ir.config_parameter lies a l'einvoicing

Aucune ecriture. Sortie forcee en UTF-8 pour eviter le crash cp1252 Windows.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import paramiko
from pathlib import Path
from dotenv import dotenv_values

DB = "OdooYJ"
env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)


def run(cmd, label=None):
    if label:
        print(f"\n===== {label} =====")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if out:
        print(out.rstrip())
    if err.strip():
        print(f"[stderr] {err.rstrip()}")
    return out


def psql(q):
    return run("docker exec odoo-db-1 psql -U odoo -d %s -t -A -F'|' -c \"%s\"" % (DB, q))


# 1. tous les modules e-invoicing / l10n_fr / edi / account_edi
psql("SELECT name, state, latest_version FROM ir_module_module "
     "WHERE name LIKE 'l10n_fr%' OR name LIKE '%edi%' OR name LIKE '%pdp%' "
     "OR name LIKE '%einvoic%' OR name LIKE '%peppol%' OR name LIKE 'account_edi%' "
     "ORDER BY state DESC, name")

# 2. champs e-invoicing presents sur res.company (selon version du module)
psql("SELECT column_name FROM information_schema.columns "
     "WHERE table_name='res_company' AND (column_name LIKE '%edi%' "
     "OR column_name LIKE '%pdp%' OR column_name LIKE '%siret%' "
     "OR column_name LIKE '%peppol%' OR column_name LIKE '%proxy%') ORDER BY column_name")

# 3. valeurs de la societe MY.LAB (id 1) sur ces champs cles si presents
run("docker exec odoo-db-1 psql -U odoo -d %s -t -A -F'|' -c \"%s\"" % (
    DB,
    "SELECT id, name, vat, "
    "(SELECT string_agg(column_name, ',') FROM information_schema.columns "
    " WHERE table_name='res_company') IS NOT NULL AS has_cols FROM res_company"),
    label="res_company (apercu)")

# 4. account_edi_proxy_user (l'enregistrement PDP/PA cote IAP s'y materialise)
psql("SELECT to_regclass('account_edi_proxy_client_user') IS NOT NULL AS table_exists")
run("docker exec odoo-db-1 psql -U odoo -d %s -t -A -F'|' -c \"%s\" 2>/dev/null || echo '(table absente)'" % (
    DB, "SELECT id, edi_identification, proxy_type, edi_mode FROM account_edi_proxy_client_user"),
    label="account_edi_proxy_client_user (enregistrement PA/PDP)")

# 5. parametres systeme lies a l'einvoicing
psql("SELECT key, value FROM ir_config_parameter WHERE key LIKE '%edi%' "
     "OR key LIKE '%pdp%' OR key LIKE '%einvoic%' OR key LIKE '%proxy%' ORDER BY key")

# 6. erreurs recentes dans les logs Odoo (pdp / einvoice / edi / traceback)
run("docker logs --since 720h odoo 2>&1 | grep -iE 'pdp|einvoic|l10n_fr_pdp|account_edi|ERROR.*edi|Traceback' "
    "| tail -40 || echo '(rien)'", label="logs Odoo (pdp/edi, 30 jours)")

ssh.close()
print("\n=== PROBE TERMINEE (aucune ecriture) ===")
