"""Restore MYVO/OUT/00043 from cancelled state back to assigned with Carton 1/1."""
from scripts.odoo._client import execute, write, search_read, search, create

PICKING_ID = 59

print("=== Step 1: Reset moves and picking to draft ===")
move_ids = search("stock.move", [("picking_id", "=", PICKING_ID)])
print(f"  Found {len(move_ids)} moves")

# Force state back to draft on all moves (bypass cancel guard)
write("stock.move", move_ids, {"state": "draft"})
write("stock.picking", [PICKING_ID], {"state": "draft"})
print("  -> All set to draft")

print("\n=== Step 2: Confirm the picking (creates new move_lines) ===")
execute("stock.picking", "action_confirm", [[PICKING_ID]])

print("\n=== Step 3: Assign (reserve stock) ===")
execute("stock.picking", "action_assign", [[PICKING_ID]])

print("\n=== Step 4: Verify state after restore ===")
p = search_read("stock.picking", [("id", "=", PICKING_ID)], ["name", "state"])[0]
print(f"  Picking {p['name']} state = {p['state']}")

moves = search_read(
    "stock.move",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "product_uom_qty", "quantity", "state"],
)
for mv in moves:
    print(f"  mv#{mv['id']:4d} | demand={mv['product_uom_qty']:5.1f} | done={mv['quantity']:5.1f} | "
          f"state={mv['state']:10s} | {mv['product_id'][1][:60]}")

mls = search_read(
    "stock.move.line",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)
print(f"\n  Move lines: {len(mls)}")
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:60]} | dst={dst}")

print("\n=== Step 5: Re-allocate the 2 ready move_lines to Carton 1/1 (pkg#192) ===")
# Find the 2 reserved move lines (bain miraculeux + serum finition)
ready_mls = [ml for ml in mls if ml["quantity"] > 0]
if ready_mls:
    # Check if pkg#192 still exists
    pkg = search_read("stock.quant.package", [("id", "=", 192)], ["id", "name"])
    if pkg:
        print(f"  pkg#192 still exists: {pkg[0]['name']}")
        ml_ids = [ml["id"] for ml in ready_mls]
        write("stock.move.line", ml_ids, {"result_package_id": 192})
        print(f"  -> Assigned {len(ml_ids)} move_lines to pkg#192")
    else:
        print("  pkg#192 deleted, creating new package...")
        new_pkg_id = create("stock.quant.package", {"name": "Carton 1/1 - 50ml Sérums/Huiles"})
        ml_ids = [ml["id"] for ml in ready_mls]
        write("stock.move.line", ml_ids, {"result_package_id": new_pkg_id})
        print(f"  -> Created pkg#{new_pkg_id} and assigned {len(ml_ids)} move_lines")
else:
    print("  WARNING: No ready move_lines (quantity > 0) — assign may have failed")

print("\n=== Final state ===")
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", PICKING_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:60]} | dst={dst}")
