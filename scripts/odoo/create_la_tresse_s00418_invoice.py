"""Create clean invoice for S00418 LA TRESSE PARISIENNE.

Replaces messy SO state. 19 product lines + 3 complement lines.
- Net total HT after global 15% discount and -77.98€ TTC credit from previous payment
- Linked to S00418 via invoice_origin
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, create, write

PARTNER_ID = 1074
COMPANY_ID = 3
TAX_ID = 103  # TVA 20% G
INVOICE_DATE = "2026-06-10"
ORIGIN = "S00418"

# 19 product lines from SO 385 (variant_id, qty, price_unit, label)
PRODUCT_LINES = [
    (2427,  8, 21.00, "shampoing nourrissant 1000ml"),
    (2444,  6, 27.90, "masque nourrissant 1000ml"),
    (2428,  6, 21.00, "shampoing protecteur de couleur 1000ml"),
    # Need to look up shampoing volume 1000ml variant
    (None,  6, 21.00, "shampoing volume 1000ml"),
    (2436,  4, 27.45, "shampoing dejaunisseur platine 1000ml"),
    (2452,  2, 34.90, "masque dejaunisseur platine 1000ml"),
    (2431,  6, 24.50, "shampoing coloristeur blond soleil 1000ml"),
    (2447,  4, 33.15, "masque coloristeur blond soleil 1000ml"),
    (2396, 24,  6.30, "shampoing nourrissant 200ml"),
    (None, 24,  7.65, "creme nourrissante 200ml"),
    (2357, 12,  9.00, "masque nourrissant 200ml"),
    (2399, 12,  6.65, "shampoing protecteur de couleur 200ml"),
    (None, 24,  6.30, "shampoing volume 200ml"),
    (2314, 24,  7.65, "creme boucles 200ml"),
    (2405, 12,  9.40, "spray texturisant 200ml"),
    (None, 24,  8.50, "bain miraculeux 50ml"),
    (None, 24,  8.50, "serum finition ultime 50ml"),
    (2390, 12,  6.65, "shampoing dejaunisseur platine 200ml"),
    (2384, 24,  6.75, "shampoing coloristeur blond soleil 200ml"),
]

# Resolve missing variant IDs by name
print("=== Resolve missing variant IDs ===")
unresolved_names = [(idx, l[3]) for idx, l in enumerate(PRODUCT_LINES) if l[0] is None]
resolved = list(PRODUCT_LINES)
for idx, name in unresolved_names:
    terms = [t for t in name.split() if len(t) > 2 and t.lower() not in ("200ml", "1000ml", "50ml", "1l")]
    domain = []
    for t in terms:
        domain.append(("name", "ilike", t))
    res = search_read("product.product", domain, ["id", "name", "list_price"], limit=3)
    if not res:
        # Loose search
        res = search_read("product.product", [("name", "ilike", name)],
                          ["id", "name", "list_price"], limit=3)
    print(f"  {name!r}:")
    for r in res:
        print(f"    -> id={r['id']} {r['name']!r} list={r['list_price']}")
    if res:
        # Pick the one with matching ml in name
        if "1000ml" in name or "1 L" in name or "1L" in name:
            best = next((r for r in res if "1000" in r["name"]), res[0])
        elif "50ml" in name:
            best = next((r for r in res if "50" in r["name"] and "200" not in r["name"]), res[0])
        elif "200ml" in name:
            best = next((r for r in res if "200" in r["name"]), res[0])
        else:
            best = res[0]
        old = resolved[idx]
        resolved[idx] = (best["id"], old[1], old[2], best["name"])
        print(f"    [picked] id={best['id']} {best['name']!r}")

# Build invoice lines
print("\n=== Build invoice lines ===")
TAX = [(6, 0, [TAX_ID])]
invoice_line_ids = []
total_check_ht = 0.0
seq = 10
for vid, qty, pu, label in resolved:
    if vid is None:
        print(f"  ⚠️ Could not resolve {label!r} - SKIPPING")
        continue
    sub = pu * qty
    total_check_ht += sub
    print(f"  seq={seq:3} {label[:45]:<45} qty={qty:>4} pu={pu:>7.2f} sub={sub:>9.2f}")
    invoice_line_ids.append((0, 0, {
        "sequence": seq,
        "product_id": vid,
        "quantity": qty,
        "price_unit": pu,
        "tax_ids": TAX,
    }))
    seq += 1

# DPD shipping (after 50% discount)
DPD_PRICE = 49.90
DPD_DISCOUNT = 50.0
DPD_NET = DPD_PRICE * (1 - DPD_DISCOUNT / 100)
total_check_ht += DPD_NET
print(f"  seq=100 {'Frais de livraison DPD Classic (-50%)':<45} qty=  1 pu={DPD_PRICE:>7.2f} sub={DPD_NET:>9.2f}")
invoice_line_ids.append((0, 0, {
    "sequence": 100,
    "name": "Frais de livraison DPD Classic - France (remise 50%)",
    "quantity": 1,
    "price_unit": DPD_PRICE,
    "discount": DPD_DISCOUNT,
    "tax_ids": TAX,
}))

# Section "REMISES & AVOIRS"
invoice_line_ids.append((0, 0, {
    "sequence": 200,
    "display_type": "line_section",
    "name": "REMISES",
}))

# Global 15% discount line
REMISE_15 = -404.33
total_check_ht += REMISE_15
print(f"  seq=210 {'Remise globale 15%':<45} qty=  1 pu={REMISE_15:>7.2f} sub={REMISE_15:>9.2f}")
invoice_line_ids.append((0, 0, {
    "sequence": 210,
    "name": "Remise commerciale 15%",
    "quantity": 1,
    "price_unit": REMISE_15,
    "tax_ids": TAX,
}))

# Credit from previous payment (-64.98 HT = -77.98 TTC)
AVOIR_HT = -64.98
total_check_ht += AVOIR_HT
print(f"  seq=220 {'Avoir règlement précédent (devis 300582)':<45} qty=  1 pu={AVOIR_HT:>7.2f} sub={AVOIR_HT:>9.2f}")
invoice_line_ids.append((0, 0, {
    "sequence": 220,
    "name": "Avoir sur règlement précédent (devis 300582 / MYLAB2196)",
    "quantity": 1,
    "price_unit": AVOIR_HT,
    "tax_ids": TAX,
}))

total_ttc = total_check_ht * 1.20
print(f"\n=== Expected totals ===")
print(f"  HT:  {total_check_ht:.2f} €")
print(f"  TVA: {total_check_ht * 0.20:.2f} €")
print(f"  TTC: {total_ttc:.2f} €")

# Find sales journal
journals = search_read("account.journal",
                       [("type", "=", "sale"), ("company_id", "=", COMPANY_ID)],
                       ["id", "name", "code"], limit=5)
journal_id = journals[0]["id"]

invoice_vals = {
    "move_type": "out_invoice",
    "partner_id": PARTNER_ID,
    "invoice_date": INVOICE_DATE,
    "company_id": COMPANY_ID,
    "journal_id": journal_id,
    "invoice_origin": ORIGIN,
    "ref": ORIGIN,
    "narration": (
        f"Facture pour commande {ORIGIN}. "
        f"Remise commerciale 15% appliquée + crédit de 77,98 € TTC issu du "
        f"trop-perçu sur le règlement précédent (devis 300582 / MYLAB2196, payé 2 347,33 € le 11/04/2026)."
    ),
    "invoice_line_ids": invoice_line_ids,
}

print(f"\n=== Create draft invoice ===")
invoice_id = create("account.move", invoice_vals)
print(f"  ✓ Created draft invoice id={invoice_id}")

# Read back
inv = search_read("account.move", [("id", "=", invoice_id)],
                  ["name", "state", "invoice_date",
                   "amount_untaxed", "amount_tax", "amount_total", "ref", "invoice_origin"], limit=1)
print(f"\n=== Invoice created ===")
for k, v in inv[0].items():
    print(f"  {k}: {v}")
print(f"\n👉 https://odoo.startec-paris.com/odoo/action-account.action_move_out_invoice_type/{invoice_id}")
