"""Compute pricelist id=3 prices for the 17 La Tresse Parisienne lines."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute

PRICELIST_ID = 3
PARTNER_ID = 1074

# (template_id, variant_search, qty, label, wp_total_ht)
LINES = [
    (2350, "shampoing nourrissant 200ml",            24, "Shampoing Nourrissant 200ml x24", 151.20),
    (2353, "shampoing protecteur de couleur 200ml",  12, "Shampoing Protecteur Couleur 200ml x12", 79.80),
    (2311, "masque nourrissant 200ml",               24, "Masque Nourrissant 200ml x24", 205.20),
    (2268, "creme boucles 200ml",                    12, "Crème Boucles 200ml x12", 96.60),
    (2359, "spray texturisant 200ml",                12, "Spray Texturisant 200ml x12", 84.00),
    (2344, "shampoing dejaunisseur platine 200ml",   12, "Shampoing Déjaunisseur Platine 200ml x12", 85.20),
    (2303, "masque dejaunisseur platine 200ml",      12, "Masque Déjaunisseur Platine 200ml x12", 109.20),
    (2338, "shampoing coloristeur blond soleil 200ml", 24, "Shampoing Coloristeur Blond Soleil 200ml x24", 162.00),
    (2297, "masque coloristeur blond soleil 200ml",  12, "Masque Coloristeur Blond Soleil 200ml x12", 109.20),
    (2381, "shampoing nourrissant 1000ml",            8, "Shampoing Nourrissant 1L", 199.20),
    (2398, "masque nourrissant 1000ml",               6, "Masque Nourrissant 1L", 197.40),
    (2383, "shampoing purifiant 1000ml",              6, "Shampoing Purifiant 1L", 149.40),
    (2390, "shampoing dejaunisseur platine 1000ml",   6, "Shampoing Déjaunisseur Platine 1L", 173.40),
    (2406, "masque dejaunisseur platine 1000ml",      4, "Masque Déjaunisseur Platine 1L", 139.60),
    (2385, "shampoing coloristeur blond soleil 1000ml", 2, "Shampoing Coloristeur Blond Soleil 1L", 57.80),
    (2401, "masque coloristeur blond soleil 1000ml",  3, "Masque Coloristeur Blond Soleil 1L", 104.70),
    (2382, "shampoing protecteur de couleur 1000ml",  6, "Shampoing Protecteur de Couleur 1L", 149.40),
]

print(f"=== Pricelist id={PRICELIST_ID} probe ===")
pl = search_read("product.pricelist", [("id", "=", PRICELIST_ID)],
                 ["id", "name", "currency_id"], limit=1)
print(f"  {pl}")

# Get variant ids from templates
print("\n=== Resolve variant ids ===")
variants_map = {}  # tmpl_id -> variant_id
for tmpl_id, _, qty, label, _ in LINES:
    res = search_read("product.product", [("product_tmpl_id", "=", tmpl_id)],
                      ["id", "name", "default_code", "list_price"], limit=2)
    if not res:
        print(f"  [MISS] tmpl_id={tmpl_id}")
        continue
    variants_map[tmpl_id] = res[0]["id"]
    print(f"  tmpl {tmpl_id} -> variant {res[0]['id']} ({res[0]['name']!r}) list={res[0]['list_price']}")

# Use product.pricelist._get_product_price (Odoo 18 API)
print("\n=== Pricelist prices (using _get_product_price) ===")
print(f"{'Product':<55} {'qty':>4} {'PL price':>10} {'×qty':>10} {'WP HT':>10}")
print("-" * 100)
total_pl = 0
total_wp = 0
results = []
for tmpl_id, _, qty, label, wp_total in LINES:
    variant_id = variants_map.get(tmpl_id)
    if not variant_id:
        continue
    # _get_product_price expects (product, quantity, currency=None, date=None, **kwargs)
    try:
        price = execute("product.pricelist", "_get_product_price",
                        [[PRICELIST_ID], variant_id, qty])
    except Exception as e:
        # Try alternative method names
        try:
            price = execute("product.pricelist", "_compute_price_rule",
                            [[PRICELIST_ID], [(variant_id, qty, False)]])
        except Exception as e2:
            print(f"  [ERR] {label}: {e2}")
            continue
    line_total = price * qty
    total_pl += line_total
    total_wp += wp_total
    print(f"{label:<55} {qty:>4} {price:>10.2f} {line_total:>10.2f} {wp_total:>10.2f}")
    results.append((tmpl_id, variant_id, qty, label, price, line_total, wp_total))

print("-" * 100)
print(f"{'TOTAL':<55} {'':>4} {'':>10} {total_pl:>10.2f} {total_wp:>10.2f}")
print(f"\nDiff WP - PL = {total_wp - total_pl:+.2f}€")
print(f"With 15% discount: PL total HT = {total_pl * 0.85:.2f}€ → TTC = {total_pl * 0.85 * 1.20:.2f}€")
print(f"WP total HT (after 14% discount) = {2253.30 - 315.58:.2f}€ → TTC = {(2253.30 - 315.58) * 1.20:.2f}€")
