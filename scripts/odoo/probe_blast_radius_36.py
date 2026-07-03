# -*- coding: utf-8 -*-
"""Read-only : ampleur d'un passage global 24->36 du carton masque 200ml.

- capacite carton actuelle des autres formats masque (400ml surtout, meme famille 24)
- autres clients (hors Cendree) avec pickings sortants ouverts contenant le masque 200ml
"""
import _client as odoo

MASK_TMPL_NAMES = ["200ml", "400ml", "1000ml", "100ml", "250ml", "300ml"]
prods = odoo.search_read(
    "product.product", [("name", "ilike", "masque nourrissant")],
    ["id", "name", "product_tmpl_id"])
tmpl_ids = sorted({p["product_tmpl_id"][0] for p in prods})
tmpls = odoo.search_read("product.template", [("id", "in", tmpl_ids)],
                         ["id", "name", "x_carton_capacity"])
print("=== Capacite carton actuelle par template masque ===")
for t in sorted(tmpls, key=lambda x: x["name"]):
    print(f"  tmpl[{t['id']}] {t['name']:45} x_carton_capacity={t.get('x_carton_capacity')}")

# variante 200ml
pp200 = next(p["id"] for p in prods if "200ml" in p["name"].lower().replace(" ", ""))
CENDREE = 1970

# pickings sortants ouverts contenant le masque 200ml, tous clients
moves = odoo.search_read(
    "stock.move",
    [("product_id", "=", pp200),
     ("picking_id.picking_type_code", "=", "outgoing"),
     ("picking_id.state", "not in", ["done", "cancel"])],
    ["picking_id", "product_uom_qty", "quantity"])
print(f"\n=== Pickings sortants OUVERTS contenant masque 200ml : {len(moves)} moves ===")
pick_ids = sorted({m["picking_id"][0] for m in moves})
if pick_ids:
    picks = odoo.search_read("stock.picking", [("id", "in", pick_ids)],
                             ["name", "partner_id", "state", "origin"])
    for pk in picks:
        pid = pk["partner_id"][0] if pk["partner_id"] else 0
        flag = "  <-- CENDREE" if pid == CENDREE else ""
        print(f"  {pk['name']} | {pk['partner_id']} | state={pk['state']} origin={pk['origin']}{flag}")

# autres clients (hors Cendree) qui ont deja recu / commande du 200ml (contexte marche)
lines = odoo.search_read(
    "sale.order.line",
    [("product_id", "=", pp200), ("order_id.state", "in", ["sale", "done"])],
    ["order_partner_id", "product_uom_qty", "qty_delivered"])
from collections import defaultdict
by_partner = defaultdict(lambda: [0.0, 0.0])
for l in lines:
    name = l["order_partner_id"][1] if l["order_partner_id"] else "?"
    by_partner[name][0] += l["product_uom_qty"] or 0
    by_partner[name][1] += l["qty_delivered"] or 0
print(f"\n=== Clients ayant commande du masque 200ml (cmd/livre cumulE) : {len(by_partner)} ===")
for name, (cmd, liv) in sorted(by_partner.items(), key=lambda x: -x[1][0]):
    print(f"  {name:35} cmd={cmd:g} livre={liv:g}")
