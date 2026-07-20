# -*- coding: utf-8 -*-
"""Repointe les stock.move des lignes BULK vers MYVO/Stock/Bulk (45).

Dry-run par defaut. --apply pour ecrire (ajoute en Task 3).
Idempotent : skip un move deja sur 45 ou un picking done/cancel.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # scripts/odoo
sys.path.insert(0, os.path.dirname(__file__))                   # stock_bulk
from _client import search_read, execute
from classify_bulk import classify_line

LOC_BULK = 45   # MYVO/Stock/Bulk
LOC_FINI = 47   # MYVO/Stock/Fini


def get_order_tags(order):
    tag_ids = order.get("tag_ids") or []
    if not tag_ids:
        return []
    tags = search_read("crm.tag", [("id", "in", tag_ids)], ["name"])
    return [t["name"] for t in tags]


def collect(order_filter=None):
    """Retourne la liste des moves bulk a repointer + les ambigus."""
    domain = [("state", "=", "sale")]
    if order_filter:
        domain.append(("name", "=", order_filter))
    orders = search_read("sale.order", domain,
                         ["id", "name", "tag_ids", "picking_ids"])
    to_route, ambiguous = [], []
    for o in orders:
        tags = get_order_tags(o)
        pickings = search_read("stock.picking",
            [("id", "in", o.get("picking_ids") or []),
             ("state", "not in", ["done", "cancel"])],
            ["id", "name", "state"])
        pick_ids = [p["id"] for p in pickings]
        if not pick_ids:
            continue
        moves = search_read("stock.move",
            [("picking_id", "in", pick_ids), ("state", "not in", ["done", "cancel"])],
            ["id", "product_id", "product_uom_qty", "location_id", "picking_id", "sale_line_id"])
        for mv in moves:
            pname = mv["product_id"][1]
            prod = search_read("product.product", [("id", "=", mv["product_id"][0])], ["default_code"])
            sku = (prod[0]["default_code"] if prod else "") or ""
            kind, cont, reason = classify_line(pname, sku, mv["product_uom_qty"], tags)
            if kind == "ambiguous":
                ambiguous.append((o["name"], pname, mv["product_uom_qty"]))
            elif kind == "bulk":
                if mv["location_id"][0] == LOC_BULK:
                    continue  # deja route
                to_route.append({
                    "order": o["name"], "move_id": mv["id"], "product": pname,
                    "qty": mv["product_uom_qty"], "from_loc": mv["location_id"][1],
                    "reason": reason,
                })
    return to_route, ambiguous


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--order", default=None, help="Limiter a une commande (ex: S00626)")
    args = ap.parse_args()

    to_route, ambiguous = collect(args.order)

    print(f"=== MOVES BULK A REPOINTER vers Bulk(45) : {len(to_route)} ===")
    for r in to_route:
        print(f"  {r['order']:8} move {r['move_id']:6} | {r['product'][:34]:34} "
              f"x{r['qty']:g} | depuis {r['from_loc']} | {r['reason']}")
    if ambiguous:
        print(f"\n=== LIGNES AMBIGUES (contenance inconnue) — A TRAITER MANUELLEMENT : {len(ambiguous)} ===")
        for oname, pname, qty in ambiguous:
            print(f"  {oname:8} | {pname} x{qty:g}")

    if not args.apply:
        print("\n(DRY-RUN — aucun write. Relancer avec --apply apres canari.)")
        return
    raise SystemExit("--apply pas encore implemente (Task 3)")


if __name__ == "__main__":
    main()
