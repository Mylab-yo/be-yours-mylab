"""Create draft invoice for LA TRESSE PARISIENNE (MARISOL SUAREZ).

Replaces WP invoice MYLAB2196 (order 300582 / 2025-11-17).
- Partner id=1074
- Pricelist id=3 (TARIFS DEGRESSIFS MYLAB), tier prices computed manually
- Global discount 15% per line
- TVA 20% G (tax id=103)
- Date 2025-11-17
- Override Spray Texturisant 200ml to list_price (7.90€)
- Fix list_price of Shampoing Protecteur de Couleur 200ml to 7€ before computing
"""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, create, write

PL_ID = 3
PARTNER_ID = 1074
COMPANY_ID = 3
TAX_ID = 103  # TVA 20% G
DISCOUNT_PCT = 15.0
INVOICE_DATE = "2025-11-17"
WP_REF = "MYLAB2196 / order WP 300582"

# Step 1: Fix list_price bug on Shampoing Protecteur de Couleur 200ml
TMPL_PROTECTEUR_COULEUR_200 = 2353
print("=== Step 1: Fix list_price bug ===")
before = search_read("product.template", [("id", "=", TMPL_PROTECTEUR_COULEUR_200)],
                    ["id", "name", "list_price"], limit=1)
print(f"  Before: tmpl {before[0]['id']} {before[0]['name']!r} list_price={before[0]['list_price']}")
if before[0]["list_price"] != 7.0:
    write("product.template", [TMPL_PROTECTEUR_COULEUR_200], {"list_price": 7.00})
    after = search_read("product.template", [("id", "=", TMPL_PROTECTEUR_COULEUR_200)],
                       ["id", "list_price"], limit=1)
    print(f"  After:  tmpl {after[0]['id']} list_price={after[0]['list_price']}")
else:
    print("  Already 7.00, skip")

# Step 2: Line definitions with manual price overrides
# (variant_id, qty, override_price_unit_or_None, label)
LINES = [
    (2396, 24, None,  "Shampoing Nourrissant 200ml"),
    (2399, 12, None,  "Shampoing Protecteur de Couleur 200ml"),
    (2357, 24, None,  "Masque Nourrissant 200ml"),
    (2314, 12, None,  "Crème Boucles 200ml"),
    (2405, 12, 7.90,  "Spray Texturisant 200ml (override list_price)"),
    (2390, 12, None,  "Shampoing Déjaunisseur Platine 200ml"),
    (2349, 12, None,  "Masque Déjaunisseur Platine 200ml"),
    (2384, 24, None,  "Shampoing Coloristeur Blond Soleil 200ml"),
    (2343, 12, None,  "Masque Coloristeur Blond Soleil 200ml"),
    (2427,  8, None,  "Shampoing Nourrissant 1L"),
    (2444,  6, None,  "Masque Nourrissant 1L"),
    (2429,  6, None,  "Shampoing Purifiant 1L"),
    (2436,  6, None,  "Shampoing Déjaunisseur Platine 1L"),
    (2452,  4, None,  "Masque Déjaunisseur Platine 1L"),
    (2431,  2, None,  "Shampoing Coloristeur Blond Soleil 1L"),
    (2447,  3, None,  "Masque Coloristeur Blond Soleil 1L"),
    (2428,  6, None,  "Shampoing Protecteur de Couleur 1L"),
]


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
        return list_price
    # Filter contamination
    clean = [it for it in items
             if it["fixed_price"] >= list_price * 0.4
             and it["fixed_price"] <= list_price * 1.2]
    if not clean:
        return list_price
    clean.sort(key=lambda x: x["min_quantity"])
    chosen = None
    for it in clean:
        if it["min_quantity"] <= qty:
            chosen = it
    if chosen is None:
        return list_price
    return chosen["fixed_price"]


# Step 3: Get fresh list_prices (after the fix)
print("\n=== Step 3: Compute prices ===")
vids = [l[0] for l in LINES]
prods = search_read("product.product", [("id", "in", vids)],
                    ["id", "name", "list_price"], limit=50)
prod_by_id = {p["id"]: p for p in prods}

invoice_line_vals = []
total_check = 0
print(f"{'Product':<50} {'Qty':>4} {'Unit':>7} {'Disc%':>6} {'LineHT':>10}")
print("-" * 90)
for vid, qty, override, label in LINES:
    list_p = prod_by_id[vid]["list_price"]
    if override is not None:
        unit = override
    else:
        unit = get_pl_price(vid, qty, list_p)
    line_total_after = unit * qty * (1 - DISCOUNT_PCT / 100)
    total_check += line_total_after
    print(f"{label:<50} {qty:>4} {unit:>7.2f} {DISCOUNT_PCT:>6.1f} {line_total_after:>10.2f}")
    invoice_line_vals.append((0, 0, {
        "product_id": vid,
        "quantity": qty,
        "price_unit": unit,
        "discount": DISCOUNT_PCT,
        "tax_ids": [(6, 0, [TAX_ID])],
    }))
print("-" * 90)
print(f"Total HT après remise: {total_check:.2f} €")
print(f"TVA 20%: {total_check * 0.20:.2f} €")
print(f"Total TTC: {total_check * 1.20:.2f} €")

# Step 4: Create draft invoice
print("\n=== Step 4: Create draft invoice ===")

# Find sales journal
journals = search_read("account.journal",
                       [("type", "=", "sale"), ("company_id", "=", COMPANY_ID)],
                       ["id", "name", "code"], limit=5)
print(f"  Sales journals available: {journals}")
journal_id = journals[0]["id"]

invoice_vals = {
    "move_type": "out_invoice",
    "partner_id": PARTNER_ID,
    "invoice_date": INVOICE_DATE,
    "company_id": COMPANY_ID,
    "journal_id": journal_id,
    "ref": WP_REF,
    "narration": (
        f"Facture régularisation remplaçant {WP_REF}. "
        f"Tarifs corrigés selon pricelist 'TARIFS DEGRESSIFS MYLAB' + remise 15%."
    ),
    "invoice_line_ids": invoice_line_vals,
}

invoice_id = create("account.move", invoice_vals)
print(f"  ✓ Created draft invoice id={invoice_id}")

# Read back to confirm
inv = search_read("account.move", [("id", "=", invoice_id)],
                  ["name", "state", "partner_id", "invoice_date",
                   "amount_untaxed", "amount_tax", "amount_total", "ref"], limit=1)
print(f"\n=== Invoice created ===")
print(f"  ID: {invoice_id}")
print(f"  Name: {inv[0]['name']}")
print(f"  State: {inv[0]['state']}")
print(f"  Partner: {inv[0]['partner_id']}")
print(f"  Date: {inv[0]['invoice_date']}")
print(f"  Ref: {inv[0]['ref']}")
print(f"  HT: {inv[0]['amount_untaxed']:.2f} €")
print(f"  TVA: {inv[0]['amount_tax']:.2f} €")
print(f"  TTC: {inv[0]['amount_total']:.2f} €")
print(f"\n👉 Open in Odoo: https://odoo.startec-paris.com/odoo/action-account.action_move_out_invoice_type/{invoice_id}")
