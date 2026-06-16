"""Read picking_type 10 (MYLAB: Bons de livraison) for default locations & company."""
from scripts.odoo._client import search_read

pt = search_read(
    "stock.picking.type",
    [("id", "=", 10)],
    ["id", "name", "code", "default_location_src_id", "default_location_dest_id",
     "warehouse_id", "company_id", "return_picking_type_id", "sequence_id"],
)[0]
print(pt)

# Also read existing picking 35 to mirror its setup for the new reliquat
pk = search_read(
    "stock.picking",
    [("id", "=", 35)],
    ["id", "name", "location_id", "location_dest_id", "company_id",
     "picking_type_id", "partner_id"],
)[0]
print("\nExisting picking 35:")
print(pk)

# Read each product to get its uom_id
prods = search_read(
    "product.product",
    [("id", "in", [2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2472])],
    ["id", "name", "uom_id"],
)
print("\nProducts to procure (uom_id):")
for p in prods:
    print(f"  pid={p['id']:5d} | uom={p['uom_id']} | {p['name'][:50]}")
