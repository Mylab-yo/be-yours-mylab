"""Render-verify the Switzerland origin note on the invoice report.

Renders a real posted invoice TWICE inside one transaction:
  1. as-is (baseline, expected non-CH -> no note)
  2. after forcing the delivery partner country to CH (-> note must appear with today's date)
Then rolls back so nothing is persisted. Read-only effect on the DB.
"""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=20)

SHELL_CODE = r'''
import re
R = env['ir.actions.report']
report = env.ref('account.account_invoices')
inv = env['account.move'].search([('move_type','=','out_invoice'),('state','=','posted')], limit=1)
print('INVOICE', inv.name, '| ship country =', inv.partner_shipping_id.country_id.code or inv.partner_id.country_id.code)

html0 = R._render_qweb_html(report.id, inv.ids)[0].decode('utf-8','replace')
print('BASELINE has EORI note:', 'EORI FR49950066800086' in html0)

ship = inv.partner_shipping_id or inv.partner_id
ship.write({'country_id': env.ref('base.ch').id})
inv.invalidate_recordset()
html1 = R._render_qweb_html(report.id, inv.ids)[0].decode('utf-8','replace')
print('CH has EORI note  :', 'EORI FR49950066800086' in html1)
print('CH has COV line   :', 'SANS COV' in html1)
print('CH has signature  :', 'Joseph DURAND' in html1)
i = html1.find('Cavaillon')
print('CH date context   :', re.sub(r'\s+',' ', html1[i-15:i+70]) if i>=0 else 'NO CAVAILLON')

env.cr.rollback()
print('ROLLED BACK (no DB change)')
'''
sftp = ssh.open_sftp()
with sftp.file('/tmp/verify_ch_note.py', 'w') as f:
    f.write(SHELL_CODE)
sftp.close()


def run(cmd):
    _in, out, err = ssh.exec_command(cmd)
    return out.read().decode('utf-8', 'replace')


run("docker cp /tmp/verify_ch_note.py odoo:/tmp/verify_ch_note.py")
out = run("docker exec odoo bash -c 'cat /tmp/verify_ch_note.py | odoo shell -d OdooYJ --no-http 2>&1' "
          "| grep -vE 'odoo\\.(modules|addons|sql_db|service|tools|api|models)'")
print(out[-2500:])
ssh.close()
