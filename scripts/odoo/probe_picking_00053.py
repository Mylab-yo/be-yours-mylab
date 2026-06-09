"""Probe state of MYVO/OUT/00053 to plan carton reorg for 30 starter packs."""
from scripts.odoo._client import search_read

pickings = search_read(
    "stock.picking",
    [("name", "=", "MYVO/OUT/00053")],
    ["id", "name", "state", "partner_id", "origin", "move_ids", "move_line_ids",
     "carrier_id", "shipping_weight", "weight", "scheduled_date"],
)
if not pickings:
    print("MYVO/OUT/00053 not found")
    raise SystemExit

p = pickings[0]
print(f"=== Picking {p['name']} (id={p['id']}, state={p['state']}) ===")
print(f"  partner    : {p['partner_id'][1] if p['partner_id'] else '-'}")
print(f"  origin     : {p['origin']}")
print(f"  carrier    : {p['carrier_id'][1] if p['carrier_id'] else '-'}")
print(f"  weight     : {p['weight']} kg | shipping_weight={p['shipping_weight']}")
print(f"  scheduled  : {p['scheduled_date']}")
print(f"  moves      : {len(p['move_ids'])} | move_lines={len(p['move_line_ids'])}")

# Read moves
moves = search_read(
    "stock.move",
    [("picking_id", "=", p["id"])],
    ["id", "product_id", "product_uom_qty", "quantity", "state", "weight"],
)
print(f"\n=== Moves ({len(moves)}) ===")
total_demand = 0
for mv in moves:
    prod = mv["product_id"][1] if mv["product_id"] else "?"
    total_demand += mv["product_uom_qty"]
    print(f"  mv#{mv['id']:5d} | demand={mv['product_uom_qty']:6.1f} | done={mv['quantity']:6.1f} | "
          f"state={mv['state']:10s} | {prod[:60]}")
print(f"  TOTAL demand qty = {total_demand}")

# Read move lines + their package destinations
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", p["id"])],
    ["id", "product_id", "quantity", "result_package_id", "state"],
)
print(f"\n=== Move Lines ({len(mls)}) ===")
pkg_count = {}
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    dst = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    dst_id = ml["result_package_id"][0] if ml["result_package_id"] else None
    print(f"  ml#{ml['id']:5d} | qty={ml['quantity']:6.1f} | dst={dst:25s} | {prod[:55]}")
    if dst_id:
        pkg_count[dst_id] = pkg_count.get(dst_id, 0) + 1

# List packages already created
pkg_ids = list(pkg_count.keys())
if pkg_ids:
    print(f"\n=== Packages already used ({len(pkg_ids)}) ===")
    pkgs = search_read(
        "stock.quant.package",
        [("id", "in", pkg_ids)],
        ["id", "name", "shipping_weight", "weight", "package_type_id"],
    )
    for pkg in pkgs:
        ptype = pkg["package_type_id"][1] if pkg["package_type_id"] else "-"
        print(f"  pkg#{pkg['id']} {pkg['name']!r} | type={ptype} | "
              f"weight={pkg['weight']} | shipping_weight={pkg['shipping_weight']} | "
              f"{pkg_count[pkg['id']]} lignes")
else:
    print("\n=== No packages assigned yet ===")

# Linked SO
if p["origin"]:
    so = search_read("sale.order", [("name", "=", p["origin"])],
                     ["id", "name", "partner_id", "amount_total", "state", "order_line"])
    if so:
        print(f"\n=== Linked SO {so[0]['name']} (id={so[0]['id']}, state={so[0]['state']}) ===")
        print(f"  partner   : {so[0]['partner_id'][1]}")
        print(f"  amount    : {so[0]['amount_total']} EUR")
        lines = search_read(
            "sale.order.line",
            [("order_id", "=", so[0]["id"])],
            ["id", "product_id", "product_uom_qty", "name"],
        )
        print(f"  lines ({len(lines)}):")
        for l in lines:
            prod = l["product_id"][1] if l["product_id"] else "?"
            print(f"    {l['product_uom_qty']:6.1f} x {prod[:60]}")
