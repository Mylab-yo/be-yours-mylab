"""Probe Odoo for 'Pompe' products — get prices + formats to wire pump add-on."""
from _client import search_read

terms = ["pompe", "pump"]
seen = {}
for term in terms:
    for t in search_read(
        "product.template",
        [("name", "ilike", term)],
        ["id", "name", "default_code", "list_price", "standard_price",
         "weight", "product_variant_id", "sale_ok", "active", "taxes_id"],
    ):
        seen[t["id"]] = t

print(f"=== {len(seen)} product.template matching pompe/pump ===")
for t in sorted(seen.values(), key=lambda x: x["name"]):
    var = t.get("product_variant_id")
    print(f"tmpl={t['id']:>5} var={var[0] if var else '?':>5} "
          f"sku={str(t.get('default_code')):>14} list={t['list_price']:>7}€ "
          f"cost={t.get('standard_price')}€ w={t.get('weight')} "
          f"sale_ok={t.get('sale_ok')} active={t.get('active')} | {t['name']}")
