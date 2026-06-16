import xmlrpc.client
URL='https://odoo.startec-paris.com'; DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# Get all SOs from last 30 days with partner email
sos = models.execute_kw(DB, UID, KEY, 'sale.order', 'search_read',
  [[['company_id','=',3], ['create_date','>=','2026-04-15 00:00:00']]],
  {'fields':['id','name','state','client_order_ref','origin','partner_id','amount_total','create_date'],
   'order':'create_date desc'})

partners = {so['partner_id'][0] for so in sos if so['partner_id']}
parts = models.execute_kw(DB, UID, KEY, 'res.partner', 'read', [list(partners)], {'fields':['id','email','name']})
pmap = {p['id']: p for p in parts}

# Group by partner email
by_email = {}
for so in sos:
    p = pmap.get(so['partner_id'][0]) if so['partner_id'] else None
    em = (p and p['email']) or 'NOEMAIL_'+str(so['partner_id'])
    by_email.setdefault(em, []).append(so)

print("=== Partners with 2+ SOs in last 30 days ===")
for em, lst in sorted(by_email.items(), key=lambda x: -len(x[1])):
    if len(lst) < 2: continue
    print(f"\n--- {em} ({len(lst)} SOs) ---")
    for so in lst:
        ref = so['client_order_ref'] or '-'
        origin = so['origin'] or '-'
        print(f"  {so['name']:8} {so['state']:6} | ref={ref:18} | origin={origin:30} | total={so['amount_total']:>9.2f} | {so['create_date']}")
