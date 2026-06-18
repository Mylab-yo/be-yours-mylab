"""PDP STEP 03b : etat exact de l'ENREGISTREMENT (KYC/PA) + tracebacks logs. READ-ONLY."""
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
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if out:
        print(out.rstrip())
    if err.strip():
        print(f"[stderr] {err.rstrip()}")
    return out


def psql(q, label=None):
    return run("docker exec odoo-db-1 psql -U odoo -d %s -t -A -F'|' -c \"%s\"" % (DB, q), label)


# 1. registration state sur la societe (+ partner vat/siret)
psql("SELECT c.id, c.name, c.pdp_kyc_status, c.pdp_authentication_uuid, "
     "c.account_peppol_proxy_state, c.l10n_fr_pdp_pilot_phase, c.l10n_fr_pdp_send_to_ppf, "
     "p.vat, p.siret "
     "FROM res_company c JOIN res_partner p ON p.id=c.partner_id ORDER BY c.id",
     label="res_company registration (KYC/PA/SIRET)")

# 2. proxy users (enrolment reel cote IAP/PA)
psql("SELECT id, edi_identification, proxy_type, edi_mode, active "
     "FROM account_edi_proxy_client_user ORDER BY id",
     label="account_edi_proxy_client_user")

# 3. config params reels (key|value)
psql("SELECT key||' = '||COALESCE(value,'<null>') FROM ir_config_parameter "
     "WHERE key LIKE '%pdp%' OR key LIKE '%peppol%' OR key LIKE '%edi%' ORDER BY key",
     label="ir_config_parameter (pdp/peppol/edi)")

# 4. FULL tracebacks recents (avec contexte apres le trigger)
run("docker logs --since 168h odoo 2>&1 | grep -A 25 'Traceback (most recent call last)' | tail -120",
    label="Tracebacks complets (7 jours)")

ssh.close()
print("\n=== FIN PROBE 03b ===")
