"""Fix print_report_name across BOTH en_US and fr_FR translations on all 7 patched reports.

Uses Odoo shell on the container to bypass XML-RPC language quirks.
"""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=30)

# Single Python that updates print_report_name on each report in both langs
fix_py = r'''
PATCHES = {
    412: "'%s - %s - %s' % (object.name, (object.partner_id.name or '').replace('/', '-'), (object.state in ('draft', 'sent') and 'Devis' or 'Bon de commande'))",
    413: "'%s - %s - PRO-FORMA' % (object.name, (object.partner_id.name or '').replace('/', '-'))",
    449: "'%s - %s - %s' % (object.name, (object.partner_id.name or '').replace('/', '-'), (object.state in ('draft', 'sent') and 'Devis' or 'Bon de commande'))",
    775: "'%s - %s - Bon de livraison' % (object.name.replace('/', '-'), (object.partner_id.name or '').replace('/', '-'))",
    507: "'%s - %s - Colisage' % (object.name.replace('/', '-'), (object.partner_id.name or '').replace('/', '-'))",
    325: "'%s - %s - %s' % ((object.name or '').replace('/', '-'), (object.partner_id.name or '').replace('/', '-'), (object.move_type == 'out_refund' and 'Avoir' or object.move_type == 'in_refund' and 'Avoir fournisseur' or object.move_type == 'in_invoice' and 'Facture fournisseur' or 'Facture'))",
    327: "'%s - %s - %s' % ((object.name or '').replace('/', '-'), (object.partner_id.name or '').replace('/', '-'), (object.move_type == 'out_refund' and 'Avoir' or object.move_type == 'in_refund' and 'Avoir fournisseur' or object.move_type == 'in_invoice' and 'Facture fournisseur' or 'Facture'))",
}

for rid, expr in PATCHES.items():
    report = env["ir.actions.report"].browse(rid)
    # Write to en_US (the master language) - this also writes the value field
    report.with_context(lang="en_US").write({"print_report_name": expr})
    # Write to fr_FR explicitly
    report.with_context(lang="fr_FR").write({"print_report_name": expr})
    print(f"OK {rid} ({report.name})")
    # Verify in both languages
    en_val = report.with_context(lang="en_US").print_report_name
    fr_val = report.with_context(lang="fr_FR").print_report_name
    en_match = "OK" if en_val == expr else "MISMATCH"
    fr_match = "OK" if fr_val == expr else "MISMATCH"
    print(f"  en_US = {en_match}")
    print(f"  fr_FR = {fr_match}")
env.cr.commit()
print("\nDone - committed")
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/fix_report_translations.py', 'w') as f:
    f.write(fix_py)
sftp.close()

def run(cmd):
    print(f"\n$ {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err: print("STDERR:", err[-3000:] if len(err) > 3000 else err)

run("docker cp /tmp/fix_report_translations.py odoo:/tmp/fix.py")
run("docker exec odoo bash -c 'cat /tmp/fix.py | odoo shell -d OdooYJ --no-http 2>&1' | tail -60")

ssh.close()
