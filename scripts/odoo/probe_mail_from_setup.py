"""Probe outgoing mail identity setup: SMTP servers, from_filter, aliases, templates, signatures.

Read-only. Sert a cadrer la config d'envoi devis/factures (contact@) vs relances (comptabilite@).
"""
from _client import search_read, execute, UID

print("=== IR.MAIL_SERVER (SMTP sortants) ===")
servers = search_read(
    "ir.mail_server", [],
    ["id", "name", "smtp_host", "smtp_port", "smtp_user", "smtp_encryption",
     "from_filter", "sequence", "active"],
)
for s in servers:
    print(" ", s)
if not servers:
    print("  (aucun serveur SMTP configure -> Odoo utilise le mailer par defaut/mailgun?)")

print("\n=== RES.COMPANY ===")
comps = search_read("res.company", [], ["id", "name", "email", "partner_id"])
for c in comps:
    print(" ", c)

print("\n=== IR.CONFIG_PARAMETER (mail.*) ===")
params = search_read(
    "ir.config_parameter", [("key", "like", "mail.")], ["key", "value"],
)
for p in params:
    print(f"  {p['key']} = {p['value']}")

print("\n=== MAIL.TEMPLATE (email_from / reply_to renseignes) ===")
tpls = search_read(
    "mail.template", [],
    ["id", "name", "model_id", "email_from", "reply_to", "subject"],
)
for t in tpls:
    if t.get("email_from") or t.get("reply_to"):
        print(f"  [{t['id']}] {t['name']}")
        print(f"       model={t['model_id']}")
        print(f"       email_from={t.get('email_from')!r}  reply_to={t.get('reply_to')!r}")

print("\n=== MAIL.TEMPLATE (cles: devis 34, facture 18, relances, tracking 27) ===")
key_tpls = search_read(
    "mail.template", [("id", "in", [18, 27, 34])],
    ["id", "name", "email_from", "reply_to", "subject", "model_id"],
)
for t in key_tpls:
    print(" ", t)

print("\n=== MAIL.TEMPLATE (relances / followup) ===")
fu = search_read(
    "mail.template", ["|", ("name", "ilike", "relance"), ("name", "ilike", "followup")],
    ["id", "name", "email_from", "reply_to", "model_id"],
)
for t in fu:
    print(" ", t)

print("\n=== RES.USERS (signature) ===")
users = search_read(
    "res.users", [("id", "=", UID)], ["id", "name", "login", "email", "signature"],
)
for u in users:
    print(f"  id={u['id']} name={u['name']} login={u['login']} email={u.get('email')}")
    print(f"  signature=\n{u.get('signature')}")

print("\n=== MAIL.ALIAS ===")
try:
    aliases = search_read(
        "mail.alias", [], ["id", "alias_name", "alias_model_id", "alias_domain"], limit=20,
    )
    for a in aliases:
        print(" ", a)
except Exception as exc:
    print("  (mail.alias illisible)", exc)

print("\n=== MODULES MAIL INSTALLES ===")
mods = search_read(
    "ir.module.module",
    [("state", "=", "installed"), ("name", "like", "mail")],
    ["name", "state"],
)
for m in mods:
    print(" ", m["name"])
