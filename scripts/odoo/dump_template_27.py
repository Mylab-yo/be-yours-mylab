"""Dump template id=27 (Shipping: Send by Email) + infos transporteur tracking."""
from pathlib import Path
from scripts.odoo._client import search_read, execute

t = search_read("mail.template", [("id", "=", 27)],
    ["name", "subject", "email_to", "partner_to", "body_html"])[0]
out = Path("scripts/odoo/_template_27_dump.html")
out.write_text(
    f"<!-- name: {t['name']} -->\n"
    f"<!-- subject: {t['subject']} -->\n"
    f"<!-- partner_to: {t['partner_to']} -->\n"
    f"<!-- email_to: {t['email_to']} -->\n\n"
    f"{t['body_html']}",
    encoding="utf-8")
print(f"Wrote {out} (body len={len(t['body_html'])})")

# Tracking URL: les carriers base_on_rule renvoient-ils un lien ?
print("\nChamps delivery.carrier lies au tracking :")
fg = execute("delivery.carrier", "fields_get", [], {"attributes": ["string", "type"]})
for f, m in sorted(fg.items()):
    if "track" in f or "url" in f or "link" in f:
        print(f"  {f:<28} {m.get('type'):<10} {m.get('string')}")
