# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# Find mail templates with subject like "MYLAB" or "Devis"
tpls = m.execute_kw(DB, UID, KEY, 'mail.template', 'search_read',
  [['|', ['subject','ilike','MYLAB'], ['subject','ilike','Devis']]],
  {'fields':['id','name','subject','model','email_from','partner_to','auto_delete']})
print(f"=== {len(tpls)} mail.template matching MYLAB/Devis ===")
for t in tpls:
    print(f"  id={t['id']} model={t['model']!r}")
    print(f"    name={t['name']!r}")
    print(f"    subject={t['subject']!r}")
    print(f"    partner_to={t['partner_to']!r}")

# base.automation id=2 detail
print()
print("=== base.automation id=2 detail ===")
a2 = m.execute_kw(DB, UID, KEY, 'base.automation', 'read', [[2]], {})
for k,v in (a2[0] if a2 else {}).items():
    s = str(v)
    if len(s) > 200: s = s[:200]+'...'
    print(f"  {k}: {s}")

# server action 782 detail
print()
print("=== ir.actions.server id=782 detail ===")
a = m.execute_kw(DB, UID, KEY, 'ir.actions.server', 'read', [[782]], {})
for k,v in (a[0] if a else {}).items():
    s = str(v)
    if len(s) > 600: s = s[:600]+'...'
    print(f"  {k}: {s}")
