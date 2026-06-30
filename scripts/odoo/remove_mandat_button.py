"""Retire le bouton/file d'attente LEGACY "Envoyer mandat de representation".

Contexte : deux mecaniques d'envoi du mandat coexistaient :
  - LIVE  : worker VPS auto_send_mandats.py (cron */15) + CLI send_mandat_representation.py
  - MORT  : bouton Odoo (ir.actions.server) -> cree une mail.activity -> cense etre
            draine par process_mandat_queue.py, JAMAIS planifie nulle part.

Le bouton mettait donc les mandats "en liste d'attente" sans jamais les envoyer.
Decision (2026-06-30) : on supprime la mecanique morte. Ce script enleve d'Odoo :
  1. les mail.activity ouvertes du type mandat (file fantome)
  2. l'ir.actions.server "Envoyer mandat de representation au client" (= le bouton)
  3. le mail.activity.type "Envoyer mandat de representation"

Idempotent : si un element est deja absent, il est simplement saute.

Usage :
    python -m scripts.odoo.remove_mandat_button --dry-run   # liste sans rien supprimer
    python -m scripts.odoo.remove_mandat_button             # supprime
"""
import argparse
from scripts.odoo._client import search_read, unlink

ACTIVITY_TYPE_NAME = "Envoyer mandat de representation"
SERVER_ACTION_NAME = "Envoyer mandat de representation au client"


def main():
    ap = argparse.ArgumentParser(description="Retire le bouton/file d'attente mandat legacy")
    ap.add_argument("--dry-run", action="store_true", help="Liste sans supprimer")
    args = ap.parse_args()
    dry = args.dry_run
    tag = "[DRY-RUN] " if dry else ""

    # --- 1. mail.activity ouvertes du type mandat ---
    atypes = search_read("mail.activity.type", [("name", "=", ACTIVITY_TYPE_NAME)], ["id", "name"])
    atype_ids = [a["id"] for a in atypes]
    print(f"mail.activity.type '{ACTIVITY_TYPE_NAME}': {atype_ids or '(absent)'}")

    if atype_ids:
        acts = search_read("mail.activity",
                           [("activity_type_id", "in", atype_ids)],
                           ["id", "res_model", "res_id", "summary"])
        print(f"  -> {len(acts)} activite(s) en file a purger")
        for a in acts:
            print(f"     activity id={a['id']} {a['res_model']}#{a['res_id']} : {a.get('summary')}")
        if acts and not dry:
            unlink("mail.activity", [a["id"] for a in acts])
            print(f"  {tag}{len(acts)} activite(s) supprimee(s)")

    # --- 2. ir.actions.server (le bouton dans le menu Action) ---
    actions = search_read("ir.actions.server", [("name", "=", SERVER_ACTION_NAME)], ["id", "name"])
    print(f"\nir.actions.server '{SERVER_ACTION_NAME}': {[a['id'] for a in actions] or '(absent)'}")
    if actions and not dry:
        unlink("ir.actions.server", [a["id"] for a in actions])
        print(f"  {tag}bouton supprime ({len(actions)} action(s))")

    # --- 3. mail.activity.type ---
    if atype_ids and not dry:
        unlink("mail.activity.type", atype_ids)
        print(f"\n{tag}mail.activity.type supprime ({atype_ids})")

    print()
    if dry:
        print("=== DRY-RUN : rien supprime. Relance sans --dry-run pour appliquer. ===")
    else:
        print("=== OK : bouton + file d'attente legacy retires. ===")
        print("Envoi du mandat = worker VPS auto (factures >=2026-06-29) + CLI "
              "send_mandat_representation.py pour le reste.")


if __name__ == "__main__":
    main()
