"""Probe LECTURE SEULE : cherche les 4 references SHP demandees pour OF vrac (kg).

SHP PURIFIANT 200KG / SHP NOURRISSANT 300KG / SHP GEL DOUCHE 120KG / SHP DEJAUNISSEUR 150KG

Pour chaque candidat trouve : UoM, type (product/consu), default_code, et BoM associee
(mrp.bom) + composants. Aucune ecriture.
"""
import _client as odoo

TERMS = ["purifiant", "nourrissant", "gel douche", "dejauniss", "gel-douche", "gel_douche"]

seen = {}
for term in TERMS:
    prods = odoo.search_read(
        "product.product",
        [("name", "ilike", term)],
        ["id", "name", "default_code", "uom_id", "type", "product_tmpl_id"],
    )
    for p in prods:
        seen[p["id"]] = p

print(f"=== {len(seen)} variantes produit trouvees (termes: {TERMS}) ===\n")
for pid, p in sorted(seen.items()):
    uom = p["uom_id"][1] if p.get("uom_id") else "?"
    tmpl = p["product_tmpl_id"][0] if p.get("product_tmpl_id") else None
    print(f"[variant {pid}] {p['name']}")
    print(f"    ref={p.get('default_code')}  UoM={uom}  type={p.get('type')}  tmpl={tmpl}")

    # BoM eventuelle (par template ou par variant)
    boms = odoo.search_read(
        "mrp.bom",
        ["|", ("product_id", "=", pid), ("product_tmpl_id", "=", tmpl)],
        ["id", "product_qty", "product_uom_id", "type", "code"],
    )
    if not boms:
        print("    BoM: AUCUNE (pas de nomenclature -> OF ne pourra pas exploser de composants)")
    for b in boms:
        buom = b["product_uom_id"][1] if b.get("product_uom_id") else "?"
        print(f"    BoM {b['id']} : produit x{b['product_qty']:g} {buom}  type={b.get('type')} code={b.get('code')}")
        lines = odoo.search_read(
            "mrp.bom.line",
            [("bom_id", "=", b["id"])],
            ["product_id", "product_qty", "product_uom_id"],
        )
        for l in lines:
            luom = l["product_uom_id"][1] if l.get("product_uom_id") else "?"
            print(f"        - {l['product_qty']:g} {luom} x {l['product_id'][1]}")
    print()
