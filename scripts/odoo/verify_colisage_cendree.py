# -*- coding: utf-8 -*-
"""Verif ciblee : colis du MASQUE NOURRISSANT 200ml (code exact) sur les 2 pickings Cendree."""
from collections import defaultdict
import _client as odoo

CODE = "masque-nourrissant-200-ml"
pp = odoo.search_read("product.product", [("default_code", "=", CODE)], ["id", "name"])[0]
PID = pp["id"]
print(f"Produit cible : [{PID}] {pp['name']}\n")

for name in ["MYVO/OUT/00171", "MYVO/OUT/00186"]:
    pk = odoo.search_read("stock.picking", [("name", "=", name)], ["id", "state"])[0]
    mls = odoo.search_read(
        "stock.move.line",
        [("picking_id", "=", pk["id"]), ("product_id", "=", PID)],
        ["quantity", "result_package_id"])
    by_pkg = defaultdict(float)
    for ml in mls:
        pkg = ml["result_package_id"][1] if ml.get("result_package_id") else "(hors colis)"
        by_pkg[pkg] += ml["quantity"]
    sizes = sorted((int(round(q)) for q in by_pkg.values()), reverse=True)
    full36 = sum(1 for s in sizes if s == 36)
    partiels = [s for s in sizes if s != 36]
    total = sum(sizes)
    print(f"{name} (state={pk['state']}) : {len(by_pkg)} colis masque nourrissant | "
          f"total={total}u")
    print(f"   {full36} colis pleins de 36" + (f" + partiels {partiels}" if partiels else "")
          + f"  (verif: {full36}*36{'+'+'+'.join(map(str,partiels)) if partiels else ''} = {total})")
