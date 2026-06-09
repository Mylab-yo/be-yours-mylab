"""Fix 00043: remove wrong 200ml assignment + force reserve the 50ml products."""
from scripts.odoo._client import execute, write, search_read, search, unlink

PICKING_ID = 59
PKG_ID = 192

# Step 1: Probe what's in stock for the 50ml products
print("=== Stock check for 50ml products ===")
for sku in ["bain-miraculeux-50-ml", "serum-finition-ultime-50-ml"]:
    prods = search_read("product.product", [("default_code", "=", sku)], ["id", "name", "qty_available", "virtual_available"])
    for p in prods:
        print(f"  {sku}: id={p['id']} qty_available={p['qty_available']} virtual={p['virtual_available']}")

# Step 2: Remove wrong package assignment on shampoing-volume-200ml move_lines
print("\n=== Step 2: Strip wrong dst package from ml#372, #373 (200ml) ===")
write("stock.move.line", [372, 373], {"result_package_id": False})
print("  -> Cleared")

# Step 3: Unreserve everything, then re-assign cleanly
print("\n=== Step 3: do_unreserve + action_assign ===")
execute("stock.picking", "do_unreserve", [[PICKING_ID]])
execute("stock.picking", "action_assign", [[PICKING_ID]])

# Step 4: Inspect new state
print("\n=== Move lines after re-assign ===")
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:60]} | dst={dst}")

# Step 5: Force reserve for the 50ml products if not done
print("\n=== Step 5: Force quantity on bain miraculeux + serum finition 50ml moves ===")
moves = search_read(
    "stock.move",
    [("picking_id", "=", PICKING_ID), ("product_id.default_code", "in",
      ["bain-miraculeux-50-ml", "serum-finition-ultime-50-ml"])],
    ["id", "product_id", "product_uom_qty", "quantity", "state", "location_id", "location_dest_id"],
)
for mv in moves:
    print(f"  mv#{mv['id']} | {mv['product_id'][1][:50]} | demand={mv['product_uom_qty']} done={mv['quantity']} state={mv['state']}")
    # If no move_line exists with quantity, create one and assign to pkg#192
    existing_mls = search_read(
        "stock.move.line",
        [("move_id", "=", mv["id"])],
        ["id", "quantity", "result_package_id"],
    )
    print(f"    existing move_lines: {len(existing_mls)}")
    for eml in existing_mls:
        print(f"      ml#{eml['id']} qty={eml['quantity']} dst={eml['result_package_id']}")

print("\n=== Done. Manual step may be needed via UI: 'Vérifier la disponibilité' then assign carton ===")
