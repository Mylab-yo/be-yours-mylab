# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

autos = m.execute_kw(DB, UID, KEY, 'base.automation', 'search_read', [[]],
  {'fields':['id','name','active','trigger','model_name','filter_domain']})
print(f"=== {len(autos)} base.automation rules ===")
for a in autos:
    print(f"  id={a['id']} active={a['active']} trigger={a['trigger']!r} model={a['model_name']!r}")
    print(f"    name={a['name']!r}")
    print(f"    filter_domain={a['filter_domain']!r}")

# server actions on sale.order that send mail
print()
print("=== ir.actions.server (sale.order, type=email or with template) ===")
acts = m.execute_kw(DB, UID, KEY, 'ir.actions.server', 'search_read',
  [[['model_id.model','=','sale.order']]],
  {'fields':['id','name','state','template_id','base_automation_id']})
for a in acts:
    print(f"  id={a['id']} state={a['state']!r} tpl={a['template_id']} auto={a.get('base_automation_id')}")
    print(f"    name={a['name']!r}")

# all server actions with type 'mail_post' or 'next_activity'
print()
print("=== ir.actions.server state=mail_post on any model ===")
acts2 = m.execute_kw(DB, UID, KEY, 'ir.actions.server', 'search_read',
  [[['state','=','mail_post']]],
  {'fields':['id','name','model_id','template_id','base_automation_id']})
for a in acts2:
    print(f"  id={a['id']} model={a['model_id']} tpl={a['template_id']} auto={a.get('base_automation_id')}")
    print(f"    name={a['name']!r}")
