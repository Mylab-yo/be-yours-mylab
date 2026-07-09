# -*- coding: utf-8 -*-
import xmlrpc.client, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
m = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# Check 8 most recent Shopify-origin SOs
sos = m.execute_kw(DB, UID, KEY, 'sale.order', 'search_read',
  [[['company_id','=',3], ['client_order_ref','!=',False], ['create_date','>=','2026-05-01']]],
  {'fields':['id','name','state','create_date','partner_id','amount_total'], 'order':'create_date desc', 'limit':10})
print(f"=== {len(sos)} Shopify-origin SOs since 2026-05-01 ===")
for so in sos:
    # Check mails sent
    msgs = m.execute_kw(DB, UID, KEY, 'mail.message', 'search_read',
      [[['model','=','sale.order'], ['res_id','=',so['id']], ['subject','ilike','Devis']]],
      {'fields':['id','date','subject','partner_ids'], 'order':'date asc'})
    auto_mail = '✗'
    delay = None
    for msg in msgs:
        if msg['partner_ids']:
            auto_mail = '✓'
            d1 = so['create_date']
            d2 = msg['date']
            from datetime import datetime
            t1 = datetime.strptime(d1, '%Y-%m-%d %H:%M:%S')
            t2 = datetime.strptime(d2, '%Y-%m-%d %H:%M:%S')
            delay = (t2-t1).total_seconds()
            break
    print(f"  {so['name']} {so['state']:6} | created {so['create_date']} | mail-quotation-sent={auto_mail} delay={delay}s | {so['amount_total']:>9.2f}€")
