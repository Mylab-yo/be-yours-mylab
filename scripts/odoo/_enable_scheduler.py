"""Reactive les crons sauvegardes par _disable_scheduler.py."""
from pathlib import Path
from scripts.odoo._client import write

ids_file = Path(__file__).parent / ".scheduler_ids"
if not ids_file.exists():
    raise SystemExit("Aucun .scheduler_ids - rien a reactiver")

ids = [int(x) for x in ids_file.read_text().strip().split(",") if x]
if not ids:
    print("Fichier .scheduler_ids vide - rien a reactiver")
else:
    write("ir.cron", ids, {"active": True})
    print(f"  [ENABLED] {len(ids)} scheduler(s) reactive(s) (ids={ids})")
ids_file.unlink()
