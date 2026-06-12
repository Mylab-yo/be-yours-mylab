"""Cree + termine un Ordre de Fabrication Odoo qui CONSOMME les composants, avec lot fini.

Pattern canonique (Odoo 18, via XML-RPC) valide en prod le 2026-06-12 sur
shampoing volume 200ml (OF MYVO/MO/00002). Voir memory feedback-odoo-mrp-xmlrpc-lot-production.

Pieges evites :
- picked=True sur les move_raw_ids AVANT button_mark_done (sinon composants non preleves).
- JAMAIS skip_consumption=True (annule les move_raw -> produit sans consommer).
- skip_backorder=True uniquement si qty exacte (pas de reliquat voulu).

Idempotence : reutilise un lot fini existant pour ce produit ; ne relance pas si un OF
'done' identique existe deja. Adapter les constantes ci-dessous avant usage.
"""
from _client import execute, create, search, search_read

# --- A PARAMETRER ---
PRODUCT_VARIANT_ID = 2403      # product.product du fini (PAS le template)
BOM_ID = 13                    # mrp.bom du fini
QTY = 150.0                    # quantite a produire
UOM_ID = 1                     # uom du fini (Units)
LOT_NAME = "220A526C"          # n° de lot a poser sur le fini
FINISHED_LOCATION_ID = 47      # MYVO/Stock/Fini
# --------------------


def get_or_create_finished_lot():
    ids = search("stock.lot", [("name", "=", LOT_NAME), ("product_id", "=", PRODUCT_VARIANT_ID)])
    if ids:
        print(f"[lot] existant reutilise id={ids[0]}")
        return ids[0]
    lid = create("stock.lot", {"name": LOT_NAME, "product_id": PRODUCT_VARIANT_ID})
    print(f"[lot] cree id={lid} ({LOT_NAME})")
    return lid


def main():
    lot_id = get_or_create_finished_lot()

    # 1. Creation + confirmation (explose la BoM, reserve, auto-assigne lots composants)
    mo_id = create("mrp.production", {
        "product_id": PRODUCT_VARIANT_ID, "product_qty": QTY,
        "bom_id": BOM_ID, "product_uom_id": UOM_ID,
    })
    execute("mrp.production", "action_confirm", [[mo_id]])

    # 2. Quantite a produire + lot fini
    execute("mrp.production", "write", [[mo_id], {"qty_producing": QTY, "lot_producing_id": lot_id}])

    mo = search_read("mrp.production", [("id", "=", mo_id)],
                     ["name", "move_raw_ids", "move_finished_ids"])[0]

    # 3. PIEGE CLE : marquer les composants comme preleves + aligner dest fini
    execute("stock.move", "write", [mo["move_raw_ids"], {"picked": True}])
    execute("stock.move", "write", [mo["move_finished_ids"], {"location_dest_id": FINISHED_LOCATION_ID}])

    # 4. Terminer (skip_backorder car qty exacte ; surtout PAS skip_consumption)
    execute("mrp.production", "button_mark_done", [[mo_id]], {"context": {"skip_backorder": True}})

    st = search_read("mrp.production", [("id", "=", mo_id)], ["name", "state"])[0]
    p = search_read("product.product", [("id", "=", PRODUCT_VARIANT_ID)], ["name", "qty_available"])[0]
    print(f"[OF] {st['name']} state={st['state']} -> {p['name']} qty_available={p['qty_available']}")


if __name__ == "__main__":
    main()
