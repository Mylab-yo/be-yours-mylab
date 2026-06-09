"""Manually trigger the auto-palette server action on S00488 to verify the code."""
from scripts.odoo._client import execute, search_read, search, write

ACTION_ID = 872

# Find S00488
so = search_read("sale.order", [("name", "=", "S00488")],
                 ["id", "name", "shipping_weight", "carrier_id", "state"])
if not so:
    print("S00488 not found")
    raise SystemExit
so = so[0]
print(f"BEFORE: {so['name']} | weight={so['shipping_weight']:.2f}kg | "
      f"carrier={so['carrier_id'][1] if so['carrier_id'] else '-'} | state={so['state']}")

# Run the server action with this record as context
result = execute(
    "ir.actions.server", "run", [[ACTION_ID]],
    {"context": {"active_model": "sale.order",
                 "active_ids": [so["id"]],
                 "active_id": so["id"]}},
)
print(f"  Action run result: {result}")

# Verify
so2 = search_read("sale.order", [("id", "=", so["id"])],
                  ["id", "name", "shipping_weight", "carrier_id", "state"])[0]
print(f"AFTER:  {so2['name']} | weight={so2['shipping_weight']:.2f}kg | "
      f"carrier={so2['carrier_id'][1] if so2['carrier_id'] else '-'} | state={so2['state']}")

if so2["carrier_id"] and so2["carrier_id"][0] == 19:
    print("\n  CODE OK -> carrier set to Envoi Palette")
else:
    print("\n  CODE may have a problem -> carrier was not set as expected")
