"""Check whether failed-relance records got x_followup_level marked anyway,
and the partner email situation -> proves the silent-skip side effect."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read

# Sample failed records from the exception queue
inv_ids = [656, 657, 649, 650, 647, 648, 390, 391, 645, 398, 446]
so_ids = [501, 526, 497, 495, 517, 476, 507]

print("=== INVOICES (failed relance) ===")
invs = search_read("account.move", [("id", "in", inv_ids)],
                   ["id", "name", "payment_state", "invoice_date_due",
                    "x_followup_level", "x_followup_last_sent_date",
                    "partner_id"])
for i in invs:
    pe = search_read("res.partner", [("id", "=", i["partner_id"][0])], ["email"])
    print(f"  {i['name']} pay={i['payment_state']} due={i['invoice_date_due']} "
          f"level={i.get('x_followup_level')} sent={i.get('x_followup_last_sent_date')} "
          f"partner_email={pe[0].get('email')!r}")

print("\n=== DEVIS (failed relance) ===")
sos = search_read("sale.order", [("id", "in", so_ids)],
                  ["id", "name", "state", "x_followup_level",
                   "x_followup_last_sent_date", "partner_id"])
for s in sos:
    pe = search_read("res.partner", [("id", "=", s["partner_id"][0])], ["email"])
    print(f"  {s['name']} state={s['state']} level={s.get('x_followup_level')} "
          f"sent={s.get('x_followup_last_sent_date')} partner_email={pe[0].get('email')!r}")

# Recovery scope: how many unpaid overdue invoices already have level>0
print("\n=== RECOVERY SCOPE ===")
overdue_marked = search_read("account.move",
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
     ("payment_state", "in", ["not_paid", "partial"]),
     ("x_followup_level", ">", 0)],
    ["id"])
print(f"Overdue unpaid invoices with x_followup_level>0 (falsely marked): {len(overdue_marked)}")
devis_marked = search_read("sale.order",
    [("state", "=", "sent"), ("x_followup_level", ">", 0)], ["id"])
print(f"Sent devis with x_followup_level>0: {len(devis_marked)}")
