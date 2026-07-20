# -*- coding: utf-8 -*-
"""Prepare un BL a etre valide EN TOTALITE (sans reliquat) et sans blocage de lot.

Deux causes de galere traitees d'un coup :

1. RELIQUAT NON VOULU — Odoo 17/18 ne regarde pas la quantite saisie mais le flag
   `picked` du stock.move. Si une seule ligne est `picked=True`, Odoo considere que
   les autres n'ont pas ete expediees et propose un reliquat. On met `picked=True`
   sur toutes les lignes ayant une quantite > 0.

2. LOT OBLIGATOIRE — un produit `tracking=lot` refuse la validation si sa move.line
   n'a pas de lot. On affecte un lot existant du produit (en preferant celui qui a
   du stock), sinon on en cree un placeholder identifiable.

Dry-run par defaut. --apply pour ecrire.

Usage :
    python prepare_picking_full.py --picking MYVO/OUT/00218
    python prepare_picking_full.py --picking MYVO/OUT/00218 --apply
    python prepare_picking_full.py --all-ready            # tous les BL prets (dry-run)
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _client import search_read, execute, create

PLACEHOLDER_PREFIX = "A-QUALIFIER-"


def get_pickings(name=None, all_ready=False):
    if name:
        dom = [("name", "=", name)]
    elif all_ready:
        dom = [("state", "=", "assigned"), ("picking_type_id.code", "=", "outgoing")]
    else:
        raise SystemExit("Preciser --picking NOM ou --all-ready")
    return search_read("stock.picking", dom, ["id", "name", "state", "origin"])


def lot_for(product_id, product_name, apply_):
    """Retourne un lot_id utilisable pour ce produit (existant de preference)."""
    lots = search_read("stock.lot", [("product_id", "=", product_id)], ["id", "name"])
    if lots:
        # preferer un lot qui a du stock
        ids = [l["id"] for l in lots]
        quants = search_read("stock.quant",
            [("lot_id", "in", ids), ("quantity", ">", 0)], ["lot_id"])
        if quants:
            lid = quants[0]["lot_id"][0]
            return lid, f"lot existant avec stock ({quants[0]['lot_id'][1]})"
        return lots[0]["id"], f"lot existant ({lots[0]['name']})"
    # aucun lot : en creer un placeholder
    from datetime import date
    name = PLACEHOLDER_PREFIX + date.today().strftime("%Y%m%d")
    if not apply_:
        return None, f"CREERAIT le lot placeholder '{name}'"
    lid = create("stock.lot", {"name": name, "product_id": product_id, "company_id": 3})
    return lid, f"lot placeholder cree '{name}'"


def process(pick, apply_):
    moves = search_read("stock.move", [("picking_id", "=", pick["id"]),
                                       ("state", "not in", ["done", "cancel"])],
        ["id", "product_id", "product_uom_qty", "quantity", "picked"])
    if not moves:
        return 0, 0
    # produits traques
    pids = list({m["product_id"][0] for m in moves})
    tracking = {p["id"]: p["tracking"] for p in
                search_read("product.product", [("id", "in", pids)], ["id", "tracking"])}

    n_picked, n_lots = 0, 0
    print(f"\n--- {pick['name']} (origine {pick.get('origin')}, state={pick['state']}) ---")

    # 1) picked=True sur toutes les lignes avec quantite > 0
    to_pick = [m["id"] for m in moves if (m.get("quantity") or 0) > 0 and not m.get("picked")]
    for m in moves:
        q = m.get("quantity") or 0
        if q > 0 and not m.get("picked"):
            print(f"    picked: {m['product_id'][1][:38]:38} qty={q:g}  False -> True")
    if to_pick:
        n_picked = len(to_pick)
        if apply_:
            execute("stock.move", "write", [to_pick, {"picked": True}])

    # 2) lots manquants sur produits traques
    mls = search_read("stock.move.line", [("picking_id", "=", pick["id"]),
                                          ("state", "not in", ["done", "cancel"])],
        ["id", "product_id", "quantity", "lot_id"])
    for l in mls:
        pid = l["product_id"][0]
        if tracking.get(pid) not in ("lot", "serial"):
            continue
        if l["lot_id"]:
            continue
        lid, why = lot_for(pid, l["product_id"][1], apply_)
        print(f"    lot   : {l['product_id'][1][:38]:38} AUCUN -> {why}")
        n_lots += 1
        if apply_ and lid:
            execute("stock.move.line", "write", [[l["id"]], {"lot_id": lid}])

    if not to_pick and n_lots == 0:
        print("    (rien a corriger)")
    return n_picked, n_lots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--picking", default=None, help="Nom du BL, ex MYVO/OUT/00218")
    ap.add_argument("--all-ready", action="store_true", help="Tous les BL sortants prets")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    picks = get_pickings(args.picking, args.all_ready)
    print(f"=== {len(picks)} BL a traiter ===")
    tp = tl = 0
    for p in picks:
        a, b = process(p, args.apply)
        tp += a; tl += b

    print(f"\n=== BILAN : {tp} ligne(s) passees en 'prelevé', {tl} lot(s) affecte(s) ===")
    if not args.apply:
        print("(DRY-RUN — aucun write. Relancer avec --apply.)")
    else:
        print("Tu peux maintenant cliquer VALIDER dans Odoo : plus de reliquat propose.")


if __name__ == "__main__":
    main()
