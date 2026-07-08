# -*- coding: utf-8 -*-
"""Fix 3 : template devis — afficher line.name (description) au lieu de line.product_id.name."""
import os, sys, xmlrpc.client
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('d:/Configurateur Designs MyLab/mylab-configurateur/.env.local')

ODOO = 'https://odoo.startec-paris.com'
DB, UID = 'OdooYJ', 8
KEY = os.environ.get('ODOO_API_KEY') or os.environ.get('ODOO_PASSWORD')
obj = xmlrpc.client.ServerProxy(f'{ODOO}/xmlrpc/2/object')

VIEW_ID = 1286  # sale.report_saleorder_document (customisée, inherit=False)

view = obj.execute_kw(DB, UID, KEY, 'ir.ui.view', 'read', [[VIEW_ID]],
    {'fields': ['key', 'arch_db', 'write_date']})[0]
arch = view['arch_db']
print(f"Vue {view['key']} — maj {view['write_date']} — arch {len(arch)} chars")

# Backup avant modif
backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'backup_report_saleorder_document_1286.xml')
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(arch)
print(f"Backup écrit : {backup_path}")

OLD = '<td name="td_name"><span t-out="line.product_id.name">Produit</span></td>'
NEW = '<td name="td_name"><span t-field="line.name">Produit</span></td>'

count = arch.count(OLD)
print(f"Occurrences de la cellule td_name à remplacer : {count}")
if count != 1:
    # afficher le contexte réel pour ajuster
    import re
    for m in re.finditer(r'td_name.{0,220}', arch, re.S):
        print('CONTEXTE:', m.group(0)[:260])
    sys.exit(1)

new_arch = arch.replace(OLD, NEW)
obj.execute_kw(DB, UID, KEY, 'ir.ui.view', 'write', [[VIEW_ID], {'arch_base': new_arch}])
print('✓ arch_base écrit')

# Vérification : relire et confirmer
check = obj.execute_kw(DB, UID, KEY, 'ir.ui.view', 'read', [[VIEW_ID]], {'fields': ['arch_db']})[0]['arch_db']
assert 't-field="line.name"' in check and OLD not in check, 'La modification ne se retrouve pas dans arch_db !'
print('✓ Vérifié en relecture : td_name rend désormais line.name')
