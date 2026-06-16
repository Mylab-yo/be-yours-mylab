"""Check if 'Masque Protecteur de Couleur 1L' exists in Odoo."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read

res = search_read("product.template",
                  [("name", "ilike", "protecteur de couleur")],
                  ["id", "name", "list_price", "active"], limit=20)
print(f"Found {len(res)} 'protecteur de couleur' templates:")
for r in res:
    print(f"  id={r['id']:5} | active={r['active']} | list={r['list_price']:>6} | {r['name']!r}")

print()
res2 = search_read("product.template",
                   ["&", ("name", "ilike", "masque"),
                    "&", ("name", "ilike", "protecteur"),
                    ("name", "ilike", "1000")],
                   ["id", "name", "list_price", "active"], limit=20)
print(f"Found {len(res2)} 'masque protecteur 1000' templates:")
for r in res2:
    print(f"  id={r['id']:5} | active={r['active']} | list={r['list_price']:>6} | {r['name']!r}")

# Also probe by tier price 27.97
print()
print("Probe pricelist items where fixed_price = 27.97 (devis unit price):")
items = search_read("product.pricelist.item",
                    [("pricelist_id", "=", 3), ("fixed_price", "=", 27.97)],
                    ["id", "product_id", "product_tmpl_id", "min_quantity"], limit=20)
for it in items:
    print(f"  {it}")
