"""Probe LECTURE SEULE : les 4 vrac sont-ils vendables ? suivis par lot ? stock actuel ?

Determine la bonne facon de "mettre en stock pour que les clients commandent".
"""
import _client as odoo

BULK = {
    2519: "Bulk shampoing purifiant (200kg)",
    2514: "Bulk shampoing nourrissant (300kg)",
    2521: "Bulk shampoing gel douche (120kg)",
    2545: "Bulk shampoing dejaunisseur platine (150kg)",
}

fields = ["name", "default_code", "sale_ok", "purchase_ok", "tracking",
          "type", "qty_available", "virtual_available", "uom_id", "route_ids"]

prods = odoo.search_read("product.product", [("id", "in", list(BULK))], fields)
for p in sorted(prods, key=lambda x: x["id"]):
    print(f"[{p['id']}] {p['name']}  ({p.get('default_code')})")
    print(f"    sale_ok={p['sale_ok']}  purchase_ok={p['purchase_ok']}  tracking={p['tracking']}  type={p['type']}")
    print(f"    stock physique={p['qty_available']:g}  previsionnel={p['virtual_available']:g} {p['uom_id'][1]}")
    print(f"    routes={p.get('route_ids')}")
    print()

# Comparaison : les FINIS correspondants sont-ils vendables et a quel stock ?
print("=== Rappel : ce sont les FINIS (flacons) qui sont vendus sur Shopify ===")
finis_terms = ["shampoing purifiant", "shampoing nourrissant", "shampoing gel douche",
               "shampoing dejaunisseur"]
dom = ["|"] * (len(finis_terms) - 1)
for t in finis_terms:
    dom.append(("name", "ilike", t))
finis = odoo.search_read(
    "product.product",
    ["&", ("sale_ok", "=", True)] + ["&"] * (len(finis_terms) - 1) + [d for d in dom],
    ["name", "sale_ok", "qty_available"], limit=0,
) if False else odoo.search_read(
    "product.product",
    dom + [("sale_ok", "=", True)],
    ["name", "default_code", "sale_ok", "qty_available", "virtual_available"], limit=0,
)
for f in sorted(finis, key=lambda x: x["name"]):
    print(f"    {f['name']:<42} vendable={f['sale_ok']} "
          f"stock={f['qty_available']:g} prev={f['virtual_available']:g}")
