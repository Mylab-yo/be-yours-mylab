"""Probe stock.move.line full schema for picking 69 — find fields needed at create()."""
from scripts.odoo._client import search_read

# Read one existing move_line completely (all fields)
mls = search_read(
    "stock.move.line",
    [("picking_id", "=", 69)],
    [
        "id", "move_id", "picking_id", "product_id", "product_uom_id",
        "location_id", "location_dest_id", "quantity", "quantity_product_uom",
        "result_package_id", "package_id", "lot_id", "lot_name",
        "state", "company_id", "owner_id",
    ],
)
ml = mls[0]
print("=== Sample move_line full record ===")
for k, v in ml.items():
    print(f"  {k}: {v!r}")

# Read fields metadata
print("\n=== stock.move.line.fields_get (required) ===")
from scripts.odoo._client import execute
schema = execute("stock.move.line", "fields_get", [[]],
                 {"attributes": ["required", "type", "string"]})
for fname, meta in sorted(schema.items()):
    if meta.get("required"):
        print(f"  REQUIRED: {fname} ({meta['type']}) - {meta['string']}")
