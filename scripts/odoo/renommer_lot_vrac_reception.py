"""Renomme les lots PROVISOIRES du vrac shampoing avec les vrais n° a reception.

Les 4 vrac sont entres en stock le 2026-07-03 sous le lot placeholder
'A-RECEPTIONNER-2026-07'. A reception de la marchandise, remplir REELS ci-dessous
avec les vrais n° de lot puis lancer ce script : il renomme le stock.lot en place
(le stock ne bouge pas, seul le name change). Cf memory project-of-vrac-shp-lots-provisoires.

Idempotent : saute un lot deja renomme ; garde-fou sur le produit attendu.
Laisser None un produit dont le lot n'est pas encore connu -> il sera saute.
"""
import _client as odoo

PLACEHOLDER = "A-RECEPTIONNER-2026-07"

# lot_id -> (product_id attendu, label, VRAI n° de lot a poser [None = pas encore connu])
REELS = {
    145: (2519, "purifiant 200kg",    None),
    146: (2514, "nourrissant 300kg",  None),
    147: (2521, "gel douche 120kg",   None),
    148: (2545, "dejaunisseur 150kg", None),
}


def main():
    for lot_id, (expected_pid, label, vrai) in REELS.items():
        rec = odoo.search_read("stock.lot", [("id", "=", lot_id)],
                               ["name", "product_id"])
        if not rec:
            print(f"[!] lot id={lot_id} ({label}) introuvable, saute")
            continue
        rec = rec[0]
        pid = rec["product_id"][0] if rec.get("product_id") else None

        if vrai is None:
            print(f"[attente] {label} : vrai lot pas encore renseigne (reste '{rec['name']}')")
            continue
        if pid != expected_pid:
            print(f"[!] {label} : lot id={lot_id} lie au produit {pid}, attendu {expected_pid} -> SAUTE (garde-fou)")
            continue
        if rec["name"] == vrai:
            print(f"[skip] {label} : deja renomme en '{vrai}'")
            continue
        if rec["name"] != PLACEHOLDER:
            print(f"[!] {label} : nom actuel '{rec['name']}' != placeholder attendu -> SAUTE (verifier a la main)")
            continue

        odoo.write("stock.lot", [lot_id], {"name": vrai})
        print(f"[ok]   {label} : '{PLACEHOLDER}' -> '{vrai}'")


if __name__ == "__main__":
    main()
