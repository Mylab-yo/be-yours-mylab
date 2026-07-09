"""Correct billing address on Maison Osmoz order S00558 + invoice FAC/2026/00093.

Customer asked (email 2026-06-12) to bill to a DIFFERENT address than shipping:
  Maison Osmoz Akbulut, Avenue d'Echallens 4a, 1004 Lausanne (Switzerland)
Shipping stays Romont. Invoice is posted+paid -> reset to draft, swap billing
partner, repost, re-reconcile the Shopify payment, drop the cached PDF.

Idempotent-ish: re-running will reuse the billing contact if already created.
"""
from _client import search_read, execute, create, write

COMPANY_ID = 2138          # Maison Osmoz (commercial entity / shipping)
SO_ID = 525                # S00558
INV_ID = 456               # FAC/2026/00093
PAYMENT_LINE_ID = 1628     # PSHOP/2026/00041 receivable counterpart line
RECV_ACCOUNT_ID = 887      # 411100 Customers
SWITZERLAND = 43

BILLING_VALS = {
    "name": "Maison Osmoz Akbulut",
    "parent_id": COMPANY_ID,
    "type": "invoice",
    "street": "Avenue d'Echallens 4a",
    "zip": "1004",
    "city": "Lausanne",
    "country_id": SWITZERLAND,
}

# --- 1. Billing contact (reuse if exists) -----------------------------------
existing = search_read(
    "res.partner",
    [("parent_id", "=", COMPANY_ID), ("type", "=", "invoice"),
     ("name", "=", "Maison Osmoz Akbulut")],
    ["id"],
)
if existing:
    billing_id = existing[0]["id"]
    print(f"[1] Reusing existing billing contact id={billing_id}")
else:
    billing_id = create("res.partner", BILLING_VALS)
    print(f"[1] Created billing contact id={billing_id}")

# --- 2. Sale order S00558: set invoice address (keep shipping) --------------
write("sale.order", [SO_ID], {"partner_invoice_id": billing_id})
so = search_read("sale.order", [("id", "=", SO_ID)],
                 ["partner_invoice_id", "partner_shipping_id"])[0]
print(f"[2] SO partner_invoice_id={so['partner_invoice_id']} "
      f"shipping={so['partner_shipping_id']}")

# --- 3. Reset invoice to draft (breaks reconciliation) ----------------------
inv = search_read("account.move", [("id", "=", INV_ID)], ["state"])[0]
if inv["state"] == "posted":
    execute("account.move", "button_draft", [[INV_ID]])
    print("[3] Invoice reset to draft")
else:
    print(f"[3] Invoice already in state={inv['state']}")

# --- 4. Swap billing partner (keep shipping = company / Romont) -------------
write("account.move", [INV_ID],
      {"partner_id": billing_id, "partner_shipping_id": COMPANY_ID})
inv = search_read("account.move", [("id", "=", INV_ID)],
                  ["partner_id", "partner_shipping_id", "commercial_partner_id"])[0]
print(f"[4] Invoice partner_id={inv['partner_id']} "
      f"shipping={inv['partner_shipping_id']} "
      f"commercial={inv['commercial_partner_id']}")

# --- 5. Repost --------------------------------------------------------------
execute("account.move", "action_post", [[INV_ID]])
print("[5] Invoice reposted")

# --- 6. Re-reconcile the Shopify payment ------------------------------------
recv_line = search_read(
    "account.move.line",
    [("move_id", "=", INV_ID), ("account_id", "=", RECV_ACCOUNT_ID)],
    ["id", "reconciled", "amount_residual"],
)[0]
print(f"[6] New receivable line id={recv_line['id']} "
      f"reconciled={recv_line['reconciled']}")
if not recv_line["reconciled"]:
    execute("account.move.line", "reconcile", [[recv_line["id"], PAYMENT_LINE_ID]])
    print("    -> reconciled with payment line 1628")

# --- 7. Drop cached PDF so it re-renders with the new address ---------------
att_ids = execute("ir.attachment", "search",
                  [[("res_model", "=", "account.move"), ("res_id", "=", INV_ID)]])
if att_ids:
    names = execute("ir.attachment", "read", [att_ids], {"fields": ["name"]})
    execute("ir.attachment", "unlink", [att_ids])
    print(f"[7] Unlinked cached attachments: {[n['name'] for n in names]}")
else:
    print("[7] No cached attachment to unlink")

# --- 8. Verify final state --------------------------------------------------
final = search_read("account.move", [("id", "=", INV_ID)],
                    ["name", "state", "payment_state", "partner_id",
                     "partner_shipping_id", "amount_residual"])[0]
print("\n=== FINAL ===")
for k, v in final.items():
    print(f"  {k}: {v}")
bill = search_read("res.partner", [("id", "=", billing_id)],
                   ["name", "street", "zip", "city", "country_id"])[0]
print("  billing address:", bill)
