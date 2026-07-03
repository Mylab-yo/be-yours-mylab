# -*- coding: utf-8 -*-
"""Tableau des reliquats (qte commandee - livree) par client
pour le Masque Nourrissant en 200ml / 400ml / 1000ml.

Reliquat = product_uom_qty - qty_delivered sur les sale.order.line
de commandes confirmees (state in sale/done), reliquat > 0.
"""
import re
from collections import defaultdict
import _client as odoo

# Formats voulus (ordre d'affichage)
FORMATS = ["200ml", "400ml", "1000ml"]


def format_of(name: str) -> str | None:
    """Deduit le format (200ml/400ml/1000ml) depuis le nom produit."""
    low = name.lower().replace(" ", "")
    for f in ("1000ml", "400ml", "200ml"):
        if f in low:
            return f
    # tolere "1l"/"1 l" pour le 1000ml
    if re.search(r"\b1l\b", name.lower()):
        return "1000ml"
    return None


# 1. Variantes "masque nourrissant"
prods = odoo.search_read(
    "product.product",
    [("name", "ilike", "masque nourrissant")],
    ["id", "name", "default_code"],
)
print("=== Produits 'masque nourrissant' trouves ===")
for p in prods:
    print(f"  [{p['id']}] {p['name']} (ref={p.get('default_code')}) -> format={format_of(p['name'])}")

# On ne garde que les formats voulus
keep = {p["id"]: format_of(p["name"]) for p in prods if format_of(p["name"]) in FORMATS}
prod_name = {p["id"]: p["name"] for p in prods}
if not keep:
    raise SystemExit("Aucune variante 200/400/1000ml trouvee.")

prod_ids = list(keep)

# 2. Lignes de commande confirmees non entierement livrees
lines = odoo.search_read(
    "sale.order.line",
    [
        ("product_id", "in", prod_ids),
        ("order_id.state", "in", ["sale", "done"]),
    ],
    ["order_id", "order_partner_id", "product_id",
     "product_uom_qty", "qty_delivered"],
)

matrix = defaultdict(lambda: defaultdict(float))   # partner -> format -> qty due
detail = []                                        # (partner, order, format, cmd, livre, du)

for l in lines:
    ordered = l["product_uom_qty"] or 0.0
    delivered = l["qty_delivered"] or 0.0
    remaining = round(ordered - delivered, 2)
    if remaining <= 0:
        continue
    pid = l["product_id"][0]
    fmt = keep.get(pid)
    if fmt not in FORMATS:
        continue
    partner = l["order_partner_id"][1] if l["order_partner_id"] else "?"
    order = l["order_id"][1] if l["order_id"] else "?"
    matrix[partner][fmt] += remaining
    detail.append((partner, order, fmt, ordered, delivered, remaining))

# 3. Detail par commande
print("\n=== DETAIL par commande (reliquat > 0) ===")
if not detail:
    print("  Aucun reliquat : tout est livre.")
for partner, order, fmt, ordered, delivered, remaining in sorted(detail):
    print(f"  {partner} | {order} | {fmt} | cmd={ordered:g} livre={delivered:g} -> DU={remaining:g}")

# 4. Tableau matriciel client x format
print("\n=== TABLEAU RELIQUATS par client ===")
if matrix:
    wname = max(len(p) for p in matrix)
    wname = max(wname, len("Client"))
    header = f"{'Client':<{wname}} | " + " | ".join(f"{f:>7}" for f in FORMATS) + " | " + f"{'Total':>7}"
    print(header)
    print("-" * len(header))
    tot_col = defaultdict(float)
    for partner in sorted(matrix):
        cells = []
        row_total = 0.0
        for f in FORMATS:
            q = matrix[partner].get(f, 0.0)
            row_total += q
            tot_col[f] += q
            cells.append(f"{q:>7g}" if q else f"{'-':>7}")
        print(f"{partner:<{wname}} | " + " | ".join(cells) + " | " + f"{row_total:>7g}")
    print("-" * len(header))
    grand = sum(tot_col.values())
    totals = " | ".join(f"{tot_col[f]:>7g}" for f in FORMATS)
    print(f"{'TOTAL':<{wname}} | " + totals + " | " + f"{grand:>7g}")
else:
    print("  Rien a livrer.")
