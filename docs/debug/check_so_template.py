# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

print("=== sale.order.template id=1 ===")
t = m.execute_kw(DB, UID, KEY, 'sale.order.template', 'read', [[1]], {})[0]
for k,v in t.items():
    s = str(v)
    if len(s) > 250: s = s[:250]+'...'
    print(f"  {k}: {s}")

# Check res.config for sale auto-send
print()
print("=== ir.config_parameter for sale.* ===")
ps = m.execute_kw(DB, UID, KEY, 'ir.config_parameter', 'search_read',
  [[['key','ilike','sale']]], {'fields':['key','value']})
for p in ps: print(f"  {p['key']:60} = {p['value']!r}")

# Check the partner has auto-send template?
print()
print("=== Smith lindsay partner 2045 ===")
p = m.execute_kw(DB, UID, KEY, 'res.partner', 'read', [[2045]], {})[0]
for k in ['id','name','email','property_payment_term_id','property_account_position_id','sale_order_template_id','sale_warn']:
    if k in p: print(f"  {k}: {p.get(k)}")
