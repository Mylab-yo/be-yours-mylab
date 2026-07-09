"""Inspection READ-ONLY via odoo shell sur VPS : OF #1 fantome + mouvements lot 51 + valorisation."""
import os, paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
HOST = env["VPS_HOST"]; PORT = int(env.get("VPS_PORT", 22))
USER = env["VPS_USER"]; PASS = env["VPS_PASS"]

SHELL_CODE = r'''
mo = env['mrp.production'].browse(1)
print('=== MO1 ===', mo.name, '| state=', mo.state)
print('raw moves :', mo.move_raw_ids.ids, mo.move_raw_ids.mapped('state'))
print('fin moves :', mo.move_finished_ids.ids, mo.move_finished_ids.mapped('state'))

print('\n=== move.lines lot 51 (fini 220A526C) ===')
for ml in env['stock.move.line'].search([('lot_id','=',51)]):
    m = ml.move_id
    print('ML', ml.id, '| move', m.id, repr(m.reference), m.state,
          '| qty', ml.quantity, '|', ml.location_id.complete_name, '->', ml.location_dest_id.complete_name,
          '| MO=', m.production_id.id or m.raw_material_production_id.id, '| inv=', bool(m.is_inventory))

print('\n=== stock.move is_inventory sur fini 2403 ===')
for m in env['stock.move'].search([('product_id','=',2403),('is_inventory','=',True)]):
    print('inv move', m.id, m.state, m.quantity, m.location_id.complete_name,'->',m.location_dest_id.complete_name)

print('\n=== valuation layers (2403,2518,2552,2561) ===')
svls = env['stock.valuation.layer'].search([('product_id','in',[2403,2518,2552,2561])])
print('count =', len(svls))
for s in svls[:20]:
    print('SVL', s.id, s.product_id.display_name[:30], 'qty=', s.quantity, 'val=', s.value,
          'ref=', s.stock_move_id.reference)
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)

sftp = ssh.open_sftp()
with sftp.file('/tmp/inspect_mo1.py', 'w') as f:
    f.write(SHELL_CODE)
sftp.close()

def run(cmd):
    _in, out, err = ssh.exec_command(cmd)
    return out.read().decode('utf-8', 'replace'), err.read().decode('utf-8', 'replace')

run("docker cp /tmp/inspect_mo1.py odoo:/tmp/inspect_mo1.py")
out, err = run("docker exec odoo bash -c 'cat /tmp/inspect_mo1.py | odoo shell -d OdooYJ --no-http 2>&1' | grep -vE 'odoo.(modules|addons|sql_db|service)' ")
print(out[-4000:])
ssh.close()
