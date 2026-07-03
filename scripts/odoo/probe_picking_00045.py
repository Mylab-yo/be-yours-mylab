"""Sonde MYVO/OUT/00045 : etat, moves, move_lines, tracking lot des produits."""
from _client import execute, search_read

NAME = "MYVO/OUT/00045"

pk = search_read("stock.picking", [("name", "=", NAME)],
                 ["id", "name", "state", "partner_id", "origin", "picking_type_id",
                  "scheduled_date", "move_ids", "move_line_ids"])
if not pk:
    raise SystemExit(f"Picking {NAME} introuvable")
pk = pk[0]
PID = pk["id"]
print(f"=== {pk['name']} (id={PID}) state={pk['state']} ===")
print(f"  partner={pk['partner_id']} origin={pk['origin']} type={pk['picking_type_id']}")
print(f"  scheduled={pk['scheduled_date']}")

moves = search_read("stock.move", [("picking_id", "=", PID)],
                    ["id", "product_id", "product_uom_qty", "quantity", "state",
                     "product_uom", "has_tracking"])
print(f"\n=== {len(moves)} stock.move ===")
prod_ids = []
for m in moves:
    prod_ids.append(m["product_id"][0])
    print(f"  move {m['id']} | {m['product_id'][1][:40]:40} | demande={m['product_uom_qty']} "
          f"reserve/done={m.get('quantity')} | state={m['state']} | has_tracking={m.get('has_tracking')}")

mls = search_read("stock.move.line", [("picking_id", "=", PID)],
                  ["id", "product_id", "quantity", "lot_id", "lot_name",
                   "location_id", "location_dest_id", "state"])
print(f"\n=== {len(mls)} stock.move.line ===")
for ml in mls:
    print(f"  ml {ml['id']} | {ml['product_id'][1][:36]:36} | qty={ml['quantity']} "
          f"| lot_id={ml.get('lot_id')} lot_name={ml.get('lot_name')!r} | state={ml['state']}")

# tracking config des produits
if prod_ids:
    prods = search_read("product.product", [("id", "in", list(set(prod_ids)))],
                        ["id", "name", "tracking", "is_storable", "type"])
    print(f"\n=== tracking produits ===")
    for p in prods:
        print(f"  [{p['id']}] {p['name'][:40]:40} tracking={p['tracking']} "
              f"storable={p.get('is_storable')} type={p['type']}")
