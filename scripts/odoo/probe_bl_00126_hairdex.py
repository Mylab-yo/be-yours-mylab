"""Localise le BL 00126 (Hairdex) + état, avant annulation."""
from _client import search_read

# pickings dont le nom contient 00126
pks = search_read("stock.picking", [("name", "ilike", "00126")],
                  ["id", "name", "state", "partner_id", "scheduled_date",
                   "origin", "picking_type_id", "sale_id"])
print("=== pickings name ilike 00126 ===")
for p in pks:
    print(f"  id={p['id']} {p['name']} | state={p['state']} | partner={p['partner_id']} "
          f"| origin={p['origin']} | type={p['picking_type_id']} | SO={p.get('sale_id')}")

# recoupe avec Hairdex
parts = search_read("res.partner", [("name", "ilike", "hairdex")], ["id", "name"])
print("\n=== partenaires Hairdex ===")
for pa in parts:
    print(f"  id={pa['id']} {pa['name']}")
