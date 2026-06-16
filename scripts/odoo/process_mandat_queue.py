"""Worker : traite les factures en file d'envoi pour le mandat de representation.

Cherche les mail.activity du type "Envoyer mandat de representation" (id=8)
sur account.move, et lance le pipeline d'envoi pour chaque.

Apres envoi reussi : l'activite est marquee 'done' (supprimee + message chatter).
Apres echec : l'activite reste, le chatter loggue l'erreur.

Usage :
    python -m scripts.odoo.process_mandat_queue              # traite tout
    python -m scripts.odoo.process_mandat_queue --dry-run    # liste sans envoyer
    python -m scripts.odoo.process_mandat_queue --limit 5    # max 5 envois
    python -m scripts.odoo.process_mandat_queue --to yoann@mylab-shop.com  # redirige
"""
import argparse
import traceback

from scripts.odoo._client import search_read, execute
from scripts.odoo.send_mandat_representation import process_invoice, ACTIVITY_TYPE_ID_DEFAULT

# Si le setup phase 2 a cree l'activity type avec un autre id, surcharge ici
ACTIVITY_TYPE_ID = ACTIVITY_TYPE_ID_DEFAULT


def main():
    ap = argparse.ArgumentParser(description="Worker file d'envoi mandat de representation")
    ap.add_argument("--dry-run", action="store_true", help="Liste les factures en attente sans envoyer")
    ap.add_argument("--limit", type=int, default=0, help="Max N envois (0 = tout)")
    ap.add_argument("--to", help="Redirige tous les mails vers cette adresse (test)")
    ap.add_argument("--activity-type-id", type=int, default=ACTIVITY_TYPE_ID,
                    help=f"ID du mail.activity.type (defaut {ACTIVITY_TYPE_ID})")
    args = ap.parse_args()

    print(f"=== Worker mandat de representation ===")
    print(f"activity_type_id={args.activity_type_id}, dry_run={args.dry_run}, limit={args.limit}")
    if args.to:
        print(f"!! REDIRECTION tous mails vers {args.to}")
    print()

    activities = search_read(
        "mail.activity",
        [("res_model", "=", "account.move"),
         ("activity_type_id", "=", args.activity_type_id)],
        ["id", "res_id", "summary", "date_deadline", "user_id"],
    )

    if not activities:
        print("(aucune facture en file d'envoi)")
        return

    print(f"-> {len(activities)} activite(s) en attente")
    print()

    todo = activities[:args.limit] if args.limit else activities
    ok, ko = [], []

    for act in todo:
        invoice_id = act["res_id"]
        print("=" * 60)
        print(f"Activity id={act['id']}  invoice_id={invoice_id}  deadline={act['date_deadline']}")
        try:
            result = process_invoice(
                invoice_id, to=args.to, force=False, dry_run=args.dry_run, verbose=True,
            )
            if result["success"] and not args.dry_run:
                # Marquer l'activite comme faite : supprimer + message chatter
                # (action_feedback retourne None et casse OdooMarshaller cote serveur)
                execute("mail.activity", "unlink", [[act["id"]]])
                execute("account.move", "message_post", [[invoice_id]], {
                    "body": (
                        f"<p>Activite <strong>Mandat de representation</strong> realisee.<br/>"
                        f"Mail envoye a {result['recipient']} pour {result['raison_sociale']}.</p>"
                    ),
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_note",
                })
                print(f"  -> activite supprimee + chatter mis a jour")
                ok.append((result["invoice"], result["recipient"]))
            elif result["success"] and args.dry_run:
                print(f"  -> (dry-run, activite conservee)")
                ok.append((result["invoice"], result["recipient"]))
            else:
                err = result.get("error", "unknown")
                print(f"  -> ECHEC: {err}")
                # Log erreur dans le chatter de la facture
                execute("account.move", "message_post", [[invoice_id]], {
                    "body": f"<p><strong>Mandat de representation NON envoye</strong>: {err}</p>",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_note",
                })
                ko.append((result.get("invoice") or f"id={invoice_id}", err))
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  -> EXCEPTION: {err}")
            print(traceback.format_exc())
            try:
                execute("account.move", "message_post", [[invoice_id]], {
                    "body": f"<p><strong>Mandat NON envoye (exception)</strong>: {err}</p>",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_note",
                })
            except Exception:
                pass
            ko.append((f"id={invoice_id}", err))
        print()

    # Resume
    print("=" * 60)
    print(f"RESUME : {len(ok)} OK, {len(ko)} ECHEC, {len(activities) - len(todo)} non traite(s)")
    if ok:
        print()
        print("OK :")
        for inv, rcp in ok:
            print(f"  + {inv} -> {rcp}")
    if ko:
        print()
        print("ECHEC :")
        for inv, err in ko:
            print(f"  - {inv} : {err}")


if __name__ == "__main__":
    main()
