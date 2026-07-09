"""Reset du stock produits finis avant le seed d'inventaire initial (step37).

PRECONDITION du passage en suivi par lot : l'inventaire physique recompte (CSV)
devient la source de verite. On remet a zero le stock fini existant (sale, avec
negatifs, a l'emplacement MYVO/Stock parent), PUIS on active tracking='lot' sur
les produits finis, PUIS step37 applique les comptages avec lots a MYVO/Stock/Fini.

Idempotent. Ne touche PAS aux vracs (deja lot) ni au packaging (reste tracking=none).
Le bulk est vierge (0), aucun reset necessaire cote vrac.
"""
from collections import Counter
from scripts.odoo._client import execute, search_read


def main():
    # 1. Produits finis (-ml)
    prods = search_read("product.product", [("default_code", "like", "-ml")],
                        ["id", "product_tmpl_id", "default_code"])
    pids = [p["id"] for p in prods]
    tmpls = sorted({p["product_tmpl_id"][0] for p in prods})
    print(f"Produits finis: {len(prods)} / templates: {len(tmpls)}")

    # 2. Emplacements internes MYVO
    locs = search_read("stock.location",
                       [("complete_name", "like", "MYVO/Stock"), ("usage", "=", "internal")],
                       ["id", "complete_name"])
    locids = [l["id"] for l in locs]

    # 3. Remettre a zero les quants finis non nuls
    quants = search_read("stock.quant",
                         [("product_id", "in", pids), ("location_id", "in", locids)],
                         ["id", "quantity"])
    to_zero = [q for q in quants if abs(q["quantity"]) > 1e-6]
    print(f"Quants finis non nuls a remettre a zero: {len(to_zero)}")
    for q in to_zero:
        execute("stock.quant", "write", [[q["id"]], {"inventory_quantity": 0}])
        execute("stock.quant", "action_apply_inventory", [[q["id"]]])

    # verif
    after = search_read("stock.quant",
                        [("product_id", "in", pids), ("location_id", "in", locids)],
                        ["quantity"])
    print(f"On-hand finis total apres reset: {sum(q['quantity'] for q in after):.0f}")

    # 4. Activer le suivi par lot (tracking_disable pour contourner le bug mail _track_prepare)
    execute("product.template", "write", [tmpls, {"tracking": "lot"}],
            {"context": {"tracking_disable": True}})
    chk = search_read("product.product", [("default_code", "like", "-ml")], ["tracking"])
    print("Tracking finis apres:", dict(Counter(c["tracking"] for c in chk)))


if __name__ == "__main__":
    main()
