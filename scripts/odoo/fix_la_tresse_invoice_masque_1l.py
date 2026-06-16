"""Replace Shampoing Protecteur de Couleur 1L → Masque Protecteur de Couleur 1L
on draft invoice 652 (LA TRESSE PARISIENNE)."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, write, create, unlink

INVOICE_ID = 652
PL_ID = 3
DISCOUNT_PCT = 15.0
TAX_ID = 103
QTY = 6

OLD_VARIANT = 2428  # shampoing protecteur de couleur 1000ml
NEW_TMPL = 2400     # masque protecteur de couleur 1000ml

# Resolve new variant id
prod = search_read("product.product", [("product_tmpl_id", "=", NEW_TMPL)],
                   ["id", "name", "list_price"], limit=2)
print(f"New product candidates: {prod}")
NEW_VARIANT = prod[0]["id"]
NEW_LIST = prod[0]["list_price"]
print(f"  → variant {NEW_VARIANT} ({prod[0]['name']!r}) list_price={NEW_LIST}")


def get_pl_price(vid, qty, list_price):
    items = search_read("product.pricelist.item",
                        [("pricelist_id", "=", PL_ID),
                         ("product_id", "=", vid),
                         ("compute_price", "=", "fixed")],
                        ["min_quantity", "fixed_price"], limit=50)
    if not items:
        prod = search_read("product.product", [("id", "=", vid)], ["product_tmpl_id"], limit=1)
        tmpl_id = prod[0]["product_tmpl_id"][0]
        items = search_read("product.pricelist.item",
                            [("pricelist_id", "=", PL_ID),
                             ("product_tmpl_id", "=", tmpl_id),
                             ("product_id", "=", False),
                             ("compute_price", "=", "fixed")],
                            ["min_quantity", "fixed_price"], limit=50)
    if not items:
        return list_price, "list (no rules)"
    clean = [it for it in items
             if it["fixed_price"] >= list_price * 0.4
             and it["fixed_price"] <= list_price * 1.2]
    if not clean:
        return list_price, "list (contaminated)"
    clean.sort(key=lambda x: x["min_quantity"])
    chosen = None
    for it in clean:
        if it["min_quantity"] <= qty:
            chosen = it
    if chosen is None:
        return list_price, "list (qty < smallest tier)"
    return chosen["fixed_price"], f"tier @{int(chosen['min_quantity'])}"


new_price, src = get_pl_price(NEW_VARIANT, QTY, NEW_LIST)
print(f"  → PL price @qty={QTY}: {new_price} ({src})")

# Find the invoice line with the old variant
lines = search_read("account.move.line",
                    [("move_id", "=", INVOICE_ID),
                     ("product_id", "=", OLD_VARIANT)],
                    ["id", "name", "product_id", "quantity", "price_unit", "discount", "price_subtotal"],
                    limit=5)
print(f"\nCurrent line(s) to replace: {lines}")
if not lines:
    print("ERROR: no line found with old product")
    sys.exit(1)

OLD_LINE_ID = lines[0]["id"]
print(f"Replacing line id={OLD_LINE_ID}: '{lines[0]['name']}' qty={lines[0]['quantity']} unit={lines[0]['price_unit']} subtotal={lines[0]['price_subtotal']}")

# Update the line: change product_id + price_unit (Odoo will recompute name from product)
result = write("account.move.line", [OLD_LINE_ID], {
    "product_id": NEW_VARIANT,
    "price_unit": new_price,
    "quantity": QTY,
    "discount": DISCOUNT_PCT,
    "tax_ids": [(6, 0, [TAX_ID])],
})
print(f"Write result: {result}")

# Read back
lines_after = search_read("account.move.line",
                          [("id", "=", OLD_LINE_ID)],
                          ["id", "name", "product_id", "quantity", "price_unit", "discount", "price_subtotal", "price_total"],
                          limit=1)
print(f"\nAfter update: {lines_after[0]}")

# Show updated invoice totals
inv = search_read("account.move", [("id", "=", INVOICE_ID)],
                  ["name", "state", "invoice_date",
                   "amount_untaxed", "amount_tax", "amount_total", "ref"], limit=1)
print(f"\n=== Updated invoice {INVOICE_ID} ===")
print(f"  Date: {inv[0]['invoice_date']}  State: {inv[0]['state']}")
print(f"  Ref: {inv[0]['ref']}")
print(f"  HT: {inv[0]['amount_untaxed']:.2f} €")
print(f"  TVA: {inv[0]['amount_tax']:.2f} €")
print(f"  TTC: {inv[0]['amount_total']:.2f} €")
print(f"\n👉 https://odoo.startec-paris.com/odoo/action-account.action_move_out_invoice_type/{INVOICE_ID}")
