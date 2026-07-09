import xmlrpc.client
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# All base.automation rules
autos = m.execute_kw(DB, UID, KEY, 'base.automation', 'search_read',
  [[]],
  {'fields':['id','name','active','trigger','model_name','filter_pre_domain','filter_domain']})
print(f"=== {len(autos)} base.automation rules ===")
for a in autos:
    print(f"  id={a['id']} active={a['active']} trigger={a['trigger']!r} model={a['model_name']}")
    print(f"    name={a['name']}")
    print(f"    filter_domain={a['filter_domain']}")
