# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# 1) Server action 444 detail
print("=== ir.actions.server id=444 'Sales: Send pending emails' ===")
a = m.execute_kw(DB, UID, KEY, 'ir.actions.server', 'read', [[444]], {})
for k,v in (a[0] if a else {}).items():
    s = str(v)
    if len(s) > 1500: s = s[:1500]+'...'
    print(f"  {k}: {s}")

# 2) Find ir.cron that calls 'send pending emails'  
print()
print("=== ir.cron on sale.order or send_email ===")
crons = m.execute_kw(DB, UID, KEY, 'ir.cron', 'search_read',
  [['|', ['model_id.model','=','sale.order'], ['name','ilike','quotation']]],
  {'fields':['id','name','active','ir_actions_server_id','interval_number','interval_type','nextcall','model_id']})
for c in crons:
    print(f"  id={c['id']} active={c['active']} interval={c['interval_number']} {c['interval_type']}")
    print(f"    name={c['name']!r} action={c['ir_actions_server_id']} model={c['model_id']}")
    print(f"    nextcall={c['nextcall']}")
