"""Envoi PREVIEW d'UNE notif tracking vers une adresse de controle (ex: Yoann).
Ne contacte JAMAIS le client, restaure le BL a son etat initial apres coup.

Securite : cree le mail SANS l'envoyer, verifie que le destinataire est bien
l'adresse de preview (sinon supprime le mail + abort), puis envoie.

Usage:
  python -m scripts.odoo.station_preview_send --order S00521 --to yoann@mylab-shop.com
"""
import argparse
import sys
from scripts.odoo._client import search_read, execute
from scripts.odoo.station_notify_tracking import (
    find_file, parse_station, build_plan,
    TEMPLATE_ID, CARRIER_RELAIS, CARRIER_DOMICILE,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", help="n° de commande (S00xxx) ou nom de BL (via fichier Station)")
    ap.add_argument("--picking", help="nom de BL (MYVO/OUT/xxxxx) en direct, sans fichier Station")
    ap.add_argument("--tracking", help="n° de colis a injecter en mode --picking")
    ap.add_argument("--to", required=True, help="adresse de preview (toi)")
    ap.add_argument("--file", help="YYYYMMDD_Expeditions.txt (defaut = le plus recent)")
    args = ap.parse_args()

    if args.picking:
        pk = search_read("stock.picking", [("name", "=", args.picking)],
                         ["id", "name", "origin", "partner_id"], limit=1)
        if not pk:
            sys.exit(f"BL {args.picking} introuvable")
        pk = pk[0]
        rec = {"pid": pk["id"], "bl": pk["name"], "origin": pk.get("origin"),
               "partner": pk["partner_id"][1] if pk.get("partner_id") else "?",
               "parcels": [args.tracking or "10843001999999"], "relay": ""}
    else:
        if not args.order:
            sys.exit("Donne --order (via fichier Station) ou --picking (direct)")
        f = find_file(args.file)
        matched, multi, *_ = build_plan(parse_station(f))
        rec = next((r for r in matched + multi
                    if r.get("origin") == args.order or r["bl"] == args.order), None)
        if not rec:
            sys.exit(f"{args.order} introuvable dans les matchs de {f.name}")

    pid = rec["pid"]
    before = search_read("stock.picking", [("id", "=", pid)],
                         ["carrier_tracking_ref", "carrier_id"])[0]
    print(f"Cible : {rec['bl']} <- {rec['origin']} | colis {rec['parcels']} "
          f"| client {rec['partner']} | PREVIEW -> {args.to}")

    carrier = CARRIER_RELAIS if rec["relay"] else CARRIER_DOMICILE
    execute("stock.picking", "write", [[pid], {
        "carrier_tracking_ref": ",".join(rec["parcels"]), "carrier_id": carrier}])
    try:
        mail_id = execute("mail.template", "send_mail", [TEMPLATE_ID, pid], {
            "force_send": False,
            "email_values": {"email_to": args.to, "recipient_ids": [(5, 0, 0)]}})
        m = search_read("mail.mail", [("id", "=", mail_id)],
                        ["email_to", "recipient_ids", "subject", "attachment_ids"])[0]
        print(f"  mail#{mail_id} | subject={m['subject']!r}")
        print(f"  email_to={m['email_to']!r} | recipient_ids={m['recipient_ids']} "
              f"| PJ={len(m.get('attachment_ids') or [])}")
        leak = bool(m["recipient_ids"]) or (m["email_to"] or "").strip().lower() != args.to.lower()
        if leak:
            execute("mail.mail", "unlink", [[mail_id]])
            sys.exit("ABORT : destinataire inattendu -> mail supprime, RIEN envoye.")
        try:
            execute("mail.mail", "send", [[mail_id]])
        except Exception as e:
            # mail.mail.send() renvoie None -> XML-RPC ne sait pas marshaler None.
            # L'envoi a bien eu lieu cote serveur ; on ignore ce Fault cosmetique.
            if "cannot marshal None" not in str(e):
                raise
        print(f"  -> ENVOYE a {args.to} (le client n'a PAS ete contacte)")
    finally:
        execute("stock.picking", "write", [[pid], {
            "carrier_tracking_ref": before.get("carrier_tracking_ref") or False,
            "carrier_id": before["carrier_id"][0] if before.get("carrier_id") else False}])
        print(f"  BL {rec['bl']} restaure a l'etat initial (ref/carrier).")


if __name__ == "__main__":
    main()
