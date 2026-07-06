"""Cree un BL neuf pour S00562 : 48 shampoing + 1 serum + 1 bain (= facture).

- shampoing SOL 2030 : 35 -> 48 (aligne sur la facture payee, plus d'avoir a faire)
- BL sortant unique liant les 3 lignes, confirme + reserve, PRET A VALIDER (par Yoann)
- Idempotent + garde anti-doublon sur le groupe 113
"""
from _client import execute, search_read, write, create

SID, GROUP, PT_OUT, SRC, DEST, PARTNER = 529, 113, 10, 28, 5, 2141
# (SOL, produit, qte)
CIBLES = [(2030, 2401, 48.0), (2031, 2375, 1.0), (2032, 2306, 1.0)]

# 0. deverrouiller si besoin
so = search_read("sale.order", [("id", "=", SID)], ["locked"])[0]
if so["locked"]:
    execute("sale.order", "action_unlock", [[SID]])
    print("SO deverrouillee.")

# 1. shampoing -> 48
cur = search_read("sale.order.line", [("id", "=", 2030)], ["product_uom_qty"])[0]["product_uom_qty"]
if cur != 48.0:
    write("sale.order.line", [2030], {"product_uom_qty": 48.0})
    print(f"Shampoing SOL 2030 : {cur} -> 48")
else:
    print("Shampoing deja a 48")

# 2. recuperer / creer le BL sortant (Odoo peut l'avoir auto-cree)
pick = None
existing = search_read("stock.picking",
                       [("group_id", "=", GROUP), ("picking_type_id", "=", PT_OUT),
                        ("state", "not in", ["done", "cancel"])],
                       ["id", "name", "state"])
if existing:
    pick = existing[0]["id"]
    print(f"BL existant reutilise : {existing[0]['name']} (id={pick})")
else:
    pick = create("stock.picking", {
        "picking_type_id": PT_OUT, "partner_id": PARTNER, "location_id": SRC,
        "location_dest_id": DEST, "origin": "S00562", "group_id": GROUP})
    print(f"BL cree : id={pick}")

# 3. garantir les 3 lignes avec la bonne qte
uoms = {p["id"]: p["uom_id"][0] for p in
        search_read("product.product", [("id", "in", [c[1] for c in CIBLES])], ["uom_id"])}
for sol_id, prod, qty in CIBLES:
    mv = search_read("stock.move",
                     [("picking_id", "=", pick), ("product_id", "=", prod)],
                     ["id", "product_uom_qty"])
    if mv:
        if mv[0]["product_uom_qty"] != qty:
            write("stock.move", [mv[0]["id"]], {"product_uom_qty": qty})
            print(f"  move {mv[0]['id']} {prod} qte -> {qty}")
        else:
            print(f"  move {prod} deja a {qty}")
    else:
        pname = search_read("product.product", [("id", "=", prod)], ["display_name"])[0]["display_name"]
        m = create("stock.move", {
            "name": pname, "product_id": prod, "product_uom_qty": qty,
            "product_uom": uoms[prod], "location_id": SRC, "location_dest_id": DEST,
            "picking_id": pick, "group_id": GROUP, "sale_line_id": sol_id})
        print(f"  + move {m} {pname[:35]} qty={qty}")

# 4. confirmer + reserver
execute("stock.picking", "action_confirm", [[pick]])
execute("stock.picking", "action_assign", [[pick]])

# 5. etat final
p = search_read("stock.picking", [("id", "=", pick)], ["name", "state"])[0]
print(f"\n=== {p['name']} (id={pick}) state={p['state']} ===")
for m in search_read("stock.move", [("picking_id", "=", pick)],
                     ["product_id", "product_uom_qty", "quantity", "state"]):
    flag = "" if m["quantity"] >= m["product_uom_qty"] else "  <-- NON reserve (stock deja engage)"
    print(f"  {m['product_id'][1][:40]:40} demande={m['product_uom_qty']} reserve={m['quantity']} {m['state']}{flag}")
print("\n>>> BL pret. A valider par Yoann (forcer lot/qte pour shampoing & bain si non reserves).")
