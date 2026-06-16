import xmlrpc.client
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
# Pull S00479, S00481, S00485, S00488, S00489 with full info incl partner email, create_uid, message_ids
names = ['S00479', 'S00481', 'S00485', 'S00488', 'S00489', 'S00490', 'S00491', 'S00492']
sos = models.execute_kw(DB, UID, KEY, 'sale.order', 'search_read',
  [[['name','in',names]]],
  {'fields': ['id','name','state','partner_id','amount_total','create_date','create_uid','write_date','date_order','order_line']})
for so in sos:
    print(f"  {so['name']} state={so['state']:8} create_uid={so['create_uid']} partner={so['partner_id']} total={so['amount_total']} lines={len(so['order_line'])}")

print()
# Now pull messages on the 'sent' ones
for n in ['S00481', 'S00489']:
    sid = [s['id'] for s in sos if s['name']==n][0]
    msgs = models.execute_kw(DB, UID, KEY, 'mail.message', 'search_read',
      [[['model','=','sale.order'], ['res_id','=',sid]]],
      {'fields':['id','date','author_id','subtype_id','subject','message_type','email_from','partner_ids','mail_activity_type_id','body'],
       'order':'date asc','limit':20})
    print(f"=== Messages on {n} (id={sid}) ===")
    for m in msgs:
        body_excerpt = (m['body'] or '')[:150].replace('\n',' ').replace('<','&lt;')
        print(f"  {m['date']} | type={m['message_type']} | author={m['author_id']} | from={m['email_from']} | subj={m['subject']}")
        print(f"     body: {body_excerpt}")
