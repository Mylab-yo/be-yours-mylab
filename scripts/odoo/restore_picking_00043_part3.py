"""Final restore for 00043: ship 50ml only in Carton 1/1, the rest in backorder."""
from scripts.odoo._client import execute, write, search_read, search, unlink, create

PICKING_ID = 59
PKG_ID = 192

# Step 1: Delete the wrong 200ml move_lines (ml#372 and 373 were the 200ml volume)
print("=== Step 1: Delete 200ml move_lines that got reserved by mistake ===")
mls_to_delete = search_read(
    "stock.move.line",
    [("picking_id", "=", PICKING_ID),
     ("product_id.default_code", "=", "shampoing-volume-200-ml")],
    ["id", "quantity"],
)
print(f"  Found {len(mls_to_delete)} 200ml move_lines to delete: {[ml['id'] for ml in mls_to_delete]}")
if mls_to_delete:
    unlink("stock.move.line", [ml["id"] for ml in mls_to_delete])
    print("  -> Deleted")

# Step 2: Get the 2 50ml moves to create move_lines for
print("\n=== Step 2: Get bain miraculeux + serum finition moves ===")
moves_50ml = search_read(
    "stock.move",
    [("picking_id", "=", PICKING_ID),
     ("product_id.default_code", "in",
      ["bain-miraculeux-50-ml", "serum-finition-ultime-50-ml"])],
    ["id", "product_id", "product_uom_qty", "product_uom", "location_id", "location_dest_id"],
)
for mv in moves_50ml:
    print(f"  mv#{mv['id']} | {mv['product_id'][1][:60]} | qty={mv['product_uom_qty']}")

# Step 3: Check if move_lines already exist (idempotent)
print("\n=== Step 3: Check + create move_lines with pkg#192 ===")
for mv in moves_50ml:
    existing = search_read(
        "stock.move.line",
        [("move_id", "=", mv["id"])],
        ["id", "quantity", "result_package_id"],
    )
    if existing:
        print(f"  mv#{mv['id']}: ml already exists ({len(existing)})")
        for eml in existing:
            print(f"    ml#{eml['id']} qty={eml['quantity']}")
            # Force the quantity + carton
            write("stock.move.line", [eml["id"]], {
                "quantity": mv["product_uom_qty"],
                "result_package_id": PKG_ID,
            })
            print(f"    -> updated to qty={mv['product_uom_qty']} dst=pkg#{PKG_ID}")
    else:
        new_ml = create("stock.move.line", {
            "move_id": mv["id"],
            "product_id": mv["product_id"][0],
            "product_uom_id": mv["product_uom"][0],
            "quantity": mv["product_uom_qty"],
            "location_id": mv["location_id"][0],
            "location_dest_id": mv["location_dest_id"][0],
            "result_package_id": PKG_ID,
            "picking_id": PICKING_ID,
        })
        print(f"  mv#{mv['id']}: created ml#{new_ml} qty={mv['product_uom_qty']} dst=pkg#{PKG_ID}")

# Step 4: Verify final state
print("\n=== Final move_lines on picking ===")
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:60]} | dst={dst}")

# Step 5: Verify moves state
print("\n=== Moves state ===")
moves = search_read(
    "stock.move",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "product_uom_qty", "quantity", "state"],
)
for mv in moves:
    print(f"  mv#{mv['id']:4d} | demand={mv['product_uom_qty']:5.1f} | done={mv['quantity']:5.1f} | "
          f"state={mv['state']:10s} | {mv['product_id'][1][:50]}")

# Step 6: Picking state
p = search_read("stock.picking", [("id", "=", PICKING_ID)], ["state"])[0]
print(f"\nPicking state: {p['state']}")
