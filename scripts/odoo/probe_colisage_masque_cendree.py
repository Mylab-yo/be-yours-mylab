# -*- coding: utf-8 -*-
"""Sonde read-only : colisage / carton du Masque Nourrissant 200ml + contexte Cendree.

Objectif : avant de poser un colisage de 36 u/carton, comprendre l'existant :
  - la/les variante(s) product.product 'masque nourrissant' 200ml + leur template
  - valeur actuelle x_carton_capacity (champ custom) sur le template
  - conditionnements natifs product.packaging existants
  - reliquat + pickings de la cliente Cendree pour ce produit
Aucune ecriture. 100% lecture.
"""
import _client as odoo

# --- 1. Variantes masque nourrissant, focus 200ml -------------------------
prods = odoo.search_read(
    "product.product",
    [("name", "ilike", "masque nourrissant")],
    ["id", "name", "default_code", "product_tmpl_id", "uom_id"],
)
print("=== Variantes 'masque nourrissant' ===")
for p in prods:
    print(f"  pp[{p['id']}] tmpl={p['product_tmpl_id']} | {p['name']} (ref={p.get('default_code')})")

# On repere le(s) 200ml
def is_200(name):
    low = name.lower().replace(" ", "")
    return "200ml" in low

p200 = [p for p in prods if is_200(p["name"])]
print("\n=== 200ml retenus ===")
for p in p200:
    print(f"  pp[{p['id']}] tmpl={p['product_tmpl_id'][0]} | {p['name']}")

tmpl_ids = sorted({p["product_tmpl_id"][0] for p in p200})
prod_ids_200 = [p["id"] for p in p200]

# --- 2. Champ x_carton_capacity sur les templates -------------------------
# Detecte si le champ existe
fields = odoo.execute("product.template", "fields_get",
                      [[], ["string", "type"]]) or {}
has_carton = "x_carton_capacity" in fields
print(f"\n=== champ x_carton_capacity present sur product.template ? {has_carton} ===")

tmpl_fields = ["id", "name", "sale_ok", "uom_id"]
if has_carton:
    tmpl_fields.append("x_carton_capacity")
if tmpl_ids:
    tmpls = odoo.search_read("product.template", [("id", "in", tmpl_ids)], tmpl_fields)
    for t in tmpls:
        cap = t.get("x_carton_capacity") if has_carton else "N/A"
        print(f"  tmpl[{t['id']}] {t['name']} | x_carton_capacity={cap}")

# --- 3. Conditionnements natifs product.packaging -------------------------
try:
    packs = odoo.search_read(
        "product.packaging",
        ["|", ("product_id", "in", prod_ids_200),
              ("product_id.product_tmpl_id", "in", tmpl_ids)],
        ["id", "name", "qty", "product_id", "sales", "purchase"],
    )
    print(f"\n=== product.packaging existants (200ml) : {len(packs)} ===")
    for pk in packs:
        print(f"  pack[{pk['id']}] {pk['name']!r} qty={pk['qty']} "
              f"prod={pk['product_id']} sales={pk.get('sales')} purch={pk.get('purchase')}")
except Exception as e:
    print(f"\n[product.packaging] erreur/inaccessible : {e}")

# --- 4. Cliente Cendree : partner + reliquat + pickings -------------------
partners = odoo.search_read(
    "res.partner", [("name", "ilike", "cendr")],
    ["id", "name", "parent_id", "customer_rank"])
print(f"\n=== Partenaires 'cendr*' : {len(partners)} ===")
for pa in partners:
    print(f"  partner[{pa['id']}] {pa['name']} parent={pa.get('parent_id')} rank={pa.get('customer_rank')}")

partner_ids = [pa["id"] for pa in partners]

# Lignes de commande masque 200ml pour Cendree, reliquat > 0
if partner_ids and prod_ids_200:
    lines = odoo.search_read(
        "sale.order.line",
        [("product_id", "in", prod_ids_200),
         ("order_partner_id", "in", partner_ids),
         ("order_id.state", "in", ["sale", "done"])],
        ["order_id", "order_partner_id", "product_id",
         "product_uom_qty", "qty_delivered"])
    print(f"\n=== Lignes cmd masque 200ml Cendree : {len(lines)} ===")
    for l in lines:
        due = round((l["product_uom_qty"] or 0) - (l["qty_delivered"] or 0), 2)
        print(f"  {l['order_id'][1]} | {l['order_partner_id'][1]} | cmd={l['product_uom_qty']:g} "
              f"livre={l['qty_delivered']:g} -> DU={due:g}")

# Pickings ouverts pour Cendree sur ce produit
if partner_ids:
    picks = odoo.search_read(
        "stock.picking",
        [("partner_id", "in", partner_ids),
         ("state", "not in", ["done", "cancel"]),
         ("picking_type_code", "=", "outgoing")],
        ["id", "name", "state", "origin", "scheduled_date"])
    print(f"\n=== Pickings sortants ouverts Cendree : {len(picks)} ===")
    for pk in picks:
        print(f"  {pk['name']} (id={pk['id']}) state={pk['state']} origin={pk['origin']}")
