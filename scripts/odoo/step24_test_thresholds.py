"""Test the acompte threshold rule by creating 2 dummy quotes (idempotent cleanup).

Creates a test partner + 2 sale.order:
  - 500 € → expects prepayment_percent = 1.0
  - 2000 € → expects prepayment_percent = 0.5

Then deletes them to leave no trace.

Run after step04 has fired.
Run: python step05_test_thresholds.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, write, execute, unlink

TEST_PARTNER_NAME = "TEST — Acompte threshold (à supprimer)"

# 1. Find or create test partner
existing_partners = search_read("res.partner", [("name", "=", TEST_PARTNER_NAME)],
                                 ["id"])
if existing_partners:
    partner_id = existing_partners[0]["id"]
    print(f"Reusing test partner id={partner_id}")
else:
    partner_id = create("res.partner", {
        "name": TEST_PARTNER_NAME,
        "is_company": True,
    })
    print(f"Created test partner id={partner_id}")

# 2. Find a generic product to put on the order
prods = search_read("product.product",
                    [("sale_ok", "=", True), ("type", "!=", "service")],
                    ["id", "name", "list_price"], limit=1)
if not prods:
    print("ERROR: no sellable product found")
    sys.exit(1)
prod = prods[0]
print(f"Using product: {prod['name']} (id={prod['id']}, price={prod['list_price']})")

created_order_ids = []

def make_order(target_amount: float, label: str) -> int:
    """Create a draft sale.order with one line totaling ~target_amount."""
    qty = max(1, round(target_amount / max(prod["list_price"], 1)))
    order_id = create("sale.order", {
        "partner_id": partner_id,
        "order_line": [(0, 0, {
            "product_id": prod["id"],
            "product_uom_qty": qty,
            "price_unit": target_amount / qty,  # force exact total
        })],
    })
    created_order_ids.append(order_id)
    return order_id

print("\n[Test 1] Creating 500€ order (expects prepayment_percent=1.0)...")
o1 = make_order(500.0, "small")
o1_data = search_read("sale.order", [("id", "=", o1)],
                      ["amount_total", "prepayment_percent"])[0]
print(f"  amount_total={o1_data['amount_total']}, "
      f"prepayment_percent={o1_data['prepayment_percent']}")
ok1 = o1_data["prepayment_percent"] == 1.0

print("\n[Test 2] Creating 2000€ order (expects prepayment_percent=0.5)...")
o2 = make_order(2000.0, "big")
o2_data = search_read("sale.order", [("id", "=", o2)],
                      ["amount_total", "prepayment_percent"])[0]
print(f"  amount_total={o2_data['amount_total']}, "
      f"prepayment_percent={o2_data['prepayment_percent']}")
ok2 = o2_data["prepayment_percent"] == 0.5

# 3. Cleanup
print(f"\n[Cleanup] Deleting test orders {created_order_ids}...")
unlink("sale.order", created_order_ids)
print(f"[Cleanup] Deleting test partner {partner_id}...")
unlink("res.partner", [partner_id])

print()
if ok1 and ok2:
    print("✓ ALL TESTS PASS — threshold rule works correctly")
else:
    print(f"✗ TESTS FAILED — small={'OK' if ok1 else 'KO'}, big={'OK' if ok2 else 'KO'}")
    print("  Check the automation rule from step04, may need debugging.")
    sys.exit(1)
