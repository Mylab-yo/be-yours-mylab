"""Find the right picking_type + locations for SO S00418 outgoing."""
from scripts.odoo._client import search_read

so = search_read("sale.order", [("id", "=", 385)],
    ["name", "warehouse_id", "company_id", "partner_id", "partner_shipping_id"])[0]
print(f"SO: {so}")

wh = search_read("stock.warehouse", [("id", "=", so['warehouse_id'][0])],
    ["name", "code", "out_type_id", "lot_stock_id"])[0]
print(f"Warehouse: {wh}")

pt = search_read("stock.picking.type", [("id", "=", wh['out_type_id'][0])],
    ["name", "code", "default_location_src_id", "default_location_dest_id", "warehouse_id", "company_id"])[0]
print(f"Picking type: {pt}")

# Customer location
cust_loc = search_read("stock.location", [("usage", "=", "customer")],
    ["id", "name"], limit=3)
print(f"Customer locations: {cust_loc}")

# Pre-existing picking from this SO to copy locations from (MYVO/OUT/00008)
ex = search_read("stock.picking", [("id", "=", 8)],
    ["picking_type_id", "location_id", "location_dest_id", "partner_id"])[0]
print(f"Existing OUT/00008 reference: {ex}")
