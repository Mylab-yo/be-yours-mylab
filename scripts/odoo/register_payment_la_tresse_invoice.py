"""Post invoice 652 + register payment 2347.33€ + reconcile partially.
The 77.98€ excess stays as outstanding customer credit (future use)."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, create

INVOICE_ID = 652
PARTNER_ID = 1074
AMOUNT_PAID = 2347.33
PAYMENT_DATE = "2026-04-11"
MEMO = "VIR INST LA TRESSE PARISIENNE - IPR000278634374 - My lab devis 300582"

# Step 0: Probe journals
print("=== Probe bank journals ===")
journals = search_read("account.journal",
                       [("type", "=", "bank"), ("company_id", "=", 3)],
                       ["id", "name", "code", "bank_account_id", "default_account_id"],
                       limit=10)
for j in journals:
    print(f"  id={j['id']:3} | code={j['code']:6} | name={j['name']!r}")

# Pick LCL
lcl_journal = next((j for j in journals if "lcl" in (j["name"] or "").lower() or "lcl" in (j["code"] or "").lower()), None)
if not lcl_journal:
    print("⚠️ No LCL journal found, using first bank journal")
    lcl_journal = journals[0]
JOURNAL_ID = lcl_journal["id"]
print(f"  → Using journal id={JOURNAL_ID} ({lcl_journal['name']!r})")

# Step 1: Check current invoice state
print("\n=== Step 1: Post invoice ===")
inv = search_read("account.move", [("id", "=", INVOICE_ID)],
                  ["name", "state", "amount_total", "amount_residual"], limit=1)
print(f"  Before: state={inv[0]['state']} name={inv[0]['name']} total={inv[0]['amount_total']}")
if inv[0]["state"] == "draft":
    execute("account.move", "action_post", [INVOICE_ID])
    inv = search_read("account.move", [("id", "=", INVOICE_ID)],
                      ["name", "state", "amount_total", "amount_residual"], limit=1)
    print(f"  After:  state={inv[0]['state']} name={inv[0]['name']} total={inv[0]['amount_total']} residual={inv[0]['amount_residual']}")
else:
    print(f"  Already posted, skip")

# Step 2: Create payment
print("\n=== Step 2: Create + post payment ===")
payment_id = create("account.payment", {
    "payment_type": "inbound",
    "partner_type": "customer",
    "partner_id": PARTNER_ID,
    "amount": AMOUNT_PAID,
    "date": PAYMENT_DATE,
    "journal_id": JOURNAL_ID,
    "memo": MEMO,
})
print(f"  Created payment id={payment_id}")
execute("account.payment", "action_post", [payment_id])
pay = search_read("account.payment", [("id", "=", payment_id)],
                  ["name", "state", "amount", "move_id"], limit=1)
print(f"  Posted: {pay[0]}")

# Step 3: Reconcile invoice receivable line with payment receivable line
print("\n=== Step 3: Reconcile ===")
payment_move_id = pay[0]["move_id"][0]

# Find receivable lines on both moves
inv_recv = search_read("account.move.line",
                       [("move_id", "=", INVOICE_ID),
                        ("account_id.account_type", "=", "asset_receivable")],
                       ["id", "debit", "credit", "amount_residual", "name", "reconciled"], limit=5)
pay_recv = search_read("account.move.line",
                       [("move_id", "=", payment_move_id),
                        ("account_id.account_type", "=", "asset_receivable")],
                       ["id", "debit", "credit", "amount_residual", "name", "reconciled"], limit=5)

print(f"  Invoice receivable line: {inv_recv}")
print(f"  Payment receivable line: {pay_recv}")

if inv_recv and pay_recv:
    line_ids = [inv_recv[0]["id"], pay_recv[0]["id"]]
    print(f"  Reconciling lines {line_ids}...")
    execute("account.move.line", "reconcile", [line_ids])
    print("  ✓ Reconciled")

# Step 4: Verify
print("\n=== Step 4: Final state ===")
inv_after = search_read("account.move", [("id", "=", INVOICE_ID)],
                        ["name", "state", "amount_total", "amount_residual", "payment_state"], limit=1)
print(f"  Invoice: {inv_after[0]}")

pay_after = search_read("account.payment", [("id", "=", payment_id)],
                        ["name", "state", "amount"], limit=1)
print(f"  Payment: {pay_after[0]}")

# Check remaining outstanding on payment move line
pay_recv_after = search_read("account.move.line",
                              [("move_id", "=", payment_move_id),
                               ("account_id.account_type", "=", "asset_receivable")],
                              ["id", "amount_residual", "reconciled"], limit=5)
print(f"  Payment receivable residual: {pay_recv_after}")

# Check partner credit
print(f"\n  Partner {PARTNER_ID} unmatched credit can be used on next invoice.")
print(f"  Invoice URL: https://odoo.startec-paris.com/odoo/action-account.action_move_out_invoice_type/{INVOICE_ID}")
print(f"  Payment URL: https://odoo.startec-paris.com/odoo/action-account.action_account_payments/{payment_id}")
