"""Preview the 17 lines with pricelist id=3 logic, flag data issues."""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read

PL_ID = 3
DISCOUNT_PCT = 15.0  # global discount on top of pricelist

# (variant_id, qty, label_display, wp_price_ht_per_unit)
LINES = [
    (2396, 24, "Shampoing Nourrissant 200ml",                151.20/24),
    (2399, 12, "Shampoing Protecteur de Couleur 200ml",      79.80/12),
    (2357, 24, "Masque Nourrissant 200ml",                   205.20/24),
    (2314, 12, "Crème Boucles 200ml",                        96.60/12),
    (2405, 12, "Spray Texturisant 200ml",                    84.00/12),
    (2390, 12, "Shampoing Déjaunisseur Platine 200ml",       85.20/12),
    (2349, 12, "Masque Déjaunisseur Platine 200ml",          109.20/12),
    (2384, 24, "Shampoing Coloristeur Blond Soleil 200ml",   162.00/24),
    (2343, 12, "Masque Coloristeur Blond Soleil 200ml",      109.20/12),
    (2427,  8, "Shampoing Nourrissant 1L",                   199.20/8),
    (2444,  6, "Masque Nourrissant 1L",                      197.40/6),
    (2429,  6, "Shampoing Purifiant 1L",                     149.40/6),
    (2436,  6, "Shampoing Déjaunisseur Platine 1L",          173.40/6),
    (2452,  4, "Masque Déjaunisseur Platine 1L",             139.60/4),
    (2431,  2, "Shampoing Coloristeur Blond Soleil 1L",      57.80/2),
    (2447,  3, "Masque Coloristeur Blond Soleil 1L",         104.70/3),
    (2428,  6, "Shampoing Protecteur de Couleur 1L",         149.40/6),
]


def get_pl_price(vid, qty, list_price):
    """Get the pricelist tier price for variant at qty, filtering contamination."""
    items = search_read("product.pricelist.item",
                        [("pricelist_id", "=", PL_ID),
                         ("product_id", "=", vid),
                         ("compute_price", "=", "fixed")],
                        ["min_quantity", "fixed_price"], limit=50)
    if not items:
        # fallback to template-level
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
    # Filter contamination: keep only rules with fixed_price >= list_price * 0.4
    # AND <= list_price * 1.5 (degressive can't make price HIGHER than list)
    clean = [it for it in items
             if it["fixed_price"] >= list_price * 0.4
             and it["fixed_price"] <= list_price * 1.2]
    if not clean:
        # No clean rule found
        return list_price, f"list (contaminated rules ignored)"
    # Sort by min_quantity ASC, pick highest min_qty <= qty
    clean.sort(key=lambda x: x["min_quantity"])
    chosen = None
    for it in clean:
        if it["min_quantity"] <= qty:
            chosen = it
    if chosen is None:
        # qty below smallest tier - use list_price
        return list_price, "list (qty < smallest tier)"
    return chosen["fixed_price"], f"tier @{int(chosen['min_quantity'])}"


# Get list_prices
vids = [l[0] for l in LINES]
prods = search_read("product.product", [("id", "in", vids)],
                    ["id", "name", "list_price"], limit=50)
prod_by_id = {p["id"]: p for p in prods}

print(f"=== Preview new invoice — LA TRESSE PARISIENNE ===")
print(f"Pricelist id={PL_ID} + global discount {DISCOUNT_PCT}%\n")
print(f"{'Product':<45} {'Qty':>4} {'List':>6} {'WP':>6} {'PL':>6}  {'PL-after-disc':>13} {'Total HT':>10}  {'Source'}")
print("-" * 130)

total_ht = 0.0
final_lines = []
flags = []
for vid, qty, label, wp_unit in LINES:
    list_p = prod_by_id[vid]["list_price"]
    pl_price, source = get_pl_price(vid, qty, list_p)
    after_disc = pl_price * (1 - DISCOUNT_PCT / 100)
    line_total = after_disc * qty
    total_ht += line_total
    final_lines.append((vid, qty, label, pl_price, line_total))
    flag = ""
    if list_p > 30 and qty < 8:
        # likely wrong list_price (200ml at >30€ unrealistic)
        flag = " ⚠️ LIST=42€"
        flags.append(label)
    if "contaminated" in source or "no rules" in source:
        flag += " ⚠️"
    print(f"{label:<45} {qty:>4} {list_p:>6.2f} {wp_unit:>6.2f} {pl_price:>6.2f}  {after_disc:>13.2f} {line_total:>10.2f}  {source}{flag}")

print("-" * 130)
total_ttc = total_ht * 1.20
print(f"\nTotal HT après remise 15%: {total_ht:.2f} €")
print(f"TVA 20%: {total_ht * 0.20:.2f} €")
print(f"Total TTC: {total_ttc:.2f} €")
print(f"\n[vs WP] WP total HT (avant remise): 2253.30 / TTC: 2325.26 €")

if flags:
    print(f"\n⚠️ Produits avec list_price suspect :")
    for f in flags:
        print(f"   - {f}")
