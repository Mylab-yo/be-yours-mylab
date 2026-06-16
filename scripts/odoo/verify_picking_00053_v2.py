"""Verify the v2 reorg of MYVO/OUT/00053."""
from scripts.odoo._client import search_read

# Check a sample pack carton content
print("=== Pack Demarrage Holicare 1/30 content ===")
pkg = search_read("stock.quant.package",
                  [("name", "=", "Pack Demarrage Holicare 1/30")],
                  ["id", "name"])
if pkg:
    pkg = pkg[0]
    mls = search_read("stock.move.line", [("result_package_id", "=", pkg["id"])],
                      ["product_id", "quantity"])
    total = sum(ml["quantity"] for ml in mls)
    print(f"pkg#{pkg['id']} : {len(mls)} mls, {total:.0f} unites totales")
    for ml in sorted(mls, key=lambda x: x["product_id"][1]):
        print(f"  qty={ml['quantity']:5.1f} | {ml['product_id'][1]}")

# Check the mixed carton
print("\n=== MIXED carton content ===")
pkg = search_read("stock.quant.package",
                  [("name", "like", "MIXE")],
                  ["id", "name"])
if pkg:
    pkg = pkg[0]
    print(f"pkg#{pkg['id']} {pkg['name']!r}")
    mls = search_read("stock.move.line", [("result_package_id", "=", pkg["id"])],
                      ["product_id", "quantity"])
    for ml in sorted(mls, key=lambda x: x["product_id"][1]):
        print(f"  qty={ml['quantity']:5.1f} | {ml['product_id'][1]}")

# Final overview
print("\n=== Total package count ===")
pkgs = search_read("stock.quant.package",
                   ["|", ("name", "like", "Pack Demarrage Holicare"),
                    ("name", "like", "Loose %/31")],
                   ["id", "name"])
print(f"Total packages : {len(pkgs)} (expected 61)")

mls = search_read("stock.move.line", [("picking_id", "=", 69)], ["id", "quantity"])
no_pkg = search_read("stock.move.line",
                     [("picking_id", "=", 69), ("result_package_id", "=", False)],
                     ["id"])
print(f"Total move_lines : {len(mls)} | sans package : {len(no_pkg)}")

# Picking state
picking = search_read("stock.picking", [("id", "=", 69)], ["name", "state"])[0]
print(f"Picking {picking['name']} state={picking['state']}")
