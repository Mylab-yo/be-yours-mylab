"""Probe invoice-sending template 18 + invoice report action + partner emails."""
from _client import search_read, execute

t = search_read("mail.template", [("id", "=", 18)],
                ["name", "subject", "email_from", "reply_to", "partner_to",
                 "email_to", "model_id", "report_template_ids", "lang"])
print("=== TEMPLATE 18 ===")
for k, v in t[0].items():
    print(f"  {k}: {v}")

# report templates available for account.move
print("\n=== INVOICE REPORT ACTIONS ===")
reps = search_read("ir.actions.report",
                   [("model", "=", "account.move")],
                   ["id", "name", "report_name", "report_type"])
for r in reps:
    print(" ", r)

# partner emails
print("\n=== PARTNERS ===")
for pid in (2138, 2177):
    p = search_read("res.partner", [("id", "=", pid)],
                    ["id", "name", "email"])
    print(" ", p)
