import xmlrpc.client, json, sys
URL='https://odoo.startec-paris.com'
DB='OdooYJ'; UID=8; KEY='e6d35b4261b948664841075e8fffc3510c8db437'
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)

# 1) Recent SOs in company 3, last 4 days
sos = models.execute_kw(DB, UID, KEY, 'sale.order', 'search_read',
    [[['company_id','=',3], ['create_date', '>=', '2026-05-11 00:00:00']]],
    {'fields': ['id','name','state','client_order_ref','origin','partner_id','amount_total','create_date','date_order'],
     'order': 'create_date desc', 'limit': 100})
print(f"=== {len(sos)} SO created since 2026-05-11 ===")
for so in sos:
    print(f"  {so['name']:15} | state={so['state']:8} | ref={so['client_order_ref']!s:18} | origin={so['origin']!s:30} | total={so['amount_total']:>9.2f} | created={so['create_date']}")

# 2) Group by client_order_ref to find duplicates
print()
print("=== Duplicates by client_order_ref ===")
groups = {}
for so in sos:
    key = so['client_order_ref'] or so['origin'] or 'NONE'
    groups.setdefault(key, []).append(so)
for k, lst in groups.items():
    if len(lst) > 1:
        print(f"  DUP ref={k!r}: {len(lst)} SOs")
        for so in lst:
            print(f"     {so['name']} | {so['state']} | {so['create_date']} | total={so['amount_total']}")
