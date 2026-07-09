"""Régénère le BL de S00566 : copie le picking annulé 143 -> nouveau brouillon. Inspecte AVANT de confirmer."""
from _client import execute, search_read

SRC = 143  # MYVO/OUT/00126 (annulé)

new_id = execute("stock.picking", "copy", [SRC])
print(f"[copy] nouveau picking id={new_id}")

p = search_read("stock.picking", [("id", "=", new_id)],
                ["name", "state", "partner_id", "origin", "picking_type_id",
                 "group_id", "sale_id", "scheduled_date", "move_ids"])[0]
print("=== nouveau picking ===")
for k, v in p.items():
    print(f"  {k}: {v}")

mv = search_read("stock.move", [("id", "in", p["move_ids"])],
                 ["product_id", "product_uom_qty", "product_uom", "state"])
print("\n=== moves ===")
for m in mv:
    print(f"  {m['product_id'][1][:40]:40} qty={m['product_uom_qty']} {m['product_uom'][1]} state={m['state']}")
print(f"\nNEW_PICKING_ID={new_id}")
