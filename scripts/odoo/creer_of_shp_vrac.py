"""Cree + CONFIRME 4 OF de vrac shampoing (mrp.production), quantites en kg.

Demande Yoann :
  SHP PURIFIANT      200 kg  -> Bulk shampoing purifiant           (variant 2519)
  SHP NOURRISSANT    300 kg  -> Bulk shampoing nourrissant         (variant 2514)
  SHP GEL DOUCHE     120 kg  -> Bulk shampoing gel douche          (variant 2521)
  SHP DEJAUNISSEUR   150 kg  -> Bulk shampoing dejaunisseur platine(variant 2545)

Ces produits vrac n'ont AUCUNE nomenclature (BoM) : l'OF ne consomme aucune matiere
premiere. On cree l'OF puis on l'amene en etat 'confirmed' (action_confirm). Rien
n'entre en stock tant que l'OF n'est pas marque 'done' manuellement dans Odoo.

Idempotent : ne recree pas si un OF vivant (draft/confirmed/progress) existe deja
pour ce produit a cette quantite.
"""
import _client as odoo

OFS = [
    {"label": "SHP PURIFIANT 200kg",    "product_id": 2519, "qty": 200.0},
    {"label": "SHP NOURRISSANT 300kg",  "product_id": 2514, "qty": 300.0},
    {"label": "SHP GEL DOUCHE 120kg",   "product_id": 2521, "qty": 120.0},
    {"label": "SHP DEJAUNISSEUR 150kg", "product_id": 2545, "qty": 150.0},
]


def uom_of(product_id):
    return odoo.search_read("product.product", [("id", "=", product_id)],
                            ["uom_id"])[0]["uom_id"][0]


def main():
    for cfg in OFS:
        existing = odoo.search_read(
            "mrp.production",
            [("product_id", "=", cfg["product_id"]),
             ("product_qty", "=", cfg["qty"]),
             ("state", "in", ["draft", "confirmed", "progress"])],
            ["name", "state"],
        )
        if existing:
            e = existing[0]
            print(f"[skip] {cfg['label']} : OF deja present {e['name']} (state={e['state']})")
            continue

        mo_id = odoo.create("mrp.production", {
            "product_id": cfg["product_id"],
            "product_qty": cfg["qty"],
            "product_uom_id": uom_of(cfg["product_id"]),
        })
        mo = odoo.search_read("mrp.production", [("id", "=", mo_id)],
                              ["name", "state", "product_qty"])[0]
        print(f"[cree]  {cfg['label']} -> {mo['name']} (id={mo_id}) state={mo['state']} "
              f"qty={mo['product_qty']:g} kg")

        # Confirmer
        try:
            odoo.execute("mrp.production", "action_confirm", [[mo_id]])
            mo2 = odoo.search_read("mrp.production", [("id", "=", mo_id)],
                                   ["name", "state", "move_raw_ids", "move_finished_ids"])[0]
            print(f"        -> confirme : state={mo2['state']} "
                  f"(composants={len(mo2['move_raw_ids'])}, finis={len(mo2['move_finished_ids'])})")
        except Exception as exc:
            print(f"        [!] action_confirm a echoue, OF laisse en draft : {exc}")


if __name__ == "__main__":
    main()
