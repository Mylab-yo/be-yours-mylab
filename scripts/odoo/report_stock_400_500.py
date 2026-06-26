"""Etat des stocks Odoo pour les produits au format 400 ml et 500 ml.

Lecture seule. Affiche qty_available (physique), virtual_available (previsionnel),
incoming/outgoing pour chaque produit stockable dont le nom ou le SKU evoque
une contenance de 400 ou 500 ml.

  python report_stock_400_500.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _client as odoo  # noqa: E402

# Match "400ml", "400 ml", "-400-ml", "400ML" ... pour 400 et 500
PAT = re.compile(r"(?<!\d)(400|500)\s*-?\s*ml\b", re.IGNORECASE)


def fmt_qty(v):
    return f"{v:g}" if v is not None else "-"


def main():
    rows = odoo.search_read(
        "product.product",
        [("is_storable", "=", True)],
        ["default_code", "name", "qty_available", "virtual_available",
         "incoming_qty", "outgoing_qty", "uom_id"],
        limit=2000,
    )

    sel = []
    for p in rows:
        hay = f"{p.get('name') or ''} {p.get('default_code') or ''}"
        m = PAT.search(hay)
        if m:
            sel.append((m.group(1), p))

    sel.sort(key=lambda x: (x[0], x[1].get("name") or ""))

    if not sel:
        print("Aucun produit stockable 400/500 ml trouve.")
        return

    print(f"=== Etat des stocks — formats 400 ml & 500 ml ({len(sel)} produits) ===\n")
    hdr = f"{'Format':<7} {'SKU':<34} {'Dispo':>7} {'Prev.':>7} {'Entr.':>7} {'Sort.':>7}  Nom"
    print(hdr)
    print("-" * len(hdr))
    cur = None
    for fmt, p in sel:
        if fmt != cur:
            cur = fmt
        sku = (p.get("default_code") or "").strip() or "(sans SKU)"
        name = (p.get("name") or "").strip()
        print(f"{fmt:<7} {sku:<34} "
              f"{fmt_qty(p.get('qty_available')):>7} "
              f"{fmt_qty(p.get('virtual_available')):>7} "
              f"{fmt_qty(p.get('incoming_qty')):>7} "
              f"{fmt_qty(p.get('outgoing_qty')):>7}  {name[:50]}")

    # Recap par format
    print("\n--- Recap par format ---")
    for fmt in ("400", "500"):
        grp = [p for f, p in sel if f == fmt]
        tot = sum((p.get("qty_available") or 0) for p in grp)
        tot_prev = sum((p.get("virtual_available") or 0) for p in grp)
        rupture = sum(1 for p in grp if (p.get("qty_available") or 0) <= 0)
        print(f"  {fmt} ml : {len(grp)} produits | dispo total {tot:g} | previsionnel {tot_prev:g} | {rupture} en rupture (<=0)")


if __name__ == "__main__":
    main()
