"""Termine (button_mark_done) les 4 OF vrac shampoing avec un LOT PROVISOIRE.

Les vrai n° de lot ne sont pas connus (recus a reception de la marchandise) mais Odoo
exige un lot pour valider une production d'un produit suivi par lot. On pose donc un lot
placeholder 'A-RECEPTIONNER-2026-07' (un par produit -> un stock.lot est lie a UN produit).
A reception, il suffira de RENOMMER ce lot (stock.lot.name) : le stock reste attache au
meme record, seul le nom change.

Le vrac entre a MYVO/Stock/Bulk (loc 45), emplacement conventionnel du vrac (ou se trouve
deja le lot reel du dejaunisseur), pour rester consommable par le conditionnement.

OF cibles (deja crees + confirmes) :
  MYVO/MO/00018  Bulk shampoing purifiant            200 kg
  MYVO/MO/00019  Bulk shampoing nourrissant          300 kg
  MYVO/MO/00020  Bulk shampoing gel douche           120 kg
  MYVO/MO/00021  Bulk shampoing dejaunisseur platine 150 kg

Idempotent : saute un OF deja 'done' ; reutilise un lot existant (name, product).
Pieges (memory feedback-odoo-mrp-xmlrpc-lot-production) :
  - lot_producing_id obligatoire (fini suivi lot)
  - PAS de move_raw ici (aucune BoM) -> pas de picked=True a poser
  - skip_backorder=True (qty exacte) ; JAMAIS skip_consumption=True
"""
import _client as odoo

LOT_NAME = "A-RECEPTIONNER-2026-07"
BULK_LOCATION_ID = 45  # MYVO/Stock/Bulk

OFS = [
    {"mo_id": 18, "product_id": 2519, "qty": 200.0, "label": "purifiant 200kg"},
    {"mo_id": 19, "product_id": 2514, "qty": 300.0, "label": "nourrissant 300kg"},
    {"mo_id": 20, "product_id": 2521, "qty": 120.0, "label": "gel douche 120kg"},
    {"mo_id": 21, "product_id": 2545, "qty": 150.0, "label": "dejaunisseur 150kg"},
]


def get_or_create_lot(product_id):
    ids = odoo.search("stock.lot", [("name", "=", LOT_NAME), ("product_id", "=", product_id)])
    if ids:
        return ids[0], False
    return odoo.create("stock.lot", {"name": LOT_NAME, "product_id": product_id}), True


def main():
    for cfg in OFS:
        mo = odoo.search_read("mrp.production", [("id", "=", cfg["mo_id"])],
                              ["name", "state", "product_qty", "move_raw_ids",
                               "move_finished_ids"])
        if not mo:
            print(f"[!] OF id={cfg['mo_id']} introuvable, saute")
            continue
        mo = mo[0]
        if mo["state"] == "done":
            print(f"[skip] {mo['name']} ({cfg['label']}) deja done")
            continue
        if mo["state"] not in ("confirmed", "progress", "to_close"):
            print(f"[!] {mo['name']} state={mo['state']} inattendu, saute")
            continue

        lot_id, created = get_or_create_lot(cfg["product_id"])
        print(f"[lot]  {cfg['label']}: lot id={lot_id} '{LOT_NAME}' "
              f"({'cree' if created else 'reutilise'})")

        # Quantite produite + lot fini
        odoo.execute("mrp.production", "write",
                     [[cfg["mo_id"]], {"qty_producing": cfg["qty"], "lot_producing_id": lot_id}])
        # Router l'entree vers Bulk (45)
        odoo.execute("stock.move", "write",
                     [mo["move_finished_ids"], {"location_dest_id": BULK_LOCATION_ID}])
        # Terminer (qty exacte -> pas de backorder ; surtout PAS skip_consumption)
        odoo.execute("mrp.production", "button_mark_done", [[cfg["mo_id"]]],
                     {"context": {"skip_backorder": True}})

        st = odoo.search_read("mrp.production", [("id", "=", cfg["mo_id"])], ["name", "state"])[0]
        print(f"[done] {st['name']} state={st['state']}")

    # Verif finale : quants internes des 4 vrac
    print("\n=== VERIF stock apres validation ===")
    quants = odoo.search_read(
        "stock.quant",
        [("product_id", "in", [c["product_id"] for c in OFS]),
         ("location_id.usage", "=", "internal")],
        ["product_id", "location_id", "quantity", "lot_id"],
    )
    for q in sorted(quants, key=lambda x: x["product_id"][1]):
        lot = q["lot_id"][1] if q.get("lot_id") else "-"
        print(f"  {q['product_id'][1]:<40} {q['location_id'][1]:<18} "
              f"qty={q['quantity']:g} lot={lot}")


if __name__ == "__main__":
    main()
