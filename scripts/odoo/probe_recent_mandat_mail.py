"""Verifier l'etat du mail.mail cree par le test precedent (sur FAC/2026/00012)."""
from scripts.odoo._client import search_read

# Find recent mail.mail linked to account.move id=221 (FAC/2026/00012)
mails = search_read(
    "mail.mail",
    [("model", "=", "account.move"), ("res_id", "=", 221)],
    ["id", "subject", "email_to", "state", "date", "failure_reason"],
    limit=5,
)
print("=== Recent mails on FAC/2026/00012 ===")
for m in mails:
    print(f"  id={m['id']:5d} state={m['state']:10s} to={m['email_to']!s:35s} date={m.get('date')} ")
    print(f"    subject={m['subject']!r}")
    if m.get("failure_reason"):
        print(f"    FAIL={m['failure_reason']!r}")
    print()

# Find attachments on this invoice
print("\n=== Recent attachments on FAC/2026/00012 ===")
attachments = search_read(
    "ir.attachment",
    [("res_model", "=", "account.move"), ("res_id", "=", 221), ("mimetype", "=", "application/pdf")],
    ["id", "name", "create_date"],
    limit=10,
)
for a in attachments:
    print(f"  id={a['id']:5d} create={a['create_date']} name={a['name']!r}")
