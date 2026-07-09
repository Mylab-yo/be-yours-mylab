"""Verify the contents of Pack Demarrage Holicare 1/30 and 30/30."""
from scripts.odoo._client import search_read

for pkg_n in [1, 15, 30]:
    pkg = search_read(
        "stock.quant.package",
        [("name", "like", f"Pack D"), ("name", "like", f" {pkg_n}/30")],
        ["id", "name"],
    )
    if not pkg:
        print(f"Pack #{pkg_n}/30 NOT FOUND")
        continue
    pkg = pkg[0]
    mls = search_read(
        "stock.move.line",
        [("result_package_id", "=", pkg["id"])],
        ["id", "product_id", "quantity"],
    )
    total_items = sum(ml["quantity"] for ml in mls)
    print(f"\n=== pkg#{pkg['id']} {pkg['name']!r} ({len(mls)} mls, {total_items:.0f} unites) ===")
    for ml in sorted(mls, key=lambda x: x["product_id"][1]):
        prod = ml["product_id"][1] if ml["product_id"] else "?"
        print(f"  qty={ml['quantity']:5.1f} | {prod}")

# Verify 1 loose package too
print("\n=== Loose 9/25 (1st loose for mn-400 mask) ===")
pkg = search_read("stock.quant.package", [("name", "=", "Loose 9/25 - masque nourrissant 400 ml (24 ex.)")],
                  ["id", "name"])[0]
mls = search_read("stock.move.line", [("result_package_id", "=", pkg["id"])],
                  ["id", "product_id", "quantity"])
print(f"pkg#{pkg['id']} {pkg['name']!r}")
for ml in mls:
    prod = ml["product_id"][1] if ml["product_id"] else "?"
    print(f"  qty={ml['quantity']:5.1f} | {prod}")

# Totals: count packages, total mls
all_pkgs = search_read("stock.quant.package",
                       ["|", ("name", "like", "Pack D"), ("name", "like", "Loose %/25")],
                       ["id", "name"])
print(f"\nTotal packages: {len(all_pkgs)} (expected 55 = 30 packs + 25 loose)")

all_mls = search_read("stock.move.line", [("picking_id", "=", 69)],
                     ["id", "quantity", "result_package_id"])
unassigned = [ml for ml in all_mls if not ml["result_package_id"]]
print(f"Total move_lines: {len(all_mls)} | unassigned (no package): {len(unassigned)}")
print(f"Total qty across all mls: {sum(ml['quantity'] for ml in all_mls):.0f}")
