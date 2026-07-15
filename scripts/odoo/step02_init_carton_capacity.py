"""Bootstrap historique (avril 2026) : init x_carton_capacity par parsing des noms.

!!! PERIME — NE PAS REJOUER SANS RELIRE CE BLOC. Exige --force depuis le 15/07/2026.

Ce script etait le seed initial. Le colisage a depuis diverge en LIVE parce que la
capacite carton depend du FLACON, pas du nom du produit — ce que le parsing de nom
ne peut pas savoir. Le rejouer tel quel DETRUIRAIT silencieusement :

- 50ml serum/huile : LIVE=69, ce script=50        (cf. set_carton_capacity_flacons_pompes.py)
- coloristeur/gloss/dejaunisseur platine 200ml : LIVE=35, ce script=24 (masques) ou 40 (shampoings)
- les 8 references 100ml (LIVE=63) : aucune regle ne matche -> ce script les mettrait a 0
- masque silver care 200ml (LIVE=54) -> 24 ; shampoing hydratant / silver glow 200ml (LIVE=80) -> 40
- masque nourrissant 100ml (LIVE=80) -> 0

La source de verite du colisage est desormais :
- set_carton_capacity_flacons_pompes.py  (flacons pompe 200ml = 35, verre ambre 50ml = 69)
- les valeurs saisies a la main dans Odoo pour les gammes marque blanche
- PARTNER_PRODUCT_CARTON dans server_action_code.py pour les colisages negocies par client

Mapping d'origine (conserve pour memoire, PLUS a jour) :
- 50ml sérum/huile           -> 50
- 200ml masque               -> 24
- 400ml masque               -> 24
- 200ml shampoing/crème      -> 40
- 500ml shampoing/crème      -> 23
- 1000ml shampoing/masque    -> 12
- autres (pack, coffret...)  -> 0

Writes a CSV log for manual review.
"""
import csv
import re
import sys
from pathlib import Path
from scripts.odoo._client import search_read, write

OUT_CSV = Path("scripts/odoo/init_carton_capacity.csv")


def detect_capacity(name: str) -> tuple[int, str]:
    """Return (capacity, reason) based on product name."""
    n = name.lower()

    # Size detection
    has_50ml = bool(re.search(r"\b50\s*ml\b", n))
    has_200ml = bool(re.search(r"\b200\s*ml\b", n))
    has_400ml = bool(re.search(r"\b400\s*ml\b", n))
    has_500ml = bool(re.search(r"\b500\s*ml\b", n))
    has_1l = bool(re.search(r"\b(1000\s*ml|1\s*l)\b", n))

    # Type detection (keyword match)
    is_masque = "masque" in n
    is_serum_huile = ("sérum" in n or "serum" in n or "huile" in n)
    is_shamp_creme = ("shampoing" in n or "shampooing" in n or
                      "crème" in n or "creme" in n or "spray" in n)
    # Leave-in products behave like shampoing/creme (family 40) not masque (family 24)
    is_sans_rincage = ("sans rinçage" in n or "sans rincage" in n)

    # Exclusions: packs, coffrets, testeurs, duo, trio
    if any(k in n for k in ["pack", "coffret", "testeur", "duo", "trio"]):
        return (0, "exclusion: pack/coffret/testeur/duo/trio")

    if has_50ml and is_serum_huile:
        return (50, "50ml serum/huile")
    # Masque sans rinçage 200ml -> famille 40 (avant la règle masque générique)
    if has_200ml and is_masque and is_sans_rincage:
        return (40, "200ml masque sans rinçage (famille shampoing)")
    if has_200ml and is_masque:
        return (24, "200ml masque")
    if has_400ml and is_masque:
        return (24, "400ml masque")
    if has_200ml and is_shamp_creme:
        return (40, "200ml shampoing/creme/spray")
    if has_500ml and is_shamp_creme:
        return (23, "500ml shampoing/creme")
    if has_1l and (is_shamp_creme or is_masque):
        return (12, "1L shampoing/creme/masque")

    return (0, "no rule matched")


def main():
    products = search_read("product.template",
                           [("sale_ok", "=", True)],
                           ["id", "name", "default_code", "x_carton_capacity"])
    print(f"Loaded {len(products)} products")

    rows = []
    to_update_by_capacity: dict[int, list[int]] = {}

    for p in products:
        cap, reason = detect_capacity(p["name"])
        current = p.get("x_carton_capacity") or 0
        changed = (cap != current)
        rows.append({
            "id": p["id"],
            "sku": p.get("default_code") or "",
            "name": p["name"],
            "current": current,
            "new": cap,
            "reason": reason,
            "changed": "YES" if changed else "",
        })
        if changed:
            to_update_by_capacity.setdefault(cap, []).append(p["id"])

    # Write CSV log
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "sku", "name", "current",
                                          "new", "reason", "changed"])
        w.writeheader()
        w.writerows(rows)
    print(f"Log written: {OUT_CSV}")

    # Batch updates
    for cap, ids in to_update_by_capacity.items():
        write("product.template", ids, {"x_carton_capacity": cap})
        print(f"  Set capacity={cap} on {len(ids)} products")

    # Summary
    counts = {}
    for r in rows:
        counts[r["new"]] = counts.get(r["new"], 0) + 1
    print("\nSummary:")
    for cap in sorted(counts):
        print(f"  capacity={cap}: {counts[cap]} products")


if __name__ == "__main__":
    if "--force" not in sys.argv:
        print(__doc__)
        print("ABANDON : script perime. Relire le bloc ci-dessus, puis --force si "
              "tu es certain de vouloir re-seeder par parsing de nom.")
        sys.exit(1)
    main()
