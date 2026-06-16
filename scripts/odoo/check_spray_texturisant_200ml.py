"""Inspect Spray Texturisant 200ml — product.template + pricelist id=3 rules."""
from _client import search_read

# Find the template
tmpls = search_read(
    "product.template",
    [("name", "ilike", "spray texturisant")],
    ["id", "name", "default_code", "list_price", "weight", "product_variant_id"],
)
print(f"Found {len(tmpls)} templates matching 'spray texturisant':")
for t in tmpls:
    print(f"  tmpl={t['id']:>5} variant={t.get('product_variant_id')} "
          f"sku={t.get('default_code')!r:30} list={t['list_price']}€  {t['name']}")

# For each template, show its rules in pricelist id=3
for t in tmpls:
    rules = search_read(
        "product.pricelist.item",
        [("pricelist_id", "=", 3), ("product_tmpl_id", "=", t["id"])],
        ["id", "min_quantity", "fixed_price", "compute_price", "applied_on",
         "date_start", "date_end"],
    )
    print(f"\n  Pricelist id=3 rules for tmpl {t['id']} ({t['name']}):")
    if not rules:
        print("    (none)")
    for r in sorted(rules, key=lambda x: x["min_quantity"]):
        print(f"    rule={r['id']:>6} qty>={int(r['min_quantity']):>3}  "
              f"price={r['fixed_price']}€  compute={r['compute_price']}  "
              f"applied={r['applied_on']}  start={r.get('date_start')}  end={r.get('date_end')}")
