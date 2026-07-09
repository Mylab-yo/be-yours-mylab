"""PDP STEP 04 : verification de l'enrolement en MODE DEMO, transaction ROLLBACK.

But (demande Yoann : "verifie d'abord en mode demo") : prouver que l'enrolement PDP
de SARL STARTEC (company id 3) passe de bout en bout, SANS aucun appel externe et SANS
laisser la moindre trace sur la prod.

Pourquoi c'est 100% sur :
  - On force le mode demo via le parametre `account_peppol.edi.mode = demo`. Du coup
    `res.company._get_peppol_edi_mode()` renvoie 'demo' -> le decorateur @handle_demo
    mocke TOUS les appels proxy (KYC, register_proxy_user, register_receiver) en local.
    Aucun trafic vers pdp.odoo.com / iap.odoo.com.
  - La chaine d'enrolement (_register_proxy_user branche pdp + _peppol_register_receiver)
    ne contient AUCUN cr.commit() interne (verifie dans le code 18.0-20260609). Les seuls
    commit du module sont dans les crons de reception de documents, pas dans l'enrolement.
  - On termine par env.cr.rollback() dans un finally -> rien n'est persiste, meme en cas
    d'erreur. La prod (137 factures STARTEC, pipeline n8n) reste intacte.

Ce script REPLIQUE les validations du wizard pdp.registration.button_register_pdp_participant
(champs obligatoires, format identifiant, etats interdits) puis appelle les memes methodes
metier, en evitant le cr.commit() force du wizard.

Sortie attendue si tout est OK :
  - proxy user cree : proxy_type=pdp, edi_mode=demo, edi_identification=0225:499500668
  - company.account_peppol_proxy_state = 'receiver'
  - l10n_fr_pdp_annuaire_start_date = 2026-09-01
  => l'enrolement PROD marchera (seule la vraie KYC differe).

Voir aussi : pdp_step02_update.py (bump image), README.md section PDP.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import paramiko
from pathlib import Path
from dotenv import dotenv_values

DB = "OdooYJ"
COMPANY_ID = 3  # SARL STARTEC (seule entite avec SIRET + 100% des factures MY.LAB)

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)

shell = r'''
import traceback
OK = True
try:
    c = env["res.company"].browse(%d)
    c = c.with_company(c)              # garantit env.company = STARTEC pour @handle_demo
    ICP = env["ir.config_parameter"].sudo()

    # 1. FORCER le mode demo (resolution: param account_peppol.edi.mode)
    ICP.set_param("account_peppol.edi.mode", "demo")
    mode = c._get_peppol_edi_mode()
    print("1) _get_peppol_edi_mode() ->", mode)
    assert mode == "demo", "PAS en mode demo, on ARRETE (securite)"

    # 2. identifiant PDP = SIREN (declenche l'inverse -> peppol_endpoint + eas 0225)
    siren = c.partner_id._l10n_fr_pdp_get_siren()
    c.pdp_identifier = siren
    print("2) siren:", siren, "| pdp_identifier:", c.pdp_identifier,
          "| eas:", c.partner_id.peppol_eas, "| endpoint:", c.partner_id.peppol_endpoint)

    # 3. validations du wizard button_register_pdp_participant
    assert c.account_peppol_contact_email, "contact email manquant"
    assert env["res.company"]._check_pdp_identifier(c.pdp_identifier), "identifiant invalide"
    assert c.account_peppol_proxy_state not in ("smp_registration", "receiver"), "deja enrole"
    assert not c.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == "peppol"), "user peppol non-PA present"
    print("3) validations wizard: OK (email, identifiant, etat, pas de peppol)")

    # 4. creation du proxy user (mocke demo, aucun appel reseau)
    PU = env["account_edi_proxy_client.user"].with_company(c)
    edi_user = PU._register_proxy_user(c, "pdp", "demo")
    print("4) proxy user cree -> id:", edi_user.id,
          "| type:", edi_user.proxy_type, "| mode:", edi_user.edi_mode,
          "| ident:", edi_user.edi_identification,
          "| cle privee:", bool(edi_user.private_key_id))

    # 5. enregistrement comme receiver (mocke demo)
    edi_user.with_company(c)._peppol_register_receiver()
    print("5) apres register_receiver -> proxy_state:", c.account_peppol_proxy_state,
          "| annuaire_start:", c.l10n_fr_pdp_annuaire_start_date,
          "| pilot_phase:", c.l10n_fr_pdp_pilot_phase)

    assert c.account_peppol_proxy_state == "receiver", "etat final != receiver"
    print("\n==> DEMO OK : l'enrolement passe de bout en bout. Prod marchera (KYC reelle en plus).")
except Exception as e:
    OK = False
    print("\n!! ECHEC DEMO :", repr(e))
    traceback.print_exc()
finally:
    env.cr.rollback()
    print("\n== ROLLBACK effectue : AUCUNE modification persistee sur la prod ==")
    print("RESULT:", "PASS" if OK else "FAIL")
''' % COMPANY_ID

sftp = ssh.open_sftp()
with sftp.file("/tmp/pdp_demo_dryrun.py", "w") as f:
    f.write(shell)
sftp.close()
ssh.exec_command("docker cp /tmp/pdp_demo_dryrun.py odoo:/tmp/pdp_demo_dryrun.py")[1].channel.recv_exit_status()

cmd = ("docker exec odoo bash -c 'cat /tmp/pdp_demo_dryrun.py | odoo shell -d %s --no-http 2>&1' "
       "| grep -vE 'INFO|WARNING|Warn:|Modules loaded|Registry|odoo.modules|odoo.service|odoo.sql_db|monkey patch'" % DB)
_, o, e = ssh.exec_command(cmd)
print(o.read().decode("utf-8", "replace"))
err = e.read().decode("utf-8", "replace").strip()
if err:
    print("[stderr]", err[-600:])
# nettoie le fichier temporaire
ssh.exec_command("docker exec odoo rm -f /tmp/pdp_demo_dryrun.py; rm -f /tmp/pdp_demo_dryrun.py")
ssh.close()
