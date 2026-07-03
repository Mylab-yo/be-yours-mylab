"""Conditionne 300 flacons 200ml par gamme (OF Bulk -> flacon), termines (done).

But : afficher du stock POSITIF sur les finis (deja commandables via backorder).
Consomme le vrac (0.2 kg/flacon) + 1 flacon 200 + 1 bouchon 24 par unite.

ATTENTION : le vrac est encore sous lot provisoire 'A-RECEPTIONNER-2026-07' (marchandise
pas physiquement recue) -> ce stock de flacons est ANTICIPE/theorique tant que l'atelier
n'a pas reellement conditionne. Assume par Yoann (03/07).

Finis (tracking=lot) : lot fini provisoire 'COND-2026-07' (un par produit).
Sortie fini -> MYVO/Stock/Fini (loc 47).

Pattern canonique (memory feedback-odoo-mrp-xmlrpc-lot-production) :
  create -> action_confirm -> action_assign -> write(qty_producing,lot_producing_id)
  -> picked=True sur move_raw_ids -> button_mark_done{skip_backorder}
Idempotent : saute si un OF non annule (qty 300, ce produit, cette BoM) existe deja.
"""
import _client as odoo

QTY = 300.0
LOT_FINI = "COND-2026-07"
FINISHED_LOCATION_ID = 47  # MYVO/Stock/Fini

# (variant fini, BoM, label)
OFS = [
    {"pid": 2401, "bom": 16, "label": "purifiant 200ml"},
    {"pid": 2396, "bom": 1,  "label": "nourrissant 200ml"},
    {"pid": 2377, "bom": 22, "label": "gel douche 200ml"},
    {"pid": 2390, "bom": 66, "label": "dejaunisseur 200ml"},
]


def get_or_create_lot(pid):
    ids = odoo.search("stock.lot", [("name", "=", LOT_FINI), ("product_id", "=", pid)])
    if ids:
        return ids[0]
    return odoo.create("stock.lot", {"name": LOT_FINI, "product_id": pid})


def main():
    for cfg in OFS:
        existing = odoo.search_read(
            "mrp.production",
            [("product_id", "=", cfg["pid"]), ("product_qty", "=", QTY),
             ("bom_id", "=", cfg["bom"]),
             ("state", "in", ["draft", "confirmed", "progress", "to_close", "done"])],
            ["name", "state"],
        )
        if existing:
            e = existing[0]
            print(f"[skip] {cfg['label']} : OF deja present {e['name']} (state={e['state']})")
            continue

        lot_id = get_or_create_lot(cfg["pid"])
        mo_id = odoo.create("mrp.production", {
            "product_id": cfg["pid"], "product_qty": QTY,
            "bom_id": cfg["bom"], "product_uom_id": 1,
        })
        odoo.execute("mrp.production", "action_confirm", [[mo_id]])
        odoo.execute("mrp.production", "action_assign", [[mo_id]])
        odoo.execute("mrp.production", "write",
                     [[mo_id], {"qty_producing": QTY, "lot_producing_id": lot_id}])

        mo = odoo.search_read("mrp.production", [("id", "=", mo_id)],
                              ["name", "move_raw_ids", "move_finished_ids"])[0]

        # Diagnostic reservation composants
        raws = odoo.search_read("stock.move", [("id", "in", mo["move_raw_ids"])],
                                ["product_id", "product_uom_qty", "quantity", "state"])
        for r in raws:
            print(f"    raw {r['product_id'][1]:<38} besoin={r['product_uom_qty']:g} "
                  f"reserve={r.get('quantity')} state={r['state']}")

        # Piege cle : prelevement + destination fini
        odoo.execute("stock.move", "write", [mo["move_raw_ids"], {"picked": True}])
        odoo.execute("stock.move", "write",
                     [mo["move_finished_ids"], {"location_dest_id": FINISHED_LOCATION_ID}])

        odoo.execute("mrp.production", "button_mark_done", [[mo_id]],
                     {"context": {"skip_backorder": True}})

        st = odoo.search_read("mrp.production", [("id", "=", mo_id)], ["name", "state"])[0]
        qa = odoo.search_read("product.product", [("id", "=", cfg["pid"])],
                              ["name", "qty_available"])[0]
        print(f"[done] {st['name']} state={st['state']} -> {qa['name']} "
              f"qty_available={qa['qty_available']:g}\n")

    # Recap vrac restant
    print("=== Vrac restant apres conditionnement ===")
    BULK = {2519: "purifiant", 2514: "nourrissant", 2521: "gel douche", 2545: "dejaunisseur"}
    for p in sorted(odoo.search_read("product.product", [("id", "in", list(BULK))],
                                     ["id", "qty_available"]), key=lambda x: x["id"]):
        print(f"  {BULK[p['id']]:<14} {p['qty_available']:g} kg")


if __name__ == "__main__":
    main()
