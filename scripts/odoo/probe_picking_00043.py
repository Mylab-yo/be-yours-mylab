"""Probe state of MYVO/OUT/00043 to diagnose empty carton issue."""
from scripts.odoo._client import search_read, search, execute

# Find the picking
pickings = search_read(
    "stock.picking",
    [("name", "=", "MYVO/OUT/00043")],
    ["id", "name", "state", "move_ids", "move_line_ids"],
)
if not pickings:
    print("MYVO/OUT/00043 not found")
    raise SystemExit

p = pickings[0]
print(f"=== Picking {p['name']} (id={p['id']}, state={p['state']}) ===")
print(f"  move_ids: {len(p['move_ids'])}")
print(f"  move_line_ids: {len(p['move_line_ids'])}")

# Read move lines
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", p["id"])],
    ["id", "product_id", "quantity", "quantity_product_uom", "package_id",
     "result_package_id", "location_dest_id", "state"],
)
print(f"\n=== Move Lines ({len(mls)}) ===")
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    src = ml["package_id"][1] if ml["package_id"] else "-"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    dst_id = ml["result_package_id"][0] if ml["result_package_id"] else None
    print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:50]:50s} | dst={dst} (id={dst_id})")

# Read packages referenced
pkg_ids = list({ml["result_package_id"][0] for ml in mls if ml["result_package_id"]})
print(f"\n=== Packages referenced ({len(pkg_ids)}): {pkg_ids} ===")
for pkg_id in pkg_ids:
    try:
        pkgs = search_read(
            "stock.quant.package",
            [("id", "=", pkg_id)],
            ["id", "name", "quant_ids", "shipping_weight", "weight"],
        )
        if pkgs:
            pkg = pkgs[0]
            print(f"  pkg#{pkg['id']}: name={pkg['name']!r}, quants={len(pkg['quant_ids'])}, "
                  f"shipping_weight={pkg['shipping_weight']}, weight={pkg['weight']}")
        else:
            print(f"  pkg#{pkg_id}: ** NOT FOUND (orphan reference) **")
    except Exception as e:
        print(f"  pkg#{pkg_id}: error {e}")

# Read moves with their reserved availability
moves = search_read(
    "stock.move",
    [("picking_id", "=", p["id"])],
    ["id", "product_id", "product_uom_qty", "quantity", "state",
     "reserved_availability"] if False else
    ["id", "product_id", "product_uom_qty", "quantity", "state"],
)
print(f"\n=== Moves ({len(moves)}) ===")
for mv in moves:
    prod = mv["product_id"][1] if mv["product_id"] else "?"
    print(f"  mv#{mv['id']:4d} | demand={mv['product_uom_qty']:5.1f} | done={mv['quantity']:5.1f} | "
          f"state={mv['state']:10s} | {prod[:50]}")
