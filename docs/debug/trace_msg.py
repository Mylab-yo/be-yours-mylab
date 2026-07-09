# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# Read mail.message 4522 — full record  
msg = m.execute_kw(DB, UID, KEY, 'mail.message', 'read', [[4522]], {})[0]
for k,v in msg.items():
    s = str(v)
    if len(s) > 250: s = s[:250]+'...'
    print(f"  {k}: {s}")

# Find mail.mail by mail_message_id=4522
print()
mails = m.execute_kw(DB, UID, KEY, 'mail.mail', 'search_read',
  [[['mail_message_id','=',4522]]], {'fields':['id','subject','state','create_uid','create_date','mail_server_id','model','res_id','email_to','recipient_ids','message_type']})
print(f"=== mail.mail for msg 4522: {len(mails)} ===")
for ma in mails:
    print(f"  id={ma['id']} state={ma['state']} subj={ma['subject']!r}")
    print(f"    create_uid={ma['create_uid']} create_date={ma['create_date']}")

# Check the SO state JUST after create - was it draft?
print()
# tracking values for SO 459 (S00492) - get state changes
print("=== state changes on S00492 ===")
mids = m.execute_kw(DB, UID, KEY, 'mail.message', 'search', [[['model','=','sale.order'], ['res_id','=',459]]], {'order':'date asc'})
print(f"All msg ids on S00492: {mids}")
