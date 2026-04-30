"""Create 2 test sale orders to validate the online payment flow on the portal.

Creates:
  - 1 quote at ~960 € TTC (under 1000) → expects 100% upfront
  - 1 quote at ~2400 € TTC (above 1000) → expects 50% acompte

Test partner is reused across runs (kept for cleanup later).
Outputs the portal URLs so user can open them in incognito.

Run: python step27_create_portal_test_quotes.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, write, execute

TEST_PARTNER_NAME = "TEST PORTAL — Yoann (à supprimer après test)"
TEST_EMAIL = "yoann@mylab-shop.com"

# 1. Test partner
existing = search_read("res.partner", [("name", "=", TEST_PARTNER_NAME)], ["id"])
if existing:
    partner_id = existing[0]["id"]
    print(f"Reusing test partner id={partner_id}")
else:
    partner_id = create("res.partner", {
        "name": TEST_PARTNER_NAME,
        "email": TEST_EMAIL,
        "is_company": True,
        "country_id": search_read("res.country", [("code", "=", "FR")],
                                  ["id"])[0]["id"],
    })
    print(f"Created test partner id={partner_id}")

# 2. Pick a real product with non-zero price
prods = search_read("product.product",
                    [("sale_ok", "=", True), ("type", "!=", "service"),
                     ("list_price", ">", 0)],
                    ["id", "name", "list_price"], limit=1)
if not prods:
    print("ERROR: no priced sellable product found")
    sys.exit(1)
prod = prods[0]
print(f"Using product: {prod['name']} (price {prod['list_price']})")

def make_quote(target_ht: float, label: str):
    qty = max(1, round(target_ht / max(prod["list_price"], 1)))
    order_id = create("sale.order", {
        "partner_id": partner_id,
        "order_line": [(0, 0, {
            "product_id": prod["id"],
            "product_uom_qty": qty,
            "price_unit": target_ht / qty,
            "name": f"TEST {label} — {prod['name']}",
        })],
    })
    # Move to 'sent' state directly (avoid action_quotation_sent which returns None
    # and crashes XML-RPC marshalling)
    write("sale.order", [order_id], {"state": "sent"})
    # Read final state
    o = search_read("sale.order", [("id", "=", order_id)],
                    ["name", "amount_untaxed", "amount_total",
                     "prepayment_percent", "state", "access_token"])[0]
    # Build portal URL
    portal_url = f"https://odoo.startec-paris.com/my/orders/{order_id}?access_token={o['access_token']}"
    return order_id, o, portal_url

print("\n--- Quote 1 : 800€ HT (under 1000 TTC, expects 100%) ---")
o1_id, o1, url1 = make_quote(800.0, "SOUS 1000")
print(f"  {o1['name']}: HT={o1['amount_untaxed']}, TTC={o1['amount_total']}, "
      f"prepayment={o1['prepayment_percent']*100:.0f}%, state={o1['state']}")
print(f"  PORTAL: {url1}")

print("\n--- Quote 2 : 2000€ HT (above 1000 TTC, expects 50%) ---")
o2_id, o2, url2 = make_quote(2000.0, "AU-DESSUS 1000")
print(f"  {o2['name']}: HT={o2['amount_untaxed']}, TTC={o2['amount_total']}, "
      f"prepayment={o2['prepayment_percent']*100:.0f}%, state={o2['state']}")
print(f"  PORTAL: {url2}")

print(f"\n→ Ouvre les 2 URLs en navigation privée pour tester le portail.")
print(f"→ Pour supprimer après test :")
print(f"   python -c \"from _client import unlink; unlink('sale.order', [{o1_id}, {o2_id}])\"")
