"""Probe partner + match 17 product lines to pricelist id=3 for MYLAB2196."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute

# 1. Find the partner
print("=== Partner search ===")
candidates = search_read(
    "res.partner",
    ["|", "|",
     ("name", "ilike", "tresse parisienne"),
     ("name", "ilike", "marisol"),
     ("email", "=", "studiomarisol33@gmail.com")],
    ["id", "name", "email", "phone", "street", "city", "zip", "country_id", "vat", "parent_id", "is_company"],
    limit=20,
)
for p in candidates:
    print(f"  id={p['id']} | name={p['name']!r} | email={p.get('email')} | parent={p.get('parent_id')} | company={p.get('is_company')}")
    print(f"     addr={p.get('street')!r} {p.get('zip')} {p.get('city')!r} country={p.get('country_id')}")

# 2. PDF lines (name pattern + total HT) - to match against products
LINES = [
    # (search_pattern, qty_on_pdf, total_ht_on_pdf, note)
    ("Shampoing nourrissant 200",       1, 151.20, "200ml x24"),
    ("Shampoing Protecteur de Couleur 200", 1, 79.80, "200ml x12"),
    ("Masque Nourrissant 200",          1, 205.20, "200ml x24"),
    ("Crème Boucles 200",          1, 96.60,  "200ml x12"),
    ("Spray Texturisant 200",           1, 84.00,  "200ml x12"),
    ("Shampoing Déjaunisseur Platine 200", 1, 85.20, "200ml x12"),
    ("Masque Déjaunisseur Platine 200",    1, 109.20, "200ml x12"),
    ("Shampoing Coloristeur Blond Soleil 200", 1, 162.00, "200ml x24"),
    ("Masque Coloristeur Blond Soleil 200",    1, 109.20, "200ml x12"),
    ("Shampoing Nourrissant 1",         8, 199.20, "1000ml"),
    ("Masque Nourrissant 1",            6, 197.40, "1000ml"),
    ("Shampoing Purifiant 1",           6, 149.40, "1000ml"),
    ("Shampoing 1L Déjaunisseur Platine", 6, 173.40, "1000ml"),
    ("Masque 1L Déjaunisseur Platine",    4, 139.60, "1000ml"),
    ("Shampoing 1L Coloristeur Blond Soleil",  2, 57.80,  "1000ml"),
    ("Masque 1L Coloristeur Blond Soleil",     3, 104.70, "1000ml"),
    ("Shampoing Protecteur de Couleur 1",      6, 149.40, "1000ml"),
]

print("\n=== Product matching ===")
for pattern, qty, total, note in LINES:
    # rough search: split into terms, do ilike per term
    terms = [t for t in pattern.split() if len(t) > 2]
    domain = []
    for t in terms:
        domain.append(("name", "ilike", t))
    results = search_read("product.template", domain, ["id", "name", "list_price", "product_variant_ids"], limit=5)
    if not results:
        print(f"  [MISS] {pattern!r} qty={qty}")
        continue
    print(f"  {pattern!r} qty={qty} total={total} ({note})")
    for r in results[:3]:
        print(f"     -> tmpl id={r['id']} name={r['name']!r} list_price={r['list_price']}")
