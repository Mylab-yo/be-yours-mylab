"""DIAGNOSTIC (lecture seule) : pourquoi les produits partent en reliquat ?

Dump complet des BL sortants actifs (draft/assigned/confirmed) :
- stock.move : product_uom_qty (demande), quantity (fait/reserve), picked, state
- stock.move.line : quantity, lot, picked
En Odoo 18 le driver du reliquat au button_validate = champ `picked` sur le move.
Si picked=False, meme reserve a 100%, la validation propose un reliquat total.
"""
from _client import search_read

# BL sortants non termines (tous types de sortie), + focus groupe S00562
picks = search_read(
    "stock.picking",
    [("picking_type_code", "=", "outgoing"),
     ("state", "not in", ["done", "cancel"])],
    ["id", "name", "state", "origin", "group_id", "partner_id", "scheduled_date"],
)
picks.sort(key=lambda p: p["id"])

if not picks:
    print("Aucun BL sortant actif (draft/assigned/confirmed).")

for p in picks:
    partner = p["partner_id"][1] if p.get("partner_id") else "?"
    grp = p["group_id"][1] if p.get("group_id") else "-"
    print(f"\n{'='*90}")
    print(f"{p['name']} (id={p['id']}) state={p['state']} origin={p.get('origin')} "
          f"partner={partner} group={grp}")
    print(f"{'='*90}")

    moves = search_read(
        "stock.move",
        [("picking_id", "=", p["id"])],
        ["id", "product_id", "product_uom_qty", "quantity", "picked", "state"],
    )
    print(f"  {'produit':40} {'demande':>8} {'fait/res':>9} {'picked':>7} {'state':>10}")
    for m in moves:
        pname = m["product_id"][1][:40] if m.get("product_id") else "?"
        print(f"  {pname:40} {m['product_uom_qty']:>8} {m['quantity']:>9} "
              f"{str(m['picked']):>7} {m['state']:>10}")

    mls = search_read(
        "stock.move.line",
        [("picking_id", "=", p["id"])],
        ["product_id", "quantity", "quantity_product_uom", "picked", "lot_id"],
    )
    if mls:
        print("  -- move lines --")
        for ml in mls:
            pname = ml["product_id"][1][:38] if ml.get("product_id") else "?"
            lot = ml["lot_id"][1] if ml.get("lot_id") else "-"
            picked = ml.get("picked")
            print(f"    {pname:38} qty={ml['quantity']:>6} picked={picked} lot={lot}")

    # verdict
    all_reserved = all(m["quantity"] >= m["product_uom_qty"] for m in moves) if moves else False
    any_not_picked = any(not m["picked"] for m in moves)
    print(f"  >>> tout reserve={all_reserved} | au moins un move picked=False={any_not_picked}")
    if all_reserved and any_not_picked:
        print("      => RELIQUAT TOTAL au button_validate : reserve OK mais picked=False.")
