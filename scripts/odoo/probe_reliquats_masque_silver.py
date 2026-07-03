"""Reliquats (qty commandee - livree) pour Masque Nourrissant / Silver Care, par client."""
from collections import defaultdict
import _client as odoo

# 1. Trouver les variantes produit correspondantes
prods = odoo.search_read(
    "product.product",
    ["|", ("name", "ilike", "masque nourrissant"), ("name", "ilike", "silver care")],
    ["id", "name", "default_code"],
)
print("=== Produits trouves ===")
for p in prods:
    print(f"  [{p['id']}] {p['name']} (ref={p.get('default_code')})")

prod_ids = [p["id"] for p in prods]
prod_name = {p["id"]: p["name"] for p in prods}
if not prod_ids:
    raise SystemExit("Aucun produit trouve.")

# 2. Lignes de commande confirmees, non entierement livrees
lines = odoo.search_read(
    "sale.order.line",
    [
        ("product_id", "in", prod_ids),
        ("order_id.state", "in", ["sale", "done"]),
    ],
    ["id", "order_id", "order_partner_id", "product_id",
     "product_uom_qty", "qty_delivered", "qty_invoiced", "state"],
)

print(f"\n=== {len(lines)} lignes de commande confirmees sur ces produits ===")

owed = defaultdict(lambda: defaultdict(float))   # partner -> product -> qty owed
owed_detail = []                                  # detail par commande

for l in lines:
    ordered = l["product_uom_qty"] or 0.0
    delivered = l["qty_delivered"] or 0.0
    remaining = round(ordered - delivered, 2)
    if remaining <= 0:
        continue
    partner = l["order_partner_id"][1] if l["order_partner_id"] else "?"
    pname = l["product_id"][1] if l["product_id"] else prod_name.get("?", "?")
    order = l["order_id"][1] if l["order_id"] else "?"
    owed[partner][pname] += remaining
    owed_detail.append((partner, order, pname, ordered, delivered, remaining))

print("\n=== DETAIL par commande (reliquat > 0) ===")
for partner, order, pname, ordered, delivered, remaining in sorted(owed_detail):
    print(f"  {partner} | {order} | {pname} | cmd={ordered:g} livre={delivered:g} -> DU={remaining:g}")

print("\n=== RECAP par client ===")
if not owed:
    print("  Rien a livrer : tout est deja livre sur ces produits.")
for partner in sorted(owed):
    print(f"\n  {partner}")
    for pname, qty in sorted(owed[partner].items()):
        print(f"     - {pname} : {qty:g}")
