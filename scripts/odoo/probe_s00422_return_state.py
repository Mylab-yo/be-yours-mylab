"""READ-ONLY : etat complet S00422 (CENDREE) — pickings, retours, move lines.

But : comprendre le retour cree par erreur (totalite du dernier BL) pour ne
garder qu'un retour de 63 shampoings hydratant 100ml.
"""
from _client import execute

# 1) La commande
so = execute("sale.order", "search_read",
             [[["name", "=", "S00422"]]],
             {"fields": ["id", "name", "partner_id", "state", "picking_ids"]})
print("=== SALE ORDER ===")
for s in so:
    print(s)

if not so:
    raise SystemExit("S00422 introuvable")

so_id = so[0]["id"]
picking_ids = so[0]["picking_ids"]

# 2) Tous les pickings lies (via sale_id + via origin)
pks = execute("stock.picking", "search_read",
              [["|", ["id", "in", picking_ids], ["origin", "=", "S00422"]]],
              {"fields": ["id", "name", "state", "origin", "picking_type_id",
                          "location_id", "location_dest_id", "scheduled_date",
                          "date_done", "return_id", "backorder_id", "move_ids"]})
print("\n=== PICKINGS (sale_id or origin=S00422) ===")
for p in sorted(pks, key=lambda x: x["id"]):
    print(f"\n[{p['id']}] {p['name']} | state={p['state']} | type={p['picking_type_id']}")
    print(f"    origin={p['origin']} | return_id={p.get('return_id')} | backorder_id={p.get('backorder_id')}")
    print(f"    loc {p['location_id']} -> {p['location_dest_id']} | date_done={p.get('date_done')}")

# 3) Detail des move lines de chaque picking
print("\n\n=== MOVE LINES DETAIL ===")
for p in sorted(pks, key=lambda x: x["id"]):
    moves = execute("stock.move", "search_read",
                    [[["picking_id", "=", p["id"]]]],
                    {"fields": ["id", "product_id", "product_uom_qty", "quantity",
                                "state", "location_id", "location_dest_id"]})
    print(f"\n--- [{p['id']}] {p['name']} ({p['state']}) ---")
    for m in moves:
        print(f"    move {m['id']}: {m['product_id'][1] if m['product_id'] else '?'}")
        print(f"        demand={m['product_uom_qty']} done={m['quantity']} state={m['state']}")
