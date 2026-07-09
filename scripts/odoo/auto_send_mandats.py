"""Worker autonome : envoie les mandats de Personne Responsable aux clients ayant
paye le dossier cosmetologique (product.product id=2313).

Poll-based : interroge Odoo pour les factures eligibles non encore servies, genere
+ envoie le mandat (via send_mandat_representation.process_invoice, qui tamponne
x_mandat_sent_at), puis notifie Telegram. Concu pour tourner en cron VPS toutes les 15 min.

Eligibilite :
    move_type in (out_invoice, out_receipt)
    state = posted
    payment_state = paid
    une ligne product_id = 2313
    invoice_date >= MANDAT_AUTO_SINCE   (garde anti-rafale sur l'historique)
    x_mandat_sent_at vide               (idempotence)

Usage:
    python -m scripts.odoo.auto_send_mandats             # envoi reel
    python -m scripts.odoo.auto_send_mandats --dry-run   # liste sans envoyer
    python -m scripts.odoo.auto_send_mandats --limit 10
    python -m scripts.odoo.auto_send_mandats --to yoann@mylab-shop.com  # redirige (test)
"""
import argparse
import os
import traceback
from datetime import datetime

from scripts.odoo._client import search_read
from scripts.odoo.send_mandat_representation import process_invoice, PRODUCT_DOSSIER_ID

# Cutoff d'activation : seules les factures dont invoice_date >= cette date partent
# automatiquement. Empeche le 1er run d'arroser les 5 factures pre-existantes.
MANDAT_AUTO_SINCE = os.environ.get("MANDAT_AUTO_SINCE", "2026-06-29")
FIELD = "x_mandat_sent_at"


def find_eligible(limit=0):
    """Retourne les factures eligibles (voir docstring module)."""
    lines = search_read("account.move.line",
                        [("product_id", "=", PRODUCT_DOSSIER_ID)], ["move_id"])
    move_ids = sorted(set(l["move_id"][0] for l in lines if l.get("move_id")))
    if not move_ids:
        return []
    domain = [
        ("id", "in", move_ids),
        ("move_type", "in", ["out_invoice", "out_receipt"]),
        ("state", "=", "posted"),
        ("payment_state", "=", "paid"),
        ("invoice_date", ">=", MANDAT_AUTO_SINCE),
        (FIELD, "=", False),
    ]
    return search_read("account.move", domain,
                       ["id", "name", "partner_id", "invoice_date"], limit=limit)


def notify_telegram(text):
    """Ping Telegram best-effort. Token + chat_id via env. Ne casse jamais le worker."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        import urllib.request
        import urllib.parse
        data = urllib.parse.urlencode({
            "chat_id": chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"  [telegram] notif KO (non bloquant): {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Envoi automatique des mandats de representation")
    ap.add_argument("--dry-run", action="store_true", help="Liste sans envoyer")
    ap.add_argument("--limit", type=int, default=0, help="Max N envois (0 = tout)")
    ap.add_argument("--to", help="Redirige tous les mails vers cette adresse (test)")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== auto_send_mandats {ts} | cutoff>={MANDAT_AUTO_SINCE} "
          f"dry_run={args.dry_run} limit={args.limit} ===")

    eligible = find_eligible(limit=args.limit)
    if not eligible:
        print("(aucune facture eligible)")
        return

    print(f"-> {len(eligible)} facture(s) eligible(s)")
    ok, ko = [], []
    for inv in eligible:
        iid = inv["id"]
        client = inv["partner_id"][1] if inv.get("partner_id") else "?"
        print("=" * 50)
        print(f"{inv['name']} (id={iid}) client={client} date={inv.get('invoice_date')}")
        try:
            # process_invoice tamponne x_mandat_sent_at lui-meme en cas de succes reel
            res = process_invoice(iid, to=args.to, force=False,
                                  dry_run=args.dry_run, verbose=True)
            if res["success"] and not args.dry_run:
                ok.append((res["invoice"], res["recipient"]))
                notify_telegram(
                    "\U0001F4E7 <b>Mandat envoye automatiquement</b>\n"
                    f"Client : {res.get('raison_sociale') or client}\n"
                    f"Facture : {res['invoice']}\n"
                    f"→ {res['recipient']}"
                )
            elif res["success"] and args.dry_run:
                ok.append((res["invoice"], res.get("recipient")))
            else:
                err = res.get("error", "unknown")
                print(f"  -> ECHEC: {err}")
                ko.append((res.get("invoice") or f"id={iid}", err))
        except (Exception, SystemExit) as e:
            # process_invoice peut lever SystemExit (BaseException) sur cas limite ;
            # on l'isole pour ne pas tuer le run entier.
            err = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  -> EXCEPTION: {err}")
            print(traceback.format_exc())
            ko.append((f"id={iid}", err))

    print("=" * 50)
    print(f"RESUME : {len(ok)} OK, {len(ko)} ECHEC")
    for inv, rcp in ok:
        print(f"  + {inv} -> {rcp}")
    for inv, err in ko:
        print(f"  - {inv} : {err}")
    if ko and not args.dry_run:
        notify_telegram(
            f"⚠️ Mandat auto : {len(ko)} echec(s) au dernier run.\n"
            + "\n".join(f"{i}: {e}" for i, e in ko)
        )


if __name__ == "__main__":
    main()
