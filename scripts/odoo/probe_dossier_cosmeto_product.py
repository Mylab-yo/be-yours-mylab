"""Trouver le product.product 'creation-du-dossier-cosmetologique' et inspecter les champs res.partner utiles pour le mandat."""
from scripts.odoo._client import search_read

print("=== Recherche produit 'dossier cosmetologique' ===")
rows = search_read(
    "product.product",
    ["|", ("name", "ilike", "dossier cosm"), ("default_code", "ilike", "dossier-cosm")],
    ["id", "name", "default_code", "list_price", "product_tmpl_id", "type", "sale_ok"],
)
for r in rows:
    print(f"  product.product [{r['id']}] name={r['name']!r}")
    print(f"    default_code={r.get('default_code')!r}  list_price={r['list_price']}")
    print(f"    product_tmpl_id={r['product_tmpl_id']}  type={r['type']}  sale_ok={r['sale_ok']}")

print("\n=== Champs disponibles sur res.partner pour mandat ===")
fields = [
    "name", "commercial_company_name", "company_name", "company_type",
    "vat", "company_registry", "siret",
    "street", "street2", "zip", "city", "country_id", "state_id",
    "email", "phone", "mobile",
    "title", "function", "parent_id", "is_company",
]
# Pick a real B2B partner to see what's populated
sample = search_read(
    "res.partner",
    [("is_company", "=", True), ("customer_rank", ">", 0)],
    fields,
    limit=3,
)
for p in sample:
    print(f"\n  res.partner [{p['id']}] {p.get('name')!r}")
    for k, v in p.items():
        if k == "id" or not v:
            continue
        print(f"    {k} = {v!r}")

print("\n=== Champs custom (x_*) sur res.partner ===")
all_fields = search_read(
    "ir.model.fields",
    [("model", "=", "res.partner"), ("name", "like", "x_")],
    ["name", "field_description", "ttype"],
)
for f in all_fields:
    print(f"  {f['name']:35s}  {f['ttype']:15s}  {f['field_description']!r}")
