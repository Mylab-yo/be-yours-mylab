"""Sweep ALL not_paid Shopify-origin invoices (not just overdue) left by the
Register Payment bug (06-06 -> 06-11). Classify card vs virement via Shopify,
settle the CARD ones on journal SHOP (id 26). Virement -> reported, not touched.
Dry-run by default; pass --apply to settle.
"""
import os, sys, io, json, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read, execute  # also loads .env.local

APPLY = "--apply" in sys.argv
SHOP_JOURNAL, SHOP_PML = 26, 17
SHOP_TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"]  # from .env.local
STORE, API = "mylab-shop-3.myshopify.com", "2024-10"

# All posted, not_paid customer invoices from Shopify (origin S00% + numeric ref)
invs = search_read("account.move",
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
     ("payment_state", "in", ["not_paid", "partial"]),
     ("invoice_origin", "like", "S00%")],
    ["id", "name", "partner_id", "amount_residual", "invoice_date",
     "invoice_origin", "ref"])
# Shopify ones have a numeric ref (the order id)
shop = [i for i in invs if (i.get("ref") or "").isdigit()]
print(f"Not-paid Shopify-origin invoices: {len(shop)}\n")

def shopify_order(oid):
    url = (f"https://{STORE}/admin/api/{API}/orders/{oid}.json"
           "?fields=name,financial_status,gateway,payment_gateway_names,total_outstanding")
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": SHOP_TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["order"]

card, transfer, other = [], [], []
for i in sorted(shop, key=lambda x: x["name"]):
    try:
        o = shopify_order(i["ref"])
    except Exception as e:
        other.append((i, f"shopify err {e}")); continue
    gw = ",".join(o.get("payment_gateway_names") or []) or (o.get("gateway") or "")
    fs = o.get("financial_status")
    is_transfer = any(k in gw.lower() for k in ["virement", "bank", "transfer", "wire"])
    tag = f"{i['name']} {i['partner_id'][1][:24]:24} {i['amount_residual']:>8.2f}EUR  gw={gw:<18} fs={fs}"
    if is_transfer:
        transfer.append((i, tag))
    elif fs == "paid":
        card.append((i, tag))
    else:
        other.append((i, tag))

print("--- CARD (paid on Shopify) -> settle ---")
for _, t in card: print("  " + t)
print("--- VIREMENT -> NOT touched (verify bank) ---")
for _, t in transfer: print("  " + t)
print("--- OTHER -> review ---")
for _, t in other: print("  " + t)

if APPLY and card:
    print("\n=== SETTLING CARD INVOICES ===")
    for i, _ in card:
        ctx = {"active_model": "account.move", "active_ids": [i["id"]], "active_id": i["id"]}
        try:
            wiz = execute("account.payment.register", "create", [{
                "journal_id": SHOP_JOURNAL, "payment_method_line_id": SHOP_PML,
                "amount": i["amount_residual"], "payment_date": i["invoice_date"],
                "communication": f"Shopify Order {i['invoice_origin']}".strip(),
            }], {"context": ctx})
            execute("account.payment.register", "action_create_payments", [[wiz]], {"context": ctx})
            chk = search_read("account.move", [("id", "=", i["id"])], ["payment_state"])[0]
            print(f"  {i['name']} -> {chk['payment_state']}")
        except Exception as e:
            print(f"  {i['name']} FAILED: {e}")
elif card:
    print("\n(dry-run — re-run with --apply to settle the CARD invoices)")
