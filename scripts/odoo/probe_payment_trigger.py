"""Investigate how template 23 'Sales: Payment Done' got triggered for SO S00473."""
from scripts.odoo._client import search_read

# 1. Payment transactions for SO S00473
print("=== payment.transaction lies au SO S00473 (id=440) ===")
txs = search_read("payment.transaction",
    [("sale_order_ids", "in", [440])],
    ["id", "reference", "state", "amount", "currency_id", "provider_id",
     "create_date", "last_state_change", "partner_id"])
for t in txs:
    print(f"  [{t['id']}] {t['reference']}  state={t['state']}  amount={t['amount']}")
    print(f"      provider={t['provider_id']}  created={t['create_date']}  last_change={t['last_state_change']}")

# 2. Provider config (Virement = id 19 per memory, Stripe = id 18)
print("\n=== payment.provider config ===")
provs = search_read("payment.provider", [("id", "in", [18, 19])],
    ["id", "name", "code", "state", "support_manual_capture", "is_published",
     "allow_express_checkout", "capture_manually"])
for p in provs:
    print(f"  [{p['id']}] {p['name']}  code={p['code']}  state={p['state']}")
    for k, v in p.items():
        if k not in ('id', 'name', 'code', 'state'):
            print(f"      {k}: {v}")

# 3. Template 23 details
print("\n=== Template 23 'Sales: Payment Done' ===")
t = search_read("mail.template", [("id", "=", 23)],
    ["name", "model", "active", "subject", "auto_delete", "body_html"])[0]
print(f"  name: {t['name']}  model: {t['model']}  active: {t['active']}  auto_delete: {t['auto_delete']}")
print(f"  subject: {t['subject']}")
body_excerpt = (t.get('body_html') or '')[:300].replace('\n', ' ')
print(f"  body excerpt: {body_excerpt}")

# 4. Check if template 23 is referenced anywhere in code/config
print("\n=== Where template 23 is referenced ===")
ir_data = search_read("ir.model.data",
    [("model", "=", "mail.template"), ("res_id", "=", 23)],
    ["module", "name"])
print(f"  ir.model.data: {ir_data}")

# 5. Check sale.order.template_id (for any sale.order template that auto-sends mails)
print("\n=== Other automation: ir.actions.server pour 'payment' ===")
sas = search_read("ir.actions.server",
    [("name", "ilike", "payment")],
    ["id", "name", "model_id", "state", "active"])
for sa in sas:
    print(f"  [{sa['id']}] {sa['name']}  model={sa['model_id']}  state={sa['state']}  active={sa['active']}")
