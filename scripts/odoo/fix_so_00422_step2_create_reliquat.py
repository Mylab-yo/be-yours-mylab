"""Step 2 (revised): create the reliquat picking manually for S00422.

We can't call _action_launch_stock_rule via XML-RPC (Odoo 18 blocks private methods),
so we build the picking + moves ourselves and call action_confirm() (public).
"""
from scripts.odoo._client import search_read, create, execute

SO_ID = 389
SO_NAME = "S00422"
PARTNER_ID = 1970
PICKING_TYPE_ID = 10
LOCATION_SRC = 28      # MYVO/Stock
LOCATION_DEST = 5      # Partners/Customers
COMPANY_ID = 3
GROUP_ID = 19
UOM_UNITS = 1

# (sale_line_id, product_id, product_name, qty_remaining)
MOVES_TO_CREATE = [
    (401, 2461, "shampoing nourrissant 100ml",            450.0),
    (402, 2462, "shampoing purifiant 100ml",              220.0),
    (403, 2463, "Shampoing boucles 100ml",                340.0),
    (404, 2464, "Shampoing volume 100ml",                 220.0),
    (405, 2465, "Shampoing platine 100ml",               1680.0),
    (406, 2466, "masque reparateur sans rincage 100ml",   500.0),
    (407, 2467, "shampoing gloss 100ml",                   50.0),
    (409, 2468, "masque gloss 100ml",                      50.0),
    (410, 2469, "masque nourrissant 100ml",               500.0),
    (412, 2472, "masque gloss 200ml",                      80.0),
]

print(f"=== Creating reliquat picking for {SO_NAME} ===")

# Build the picking with embedded moves via move_ids one2many in create
move_vals = []
for sol_id, pid, name, qty in MOVES_TO_CREATE:
    move_vals.append((0, 0, {
        "name": name,
        "product_id": pid,
        "product_uom_qty": qty,
        "product_uom": UOM_UNITS,
        "location_id": LOCATION_SRC,
        "location_dest_id": LOCATION_DEST,
        "picking_type_id": PICKING_TYPE_ID,
        "company_id": COMPANY_ID,
        "partner_id": PARTNER_ID,
        "group_id": GROUP_ID,
        "sale_line_id": sol_id,
        "origin": SO_NAME,
    }))

picking_id = create("stock.picking", {
    "partner_id": PARTNER_ID,
    "picking_type_id": PICKING_TYPE_ID,
    "location_id": LOCATION_SRC,
    "location_dest_id": LOCATION_DEST,
    "company_id": COMPANY_ID,
    "group_id": GROUP_ID,
    "sale_id": SO_ID,
    "origin": SO_NAME,
    "move_ids": move_vals,
})
print(f"  Created picking id={picking_id}")

# Read back
pk = search_read("stock.picking", [("id", "=", picking_id)],
                 ["id", "name", "state", "origin", "partner_id", "sale_id",
                  "group_id", "move_ids"])[0]
print(f"  {pk['name']} | state={pk['state']} | sale_id={pk['sale_id']} | "
      f"group_id={pk['group_id']} | moves={len(pk['move_ids'])}")

# Confirm the picking (public method) to trigger reservation flow
print("\nCalling action_confirm on picking...")
execute("stock.picking", "action_confirm", [[picking_id]])

# Also try action_assign to reserve quants where available
print("Calling action_assign on picking...")
execute("stock.picking", "action_assign", [[picking_id]])

# Read back final state
pk = search_read("stock.picking", [("id", "=", picking_id)],
                 ["id", "name", "state", "origin", "partner_id", "sale_id",
                  "group_id", "move_ids", "scheduled_date"])[0]
print(f"\n  After confirm: {pk['name']} | state={pk['state']} | "
      f"scheduled={pk['scheduled_date']} | moves={len(pk['move_ids'])}")

# Verify SO state
so = search_read("sale.order", [("id", "=", SO_ID)],
                 ["picking_ids", "delivery_status"])[0]
print(f"\n  SO {SO_NAME}: picking_ids={so['picking_ids']} delivery_status={so['delivery_status']}")

# Show the new picking's moves
mvs = search_read(
    "stock.move",
    [("picking_id", "=", picking_id)],
    ["id", "product_id", "product_uom_qty", "quantity", "state",
     "sale_line_id"],
)
print(f"\n=== Moves of new reliquat picking ({len(mvs)}) ===")
for mv in mvs:
    prod = mv["product_id"][1] if mv["product_id"] else "?"
    sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
    print(f"  mv#{mv['id']:5d} | demand={mv['product_uom_qty']:7.2f} | "
          f"reserved/done={mv['quantity']:7.2f} | state={mv['state']:10s} | "
          f"sol={sl} | {prod[:45]}")
