"""Assign bain miraculeux move line to Carton 1/1 (pkg#192) on MYVO/OUT/00043."""
from scripts.odoo._client import write, search_read

ML_ID = 368  # bain miraculeux 50ml
PKG_ID = 192  # Carton 1/1 - 50ml Serums/Huiles

before = search_read(
    "stock.move.line",
    [("id", "=", ML_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)[0]
print(f"BEFORE: ml#{before['id']} | {before['product_id'][1]} | qty={before['quantity']} | dst={before['result_package_id']}")

write("stock.move.line", [ML_ID], {"result_package_id": PKG_ID})

after = search_read(
    "stock.move.line",
    [("id", "=", ML_ID)],
    ["id", "product_id", "quantity", "result_package_id"],
)[0]
print(f"AFTER:  ml#{after['id']} | {after['product_id'][1]} | qty={after['quantity']} | dst={after['result_package_id']}")
