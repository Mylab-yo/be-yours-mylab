"""Settle the 7 card-paid Shopify invoices stuck in not_paid (Odoo reconciliation
gap — n8n auto-payment didn't run for them). Replicates 09_register_payment.js:
register an inbound payment on journal SHOP id=26 -> payment_state=paid -> they
drop off the followup cron. The Stripe payout later clears 512002 via the LCL
statement reconciliation (reconcile_shopify_payouts.py).

EXCLUDES FAC/2026/00098 (#3491, Virement bancaire) — handled separately.
Idempotent: skips invoices already paid.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read, execute

SHOPIFY_JOURNAL_ID = 26
SHOPIFY_PML_ID = 17

CARD_FACS = ["FAC/2026/00096", "FAC/2026/00097", "FAC/2026/00099",
             "FAC/2026/00101", "FAC/2026/00102", "FAC/2026/00104",
             "FAC/2026/00107"]

invs = search_read("account.move", [("name", "in", CARD_FACS)],
                   ["id", "name", "state", "payment_state", "move_type",
                    "amount_residual", "invoice_date", "invoice_origin"])

paid, skipped, failed = [], [], []
for inv in sorted(invs, key=lambda x: x["name"]):
    if inv["state"] != "posted":
        skipped.append((inv["name"], f"state={inv['state']}")); continue
    if inv["payment_state"] == "paid":
        skipped.append((inv["name"], "already paid")); continue
    if inv["move_type"] != "out_invoice":
        skipped.append((inv["name"], f"move_type={inv['move_type']}")); continue

    ctx = {"active_model": "account.move", "active_ids": [inv["id"]],
           "active_id": inv["id"]}
    try:
        wiz = execute("account.payment.register", "create", [{
            "journal_id": SHOPIFY_JOURNAL_ID,
            "payment_method_line_id": SHOPIFY_PML_ID,
            "amount": inv["amount_residual"],
            "payment_date": inv["invoice_date"],
            "communication": f"Shopify Order {inv['invoice_origin'] or ''}".strip(),
        }], {"context": ctx})
        execute("account.payment.register", "action_create_payments",
                [[wiz]], {"context": ctx})
    except Exception as e:
        failed.append((inv["name"], str(e))); continue

    chk = search_read("account.move", [("id", "=", inv["id"])],
                      ["payment_state", "amount_residual"])[0]
    if chk["payment_state"] == "paid":
        paid.append((inv["name"], inv["amount_residual"]))
    else:
        failed.append((inv["name"], f"still {chk['payment_state']} "
                                    f"residual={chk['amount_residual']}"))

print("=== PAID ===")
for n, a in paid:
    print(f"  {n}  {a:.2f}€ -> paid")
print("=== SKIPPED ===")
for n, r in skipped:
    print(f"  {n}  {r}")
print("=== FAILED ===")
for n, r in failed:
    print(f"  {n}  {r}")
print(f"\nTotal: {len(paid)} paid, {len(skipped)} skipped, {len(failed)} failed")
