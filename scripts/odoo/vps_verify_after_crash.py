"""Verifie l'etat REEL apres le crash : moves/MO1 supprimes ou rollback ? Stocks intacts ?"""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(env["VPS_HOST"], port=int(env.get("VPS_PORT", 22)),
            username=env["VPS_USER"], password=env["VPS_PASS"], timeout=20)

SHELL_CODE = r'''
print('MO1 existe ?', bool(env['mrp.production'].browse(1).exists()))
print('MO2 existe ?', bool(env['mrp.production'].browse(2).exists()))
mv = env['stock.move'].browse([1306,1307,1311,1312,1308,1309,1310]).exists()
print('moves fantomes restants:', mv.ids)
print('move 1316 (MO2 fini) existe ?', bool(env['stock.move'].browse(1316).exists()))
print('STOCKS:', {vid: env['product.product'].browse(vid).qty_available for vid in (2518,2403,2552,2561)})
q = env['stock.quant'].search([('product_id','=',2403),('location_id.usage','=','internal'),('quantity','>',0)])
for r in q:
    print('quant fini', r.id, r.location_id.complete_name, r.lot_id.name, r.quantity)
m1 = env['mrp.production'].browse(1).exists()
if m1:
    print('MO1 state =', m1.state, '| fin moves:', m1.move_finished_ids.ids,
          '| raw moves:', m1.move_raw_ids.ids)
'''
sftp = ssh.open_sftp()
with sftp.file('/tmp/verify_crash.py', 'w') as f:
    f.write(SHELL_CODE)
sftp.close()
def run(cmd):
    _in, out, err = ssh.exec_command(cmd); return out.read().decode('utf-8','replace')
run("docker cp /tmp/verify_crash.py odoo:/tmp/verify_crash.py")
out = run("docker exec odoo bash -c 'cat /tmp/verify_crash.py | odoo shell -d OdooYJ --no-http 2>&1' | grep -vE 'odoo.(modules|addons|sql_db|service|tools)'")
print(out[-2500:])
ssh.close()
