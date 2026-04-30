"""Create the missing 'Down Payment' / 'Acompte' service product.

Odoo 18's partial prepayment flow expects this product to exist on the
company. When prepayment_percent < 1.0 and a customer pays via wire transfer,
Odoo tries to create a down payment invoice using this product. If missing,
the flow fails silently and the portal redirects.

Idempotent: skips if a deposit product already exists.

Run: python step30_create_downpayment_product.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, execute

# Skip if we already have one
existing = search_read("product.product",
                       [("default_code", "=", "DOWN_PAYMENT")],
                       ["id"])
if existing:
    print(f"✓ Down payment product already exists (id={existing[0]['id']})")
    sys.exit(0)

# Get the 20% G tax (memory says taxes_id=[103] for products)
tax_ids = search_read("account.tax",
                      [("type_tax_use", "=", "sale"),
                       ("amount", "=", 20.0),
                       ("company_id", "=", 3)],
                      ["id", "name"])
print(f"Found sale taxes (20%, company 3):")
for t in tax_ids:
    print(f"  [{t['id']}] {t['name']}")

# Pick the first matching one (should be 20% G)
default_tax_id = tax_ids[0]["id"] if tax_ids else False

# Create as service product with standard settings
values = {
    "name": "Acompte",
    "default_code": "DOWN_PAYMENT",
    "type": "service",
    "invoice_policy": "order",
    "list_price": 0.0,
    "purchase_ok": False,
    "sale_ok": True,
    "company_id": 3,
}
if default_tax_id:
    values["taxes_id"] = [(6, 0, [default_tax_id])]

product_id = create("product.product", values)
print(f"\n✓ Down Payment product created: id={product_id}, default_code=DOWN_PAYMENT")
print()
print("Pour rendre ce produit la valeur par défaut du wizard d'acompte,")
print("Odoo le détecte automatiquement via default_code='DOWN_PAYMENT'.")
