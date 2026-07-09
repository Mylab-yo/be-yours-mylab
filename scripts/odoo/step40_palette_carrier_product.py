"""Create a dedicated 'Envoi palette Europe' product and link it to carrier id=19.

Avoids touching product #2413 'Frais de livraison DPD' which is shared by the 8 DPD carriers.
"""
from scripts.odoo._client import execute, search_read, search, create, write

PALETTE_CARRIER_ID = 19
NEW_PRODUCT_NAME = "Envoi palette Europe"
FIXED_PRICE = 250.0  # matches carrier.fixed_price

# Step 1: Look up sale tax 20% G (per project memory: id 103)
TAX_ID = 103
tax = search_read("account.tax", [("id", "=", TAX_ID)], ["id", "name", "amount", "type_tax_use"])
if tax:
    print(f"Sale tax id={TAX_ID}: {tax[0]['name']} ({tax[0]['amount']}%, {tax[0]['type_tax_use']})")
else:
    print(f"WARN: tax id={TAX_ID} not found, product will be tax-less")

# Step 2: Check if product already exists (idempotent)
existing = search("product.product", [("name", "=", NEW_PRODUCT_NAME)])
if existing:
    new_pid = existing[0]
    print(f"\nProduct '{NEW_PRODUCT_NAME}' already exists: id={new_pid}")
else:
    # Look up the original product to clone categ_id, etc.
    orig = search_read("product.product", [("id", "=", 2413)],
                       ["categ_id", "uom_id", "uom_po_id", "type"])[0]
    print(f"\nOriginal product 2413: categ={orig['categ_id']}, uom={orig['uom_id']}, type={orig['type']}")

    new_pid = create("product.product", {
        "name": NEW_PRODUCT_NAME,
        "type": "service",
        "list_price": FIXED_PRICE,
        "sale_ok": True,
        "purchase_ok": False,
        "categ_id": orig["categ_id"][0],
        "uom_id": orig["uom_id"][0],
        "uom_po_id": orig["uom_po_id"][0],
        "taxes_id": [(6, 0, [TAX_ID])] if tax else [(5, 0, 0)],
    })
    print(f"Created product id={new_pid}: {NEW_PRODUCT_NAME!r}")

# Step 3: Link the carrier to the new product
print("\n=== Link carrier id=19 -> new product ===")
write("delivery.carrier", [PALETTE_CARRIER_ID], {"product_id": new_pid})

# Verify
verify = search_read("delivery.carrier", [("id", "=", PALETTE_CARRIER_ID)],
                     ["id", "name", "product_id"])[0]
print(f"  carrier id={verify['id']} | {verify['name']!r} -> product {verify['product_id']}")

# Step 4: Make sure DPD carriers still use product 2413
print("\n=== Verify DPD carriers unchanged ===")
dpd = search_read("delivery.carrier", [("id", "in", [11, 12, 13, 14, 15, 16, 17, 18])],
                  ["id", "name", "product_id"])
for c in dpd:
    pid = c["product_id"][0] if c["product_id"] else None
    flag = "OK" if pid == 2413 else "WARN"
    print(f"  [{flag}] id={c['id']} | {c['name'][:50]} -> product_id={pid}")

# Step 5: Check existing SO that have delivery lines using product 2413 with carrier=19
# (devis already-saved palette devis that need their delivery line product swapped)
print("\n=== Existing SOs with carrier=19 + delivery line of product 2413 ===")
sos = search_read("sale.order",
                  [("carrier_id", "=", PALETTE_CARRIER_ID),
                   ("state", "in", ["draft", "sent", "sale"])],
                  ["id", "name", "state", "order_line"])
print(f"  Found {len(sos)} SOs with carrier=19")
for so in sos:
    lines = search_read("sale.order.line",
                        [("order_id", "=", so["id"]),
                         ("is_delivery", "=", True),
                         ("product_id", "=", 2413)],
                        ["id", "name", "price_unit"])
    if not lines:
        continue
    line_ids = [l["id"] for l in lines]
    print(f"  {so['name']} (state={so['state']}): delivery lines using prod 2413: {line_ids}")

    if so["state"] != "draft":
        # Confirmed/sent: only update the display name (product change is forbidden)
        try:
            write("sale.order.line", line_ids, {"name": NEW_PRODUCT_NAME})
            print(f"    -> [confirmed] renamed line label only (product kept = 2413)")
        except Exception as e:
            print(f"    -> [confirmed] could not update label: {e}")
        continue

    try:
        write("sale.order.line", line_ids, {
            "product_id": new_pid,
            "name": NEW_PRODUCT_NAME,
        })
        print(f"    -> [draft] swapped to product {new_pid} / name='{NEW_PRODUCT_NAME}'")
    except Exception as e:
        print(f"    -> ERROR: {e}")

print("\nDone.")
