"""Desactive le cron 'Run Scheduler' d'Odoo. Sauvegarde l'ID dans un fichier
pour pouvoir le reactiver ensuite via _enable_scheduler.py."""
from pathlib import Path
from scripts.odoo._client import search_read, write

# Trouver le cron du scheduler. En Odoo 18, il s'appelle typiquement "Run Scheduler"
# (parfois "Stock: Schedulers" ou variantes localisees)
candidates = ["Run Scheduler", "Stock: Schedulers", "Inventory: Run Scheduler",
              "Lancer le planificateur", "Stock : Planificateurs",
              "Procurement: run scheduler", "Approvisionnements : lancer le planificateur"]
crons = search_read("ir.cron", [
    ("cron_name", "in", candidates),
], ["id", "cron_name", "active"])

if not crons:
    print("ERROR: scheduler cron introuvable. Liste tous les crons actifs avec :")
    print("  python -c \"from scripts.odoo._client import search_read; [print(c) for c in search_read('ir.cron', [('active','=',True)], ['id','cron_name'])]\"")
    raise SystemExit(1)

ids_to_save = []
for c in crons:
    if c["active"]:
        write("ir.cron", [c["id"]], {"active": False})
        print(f"  [DISABLED] {c['cron_name']} (id={c['id']})")
        ids_to_save.append(c["id"])
    else:
        print(f"  [ALREADY-OFF] {c['cron_name']} (id={c['id']})")

Path(__file__).parent.joinpath(".scheduler_ids").write_text(",".join(map(str, ids_to_save)))
print(f"\nIDs sauvegardes dans .scheduler_ids ({len(ids_to_save)} crons disables). Reactiver avec _enable_scheduler.py")
