"""Replace pricelist id=3 rules for spray texturisant 200ml (tmpl 2359).

New tiers (qty -> price € per unit):
  6 -> 7.90, 12 -> 7.50, 24 -> 7.00, 48 -> 6.50, 96 -> 6.00, 196 -> 5.30

Old rules (395-399) were inverted (9.90 € at qty 6 > list_price 7.90 €).
See feedback_pricelist_id3_data_quality.md.
"""
from _client import search_read, search, create, unlink

TMPL_ID = 2359
PRICELIST_ID = 3
COMPANY_ID = 3
CURRENCY_EUR = 125

NEW_TIERS = [
    (6, 7.90),
    (12, 7.50),
    (24, 7.00),
    (48, 6.50),
    (96, 6.00),
    (196, 5.30),
]

# Step 1: confirm template still exists with expected name
tmpl = search_read(
    "product.template",
    [("id", "=", TMPL_ID)],
    ["name", "default_code", "list_price"],
)
assert tmpl, f"Template {TMPL_ID} not found"
print(f"Target: tmpl={TMPL_ID}  sku={tmpl[0]['default_code']!r}  "
      f"name={tmpl[0]['name']!r}  list_price={tmpl[0]['list_price']}€")

# Step 2: find + drop existing rules in pricelist 3
existing = search(
    "product.pricelist.item",
    [("pricelist_id", "=", PRICELIST_ID), ("product_tmpl_id", "=", TMPL_ID)],
)
print(f"\nDeleting {len(existing)} existing rules: {existing}")
if existing:
    unlink("product.pricelist.item", existing)

# Step 3: create new rules
created = []
for qty, price in NEW_TIERS:
    rule_id = create("product.pricelist.item", {
        "pricelist_id": PRICELIST_ID,
        "company_id": COMPANY_ID,
        "currency_id": CURRENCY_EUR,
        "product_tmpl_id": TMPL_ID,
        "applied_on": "1_product",
        "base": "list_price",
        "compute_price": "fixed",
        "min_quantity": qty,
        "fixed_price": price,
    })
    created.append((rule_id, qty, price))
    print(f"  created rule={rule_id}  qty>={qty}  {price}€")

# Step 4: verify
print("\nVerification (pricelist 3 / tmpl 2359):")
verify = search_read(
    "product.pricelist.item",
    [("pricelist_id", "=", PRICELIST_ID), ("product_tmpl_id", "=", TMPL_ID)],
    ["id", "min_quantity", "fixed_price"],
)
for r in sorted(verify, key=lambda x: x["min_quantity"]):
    print(f"  rule={r['id']:>6}  qty>={int(r['min_quantity']):>3}  {r['fixed_price']}€")
