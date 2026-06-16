# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# ir.default for sale.order.sale_order_template_id
print("=== ir.default for sale.order ===")
defs = m.execute_kw(DB, UID, KEY, 'ir.default', 'search_read',
  [[['field_id.model','=','sale.order']]],
  {'fields':['id','field_id','json_value','company_id','user_id','condition']})
for d in defs:
    print(f"  id={d['id']} field={d['field_id']} value={d['json_value']!r} company={d['company_id']} user={d['user_id']}")

# Companies that have sale_order_template_id set
print()
print("=== res.company 3 sale settings ===")
c = m.execute_kw(DB, UID, KEY, 'res.company', 'read', [[3]],
  {'fields':['id','name','quotation_validity_days','portal_confirmation_sign','portal_confirmation_pay']})
print(c)

# Test: create empty draft SO via XML-RPC and check if template applies
# (just simulate by checking default_get)
print()
print("=== sale.order default_get for sale_order_template_id ===")
ctx = {'company_id': 3, 'allowed_company_ids': [3]}
defs = m.execute_kw(DB, UID, KEY, 'sale.order', 'default_get', [['sale_order_template_id', 'company_id', 'pricelist_id']], {'context': ctx})
print(defs)
