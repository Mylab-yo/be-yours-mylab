"""Step 1: link MYVO/OUT/00026 to S00422.

Maps:
  picking 35 → sale_id=389, group_id=19
  move 147 (shampoing gloss 200ml) → sale_line_id=411
  move 148 (masque gloss 200ml)    → sale_line_id=412
"""
from scripts.odoo._client import search_read, write, execute

SO_ID = 389
GROUP_ID = 19
PICKING_ID = 35

MOVES_TO_LINK = [
    {"move_id": 147, "sale_line_id": 411, "product": "shampoing gloss 200ml"},
    {"move_id": 148, "sale_line_id": 412, "product": "masque gloss 200ml"},
]

print("=== Before ===")
mvs = search_read("stock.move", [("id", "in", [147, 148])],
                  ["id", "product_id", "sale_line_id", "group_id"])
for mv in mvs:
    print(f"  mv#{mv['id']} | sale_line_id={mv['sale_line_id']} | group_id={mv['group_id']}")

pk = search_read("stock.picking", [("id", "=", PICKING_ID)],
                 ["id", "name", "sale_id", "group_id"])[0]
print(f"  picking#{pk['id']} {pk['name']} | sale_id={pk['sale_id']} | group_id={pk['group_id']}")

# Write sale_line_id + group_id on moves
for m in MOVES_TO_LINK:
    write("stock.move", [m["move_id"]],
          {"sale_line_id": m["sale_line_id"], "group_id": GROUP_ID})
    print(f"  [OK] move#{m['move_id']} -> sale_line_id={m['sale_line_id']}, group_id={GROUP_ID}")

# Write sale_id + group_id on picking
write("stock.picking", [PICKING_ID],
      {"sale_id": SO_ID, "group_id": GROUP_ID})
print(f"  [OK] picking#{PICKING_ID} -> sale_id={SO_ID}, group_id={GROUP_ID}")

print("\n=== After ===")
mvs = search_read("stock.move", [("id", "in", [147, 148])],
                  ["id", "product_id", "sale_line_id", "group_id", "quantity", "state"])
for mv in mvs:
    sl = mv["sale_line_id"]
    gr = mv["group_id"]
    print(f"  mv#{mv['id']} | qty={mv['quantity']} | state={mv['state']} | sale_line_id={sl} | group_id={gr}")

pk = search_read("stock.picking", [("id", "=", PICKING_ID)],
                 ["id", "name", "sale_id", "group_id", "state"])[0]
print(f"  picking#{pk['id']} {pk['name']} | state={pk['state']} | sale_id={pk['sale_id']} | group_id={pk['group_id']}")

# Verify qty_delivered on SO lines
print("\n=== qty_delivered on SO lines (after linkage) ===")
sols = search_read("sale.order.line", [("id", "in", [411, 412])],
                   ["id", "name", "product_uom_qty", "qty_delivered", "move_ids"])
for sl in sols:
    print(f"  sol#{sl['id']} | ordered={sl['product_uom_qty']:.2f} | "
          f"delivered={sl['qty_delivered']:.2f} | moves={sl['move_ids']} | "
          f"{sl['name'][:50]}")

# Check picking_ids on SO
so = search_read("sale.order", [("id", "=", SO_ID)],
                 ["id", "name", "picking_ids", "delivery_status"])[0]
print(f"\n  SO {so['name']} picking_ids={so['picking_ids']} delivery_status={so.get('delivery_status')}")
