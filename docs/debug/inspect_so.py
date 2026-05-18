# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# Full S00492 read with key fields
so = m.execute_kw(DB, UID, KEY, 'sale.order', 'read', [[459]], {})[0]
relevant = [k for k in so.keys() if any(x in k.lower() for x in ['template','mail','send','quotation','signature','payment','prepay','portal','online','confirm'])]
print("=== S00492 sale.order fields (template/mail/signature/etc) ===")
for k in sorted(relevant):
    print(f"  {k}: {so[k]!r}")

# mail.template id=21 full
print()
print("=== mail.template id=21 'Sales: Send Quotation' ===")
t = m.execute_kw(DB, UID, KEY, 'mail.template', 'read', [[21]], {})[0]
for k,v in t.items():
    s = str(v)
    if len(s) > 250: s = s[:250]+'...'
    print(f"  {k}: {s}")
