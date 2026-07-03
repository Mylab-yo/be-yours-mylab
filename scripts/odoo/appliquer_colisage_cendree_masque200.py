# -*- coding: utf-8 -*-
"""Applique 'Repartir en cartons' sur les 2 pickings Cendree ouverts et verifie
le colisage 36 u/carton du masque nourrissant 200ml.

Ne valide RIEN (pas de mouvement de stock) : cree/organise seulement les colis
(stock.quant.package) et les move.line. Rejouable a volonte (l'action purge et
reconstruit les colis auto a chaque passage).
"""
from collections import defaultdict
import _client as odoo

ACTION_NAME = "Répartir en cartons"
PICKINGS = ["MYVO/OUT/00171", "MYVO/OUT/00186"]   # S00493 (700u) + S00626 (2000u)
MASQUE_200_CODE = "masque-nourrissant-200-ml"

sa_id = odoo.search("ir.actions.server", [("name", "=", ACTION_NAME)])[0]


def dump_packages(pid, tag):
    mls = odoo.search_read(
        "stock.move.line", [("picking_id", "=", pid)],
        ["product_id", "quantity", "result_package_id"])
    # regroupe par colis
    by_pkg = defaultdict(lambda: defaultdict(float))
    loose = defaultdict(float)
    for ml in mls:
        pname = ml["product_id"][1]
        if ml.get("result_package_id"):
            by_pkg[ml["result_package_id"][1]][pname] += ml["quantity"]
        else:
            loose[pname] += ml["quantity"]
    print(f"\n  --- {tag} : {len(by_pkg)} colis" + (f" + hors-colis" if loose else "") + " ---")
    # tri par nom de colis
    for pkg in sorted(by_pkg):
        contents = ", ".join(f"{q:g}x {n[:32]}" for n, q in sorted(by_pkg[pkg].items()))
        print(f"    [{pkg}] {contents}")
    for n, q in sorted(loose.items()):
        print(f"    (hors colis) {q:g}x {n}")
    return by_pkg


def masque_carton_stats(by_pkg):
    # taille de chaque colis contenant du masque 200ml
    sizes = []
    for pkg, contents in by_pkg.items():
        for n, q in contents.items():
            if "200ml" in n.lower().replace(" ", "") and "masque" in n.lower():
                sizes.append(int(round(q)))
    return sizes


for name in PICKINGS:
    pk = odoo.search_read("stock.picking", [("name", "=", name)],
                          ["id", "name", "state", "partner_id", "origin"])[0]
    pid = pk["id"]
    print(f"\n========== {pk['name']} (id={pid}) state={pk['state']} "
          f"partner={pk['partner_id'][1]} origin={pk['origin']} ==========")

    # quantite masque 200ml sur le picking
    moves = odoo.search_read("stock.move", [("picking_id", "=", pid)],
                             ["product_id", "product_uom_qty", "quantity"])
    for m in moves:
        if m["product_id"][1] and MASQUE_200_CODE.replace("-", "") in \
                m["product_id"][1].lower().replace(" ", "").replace("-", ""):
            print(f"  masque 200ml : demande={m['product_uom_qty']:g} reserve={m['quantity']:g}")

    dump_packages(pid, "AVANT")

    odoo.execute("ir.actions.server", "run", [[sa_id]],
                 {"context": {"active_model": "stock.picking",
                              "active_ids": [pid], "active_id": pid}})

    by_pkg = dump_packages(pid, "APRES")
    sizes = masque_carton_stats(by_pkg)
    if sizes:
        full = sum(1 for s in sizes if s == 36)
        partial = [s for s in sizes if s != 36]
        print(f"\n  >>> masque 200ml : {len(sizes)} colis | {full} pleins (36u)"
              + (f" | dernier partiel = {partial}" if partial else " | tous pleins"))
        print(f"  >>> total unites masque 200ml en colis = {sum(sizes)}")
