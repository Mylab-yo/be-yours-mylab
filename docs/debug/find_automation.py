import xmlrpc.client
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

sos = m.execute_kw(DB, UID, KEY, 'sale.order', 'search_read', [[['name','=','S00492']]], {'fields':['id'], 'limit':1})
soid = sos[0]['id']

msgs = m.execute_kw(DB, UID, KEY, 'mail.message', 'search_read',
  [[['model','=','sale.order'], ['res_id','=',soid], ['message_type','=','comment']]],
  {'fields':['id','date','subject','email_from','author_id','partner_ids','subtype_id','body'],
   'order':'date asc'})
print(f"=== {len(msgs)} comments on S00492 ===")
for msg in msgs:
    print(f"  msg id={msg['id']} date={msg['date']}")
    print(f"    subj={msg['subject']!r} from={msg['email_from']}")
    print(f"    subtype={msg['subtype_id']} author={msg['author_id']}")
    print(f"    partners={msg['partner_ids']}")
    print(f"    body (first 300 char): {(msg['body'] or '')[:300]}")
    print()

# tracking_value / mail.tracking.value pour voir l'état avant
trks = m.execute_kw(DB, UID, KEY, 'mail.tracking.value', 'search_read',
  [[['mail_message_id','in',[msg['id'] for msg in msgs]]]],
  {'fields':['id','mail_message_id','field_desc','old_value_char','new_value_char']})
print("tracking:")
for t in trks: print(f"  msg={t['mail_message_id']} field={t['field_desc']}: {t['old_value_char']} -> {t['new_value_char']}")

# Find mail.mail / outgoing
mails = m.execute_kw(DB, UID, KEY, 'mail.mail', 'search_read',
  [[['mail_message_id','in',[msg['id'] for msg in msgs]]]],
  {'fields':['id','subject','state','message_id','date','mail_message_id','recipient_ids','email_to','reply_to','model','res_id','mail_server_id','create_uid','create_date']})
print()
print(f"=== {len(mails)} mail.mail ===")
for ma in mails:
    print(f"  id={ma['id']} state={ma['state']} subj={ma['subject']!r}")
    print(f"    msg={ma['mail_message_id']} recip={ma['recipient_ids']} to={ma['email_to']}")
    print(f"    created_by={ma['create_uid']} at={ma['create_date']} server={ma['mail_server_id']}")
