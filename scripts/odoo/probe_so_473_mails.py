"""Trace what triggered the 'paiement recu' email on SO S00473."""
from scripts.odoo._client import search_read

# 1. Find SO
so = search_read("sale.order", [("name", "=", "S00473")],
    ["id", "name", "state", "partner_id", "amount_total", "create_date",
     "date_order", "invoice_status"])
if not so:
    print("SO S00473 introuvable")
    raise SystemExit(0)
so = so[0]
print(f"=== SO {so['name']} (id={so['id']}) ===")
for k, v in so.items():
    print(f"  {k}: {v}")

# 2. Mail messages (chatter) on this SO
print(f"\n=== mail.message sur SO ===")
msgs = search_read("mail.message",
    [("model", "=", "sale.order"), ("res_id", "=", so['id'])],
    ["id", "date", "subject", "subtype_id", "message_type", "author_id",
     "email_from", "body"])
for m in msgs:
    body_excerpt = (m.get('body') or '')[:120].replace('\n', ' ')
    print(f"  [{m['id']}] {m['date']}  type={m['message_type']}  subtype={m['subtype_id']}")
    print(f"     subject={m['subject']}  template={m.get('mail_template_id')}")
    print(f"     author={m['author_id']}  from={m.get('email_from')}")
    print(f"     body={body_excerpt}")
    print()

# 3. Find mail.template that match the wording
print(f"=== Templates contenant 'paiement' OU 'reception' ===")
tpls = search_read("mail.template",
    ["|", ("name", "ilike", "paiement"), ("name", "ilike", "reception")],
    ["id", "name", "model", "subject", "active"])
for t in tpls:
    print(f"  [{t['id']}] {t['name']}  model={t['model']}  active={t['active']}  subject={t['subject']}")

# 4. Find templates that mention "paiement pour la commande" in body (the exact wording)
print(f"\n=== Templates dont le corps contient 'paiement pour la commande' ===")
tpls2 = search_read("mail.template",
    [("body_html", "ilike", "paiement pour la commande")],
    ["id", "name", "model", "subject", "active"])
for t in tpls2:
    print(f"  [{t['id']}] {t['name']}  model={t['model']}  active={t['active']}  subject={t['subject']}")

# 5. Automated actions (base.automation) on sale.order
print(f"\n=== base.automation sur sale.order ===")
autos = search_read("base.automation",
    [("model_name", "=", "sale.order")],
    ["id", "name", "trigger", "active", "action_server_ids"])
for a in autos:
    print(f"  [{a['id']}] {a['name']}  trigger={a['trigger']}  active={a['active']}  actions={a['action_server_ids']}")

# 6. Recent mail.mail outgoing for this SO
print(f"\n=== mail.mail recent (any) ===")
mails = search_read("mail.mail",
    [("model", "=", "sale.order"), ("res_id", "=", so['id'])],
    ["id", "subject", "state", "date", "email_to", "mail_message_id"])
for m in mails:
    print(f"  [{m['id']}] {m['date']}  state={m['state']}  to={m['email_to']}  subject={m['subject']}")
