"""Probe state of MYVO/OUT/00113 and MYVO/OUT/00116 to plan qty adjustments."""
from scripts.odoo._client import search_read

for name in ("MYVO/OUT/00113", "MYVO/OUT/00116"):
    pickings = search_read(
        "stock.picking",
        [("name", "=", name)],
        ["id", "name", "state", "partner_id", "origin", "scheduled_date", "date_done"],
    )
    if not pickings:
        print(f"{name} NOT FOUND\n")
        continue
    p = pickings[0]
    print(f"=== {p['name']} (id={p['id']}, state={p['state']}) ===")
    print(f"  partner   : {p['partner_id'][1] if p['partner_id'] else '-'}")
    print(f"  origin    : {p['origin']}")
    print(f"  scheduled : {p['scheduled_date']} | done={p['date_done']}")

    moves = search_read(
        "stock.move",
        [("picking_id", "=", p["id"])],
        ["id", "product_id", "product_uom_qty", "quantity", "state"],
    )
    print(f"  --- Moves ({len(moves)}) ---")
    for mv in moves:
        prod = mv["product_id"][1] if mv["product_id"] else "?"
        print(f"    mv#{mv['id']:6d} | demand={mv['product_uom_qty']:7.1f} | done={mv['quantity']:7.1f} | "
              f"state={mv['state']:10s} | {prod[:70]}")
    print()
