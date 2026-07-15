"""Probe mail.alias.domain (Odoo 18 default_from/catchall) + Gmail server auth mode. Read-only."""
from _client import search_read, execute

print("=== MAIL.ALIAS.DOMAIN (Odoo 18) ===")
try:
    doms = execute("mail.alias.domain", "search_read", [[]],
                   {"fields": ["id", "name", "default_from", "catchall_alias",
                               "bounce_alias", "company_ids"]})
    for d in doms:
        print(" ", d)
except Exception as exc:
    print("  ERREUR:", exc)

print("\n=== IR.MAIL_SERVER : champs disponibles (auth mode) ===")
fields = execute("ir.mail_server", "fields_get", [], {"attributes": ["string", "type"]})
for k in sorted(fields):
    if any(tok in k for tok in ("google", "oauth", "auth", "smtp_pass", "from_filter")):
        print(f"  {k}: {fields[k]}")

print("\n=== IR.MAIL_SERVER : valeurs auth ===")
srv = execute("ir.mail_server", "search_read", [[]],
              {"fields": ["id", "name", "smtp_authentication", "smtp_user",
                          "from_filter", "sequence"]})
for s in srv:
    print(" ", s)

print("\n=== RES.COMPANY : catchall / alias domain ===")
c = search_read("res.company", [("id", "=", 3)],
                ["id", "name", "email", "alias_domain_id", "catchall_email",
                 "catchall_formatted", "email_formatted"])
for x in c:
    print(" ", x)

print("\n=== TEMPLATE 34 (devis) : corps + signature incluse ? ===")
t = search_read("mail.template", [("id", "=", 34)], ["id", "name", "body_html"])
if t:
    body = t[0].get("body_html") or ""
    print(f"  longueur body={len(body)}")
    print(f"  contient 'user.signature' : {'user.signature' in body}")
    print(f"  contient 'signature'      : {'signature' in body.lower()}")
