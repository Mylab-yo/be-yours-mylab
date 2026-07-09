import xmlrpc.client
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

sos = m.execute_kw(DB, UID, KEY, 'sale.order', 'search_read', [[['name','=','S00492']]], {'fields':['id','state'], 'limit':1})
soid = sos[0]['id']
print(f"S00492 id={soid} state={sos[0]['state']}")

# All mail messages
msgs = m.execute_kw(DB, UID, KEY, 'mail.message', 'search_read',
  [[['model','=','sale.order'], ['res_id','=',soid]]],
  {'fields':['id','date','subject','email_from','author_id','partner_ids','subtype_id','body','message_type'],
   'order':'date asc'})
print(f"=== {len(msgs)} all messages on S00492 ===")
for msg in msgs:
    print(f"  id={msg['id']} type={msg['message_type']} subj={msg['subject']!r} date={msg['date']}")
    print(f"    author={msg['author_id']} from={msg['email_from']} partners={msg['partner_ids']}")
    print(f"    body excerpt: {(msg['body'] or '')[:250].replace(chr(10),' ')}")
    print()
