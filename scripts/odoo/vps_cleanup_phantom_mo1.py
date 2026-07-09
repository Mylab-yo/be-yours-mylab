"""Cleanup VPS odoo shell : supprime OF #1 fantome + moves fantomes (1306/1307/1311/1312) + SVL.
Garde-fou transactionnel : commit SEULEMENT si stocks inchanges (vrac40/fini150/flacon1450/bouchon7350)."""
import paramiko
from pathlib import Path
from dotenv import dotenv_values

env = dotenv_values(Path(r"d:\be-yours-mylab\.env.vps"))
HOST = env["VPS_HOST"]; PORT = int(env.get("VPS_PORT", 22))
USER = env["VPS_USER"]; PASS = env["VPS_PASS"]

SHELL_CODE = r'''
def stocks():
    return {vid: env['product.product'].browse(vid).qty_available
            for vid in (2518, 2403, 2552, 2561)}

before = stocks()
print('AVANT', before)

PHANTOM_MOVES = [1306, 1307, 1311, 1312, 1308, 1309, 1310]
moves = env['stock.move'].browse(PHANTOM_MOVES).exists()

# 1. tout en draft (write direct = pas de reversal de quant)
moves.write({'state': 'draft'})
# 2. supprime move lines (draft -> aucun impact quant)
moves.mapped('move_line_ids').unlink()
# 3. supprime SVL lies (valeur 0)
svls = env['stock.valuation.layer'].search([('stock_move_id', 'in', PHANTOM_MOVES)])
print('SVL a supprimer:', svls.ids)
svls.unlink()
# 4. supprime les moves
moves.unlink()
# 5. supprime l'OF #1 (state 'cancel' requis avant unlink, pas 'draft')
mo = env['mrp.production'].browse(1).exists()
if mo:
    mo.write({'state': 'cancel'})
    mo.unlink()
    print('MO1 supprime')

after = stocks()
print('APRES', after)

expected = {2518: 40.0, 2403: 150.0, 2552: 1450.0, 2561: 7350.0}
mo1_gone = not env['mrp.production'].browse(1).exists()
if after == expected and mo1_gone:
    env.cr.commit()
    print('>>> COMMIT OK — stocks intacts, MO1 supprime')
else:
    env.cr.rollback()
    print('>>> ROLLBACK — ecart detecte ou MO1 present, rien change')
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=20)
sftp = ssh.open_sftp()
with sftp.file('/tmp/cleanup_mo1.py', 'w') as f:
    f.write(SHELL_CODE)
sftp.close()

def run(cmd):
    _in, out, err = ssh.exec_command(cmd)
    return out.read().decode('utf-8', 'replace'), err.read().decode('utf-8', 'replace')

run("docker cp /tmp/cleanup_mo1.py odoo:/tmp/cleanup_mo1.py")
out, err = run("docker exec odoo bash -c 'cat /tmp/cleanup_mo1.py | odoo shell -d OdooYJ --no-http 2>&1' | grep -vE 'odoo.(modules|addons|sql_db|service|tools)' ")
print(out[-3000:])
ssh.close()
