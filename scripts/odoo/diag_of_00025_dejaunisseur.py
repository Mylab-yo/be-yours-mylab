"""Diagnostic de l'OF dejaunisseur bloque (MYVO/MO/00025) + stock reel flacon 200."""
import _client as odoo

# 1. Etat OF 00025
mo = odoo.search_read("mrp.production",
                      [("name", "=", "MYVO/MO/00025")],
                      ["id", "state", "product_qty", "qty_producing", "qty_produced",
                       "move_raw_ids", "move_finished_ids"])
if mo:
    mo = mo[0]
    print(f"OF {mo['id']} state={mo['state']} product_qty={mo['product_qty']:g} "
          f"qty_producing={mo.get('qty_producing')} qty_produced={mo.get('qty_produced')}")
    # backorders eventuels
    bo = odoo.search_read("mrp.production", [("origin", "like", "MYVO/MO/00025")],
                          ["name", "state", "product_qty"])
    print(f"  backorders lies: {[(b['name'], b['state'], b['product_qty']) for b in bo]}")
    raws = odoo.search_read("stock.move", [("id", "in", mo["move_raw_ids"])],
                            ["product_id", "product_uom_qty", "quantity", "state", "picked"])
    for r in raws:
        print(f"  raw {r['product_id'][1]:<38} besoin={r['product_uom_qty']:g} "
              f"reserve={r.get('quantity')} picked={r.get('picked')} state={r['state']}")

# 2. Stock reel flacon 200 (qty_available vs free_qty vs reserved)
p = odoo.execute("product.product", "read", [[2552],
                 ["name", "qty_available", "free_qty", "outgoing_qty", "virtual_available"]])[0]
print(f"\nFLACON-PLA-200 : qty_available={p['qty_available']:g}  free_qty={p['free_qty']:g}  "
      f"sortant={p['outgoing_qty']:g}  previsionnel={p['virtual_available']:g}")

# Qui reserve les flacons 200 ? (move lines assignes non done)
mls = odoo.search_read("stock.move",
                       [("product_id", "=", 2552), ("state", "in", ["assigned", "partially_available"]),
                        ("quantity", ">", 0)],
                       ["reference", "quantity", "location_id", "state", "raw_material_production_id"])
print("\nReservations actives sur FLACON-PLA-200 :")
for m in mls:
    print(f"  {m.get('reference')}: reserve={m['quantity']:g} state={m['state']} "
          f"of={m.get('raw_material_production_id')}")
