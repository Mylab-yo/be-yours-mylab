"""Regle le 'Tracking Link' sur les 8 carriers DPD Odoo (rend le n° de suivi
cliquable dans le mail d'expedition). Idempotent.

Placeholder Odoo = <shipmenttrackingnumber>."""
from scripts.odoo._client import search_read, write

DPD_IDS = [11, 12, 13, 14, 15, 16, 17, 18]
URL = "https://www.dpd.fr/trace/<shipmenttrackingnumber>"

carriers = search_read("delivery.carrier", [("id", "in", DPD_IDS)],
    ["id", "name", "tracking_url"])
to_update = [c["id"] for c in carriers if (c.get("tracking_url") or "") != URL]

if to_update:
    write("delivery.carrier", to_update, {"tracking_url": URL})
    print(f"MAJ tracking_url sur {len(to_update)} carriers : {to_update}")
else:
    print("Deja a jour, rien a faire.")

print("\nEtat final :")
for c in search_read("delivery.carrier", [("id", "in", DPD_IDS)],
        ["id", "name", "tracking_url"]):
    print(f"  id={c['id']:>2}  {c['name']:<45} -> {c.get('tracking_url')!r}")
