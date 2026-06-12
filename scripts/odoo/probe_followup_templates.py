"""Probe followup templates recipient config + failed mails dates + cron state."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read

NAMES = ["mylab_devis_relance_l1", "mylab_devis_relance_l2",
         "mylab_facture_relance_l1", "mylab_facture_relance_l2",
         "mylab_facture_relance_l3"]

print("=== TEMPLATES RECIPIENT CONFIG ===")
tpls = search_read("mail.template", [("name", "in", NAMES)],
                   ["id", "name", "partner_to", "email_to", "use_default_to",
                    "auto_delete"])
for t in tpls:
    print(t)

print("\n=== FAILED FOLLOWUP MAILS (date + record) ===")
failed = search_read("mail.mail",
                     [("state", "=", "exception")],
                     ["id", "subject", "date", "create_date", "model", "res_id",
                      "email_to", "recipient_ids"], limit=50)
# only the followup-looking ones
for m in sorted(failed, key=lambda x: x.get("create_date") or "", reverse=True):
    print(f"  [{m['id']}] {m.get('create_date')} | {m['model']}#{m['res_id']} "
          f"| to={m['email_to']!r} recip={m.get('recipient_ids')} | {m['subject']}")

print(f"\nTotal exception mails: {len(failed)}")

print("\n=== FOLLOWUP CRON STATE ===")
crons = search_read("ir.cron",
                    [("ir_actions_server_id.name", "=",
                      "MyLab — Relances devis & factures")],
                    ["id", "active", "nextcall", "lastcall"])
print(crons)
