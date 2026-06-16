# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# 1) Read all fields of S00492 to find any 'auto_send' flag
print("=== S00492 fields containing 'mail', 'send', 'auto', 'template' ===")
fields = m.execute_kw(DB, UID, KEY, 'sale.order', 'fields_get', [[]], {'attributes':['type','help','string']})
relevant = sorted([f for f in fields if any(k in f.lower() for k in ['mail','send','auto_send','template','quotation'])])
print('relevant fields:', relevant)
print()
so = m.execute_kw(DB, UID, KEY, 'sale.order', 'read', [[459]], {'fields': relevant + ['state','company_id','team_id','partner_id']})
for k,v in so[0].items():
    print(f"  {k}: {v}")

# 2) Check installed modules
print()
print("=== installed modules with 'sale' or 'quote' or 'auto' ===")
mods = m.execute_kw(DB, UID, KEY, 'ir.module.module', 'search_read',
  [[['state','=','installed'], '|', '|', ['name','ilike','sale_'], ['name','ilike','quote'], ['name','ilike','auto_send']]],
  {'fields':['id','name','shortdesc','author','installed_version']})
for mod in mods: print(f"  {mod['name']:40} | {mod['shortdesc']}")
