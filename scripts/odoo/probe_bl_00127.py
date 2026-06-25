"""Inspect MYVO/OUT/00127 : moves, move lines, current packages."""
from scripts.odoo._client import execute, search_read

pk = search_read("stock.picking", [("name", "=", "MYVO/OUT/00127")],
                 ["id", "name", "state", "partner_id", "origin", "company_id", "scheduled_date"])
if not pk:
    print("NOT FOUND")
    raise SystemExit
pk = pk[0]
PID = pk["id"]
print(f"#{PID} {pk['name']} | {pk['state']} | {pk['partner_id']} | origin={pk['origin']} | company={pk['company_id']}")

print("\n=== MOVES ===")
moves = search_read("stock.move", [("picking_id", "=", PID)],
                    ["id", "product_id", "product_uom_qty", "quantity", "product_uom",
                     "location_id", "location_dest_id", "state"])
for m in moves:
    code = search_read("product.product", [("id", "=", m["product_id"][0])], ["default_code"])
    dc = code[0]["default_code"] if code else "?"
    print(f"  mv#{m['id']} | [{dc}] {m['product_id'][1]} | dmd={m['product_uom_qty']:.0f} done={m['quantity']:.0f} | uom={m['product_uom']} | {m['location_id'][1]}->{m['location_dest_id'][1]} | {m['state']}")

print("\n=== MOVE LINES ===")
mls = search_read("stock.move.line", [("picking_id", "=", PID)],
                  ["id", "move_id", "product_id", "quantity", "result_package_id", "lot_id", "location_id", "location_dest_id"])
for ml in mls:
    pkg = ml["result_package_id"][1] if ml["result_package_id"] else "-"
    lot = ml["lot_id"][1] if ml["lot_id"] else "-"
    print(f"  ml#{ml['id']} | mv#{ml['move_id'][0]} | {ml['product_id'][1]} | qty={ml['quantity']:.0f} | pkg={pkg} | lot={lot}")

print("\n=== PACKAGES referenced ===")
pkg_ids = sorted({ml["result_package_id"][0] for ml in mls if ml["result_package_id"]})
if pkg_ids:
    pkgs = search_read("stock.quant.package", [("id", "in", pkg_ids)], ["id", "name"])
    for p in pkgs:
        print(f"  pkg#{p['id']} | {p['name']}")
else:
    print("  (none)")
