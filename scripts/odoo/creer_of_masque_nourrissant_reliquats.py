"""Cree en BROUILLON les OF pour combler les reliquats Masque Nourrissant.

- 200ml x102 (BoM 25, produit 2357)  -> fin reliquat Cendree S00493
- 400ml x36  (BoM 26, produit 2439)  -> Holicare 24 + La Maison du Coloriste 6 + Charly 6

Finis suivis par LOT : le lot sera pose au moment de la production (pas en brouillon).
Composants a 0 en stock : l'OF NE PEUT PAS etre reserve/termine tant que le vrac +
pots + capots ne sont pas approvisionnes. On s'arrete donc a l'etat 'draft'.

Idempotent : ne recree pas si un OF non annule (draft/confirmed) existe deja
pour ce produit a cette quantite.
"""
from _client import execute, create, search_read

OFS = [
    {"label": "200ml x102", "product_id": 2357, "bom_id": 25, "qty": 102.0},
    {"label": "400ml x36",  "product_id": 2439, "bom_id": 26, "qty": 36.0},
]


def uom_of(product_id):
    return search_read("product.product", [("id", "=", product_id)], ["uom_id"])[0]["uom_id"][0]


def main():
    for cfg in OFS:
        # Idempotence : OF vivant deja present pour ce produit + qty ?
        existing = search_read(
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

        mo_id = create("mrp.production", {
            "product_id": cfg["product_id"],
            "product_qty": cfg["qty"],
            "bom_id": cfg["bom_id"],
            "product_uom_id": uom_of(cfg["product_id"]),
        })
        mo = search_read("mrp.production", [("id", "=", mo_id)],
                         ["name", "state", "product_qty", "move_raw_ids"])[0]
        print(f"[cree] {cfg['label']} -> {mo['name']} (id={mo_id}) state={mo['state']} qty={mo['product_qty']:g}")
        # composants exploses ?
        if mo["move_raw_ids"]:
            raws = search_read("stock.move", [("id", "in", mo["move_raw_ids"])],
                               ["product_id", "product_uom_qty"])
            for r in raws:
                print(f"        consomme {r['product_uom_qty']:g} x {r['product_id'][1]}")
        else:
            print("        (composants non exploses en brouillon -> s'ouvriront a la confirmation)")


if __name__ == "__main__":
    main()
